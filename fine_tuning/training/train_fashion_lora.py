"""
Fashion Stable Diffusion LoRA Fine-Tuning
===========================================
Fine-tune Stable Diffusion model on fashion dataset with augmentations
Uses LoRA (Low-Rank Adaptation) for efficient training
"""

import os
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
import wandb

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
    
    def __init__(self, config: Dict):
        self.config = config
        self.accelerator = Accelerator()
        
        # Initialize models
        self._load_models()
        
        # Setup LoRA
        self._setup_lora()
        
        print(f"Training on device: {self.accelerator.device}")
    
    def _load_models(self):
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
        self.noise_scheduler = DDPMScheduler.from_pretrained(
            model_id, subfolder="scheduler"
        )
        
        # Freeze base models
        self.vae.requires_grad_(False)
        self.text_encoder.requires_grad_(False)
        self.unet.requires_grad_(False)
    
    def _setup_lora(self):
        """Setup LoRA adapters for UNet and Text Encoder"""
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
    
    def _encode_text(self, captions: List[str]):
        """Encode text captions using CLIP text encoder"""
        inputs = self.tokenizer(
            captions,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            text_embeddings = self.text_encoder(inputs.input_ids.to(self.accelerator.device))[0]
        
        return text_embeddings
    
    def train(self, train_dataloader: DataLoader):
        """Main training loop"""
        # Setup optimizer and scheduler
        optimizer = torch.optim.AdamW(
            list(self.unet.parameters()) + list(self.text_encoder.parameters()),
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
        self.unet, self.text_encoder, optimizer, train_dataloader, lr_scheduler = self.accelerator.prepare(
            self.unet, self.text_encoder, optimizer, train_dataloader, lr_scheduler
        )
        
        # Training loop
        print(f"Starting training for {self.config['epochs']} epochs...")
        
        for epoch in range(self.config["epochs"]):
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
                    
                    # Encode text
                    text_embeddings = self._encode_text(batch["caption"])
                    
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
                progress_bar.set_postfix({
                    "loss": f"{loss.item():.4f}",
                    "avg_loss": f"{total_loss/(step+1):.4f}",
                    "lr": f"{lr_scheduler.get_last_lr()[0]:.2e}"
                })
                
                # Log to wandb
                if self.config.get("use_wandb", False):
                    wandb.log({
                        "loss": loss.item(),
                        "learning_rate": lr_scheduler.get_last_lr()[0],
                        "epoch": epoch,
                        "step": step
                    })
            
            # Save checkpoint
            if (epoch + 1) % self.config["save_every"] == 0:
                self.save_checkpoint(epoch + 1)
            
            print(f"Epoch {epoch+1} completed - Average Loss: {total_loss/len(train_dataloader):.4f}")
        
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
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--learning_rate", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--augment_multiplier", type=int, default=3, help="Dataset augmentation multiplier")
    parser.add_argument("--use_wandb", action="store_true", help="Use Weights & Biases for logging")
    args = parser.parse_args()
    
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
        "use_wandb": args.use_wandb
    }
    
    # Initialize wandb if requested
    if args.use_wandb:
        wandb.init(project="fashion-stable-diffusion", config=config)
    
    # Create augmented dataset
    augmented_pairs = create_augmented_dataset(
        args.data_root, 
        args.captions_root, 
        args.output_dir,
        args.augment_multiplier
    )
    
    # Create dataset and dataloader
    class AugmentedFashionDataset(FashionDataset):
        def __init__(self, pairs, image_size=512):
            self.image_caption_pairs = pairs
            self.image_size = image_size
            self.augment_level = "mixed"  # Mixed augmentation
            
            self.base_transform = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5])
            ])
    
    dataset = AugmentedFashionDataset(augmented_pairs)
    dataloader = DataLoader(
        dataset, 
        batch_size=config["batch_size"],
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    
    # Initialize trainer and start training
    trainer = FashionLoRATrainer(config)
    trainer.train(dataloader)
    
    print("Fine-tuning completed!")
    print(f"Model saved to: {args.output_dir}")
    print("You can now load the LoRA weights in your image generator!")

if __name__ == "__main__":
    main()