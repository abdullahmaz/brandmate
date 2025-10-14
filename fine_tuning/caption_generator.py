"""
Auto-Caption Generator for Fashion Dataset using GIT (GenerativeImage2Text) Model
Based on: https://huggingface.co/docs/transformers/main/tasks/image_captioning
"""

import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import torch

# Check if required packages are installed
try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    from accelerate import Accelerator
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: Required packages not installed!")
    print("=" * 60)
    print("\nPlease install them using:")
    print("  pip install transformers accelerate torch Pillow tqdm")
    print("=" * 60)
    exit(1)


class FashionCaptioner:
    def __init__(self, model_name="microsoft/git-base"):
        """Initialize GIT model for image captioning"""
        print(f"Loading model: {model_name}")
        print("This may take a few minutes on first run...")
        
        # Set up device using Accelerator
        self.device = Accelerator().device
        print(f"Using device: {self.device}")
        
        if self.device.type == "cpu":
            print("WARNING: Running on CPU. This will be SLOW!")
            print("Consider using a GPU for faster processing.")
        
        # Load processor and model
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        
        print("[OK] Model loaded successfully!\n")
    
    def generate_caption(self, image_path, category_prefix=""):
        """Generate caption for a single image using GIT model"""
        try:
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Prepare image for the model
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            pixel_values = inputs.pixel_values
            
            # Generate caption
            generated_ids = self.model.generate(
                pixel_values=pixel_values, 
                max_length=50
            )
            
            # Decode the prediction
            caption = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # Add category-specific context
            enhanced_caption = self.enhance_caption(caption, category_prefix)
            
            return enhanced_caption
            
        except Exception as e:
            print(f"\n[ERROR] Failed to process {image_path}: {e}")
            return None
    
    def enhance_caption(self, base_caption, category):
        """Add category-specific keywords to caption"""
        
        # Define category-specific enhancements
        category_keywords = {
            "Winter_Men": "pakistani winter men's formal wear, waistcoat,",
            "Winter_Women": "pakistani winter women's clothing, khaddar fabric,",
            "Summer_Men": "pakistani summer men's eastern wear, kurta,",
            "Summer_Women": "pakistani summer women's lawn fabric, unstitched,"
        }
        
        # Get enhancement based on category
        enhancement = category_keywords.get(category, "")
        
        # Combine enhancement with base caption
        if enhancement:
            enhanced = f"{enhancement} {base_caption}"
        else:
            enhanced = base_caption
        
        return enhanced
    
    def process_dataset(self, data_root="data", overwrite=False, max_images=None):
        """Process all images in the dataset"""
        
        categories = {
            "Winter_Men": os.path.join(data_root, "Winter", "Men"),
            "Winter_Women": os.path.join(data_root, "Winter", "Women"),
            "Summer_Men": os.path.join(data_root, "Summer", "Men"),
            "Summer_Women": os.path.join(data_root, "Summer", "Women")
        }
        
        print("=" * 60)
        print("AUTO-CAPTIONING DATASET - GIT Model")
        print("=" * 60)
        print(f"Data root: {os.path.abspath(data_root)}")
        print(f"Overwrite existing captions: {overwrite}")
        if max_images:
            print(f"Processing first {max_images} images per category (test mode)")
        print()
        
        # Statistics
        total_processed = 0
        total_skipped = 0
        total_errors = 0
        
        for category_name, category_path in categories.items():
            if not os.path.exists(category_path):
                print(f"[MISSING] {category_path}")
                continue
            
            print(f"\nProcessing: {category_name}")
            print("-" * 60)
            
            # Get all image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
            image_files = [
                f for f in os.listdir(category_path)
                if os.path.splitext(f.lower())[1] in image_extensions
            ]
            
            # Limit images if in test mode
            if max_images:
                image_files = image_files[:max_images]
            
            print(f"Found {len(image_files)} images")
            
            # Process each image
            category_processed = 0
            category_skipped = 0
            category_errors = 0
            
            for image_file in tqdm(image_files, desc=f"Captioning {category_name}"):
                image_path = os.path.join(category_path, image_file)
                
                # Create caption file path
                base_name = os.path.splitext(image_file)[0]
                caption_path = os.path.join(category_path, f"{base_name}.txt")
                
                # Skip if caption already exists and overwrite is False
                if os.path.exists(caption_path) and not overwrite:
                    category_skipped += 1
                    continue
                
                # Generate caption
                caption = self.generate_caption(image_path, category_name)
                
                if caption:
                    # Save caption to file
                    try:
                        with open(caption_path, 'w', encoding='utf-8') as f:
                            f.write(caption)
                        category_processed += 1
                    except Exception as e:
                        print(f"\n[ERROR] Failed to save caption for {image_file}: {e}")
                        category_errors += 1
                else:
                    category_errors += 1
            
            # Category summary
            print(f"[OK] {category_name}: {category_processed} captioned, {category_skipped} skipped, {category_errors} errors")
            
            total_processed += category_processed
            total_skipped += category_skipped
            total_errors += category_errors
        
        # Final summary
        print("\n" + "=" * 60)
        print("CAPTIONING COMPLETE")
        print("=" * 60)
        print(f"Total captions generated: {total_processed}")
        print(f"Total skipped (already exist): {total_skipped}")
        print(f"Total errors: {total_errors}")
        print(f"Total files: {total_processed + total_skipped}")
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-generate captions for fashion images using GIT model'
    )
    parser.add_argument(
        '--data-root', 
        type=str, 
        default='data',
        help='Root directory of the dataset (default: data)'
    )
    parser.add_argument(
        '--overwrite', 
        action='store_true',
        help='Overwrite existing captions'
    )
    parser.add_argument(
        '--test', 
        type=int, 
        default=None,
        help='Test mode: process only N images per category (e.g., --test 10)'
    )
    parser.add_argument(
        '--model', 
        type=str, 
        default='microsoft/git-base',
        choices=['microsoft/git-base', 'microsoft/git-large'],
        help='GIT model to use (default: git-base)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("FASHION DATASET AUTO-CAPTIONING")
    print("Using GIT (GenerativeImage2Text) Model")
    print("=" * 60)
    print()
    
    # Initialize captioner
    captioner = FashionCaptioner(model_name=args.model)
    
    # Process dataset
    captioner.process_dataset(
        data_root=args.data_root,
        overwrite=args.overwrite,
        max_images=args.test
    )
    
    print("\n[SUCCESS] Captioning complete!")
    print("You can now use these captions for model training.")


if __name__ == "__main__":
    main()
