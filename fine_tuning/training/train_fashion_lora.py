"""
Fashion Stable Diffusion LoRA Fine-Tuning
===========================================
Fine-tune Stable Diffusion model on fashion dataset with augmentations
Uses LoRA (Low-Rank Adaptation) for efficient training
"""

import os
import sys
import json
import csv
import random
from pathlib import Path
from typing import List, Tuple, Dict
import argparse
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from transformers import CLIPTextModel, CLIPTokenizer
from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler
from diffusers.optimization import get_scheduler
from peft import LoraConfig, get_peft_model
from accelerate import Accelerator
from tqdm import tqdm
from torch.utils.data import random_split
import re

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Optional wandb import
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False

class FashionDataset(Dataset):
    """Dataset for fashion images and captions with augmentations"""
    
    def __init__(self, data_root: str, captions_root: str, image_size: int = 512, 
                 augment_level: str = "normal"):
        """
        Args:
            data_root: Path to image data (data_backup/)
            captions_root: Path to caption CSV files (captions/)
            image_size: Target image size for training
            augment_level: "none", "normal", or "strong"
        """
        self.data_root = Path(data_root)
        self.captions_root = Path(captions_root)
        self.image_size = image_size
        self.augment_level = augment_level
        
        # Load all image-caption pairs
        self.image_caption_pairs = self._load_dataset()
        
        # Base transforms
        self.base_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])  # Normalize to [-1, 1]
        ])
        
        print(f"Loaded {len(self.image_caption_pairs)} image-caption pairs")
        print(f"Augmentation level: {augment_level}")
    
    def _load_dataset(self) -> List[Tuple[str, str]]:
        """Load all image paths and their corresponding captions"""
        pairs = []
        categories = ["Summer_Men", "Summer_Women", "Winter_Men", "Winter_Women"]
        
        for category in categories:
            # Load captions from CSV
            csv_file = self.captions_root / f"captions_{category}.csv"
            if not csv_file.exists():
                print(f"Warning: {csv_file} not found, skipping {category}")
                continue
            
            captions_dict = {}
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        filename = row['filename']
                        caption = row['caption']
                        captions_dict[filename] = caption
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
                continue
            
            # Find corresponding images
            season, gender = category.split('_')
            image_dir = self.data_root / season / gender
            
            if not image_dir.exists():
                print(f"Warning: {image_dir} not found, skipping {category}")
                continue
            
            # Match images with captions
            for image_file in image_dir.glob("*.jpg"):
                if image_file.name in captions_dict:
                    pairs.append((str(image_file), captions_dict[image_file.name]))
        
        return pairs
    
    def _apply_augmentation(self, image: Image.Image) -> Image.Image:
        """Apply random augmentations based on level"""
        if self.augment_level == "none":
            return image
        
        # Determine augmentation strength
        if self.augment_level == "normal":
            rotation_range = 15
            brightness_range = 0.2
            contrast_range = 0.15
            add_noise = False
            add_blur = False
        elif self.augment_level == "strong":
            rotation_range = 30
            brightness_range = 0.4
            contrast_range = 0.3
            add_noise = True
            add_blur = True
        else:
            return image
        
        # Apply random rotation
        if random.random() < 0.5:
            angle = random.uniform(-rotation_range, rotation_range)
            image = image.rotate(angle, expand=False, fillcolor=(255, 255, 255))
        
        # Apply brightness adjustment
        if random.random() < 0.5:
            factor = random.uniform(1 - brightness_range, 1 + brightness_range)
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(factor)
        
        # Apply contrast adjustment
        if random.random() < 0.5:
            factor = random.uniform(1 - contrast_range, 1 + contrast_range)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(factor)
        
        # Add noise (strong augmentation only)
        if add_noise and random.random() < 0.3:
            np_image = np.array(image)
            noise = np.random.normal(0, 10, np_image.shape).astype(np.uint8)
            np_image = np.clip(np_image + noise, 0, 255)
            image = Image.fromarray(np_image)
        
        # Add blur (strong augmentation only)
        if add_blur and random.random() < 0.2:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return image
    
    def __len__(self):
        return len(self.image_caption_pairs)
    
    def __getitem__(self, idx):
        image_path, caption = self.image_caption_pairs[idx]
        
        # Load and augment image
        try:
            image = Image.open(image_path).convert('RGB')
            image = self._apply_augmentation(image)
            image_tensor = self.base_transform(image)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a black image as fallback
            image_tensor = torch.zeros(3, self.image_size, self.image_size)
        
        return {
            "pixel_values": image_tensor,
            "caption": caption,
            "image_path": image_path
        }

class FashionLoRATrainer:
    """LoRA trainer for fashion Stable Diffusion model"""
    
    def __init__(self, config: Dict, resume_from_checkpoint=None):
        self.config = config
        self.start_epoch = 0
        # Enable mixed precision training for better performance and memory efficiency
        kwargs = {}
        if self.config.get("mixed_precision", "fp16") in ["fp16", "bf16"]:
            kwargs["mixed_precision"] = self.config.get("mixed_precision", "fp16")
        self.accelerator = Accelerator(**kwargs)
        
        # Initialize models
        self._load_models(resume_from_checkpoint)
        
        # Setup LoRA and get starting epoch
        checkpoint_epoch = self._setup_lora()
        
        # Adjust total epochs to continue training beyond checkpoint
        if checkpoint_epoch > 0 and self.config["epochs"] <= checkpoint_epoch:
            # If resuming and total epochs <= checkpoint epoch, train additional epochs
            additional_epochs = max(5, self.config.get("additional_epochs", 5))
            self.config["epochs"] = checkpoint_epoch + additional_epochs
            print(f"[INFO] Training will continue for {additional_epochs} additional epochs (total: {self.config['epochs']})")
        else:
            self.start_epoch = checkpoint_epoch
        
        print(f"Training on device: {self.accelerator.device}")
        if kwargs.get("mixed_precision"):
            print(f"Mixed precision: {kwargs['mixed_precision']}")
    
    def _load_models(self, resume_from_checkpoint=None):
        """Load Stable Diffusion components"""
        model_id = self.config["model_id"]
        print(f"Loading models from: {model_id}")
        
        # Load models
        self.tokenizer = CLIPTokenizer.from_pretrained(
            model_id, subfolder="tokenizer"
        )
        self.text_encoder = CLIPTextModel.from_pretrained(
            model_id, subfolder="text_encoder"
        )
        self.vae = AutoencoderKL.from_pretrained(
            model_id, subfolder="vae"
        )
        self.unet = UNet2DConditionModel.from_pretrained(
            model_id, subfolder="unet"
        )
        
        # Enable gradient checkpointing for memory efficiency
        if hasattr(self.unet, 'enable_gradient_checkpointing'):
            self.unet.enable_gradient_checkpointing()
        if hasattr(self.text_encoder, 'enable_gradient_checkpointing'):
            self.text_encoder.gradient_checkpointing_enable()
        self.noise_scheduler = DDPMScheduler.from_pretrained(
            model_id, subfolder="scheduler"
        )
        
        # Freeze base models
        self.vae.requires_grad_(False)
        self.text_encoder.requires_grad_(False)
        self.unet.requires_grad_(False)
        
        # Store resume checkpoint path
        self.resume_from_checkpoint = resume_from_checkpoint
        
        # VAE will be moved to device by accelerator.prepare()
    
    def _setup_lora(self, subsequent_epochs=0):
        """Setup LoRA adapters for UNet and Text Encoder"""
        # If resuming, load LoRA weights first
        if self.resume_from_checkpoint:
            checkpoint_path = Path(self.resume_from_checkpoint)
            unet_lora_path = checkpoint_path / "unet_lora"
            text_encoder_lora_path = checkpoint_path / "text_encoder_lora"
            
            if unet_lora_path.exists() and text_encoder_lora_path.exists():
                print(f"Loading LoRA weights from checkpoint...")
                # Load LoRA weights directly using PeftModel.from_pretrained
                from peft import PeftModel
                
                # Load LoRA adapters directly on base models
                self.unet = PeftModel.from_pretrained(self.unet, unet_lora_path)
                self.text_encoder = PeftModel.from_pretrained(self.text_encoder, text_encoder_lora_path)
                
                # Ensure LoRA parameters have gradients enabled
                for name, param in self.unet.named_parameters():
                    if 'lora' in name.lower():
                        param.requires_grad = True
                for name, param in self.text_encoder.named_parameters():
                    if 'lora' in name.lower():
                        param.requires_grad = True
                
                print(f"[OK] Loaded LoRA weights from checkpoint")
                # Get epoch number from checkpoint
                if "checkpoint-final" in str(checkpoint_path):
                    config_file = checkpoint_path / "training_config.json"
                    if config_file.exists():
                        with open(config_file) as f:
                            checkpoint_config = json.load(f)
                            epoch_num = checkpoint_config.get("epochs", 10)
                else:
                    try:
                        epoch_num = int(checkpoint_path.name.split("-")[1])
                    except:
                        epoch_num = 10
                
                print(f"   Continuing from epoch {epoch_num + 1}")
                return epoch_num
        
        # LoRA config for UNet
        unet_lora_config = LoraConfig(
            r=self.config["lora_rank"],
            lora_alpha=self.config["lora_alpha"],
            target_modules=[
                "to_k", "to_q", "to_v", "to_out.0",
                "proj_in", "proj_out",
                "ff.net.0.proj", "ff.net.2"
            ],
            lora_dropout=self.config["lora_dropout"],
        )
        
        # LoRA config for Text Encoder
        text_encoder_lora_config = LoraConfig(
            r=self.config["lora_rank"],
            lora_alpha=self.config["lora_alpha"],
            target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
            lora_dropout=self.config["lora_dropout"],
        )
        
        # Apply LoRA to models
        self.unet = get_peft_model(self.unet, unet_lora_config)
        self.text_encoder = get_peft_model(self.text_encoder, text_encoder_lora_config)
        
        print(f"LoRA setup complete - Rank: {self.config['lora_rank']}, Alpha: {self.config['lora_alpha']}")
        return 0
    
    def _encode_text(self, captions: List[str]):
        """Encode text captions using CLIP text encoder"""
        inputs = self.tokenizer(
            captions,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt"
        )
        
        # Remove torch.no_grad() to allow LoRA gradients to flow through text encoder
        # Since we're training LoRA adapters on text encoder, we need gradients
        text_embeddings = self.text_encoder(inputs.input_ids.to(self.accelerator.device))[0]
        
        return text_embeddings
    
    def _clean_caption(self, caption: str) -> str:
        """Clean and validate caption text"""
        # Remove weird characters but keep basic punctuation
        caption = re.sub(r'[^\w\s\.,\!\?\-\'\(\)]', '', caption)
        # Remove extra whitespace
        caption = ' '.join(caption.split())
        # Ensure minimum length
        if len(caption) < 5:
            return caption + " fashion clothing"
        return caption
    
    def _generate_sample_images(self, epoch: int, step: int):
        """Generate sample images during training for visual evaluation"""
        if not self.config.get("generate_samples", True):
            return
        
        sample_interval = self.config.get("sample_interval", 500)  # Every N steps
        if step % sample_interval != 0 or step == 0:
            return
        
        try:
            # Use only on main process
            if not self.accelerator.is_main_process:
                return
            
            # Test prompts for evaluation
            test_prompts = [
                "pakistani men's shalwar kameez, traditional eastern clothing",
                "women's eastern wear, summer fashion",
                "winter kurta with embroidery, elegant style"
            ]
            
            # Note: Full pipeline generation requires loading inference pipeline
            # This is a placeholder - full implementation would load pipeline with current LoRA weights
            print(f"[Sample Generation] Epoch {epoch}, Step {step}: Would generate samples for prompts")
            if self.config.get("use_wandb", False) and WANDB_AVAILABLE:
                wandb.log({
                    "sample_generation_step": step,
                    "sample_epoch": epoch
                })
        except Exception as e:
            print(f"Warning: Sample generation failed: {e}")
    
    def _validate(self, val_dataloader: DataLoader) -> float:
        """Run validation and return validation loss"""
        self.unet.eval()
        self.text_encoder.eval()
        
        total_val_loss = 0
        val_steps = 0
        
        with torch.no_grad():
            for batch in val_dataloader:
                # Encode images to latent space
                pixel_values = batch["pixel_values"].to(self.accelerator.device)
                with torch.no_grad():
                    latents = self.vae.encode(pixel_values).latent_dist.sample()
                    latents = latents * self.vae.config.scaling_factor
                
                # Add noise
                noise = torch.randn_like(latents)
                timesteps = torch.randint(
                    0, self.noise_scheduler.config.num_train_timesteps,
                    (latents.shape[0],), device=latents.device
                ).long()
                noisy_latents = self.noise_scheduler.add_noise(latents, noise, timesteps)
                
                # Encode text
                text_embeddings = self._encode_text(batch["caption"])
                
                # Predict noise
                noise_pred = self.unet(noisy_latents, timesteps, text_embeddings).sample
                
                # Calculate loss
                loss = F.mse_loss(noise_pred, noise, reduction="mean")
                total_val_loss += loss.item()
                val_steps += 1
        
        avg_val_loss = total_val_loss / val_steps if val_steps > 0 else 0
        return avg_val_loss
    
    def train(self, train_dataloader: DataLoader, val_dataloader: DataLoader = None):
        """Main training loop with optional validation"""
        # Setup optimizer and scheduler
        # Only optimize trainable parameters (LoRA adapters that require grad)
        trainable_params = []
        
        # Collect only parameters that require gradients
        for param in self.unet.parameters():
            if param.requires_grad:
                trainable_params.append(param)
        
        for param in self.text_encoder.parameters():
            if param.requires_grad:
                trainable_params.append(param)
        
        if len(trainable_params) == 0:
            raise ValueError("No trainable parameters found! Check LoRA setup.")
        
        print(f"Training {len(trainable_params)} parameter groups")
        optimizer = torch.optim.AdamW(
            trainable_params,
            lr=self.config["learning_rate"],
            weight_decay=self.config["weight_decay"]
        )
        
        lr_scheduler = get_scheduler(
            self.config["lr_scheduler"],
            optimizer=optimizer,
            num_warmup_steps=self.config["warmup_steps"],
            num_training_steps=len(train_dataloader) * self.config["epochs"]
        )
        
        # Prepare for distributed training
        # Include VAE in prepare list to ensure it's on the correct device
        prepare_list = [self.unet, self.text_encoder, self.vae, optimizer, train_dataloader, lr_scheduler]
        if val_dataloader is not None:
            prepare_list.append(val_dataloader)
        
        prepared = self.accelerator.prepare(*prepare_list)
        self.unet, self.text_encoder, self.vae, optimizer, train_dataloader, lr_scheduler = prepared[:6]
        if val_dataloader is not None:
            val_dataloader = prepared[6]
        
        # Training loop
        total_epochs = self.config["epochs"]
        start_epoch = self.start_epoch
        print(f"Starting training for {total_epochs} total epochs (starting from epoch {start_epoch + 1})...")
        
        if start_epoch >= total_epochs:
            print(f"[WARNING] Already trained {start_epoch} epochs. Total epochs is {total_epochs}.")
            print(f"   No new epochs to train. Increase --epochs to continue training.")
            return
        
        for epoch in range(start_epoch, total_epochs):
            self.unet.train()
            self.text_encoder.train()
            
            total_loss = 0
            progress_bar = tqdm(train_dataloader, desc=f"Epoch {epoch+1}/{self.config['epochs']}")
            
            for step, batch in enumerate(progress_bar):
                with self.accelerator.accumulate(self.unet):
                    # Encode images to latent space
                    pixel_values = batch["pixel_values"].to(self.accelerator.device)
                    with torch.no_grad():
                        latents = self.vae.encode(pixel_values).latent_dist.sample()
                        latents = latents * self.vae.config.scaling_factor
                    
                    # Add noise to latents
                    noise = torch.randn_like(latents)
                    timesteps = torch.randint(
                        0, self.noise_scheduler.config.num_train_timesteps, 
                        (latents.shape[0],), device=latents.device
                    ).long()
                    noisy_latents = self.noise_scheduler.add_noise(latents, noise, timesteps)
                    
                    # Clean and encode text
                    cleaned_captions = [self._clean_caption(cap) for cap in batch["caption"]]
                    text_embeddings = self._encode_text(cleaned_captions)
                    
                    # Predict noise
                    noise_pred = self.unet(noisy_latents, timesteps, text_embeddings).sample
                    
                    # Calculate loss
                    loss = F.mse_loss(noise_pred, noise, reduction="mean")
                    
                    # Backward pass
                    self.accelerator.backward(loss)
                    
                    if self.accelerator.sync_gradients:
                        self.accelerator.clip_grad_norm_(
                            list(self.unet.parameters()) + list(self.text_encoder.parameters()),
                            self.config["max_grad_norm"]
                        )
                    
                    optimizer.step()
                    lr_scheduler.step()
                    optimizer.zero_grad()
                
                # Update progress
                total_loss += loss.detach().item()
                
                # Generate sample images periodically
                self._generate_sample_images(epoch, step)
                
                progress_bar.set_postfix({
                    "loss": f"{loss.item():.4f}",
                    "avg_loss": f"{total_loss/(step+1):.4f}",
                    "lr": f"{lr_scheduler.get_last_lr()[0]:.2e}"
                })
                
                # Log to wandb
                if self.config.get("use_wandb", False) and WANDB_AVAILABLE:
                    wandb.log({
                        "train_loss": loss.item(),
                        "learning_rate": lr_scheduler.get_last_lr()[0],
                        "epoch": epoch,
                        "step": step
                    })
            
            # Run validation
            avg_val_loss = None
            if val_dataloader is not None:
                avg_val_loss = self._validate(val_dataloader)
                print(f"Epoch {epoch+1} - Train Loss: {total_loss/len(train_dataloader):.4f}, Val Loss: {avg_val_loss:.4f}")
                
                if self.config.get("use_wandb", False) and WANDB_AVAILABLE:
                    wandb.log({
                        "val_loss": avg_val_loss,
                        "epoch": epoch
                    })
            else:
                print(f"Epoch {epoch+1} completed - Average Loss: {total_loss/len(train_dataloader):.4f}")
            
            # Save checkpoint
            if (epoch + 1) % self.config["save_every"] == 0:
                self.save_checkpoint(epoch + 1)
        
        # Save final model
        self.save_checkpoint("final")
        print("Training completed!")
    
    def save_checkpoint(self, epoch):
        """Save LoRA weights"""
        output_dir = Path(self.config["output_dir"]) / f"checkpoint-{epoch}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save LoRA weights
        self.unet.save_pretrained(output_dir / "unet_lora")
        self.text_encoder.save_pretrained(output_dir / "text_encoder_lora")
        
        # Save training config
        with open(output_dir / "training_config.json", "w") as f:
            json.dump(self.config, f, indent=2)
        
        print(f"Checkpoint saved to {output_dir}")

class AugmentedFashionDataset(Dataset):
    """Dataset wrapper that uses pre-loaded image-caption pairs"""
    def __init__(self, pairs, image_size=512):
        self.image_caption_pairs = pairs
        self.image_size = image_size
        self.augment_level = "mixed"  # Mixed augmentation
        
        # Initialize transforms
        self.base_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])
    
    def __len__(self):
        return len(self.image_caption_pairs)
    
    def _apply_augmentation(self, image: Image.Image) -> Image.Image:
        """Apply random augmentations - reuse logic from FashionDataset"""
        # Just return image as-is since augmentation was done during dataset creation
        return image
    
    def __getitem__(self, idx):
        image_path, caption = self.image_caption_pairs[idx]
        
        # Load and process image
        try:
            image = Image.open(image_path).convert('RGB')
            image = self._apply_augmentation(image)
            image_tensor = self.base_transform(image)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a black image as fallback
            image_tensor = torch.zeros(3, self.image_size, self.image_size)
        
        return {
            "pixel_values": image_tensor,
            "caption": caption,
            "image_path": image_path
        }

def create_augmented_dataset(data_root: str, captions_root: str, output_dir: str, 
                           target_multiplier: int = 3):
    """Create augmented dataset with multiple variants of each image"""
    print(f"Creating augmented dataset (x{target_multiplier})...")
    
    # Create datasets with different augmentation levels
    datasets = []
    
    # Original dataset (no augmentation)
    datasets.append(FashionDataset(data_root, captions_root, augment_level="none"))
    
    # Normal augmentation dataset
    if target_multiplier >= 2:
        datasets.append(FashionDataset(data_root, captions_root, augment_level="normal"))
    
    # Strong augmentation dataset
    if target_multiplier >= 3:
        datasets.append(FashionDataset(data_root, captions_root, augment_level="strong"))
    
    # Combine datasets
    combined_pairs = []
    for dataset in datasets:
        combined_pairs.extend(dataset.image_caption_pairs)
    
    print(f"Total augmented samples: {len(combined_pairs)}")
    return combined_pairs

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Stable Diffusion on Fashion Dataset")
    parser.add_argument("--data_root", type=str, default="data_backup", help="Path to image data")
    parser.add_argument("--captions_root", type=str, default="captions", help="Path to caption CSV files")
    parser.add_argument("--output_dir", type=str, default="models/fashion_lora", help="Output directory for trained model")
    parser.add_argument("--model_id", type=str, default="prompthero/openjourney", help="Base model to fine-tune")
    parser.add_argument("--batch_size", type=int, default=4, help="Training batch size")
    parser.add_argument("--epochs", type=int, default=20, help="Total number of training epochs (will continue from checkpoint if resuming)")
    parser.add_argument("--learning_rate", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--augment_multiplier", type=int, default=2, help="Dataset augmentation multiplier")
    parser.add_argument("--use_wandb", action="store_true", help="Use Weights & Biases for logging")
    parser.add_argument("--val_split", type=float, default=0.1, help="Validation split ratio (0.1 = 10%%)")
    parser.add_argument("--mixed_precision", type=str, default="fp16", choices=["no", "fp16", "bf16"], help="Mixed precision training")
    parser.add_argument("--generate_samples", type=lambda x: x.lower() in ['true', '1', 'yes'], default=True, help="Generate sample images during training (default: True)")
    parser.add_argument("--no_generate_samples", action="store_false", dest="generate_samples", help="Disable sample generation")
    parser.add_argument("--sample_interval", type=int, default=500, help="Generate samples every N steps")
    parser.add_argument("--resume_from", type=str, default=None, help="Resume from checkpoint directory (auto-detects latest if not specified)")
    args = parser.parse_args()
    
    # Find latest checkpoint if resuming
    resume_from_checkpoint = args.resume_from
    if resume_from_checkpoint is None:
        output_path = Path(args.output_dir)
        if output_path.exists():
            checkpoints = []
            for checkpoint_dir in output_path.iterdir():
                if checkpoint_dir.is_dir() and checkpoint_dir.name.startswith("checkpoint-"):
                    try:
                        if checkpoint_dir.name == "checkpoint-final":
                            config_file = checkpoint_dir / "training_config.json"
                            if config_file.exists():
                                with open(config_file) as f:
                                    config = json.load(f)
                                    epoch_num = config.get("epochs", 10)
                                    checkpoints.append((epoch_num, checkpoint_dir))
                        else:
                            epoch_num = int(checkpoint_dir.name.split("-")[1])
                            checkpoints.append((epoch_num, checkpoint_dir))
                    except (ValueError, IndexError):
                        continue
            
            if checkpoints:
                checkpoints.sort(key=lambda x: x[0], reverse=True)
                resume_from_checkpoint = str(checkpoints[0][1])
                print(f"[CHECKPOINT] Found existing checkpoint: {resume_from_checkpoint}")
                print(f"   Will resume training from epoch {checkpoints[0][0] + 1}")
    
    # Training configuration
    config = {
        "model_id": args.model_id,
        "output_dir": args.output_dir,
        "batch_size": args.batch_size,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "weight_decay": 1e-2,
        "lora_rank": args.lora_rank,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": 0.1,
        "max_grad_norm": 1.0,
        "warmup_steps": 100,
        "lr_scheduler": "cosine",
        "save_every": 2,
        "use_wandb": args.use_wandb,
        "mixed_precision": args.mixed_precision,
        "generate_samples": args.generate_samples,
        "sample_interval": args.sample_interval
    }
    
    # Initialize wandb if requested
    if args.use_wandb:
        if WANDB_AVAILABLE:
            wandb.init(project="fashion-stable-diffusion", config=config)
        else:
            print("⚠️  Wandb requested but not installed. Install with: pip install wandb")
            print("Continuing without wandb logging...")
            config["use_wandb"] = False
    
    # Create augmented dataset
    augmented_pairs = create_augmented_dataset(
        args.data_root, 
        args.captions_root, 
        args.output_dir,
        args.augment_multiplier
    )
    
    # Create dataset from augmented pairs (using module-level class)
    dataset = AugmentedFashionDataset(augmented_pairs)
    
    # Split into train and validation sets
    val_split = args.val_split
    if val_split > 0:
        val_size = int(len(dataset) * val_split)
        train_size = len(dataset) - val_size
        train_dataset, val_dataset = random_split(
            dataset, 
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)  # Reproducible split
        )
        print(f"Dataset split: {train_size} train, {val_size} validation ({val_split*100:.1f}%)")
    else:
        train_dataset = dataset
        val_dataset = None
        print("No validation split (val_split=0)")
    
    # Use num_workers=0 on Windows to avoid multiprocessing issues
    # Windows uses spawn instead of fork, which has pickling issues with nested classes
    import platform
    num_workers = 0 if platform.system() == 'Windows' else 4
    
    train_dataloader = DataLoader(
        train_dataset, 
        batch_size=config["batch_size"],
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True if num_workers > 0 else False
    )
    
    val_dataloader = None
    if val_dataset is not None:
        val_dataloader = DataLoader(
            val_dataset,
            batch_size=config["batch_size"],
            shuffle=False,
            num_workers=0 if platform.system() == 'Windows' else 2,
            pin_memory=True if num_workers > 0 else False
        )
    
    # Initialize trainer and start training
    trainer = FashionLoRATrainer(config, resume_from_checkpoint=resume_from_checkpoint)
    trainer.train(train_dataloader, val_dataloader)
    
    print("Fine-tuning completed!")
    print(f"Model saved to: {args.output_dir}")
    print("You can now load the LoRA weights in your image generator!")

if __name__ == "__main__":
    main()