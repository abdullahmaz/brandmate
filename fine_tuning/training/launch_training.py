#!/usr/bin/env python3
"""
Fashion LoRA Training Launcher
=============================
Easy launcher for fashion Stable Diffusion fine-tuning
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        "torch", "diffusers", "transformers", 
        "accelerate", "peft", "wandb"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("📦 Install them with: pip install -r requirements_training.txt")
        return False
    
    print("✅ All required packages are installed!")
    return True

def check_data():
    """Check if data and captions are available"""
    data_root = Path("data_backup")
    captions_root = Path("captions")
    
    # Check data directories
    required_dirs = [
        "../data_backup/Summer/Men",
        "../data_backup/Summer/Women", 
        "../data_backup/Winter/Men",
        "../data_backup/Winter/Women"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing data directories: {missing_dirs}")
        return False
    
    # Check caption files
    required_csvs = [
        "../captions/captions_Summer_Men.csv",
        "../captions/captions_Summer_Women.csv",
        "../captions/captions_Winter_Men.csv", 
        "../captions/captions_Winter_Women.csv"
    ]
    
    missing_csvs = []
    for csv_path in required_csvs:
        if not Path(csv_path).exists():
            missing_csvs.append(csv_path)
    
    if missing_csvs:
        print(f"❌ Missing caption files: {missing_csvs}")
        print("📝 Run the captioning script first!")
        return False
    
    print("✅ Data and captions are ready!")
    return True

def estimate_training_time(config):
    """Estimate training time based on dataset size and config"""
    # Count total images with captions
    total_images = 0
    for csv_file in Path("../captions").glob("captions_*.csv"):
        try:
            with open(csv_file, 'r') as f:
                total_images += sum(1 for line in f) - 1  # Subtract header
        except:
            continue
    
    # Calculate with augmentation
    augmented_total = total_images * config["data_settings"]["augmentation_multiplier"]
    
    # Rough time estimation (assumes ~2-3 seconds per image on GPU)
    time_per_image = 2.5  # seconds
    epochs = config["training_settings"]["epochs"]
    
    total_time_seconds = augmented_total * epochs * time_per_image
    hours = total_time_seconds / 3600
    
    print(f"📊 Training Estimation:")
    print(f"   Original images: {total_images}")
    print(f"   With augmentation: {augmented_total}")
    print(f"   Epochs: {epochs}")
    print(f"   Estimated time: {hours:.1f} hours")
    
    return hours

def main():
    print("🎨 Fashion Stable Diffusion LoRA Training Launcher")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check data availability
    if not check_data():
        return 1
    
    # Load config
    try:
        with open("config_training.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config_training.json not found!")
        return 1
    
    # Show training estimation
    hours = estimate_training_time(config)
    
    # Confirm before starting
    print("\n🚀 Ready to start training!")
    response = input("Continue? (y/N): ").lower().strip()
    
    if response != 'y':
        print("Training cancelled.")
        return 0
    
    # Launch training
    cmd = [
        sys.executable, 
        "train_fashion_lora.py",
        "--data_root", config["data_settings"]["data_root"],
        "--captions_root", config["data_settings"]["captions_root"],
        "--output_dir", config["output_settings"]["output_dir"],
        "--model_id", config["model_settings"]["base_model"],
        "--batch_size", str(config["training_settings"]["batch_size"]),
        "--epochs", str(config["training_settings"]["epochs"]),
        "--learning_rate", str(config["training_settings"]["learning_rate"]),
        "--lora_rank", str(config["lora_settings"]["rank"]),
        "--lora_alpha", str(config["lora_settings"]["alpha"]),
        "--augment_multiplier", str(config["data_settings"]["augmentation_multiplier"])
    ]
    
    if config["logging"]["use_wandb"]:
        cmd.append("--use_wandb")
    
    print(f"🔥 Starting training...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 Training completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Training failed with error code {e.returncode}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Training interrupted by user")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())