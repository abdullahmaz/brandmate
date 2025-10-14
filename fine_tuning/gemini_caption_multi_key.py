"""
Fashion Image Captioning using Google Gemini API with Multiple Keys
Features:
- Rotates through multiple API keys when quota is exceeded
- Automatic retry with exponential backoff
- Saves progress and can resume from interruption
- No images skipped
"""

import os
from pathlib import Path
from tqdm import tqdm
import time
import json
from datetime import datetime

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


class MultiKeyGeminiFashionCaptioner:
    def __init__(self, api_keys, wait_time=0.5):
        """
        Initialize Gemini captioner with multiple API keys
        
        Args:
            api_keys: List of Gemini API keys
            wait_time: Wait time between requests (seconds) to avoid rate limits
        """
        print("Initializing Multi-Key Gemini Captioner...")
        
        if not api_keys or len(api_keys) == 0:
            print("\n[ERROR] Please provide at least one valid Gemini API key!")
            print("Get your API key from: https://aistudio.google.com/apikey")
            exit(1)
        
        self.api_keys = api_keys
        self.current_key_index = 0
        self.wait_time = wait_time
        self.model_name = "gemini-2.0-flash-exp"
        
        # Configure with first key
        self._configure_current_key()
        
        print(f"[OK] Using {len(api_keys)} API key(s)")
        print(f"[OK] Model: {self.model_name}")
        print(f"[OK] Wait time: {wait_time}s between requests")
        print()
    
    def _configure_current_key(self):
        """Configure Gemini with current API key"""
        genai.configure(api_key=self.api_keys[self.current_key_index])
    
    def _rotate_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_current_key()
        print(f"\n[INFO] Rotated to API key #{self.current_key_index + 1}")
    
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
    
    def generate_caption(self, image_path, category, max_retries=5):
        """
        Generate caption for a single image with automatic retry and key rotation
        
        Args:
            image_path: Path to image file
            category: Category name for context
            max_retries: Maximum number of retry attempts
            
        Returns:
            caption string or None if failed
        """
        
        for attempt in range(max_retries):
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
                
                # Wait before next request to avoid rate limits
                time.sleep(self.wait_time)
                
                return caption
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a quota error
                if "429" in error_str or "quota" in error_str.lower():
                    print(f"\n[QUOTA] API key #{self.current_key_index + 1} quota exceeded")
                    
                    # If we have multiple keys, try rotating
                    if len(self.api_keys) > 1:
                        self._rotate_key()
                        print(f"[RETRY] Retrying with API key #{self.current_key_index + 1}...")
                        continue
                    else:
                        # Single key - wait and retry with exponential backoff
                        wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                        print(f"[WAIT] Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                else:
                    # Other error - log and retry
                    print(f"\n[ERROR] Attempt {attempt + 1}/{max_retries} failed: {error_str}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
        
        # All retries failed
        print(f"\n[FAILED] Could not caption {image_path} after {max_retries} attempts")
        return None
    
    def process_category(self, category_name, category_path, overwrite=False, 
                        max_images=None, resume=True):
        """Process all images in a single category with progress tracking"""
        
        if not os.path.exists(category_path):
            print(f"[ERROR] Category path does not exist: {category_path}")
            return 0, 0, 0
        
        print(f"\n{'=' * 60}")
        print(f"Processing Category: {category_name}")
        print(f"{'=' * 60}")
        print(f"Path: {category_path}")
        
        # Progress file for resume capability
        progress_file = os.path.join(category_path, f".caption_progress_{category_name}.json")
        
        # Load progress if resuming
        completed_files = set()
        if resume and os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                    completed_files = set(progress_data.get('completed', []))
                print(f"[RESUME] Loaded progress: {len(completed_files)} files already completed")
            except:
                pass
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        all_image_files = [
            f for f in os.listdir(category_path)
            if os.path.splitext(f.lower())[1] in image_extensions
        ]
        
        # Filter out already completed if resuming
        if resume:
            image_files = [f for f in all_image_files if f not in completed_files]
        else:
            image_files = all_image_files
        
        # Limit images if specified
        if max_images:
            image_files = image_files[:max_images]
            print(f"Processing first {max_images} remaining images (test mode)")
        
        print(f"Total images: {len(all_image_files)}")
        print(f"Already completed: {len(completed_files)}")
        print(f"To process: {len(image_files)}")
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
                completed_files.add(image_file)
                continue
            
            # Generate caption with retry
            caption = self.generate_caption(image_path, category_name)
            
            if caption:
                # Save caption to file
                try:
                    with open(caption_path, 'w', encoding='utf-8') as f:
                        f.write(caption)
                    processed += 1
                    completed_files.add(image_file)
                    
                    # Save progress every 10 images
                    if processed % 10 == 0:
                        self._save_progress(progress_file, completed_files)
                        
                except Exception as e:
                    print(f"\n[ERROR] Failed to save caption for {image_file}: {e}")
                    errors += 1
            else:
                errors += 1
        
        # Save final progress
        self._save_progress(progress_file, completed_files)
        
        # Summary
        print(f"\n[OK] {category_name} Complete:")
        print(f"  - Captioned: {processed}")
        print(f"  - Skipped: {skipped}")
        print(f"  - Errors: {errors}")
        print(f"  - Total completed: {len(completed_files)}/{len(all_image_files)}")
        
        return processed, skipped, errors
    
    def _save_progress(self, progress_file, completed_files):
        """Save progress to file"""
        try:
            with open(progress_file, 'w') as f:
                json.dump({
                    'completed': list(completed_files),
                    'timestamp': datetime.now().isoformat()
                }, f)
        except:
            pass


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate fashion image captions using multiple Gemini API keys'
    )
    parser.add_argument(
        '--api-keys',
        type=str,
        nargs='+',
        required=False,
        help='One or more Google Gemini API keys (space-separated)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='run_captioning_config.py',
        help='Path to config file with API keys (default: run_captioning_config.py)'
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
        help='Test mode: process only N images (e.g., --test 50)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing captions'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Disable resume functionality (start from scratch)'
    )
    parser.add_argument(
        '--wait-time',
        type=float,
        default=0.5,
        help='Wait time between requests in seconds (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    # Load API keys from config file or command line
    api_keys = args.api_keys
    
    if not api_keys:
        # Try to load from config file
        print(f"Loading API keys from: {args.config}")
        try:
            config_globals = {}
            with open(args.config, 'r') as f:
                exec(f.read(), config_globals)
            
            api_keys = config_globals.get('API_KEYS', [])
            
            if not api_keys:
                print("\n[ERROR] No API keys found in config file!")
                print(f"Please edit {args.config} and add your API keys.")
                exit(1)
            
            print(f"[OK] Loaded {len(api_keys)} API key(s) from config\n")
            
        except FileNotFoundError:
            print(f"\n[ERROR] Config file not found: {args.config}")
            print("Please provide API keys using --api-keys or create a config file.")
            exit(1)
        except Exception as e:
            print(f"\n[ERROR] Failed to load config: {e}")
            exit(1)
    
    print("\n" + "=" * 60)
    print("MULTI-KEY GEMINI FASHION CAPTIONING")
    print("=" * 60)
    print(f"API Keys: {len(api_keys)}")
    print(f"Wait time: {args.wait_time}s")
    print(f"Resume: {not args.no_resume}")
    print("=" * 60)
    print()
    
    # Initialize captioner
    captioner = MultiKeyGeminiFashionCaptioner(
        api_keys=api_keys,
        wait_time=args.wait_time
    )
    
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
            max_images=args.test,
            resume=not args.no_resume
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

