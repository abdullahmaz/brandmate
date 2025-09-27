#!/usr/bin/env python3
"""
Script to download and cache the required models locally.
Run this before starting the main application.
"""

import os
import sys
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from diffusers import StableDiffusionPipeline
import torch

def download_llm_model():
    """Download the LLM model for orchestration"""
    print("Downloading LLM model (Llama 3.2 3B Instruct)...")
    try:
        model_name = "meta-llama/Llama-3.2-3B-Instruct"
        print(f"Loading tokenizer for {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        print(f"Loading model {model_name}...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        print("✓ LLM model downloaded successfully!")
        return True
    except Exception as e:
        print(f"✗ Error downloading LLM model: {e}")
        return False

def download_image_model():
    """Download the image generation model"""
    print("Downloading image generation model (Stable Diffusion v1.5)...")
    try:
        model_name = "runwayml/stable-diffusion-v1-5"
        pipe = StableDiffusionPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            safety_checker=None,
            requires_safety_checker=False
        )
        print("✓ Image generation model downloaded successfully!")
        return True
    except Exception as e:
        print(f"✗ Error downloading image model: {e}")
        return False

def main():
    print("Brandmate Model Installation Script")
    print("=" * 40)
    
    # Check if CUDA is available
    if torch.cuda.is_available():
        print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        print("⚠ CUDA not available, using CPU (slower)")
    
    print("\nThis will download models (~6GB total):")
    print("- Llama 3.2 3B Instruct (~6GB)")
    print("- Stable Diffusion v1.5 (~4GB)")
    print("Models will be cached locally for future use.")
    
    response = input("\nContinue? (y/N): ").strip().lower()
    if response != 'y':
        print("Installation cancelled.")
        return
    
    print("\nStarting model downloads...")
    
    # Download models
    llm_success = download_llm_model()
    image_success = download_image_model()
    
    print("\n" + "=" * 40)
    if llm_success and image_success:
        print("✓ All models downloaded successfully!")
        print("You can now run: python main.py")
    else:
        print("✗ Some models failed to download.")
        print("Check your internet connection and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
