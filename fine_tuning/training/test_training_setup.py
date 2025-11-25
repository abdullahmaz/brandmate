"""
Test Training Setup
===================
Comprehensive test script to verify training environment before running full training.
Tests dependencies, data loading, model initialization, and a single training step.
"""

import os
import sys
from pathlib import Path
import traceback

def test_imports():
    """Test if all required packages are available"""
    print("=" * 60)
    print("TEST 1: Checking Dependencies")
    print("=" * 60)
    
    required = {
        "torch": "PyTorch",
        "diffusers": "Diffusers",
        "transformers": "Transformers",
        "accelerate": "Accelerate",
        "peft": "PEFT (LoRA)",
        "PIL": "Pillow",
        "tqdm": "tqdm",
    }
    
    missing = []
    for module, name in required.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - MISSING")
            missing.append(name)
    
    # Test optional packages
    try:
        import wandb
        print(f"  ✅ Wandb (optional)")
    except ImportError:
        print(f"  ⚠️  Wandb (optional) - Not installed")
    
    if missing:
        print(f"\n❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("\n✅ All required dependencies available!")
    return True

def test_cuda():
    """Test CUDA availability"""
    print("\n" + "=" * 60)
    print("TEST 2: Checking GPU/CUDA")
    print("=" * 60)
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✅ CUDA Available")
            print(f"  ✅ Device: {torch.cuda.get_device_name(0)}")
            print(f"  ✅ CUDA Version: {torch.version.cuda}")
            print(f"  ✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            return True
        else:
            print(f"  ⚠️  CUDA Not Available - Training will be slow on CPU")
            print(f"  ⚠️  Consider using GPU for better performance")
            return False
    except Exception as e:
        print(f"  ❌ Error checking CUDA: {e}")
        return False

def test_data_paths():
    """Test if data directories exist"""
    print("\n" + "=" * 60)
    print("TEST 3: Checking Data Paths")
    print("=" * 60)
    
    # Adjust paths based on where script is run from
    base_dir = Path(__file__).parent.parent
    data_root = base_dir / "data_backup"
    captions_root = base_dir / "captions"
    
    print(f"  Looking for data in: {data_root}")
    print(f"  Looking for captions in: {captions_root}")
    
    # Check data directories
    categories = ["Summer/Men", "Summer/Women", "Winter/Men", "Winter/Women"]
    all_exist = True
    
    for cat in categories:
        cat_path = data_root / cat
        if cat_path.exists():
            image_count = len(list(cat_path.glob("*.jpg")))
            print(f"  ✅ {cat}: {image_count} images")
        else:
            print(f"  ❌ {cat}: Directory not found")
            all_exist = False
    
    # Check caption files
    caption_files = [
        "captions_Summer_Men.csv",
        "captions_Summer_Women.csv",
        "captions_Winter_Men.csv",
        "captions_Winter_Women.csv"
    ]
    
    for csv_file in caption_files:
        csv_path = captions_root / csv_file
        if csv_path.exists():
            try:
                import csv
                with open(csv_path, 'r', encoding='utf-8') as f:
                    count = sum(1 for _ in f) - 1
                print(f"  ✅ {csv_file}: {count} captions")
            except Exception as e:
                print(f"  ⚠️  {csv_file}: Error reading ({e})")
        else:
            print(f"  ❌ {csv_file}: Not found")
            all_exist = False
    
    if not all_exist:
        print("\n⚠️  Some data paths are missing. Check your data_backup/ and captions/ directories.")
        return False
    
    print("\n✅ All data paths exist!")
    return True

def test_data_loading():
    """Test if we can load a sample image-caption pair"""
    print("\n" + "=" * 60)
    print("TEST 4: Testing Data Loading")
    print("=" * 60)
    
    # Check if peft is available first
    try:
        import peft
    except ImportError:
        print("  ❌ Cannot test - PEFT package missing")
        print("  Install with: pip install peft")
        return False
    
    try:
        # Add parent directory to path to import training module
        sys.path.insert(0, str(Path(__file__).parent))
        from train_fashion_lora import FashionDataset
        
        base_dir = Path(__file__).parent.parent
        dataset = FashionDataset(
            data_root=str(base_dir / "data_backup"),
            captions_root=str(base_dir / "captions"),
            image_size=512,
            augment_level="none"
        )
        
        if len(dataset) == 0:
            print("  ❌ Dataset is empty!")
            return False
        
        print(f"  ✅ Dataset loaded: {len(dataset)} image-caption pairs")
        
        # Try to load one sample
        sample = dataset[0]
        print(f"  ✅ Sample loaded successfully")
        print(f"     Image shape: {sample['pixel_values'].shape}")
        print(f"     Caption length: {len(sample['caption'])} chars")
        
        return True
    except Exception as e:
        print(f"  ❌ Error loading dataset: {e}")
        traceback.print_exc()
        return False

def test_model_loading():
    """Test if we can load the base model"""
    print("\n" + "=" * 60)
    print("TEST 5: Testing Model Loading")
    print("=" * 60)
    
    try:
        from transformers import CLIPTokenizer, CLIPTextModel
        from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler
        
        model_id = "prompthero/openjourney"
        print(f"  Loading model: {model_id}")
        
        print("  Loading tokenizer...")
        tokenizer = CLIPTokenizer.from_pretrained(model_id, subfolder="tokenizer")
        print("  ✅ Tokenizer loaded")
        
        print("  Loading text encoder...")
        text_encoder = CLIPTextModel.from_pretrained(model_id, subfolder="text_encoder")
        print("  ✅ Text encoder loaded")
        
        print("  Loading VAE...")
        vae = AutoencoderKL.from_pretrained(model_id, subfolder="vae")
        print("  ✅ VAE loaded")
        
        print("  Loading UNet...")
        unet = UNet2DConditionModel.from_pretrained(model_id, subfolder="unet")
        print("  ✅ UNet loaded")
        
        print("  Loading scheduler...")
        scheduler = DDPMScheduler.from_pretrained(model_id, subfolder="scheduler")
        print("  ✅ Scheduler loaded")
        
        print("\n✅ All model components loaded successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ Error loading models: {e}")
        print("  ⚠️  First-time model download may take several minutes")
        print("  ⚠️  Check your internet connection")
        traceback.print_exc()
        return False

def test_lora_setup():
    """Test LoRA configuration"""
    print("\n" + "=" * 60)
    print("TEST 6: Testing LoRA Setup")
    print("=" * 60)
    
    try:
        from peft import LoraConfig, get_peft_model
    except ImportError:
        print("  ❌ Cannot test - PEFT package missing")
        print("  Install with: pip install peft")
        return False
    
    try:
        from diffusers import UNet2DConditionModel
        from transformers import CLIPTextModel
        
        model_id = "prompthero/openjourney"
        
        # Load models
        print("  Loading base models...")
        unet = UNet2DConditionModel.from_pretrained(model_id, subfolder="unet")
        text_encoder = CLIPTextModel.from_pretrained(model_id, subfolder="text_encoder")
        
        # Setup LoRA for UNet
        print("  Setting up UNet LoRA...")
        unet_lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            lora_dropout=0.1,
        )
        unet_lora = get_peft_model(unet, unet_lora_config)
        trainable_params = sum(p.numel() for p in unet_lora.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in unet_lora.parameters())
        print(f"  ✅ UNet LoRA: {trainable_params:,} trainable / {total_params:,} total params")
        
        # Setup LoRA for Text Encoder
        print("  Setting up Text Encoder LoRA...")
        text_encoder_lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
            lora_dropout=0.1,
        )
        text_encoder_lora = get_peft_model(text_encoder, text_encoder_lora_config)
        trainable_params = sum(p.numel() for p in text_encoder_lora.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in text_encoder_lora.parameters())
        print(f"  ✅ Text Encoder LoRA: {trainable_params:,} trainable / {total_params:,} total params")
        
        print("\n✅ LoRA setup successful!")
        return True
        
    except Exception as e:
        print(f"  ❌ Error setting up LoRA: {e}")
        traceback.print_exc()
        return False

def test_single_training_step():
    """Test a single training step"""
    print("\n" + "=" * 60)
    print("TEST 7: Testing Single Training Step")
    print("=" * 60)
    
    # Check dependencies first
    try:
        import peft
        import torch
        from torch.utils.data import DataLoader
    except ImportError as e:
        print(f"  ❌ Cannot test - Missing dependency: {e}")
        print("  Install with: pip install peft torch")
        return False
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from train_fashion_lora import FashionDataset, FashionLoRATrainer
        
        print("  Loading small dataset...")
        base_dir = Path(__file__).parent.parent
        dataset = FashionDataset(
            data_root=str(base_dir / "data_backup"),
            captions_root=str(base_dir / "captions"),
            image_size=512,
            augment_level="none"
        )
        
        if len(dataset) == 0:
            print("  ❌ No data to test with")
            return False
        
        # Create small dataloader with just 2 samples
        test_indices = list(range(min(4, len(dataset))))
        test_dataset = torch.utils.data.Subset(dataset, test_indices)
        dataloader = DataLoader(test_dataset, batch_size=2, shuffle=False)
        
        print("  Initializing trainer...")
        config = {
            "model_id": "prompthero/openjourney",
            "output_dir": "/tmp/test_output",
            "batch_size": 2,
            "epochs": 1,
            "learning_rate": 1e-4,
            "weight_decay": 1e-2,
            "lora_rank": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "max_grad_norm": 1.0,
            "warmup_steps": 10,
            "lr_scheduler": "cosine",
            "save_every": 10,
            "use_wandb": False,
            "mixed_precision": "no",  # Disable for testing to avoid precision issues
            "generate_samples": False
        }
        
        trainer = FashionLoRATrainer(config)
        
        print("  Running single training step...")
        # Get one batch
        batch = next(iter(dataloader))
        
        # Ensure all models are on the same device
        device = trainer.accelerator.device
        trainer.vae = trainer.vae.to(device)
        trainer.unet = trainer.unet.to(device)
        trainer.text_encoder = trainer.text_encoder.to(device)
        
        # Manually run one step (simplified)
        pixel_values = batch["pixel_values"].to(device)
        
        # Encode to latents
        with torch.no_grad():
            latents = trainer.vae.encode(pixel_values).latent_dist.sample()
            latents = latents * trainer.vae.config.scaling_factor
        
        # Add noise
        noise = torch.randn_like(latents)
        timesteps = torch.randint(
            0, trainer.noise_scheduler.config.num_train_timesteps,
            (latents.shape[0],), device=device
        ).long()
        noisy_latents = trainer.noise_scheduler.add_noise(latents, noise, timesteps)
        
        # Encode text
        text_embeddings = trainer._encode_text(batch["caption"])
        
        # Predict noise
        noise_pred = trainer.unet(noisy_latents, timesteps, text_embeddings).sample
        
        # Calculate loss
        loss = torch.nn.functional.mse_loss(noise_pred, noise)
        print(f"  ✅ Training step successful! Loss: {loss.item():.4f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in training step: {e}")
        traceback.print_exc()
        return False

def test_memory_estimate():
    """Estimate memory requirements"""
    print("\n" + "=" * 60)
    print("TEST 8: Memory Estimation")
    print("=" * 60)
    
    try:
        import torch
        
        if not torch.cuda.is_available():
            print("  ⚠️  CUDA not available, skipping memory estimation")
            return True
        
        # Rough memory estimates
        batch_size = 4
        image_size = 512
        
        # Model weights: ~4GB (base model, cached)
        # LoRA weights: ~100MB
        # Activations per batch: ~2-4GB (depends on batch size)
        
        print(f"  Estimated memory requirements (batch_size={batch_size}):")
        print(f"    Base model: ~4 GB")
        print(f"    LoRA weights: ~100 MB")
        print(f"    Activations: ~2-4 GB")
        print(f"    Total: ~6-8 GB minimum")
        
        # Check available memory
        props = torch.cuda.get_device_properties(0)
        total_memory = props.total_memory / 1e9
        print(f"\n  Your GPU: {total_memory:.1f} GB")
        
        if total_memory < 6:
            print(f"  ⚠️  GPU memory may be insufficient")
            print(f"  💡 Try: batch_size=2, enable gradient checkpointing (already enabled)")
        elif total_memory < 8:
            print(f"  ⚠️  GPU memory may be tight")
            print(f"  💡 Monitor memory usage, reduce batch_size if needed")
        else:
            print(f"  ✅ GPU memory should be sufficient")
        
        return True
        
    except Exception as e:
        print(f"  ⚠️  Error estimating memory: {e}")
        return True  # Not critical

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FASHION LORA TRAINING - PRE-FLIGHT CHECKS")
    print("=" * 60)
    print("\nRunning comprehensive tests before training...")
    
    results = {}
    
    results['imports'] = test_imports()
    results['cuda'] = test_cuda()
    results['data_paths'] = test_data_paths()
    results['data_loading'] = test_data_loading()
    results['model_loading'] = test_model_loading()
    results['lora_setup'] = test_lora_setup()
    results['training_step'] = test_single_training_step()
    results['memory'] = test_memory_estimate()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.upper():20} {status}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 ALL TESTS PASSED! Ready to train!")
        print("=" * 60)
        return 0
    else:
        print(f"⚠️  {total - passed} TEST(S) FAILED")
        print("Please fix the issues above before training.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit(main())

