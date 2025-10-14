"""
Fashion Image Captioning using Google Gemini API
Generates detailed captions focused on clothing and fashion details
"""

import os
from pathlib import Path
from tqdm import tqdm
import time

# Check if required packages are installed
try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print("\n" + "=" * 60)
    print("ERROR: Required packages not installed!")
    print("=" * 60)
    print(f"\n{e}")
    print("\nPlease install them using:")
    print("  pip install google-generativeai Pillow tqdm")
    print("=" * 60)
    exit(1)


class GeminiFashionCaptioner:
    def __init__(self, api_key):
        """Initialize Gemini client for image captioning"""
        print("Initializing Gemini API...")
        
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("\n[ERROR] Please provide a valid Gemini API key!")
            print("Get your API key from: https://aistudio.google.com/apikey")
            exit(1)
        
        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.0-flash-exp"
        
        print(f"[OK] Using model: {self.model_name}\n")
    
    def get_system_instruction(self, category):
        """Get category-specific system instruction for better captions"""
        
        base_instruction = (
            "You are an expert fashion image captioning assistant specializing in Pakistani clothing. "
            "Generate precise, detailed captions for model fine-tuning. "
            "Focus primarily on the CLOTHING and FASHION details, then mention other visible elements. "
        )
        
        category_specific = {
            "Winter_Men": (
                "This image shows Pakistani men's winter formal wear. "
                "Describe the type of clothing (waistcoat, coat, sherwani, suit, shalwar kameez), "
                "fabric type (wool, khaddar, blended), colors, patterns (plain, embroidered, printed), "
                "fit (slim, regular, loose), styling details (buttons, collar, pockets, embroidery). "
                "Then briefly mention the model's pose, background, and any accessories (shoes, watch). "
                "Use terms like: waistcoat, sherwani, shalwar kameez, kurta, formal wear, winter clothing."
            ),
            "Winter_Women": (
                "This image shows Pakistani women's winter clothing. "
                "Describe the type of outfit (khaddar suit, shawl, printed fabric, three-piece unstitched), "
                "fabric type (khaddar, karandi, linen, wool), colors, print patterns (floral, geometric, striped), "
                "embroidery details, styling. Then mention the model's appearance, pose, and background. "
                "Use terms like: khaddar, three-piece, unstitched, dupatta, printed, embroidered, winter collection."
            ),
            "Summer_Men": (
                "This image shows Pakistani men's summer eastern wear. "
                "Describe the type of clothing (kurta, shalwar kameez, casual eastern wear), "
                "fabric type (lawn, cotton, linen, cambric), colors, patterns, fit, collar style. "
                "Then mention the model's styling, pose, and background. "
                "Use terms like: shalwar kameez, kurta, lawn fabric, summer wear, eastern clothing, casual."
            ),
            "Summer_Women": (
                "This image shows Pakistani women's summer lawn clothing. "
                "Describe the outfit type (lawn suit, unstitched fabric, three-piece, printed lawn), "
                "fabric quality (lawn, cotton, silk blend), colors, print style (floral, abstract, traditional), "
                "design details, embroidery or embellishments. Then mention styling and background. "
                "Use terms like: lawn fabric, unstitched, three-piece suit, printed, summer collection, dupatta."
            )
        }
        
        specific = category_specific.get(category, "")
        
        closing = (
            "\n\nFormat: Write 2-4 sentences. "
            "Start with clothing description (1-2 sentences), then add context (1-2 sentences). "
            "Use clear, factual language. Avoid artistic or subjective phrases. "
            "Be specific about colors, fabrics, and clothing types."
        )
        
        return base_instruction + specific + closing
    
    def generate_caption(self, image_path, category):
        """Generate caption for a single image using Gemini"""
        try:
            # Load image
            img = Image.open(image_path)
            
            # Get category-specific system instruction
            system_instruction = self.get_system_instruction(category)
            
            # Create model with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            # Generate caption
            response = model.generate_content(
                ["Caption this image following the instructions.", img],
                generation_config=genai.types.GenerationConfig(temperature=0.4)
            )
            
            # Extract caption text
            caption = response.text.strip()
            
            return caption
            
        except Exception as e:
            print(f"\n[ERROR] Failed to process {image_path}: {e}")
            return None
    
    def process_category(self, category_name, category_path, overwrite=False, max_images=None):
        """Process all images in a single category"""
        
        if not os.path.exists(category_path):
            print(f"[ERROR] Category path does not exist: {category_path}")
            return 0, 0, 0
        
        print(f"\n{'=' * 60}")
        print(f"Processing Category: {category_name}")
        print(f"{'=' * 60}")
        print(f"Path: {category_path}")
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        image_files = [
            f for f in os.listdir(category_path)
            if os.path.splitext(f.lower())[1] in image_extensions
        ]
        
        # Limit images if specified
        if max_images:
            image_files = image_files[:max_images]
            print(f"Processing first {max_images} images (test mode)")
        
        print(f"Found {len(image_files)} images")
        print()
        
        # Statistics
        processed = 0
        skipped = 0
        errors = 0
        
        # Process each image with progress bar
        for image_file in tqdm(image_files, desc=f"Captioning {category_name}"):
            image_path = os.path.join(category_path, image_file)
            
            # Create caption file path
            base_name = os.path.splitext(image_file)[0]
            caption_path = os.path.join(category_path, f"{base_name}.txt")
            
            # Skip if caption already exists and overwrite is False
            if os.path.exists(caption_path) and not overwrite:
                skipped += 1
                continue
            
            # Generate caption
            caption = self.generate_caption(image_path, category_name)
            
            if caption:
                # Save caption to file
                try:
                    with open(caption_path, 'w', encoding='utf-8') as f:
                        f.write(caption)
                    processed += 1
                except Exception as e:
                    print(f"\n[ERROR] Failed to save caption for {image_file}: {e}")
                    errors += 1
            else:
                errors += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Summary
        print(f"\n[OK] {category_name} Complete:")
        print(f"  - Captioned: {processed}")
        print(f"  - Skipped: {skipped}")
        print(f"  - Errors: {errors}")
        
        return processed, skipped, errors


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate fashion image captions using Google Gemini API'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        required=True,
        help='Google Gemini API key (get from https://aistudio.google.com/apikey)'
    )
    parser.add_argument(
        '--category',
        type=str,
        required=True,
        choices=['Winter_Men', 'Winter_Women', 'Summer_Men', 'Summer_Women', 'all'],
        help='Category to process (or "all" for all categories)'
    )
    parser.add_argument(
        '--data-root',
        type=str,
        default='data',
        help='Root directory of the dataset (default: data)'
    )
    parser.add_argument(
        '--test',
        type=int,
        default=None,
        help='Test mode: process only N images (e.g., --test 5)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing captions'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("FASHION IMAGE CAPTIONING - GOOGLE GEMINI")
    print("=" * 60)
    print()
    
    # Initialize captioner
    captioner = GeminiFashionCaptioner(api_key=args.api_key)
    
    # Define categories
    categories = {
        "Winter_Men": os.path.join(args.data_root, "Winter", "Men"),
        "Winter_Women": os.path.join(args.data_root, "Winter", "Women"),
        "Summer_Men": os.path.join(args.data_root, "Summer", "Men"),
        "Summer_Women": os.path.join(args.data_root, "Summer", "Women")
    }
    
    # Determine which categories to process
    if args.category == 'all':
        categories_to_process = categories
    else:
        categories_to_process = {args.category: categories[args.category]}
    
    # Process categories
    total_processed = 0
    total_skipped = 0
    total_errors = 0
    
    for category_name, category_path in categories_to_process.items():
        processed, skipped, errors = captioner.process_category(
            category_name=category_name,
            category_path=category_path,
            overwrite=args.overwrite,
            max_images=args.test
        )
        
        total_processed += processed
        total_skipped += skipped
        total_errors += errors
    
    # Final summary
    print("\n" + "=" * 60)
    print("CAPTIONING COMPLETE")
    print("=" * 60)
    print(f"Total captions generated: {total_processed}")
    print(f"Total skipped: {total_skipped}")
    print(f"Total errors: {total_errors}")
    print(f"Total files: {total_processed + total_skipped}")
    print("=" * 60)
    print("\n[SUCCESS] Captioning complete!")


if __name__ == "__main__":
    main()
