"""
Fashion Image Captioning using Google Gemini API - CSV Output with Batch Processing
Features:
- Outputs captions to CSV file (filename, caption)
- Processes images in batches of 100 per API key
- Rotates through multiple API keys (up to 8)
- Daily processing workflow with resume capability
- Progress tracking and state persistence
"""

import os
import csv
from pathlib import Path
from tqdm import tqdm
import time
import json
from datetime import datetime, date
import argparse

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


class BatchGeminiFashionCaptioner:
    def __init__(self, api_keys, batch_size=100, wait_time=0.5):
        """
        Initialize Gemini captioner with batch processing and multiple API keys
        
        Args:
            api_keys: List of Gemini API keys (up to 8)
            batch_size: Number of images to process per API key (default: 100)
            wait_time: Wait time between requests (seconds)
        """
        print("Initializing Batch Gemini Captioner...")
        
        if not api_keys or len(api_keys) == 0:
            print("\n[ERROR] Please provide at least one valid Gemini API key!")
            print("Get your API key from: https://aistudio.google.com/apikey")
            exit(1)
        
        if len(api_keys) > 8:
            print(f"\n[WARNING] Using only first 8 API keys (provided {len(api_keys)})")
            api_keys = api_keys[:8]
        
        self.api_keys = api_keys
        self.batch_size = batch_size
        self.current_key_index = 0
        self.wait_time = wait_time
        self.model_name = "gemini-2.0-flash-thinking-exp"  # Pro model with better reasoning
        self.images_processed_today = 0
        self.max_images_per_day = len(api_keys) * batch_size
        
        # Configure with first key
        self._configure_current_key()
        
        print(f"[OK] Using {len(api_keys)} API key(s)")
        print(f"[OK] Batch size: {batch_size} images per key")
        print(f"[OK] Max images per day: {self.max_images_per_day}")
        print(f"[OK] Model: {self.model_name}")
        print(f"[OK] Wait time: {wait_time}s between requests")
        print()
    
    def _configure_current_key(self):
        """Configure Gemini with current API key"""
        # Safety check for valid key index
        if self.current_key_index >= len(self.api_keys):
            print(f"[WARNING] Key index {self.current_key_index} out of range for {len(self.api_keys)} keys")
            self.current_key_index = 0  # Reset to first key
        
        genai.configure(api_key=self.api_keys[self.current_key_index])
    
    def _should_rotate_key(self, batch_processed):
        """Check if we should rotate to next API key"""
        return batch_processed >= self.batch_size
    
    def _rotate_key(self):
        """Rotate to next API key"""
        if self.current_key_index + 1 < len(self.api_keys):
            self.current_key_index += 1
            self._configure_current_key()
            print(f"\n[INFO] Rotated to API key #{self.current_key_index + 1}")
            return True
        else:
            print(f"\n[INFO] All {len(self.api_keys)} API keys used for today")
            return False
    
    def get_system_instruction(self, category):
        """Get category-specific system instruction for better captions"""
        
        base_instruction = (
            "You are an expert at creating image captions for AI model training. "
            "Generate concise, descriptive captions that describe what is visible in the image. "
            "CRITICAL RULES: "
            "1. ALWAYS start with 'A man wearing' or 'A woman wearing' (never 'The model' or 'This person') "
            "2. Focus on clothing description first (fabric, color, style, patterns) "
            "3. Then briefly mention pose/setting if relevant "
            "4. Write 1-2 sentences maximum "
            "5. Use simple, direct language like training data "
            "6. NO explanatory phrases like 'This is' or 'The image shows' "
        )
        
        category_instructions = {
            "Summer_Men": (
                "Caption Pakistani men's summer clothing. "
                "Start with 'A man wearing' then describe: shalwar kameez, kurta, lawn fabric, "
                "cotton clothing, colors, patterns, collar styles. "
                "Example: 'A man wearing a white cotton shalwar kameez with mandarin collar, standing indoors.' "
            ),
            "Summer_Women": (
                "Caption Pakistani women's summer clothing. "
                "Start with 'A woman wearing' then describe: lawn suits, three-piece sets, "
                "dupatta, printed fabrics, colors, patterns. "
                "Example: 'A woman wearing a floral printed lawn suit with matching dupatta, posed elegantly.' "
            ),
            "Winter_Men": (
                "Caption Pakistani men's winter clothing. "
                "Start with 'A man wearing' then describe: waistcoats, sherwanis, formal suits, "
                "wool fabric, khaddar, embroidery, colors. "
                "Example: 'A man wearing a navy blue wool waistcoat with gold embroidery, formal pose.' "
            ),
            "Winter_Women": (
                "Caption Pakistani women's winter clothing. "
                "Start with 'A woman wearing' then describe: khaddar suits, shawls, wool fabric, "
                "winter patterns, embroidered clothing, colors. "
                "Example: 'A woman wearing a burgundy khaddar suit with embroidered details and shawl.' "
            )
        }
        
        specific = category_instructions.get(category, "")
        
        format_instruction = (
            "\n\nFormat requirements: "
            "Write 1-2 short sentences. "
            "Sentence 1: 'A [man/woman] wearing [clothing description with fabric, color, style]' "
            "Sentence 2 (optional): Brief pose or setting description. "
            "Use simple, factual language suitable for AI training data. "
            "NO line breaks, NO explanatory introductions."
        )
        
        return base_instruction + specific + format_instruction
    
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
            
            # Sanitize caption for CSV format:
            # 1. Remove newlines (replace with spaces)
            caption = caption.replace('\n\n', ' ').replace('\n', ' ')
            
            # 2. Remove common preambles and fix format
            preambles = [
                "Here is a caption for the image:",
                "Here is a caption:",
                "Here's a caption for the image:",
                "Here's a caption:",
                "Caption:",
                "This image shows:",
                "The image shows:",
                "This is a",
                "This shows a",
            ]
            for preamble in preambles:
                if caption.lower().startswith(preamble.lower()):
                    caption = caption[len(preamble):].strip()
                    # If it started with "This is a", add "A" back to start properly
                    if preamble.lower() in ["this is a", "this shows a"]:
                        caption = "A " + caption
                    break
            
            # 3. Fix format to ensure proper training style
            # Convert "The model/person is wearing" to "A man/woman wearing"
            if caption.startswith("The model is wearing"):
                if "Men" in category:
                    caption = "A man wearing" + caption[19:]  # Remove "The model is wearing"
                else:
                    caption = "A woman wearing" + caption[19:]
            elif caption.startswith("The person is wearing"):
                if "Men" in category:
                    caption = "A man wearing" + caption[20:]  # Remove "The person is wearing"
                else:
                    caption = "A woman wearing" + caption[20:]
            elif caption.startswith("The man is wearing"):
                caption = "A man wearing" + caption[17:]  # Remove "The man is wearing"
            elif caption.startswith("The woman is wearing"):
                caption = "A woman wearing" + caption[19:]  # Remove "The woman is wearing"
            
            # 4. Ensure no extra whitespace
            caption = ' '.join(caption.split())
            
            return caption
            
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "limit" in error_str:
                print(f"\n[ERROR] Quota exceeded: {e}")
                # This is a quota error - should trigger key rotation
                raise Exception(f"QUOTA_EXCEEDED: {e}")
            else:
                print(f"\n[ERROR] Failed to process {image_path}: {e}")
                return None
    
    def load_progress_state(self, category_name):
        """Load processing progress for resuming"""
        progress_file = f"progress/.caption_progress_{category_name}.json"
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    state = json.load(f)
                
                # Check if it's from today
                today = str(date.today())
                if state.get('date') == today:
                    print(f"[INFO] Resuming from previous session (processed {state.get('processed', 0)} images)")
                    return state
                else:
                    print(f"[INFO] Starting fresh session (previous session was on {state.get('date', 'unknown date')})")
                    
            except Exception as e:
                print(f"[WARNING] Could not load progress file: {e}")
        
        return {
            'date': str(date.today()),
            'processed': 0,
            'processed_files': [],
            'current_key_index': 0,
            'batch_processed': 0
        }
    
    def save_progress_state(self, category_name, state):
        """Save processing progress"""
        progress_file = f"progress/.caption_progress_{category_name}.json"
        
        try:
            with open(progress_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Could not save progress: {e}")
    
    def process_category(self, category_name, category_path, csv_output_path, max_images_today=125):
        """Process up to 125 uncaptionsed images in a category, skip already captioned, stop on quota error"""
        if not os.path.exists(category_path):
            print(f"[ERROR] Category path does not exist: {category_path}")
            return 0, 0
        print(f"\n{'=' * 60}")
        print(f"Processing Category: {category_name}")
        print(f"{'=' * 60}")
        print(f"Path: {category_path}")
        print(f"CSV Output: {csv_output_path}")
        # Load progress state
        state = self.load_progress_state(category_name)
        self.current_key_index = state['current_key_index']
        
        # Validate key index for current number of API keys
        if self.current_key_index >= len(self.api_keys):
            print(f"[WARNING] Previous key index {self.current_key_index} out of range for {len(self.api_keys)} keys, resetting to 0")
            self.current_key_index = 0
            
        self.images_processed_today = state['processed']
        batch_processed = state['batch_processed']
        # Configure current key
        self._configure_current_key()
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        all_image_files = [
            f for f in os.listdir(category_path)
            if os.path.splitext(f.lower())[1] in image_extensions
        ]
        # Check which images are already captioned in CSV
        already_captioned = set()
        if os.path.exists(csv_output_path):
            with open(csv_output_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)  # skip header
                for row in reader:
                    if row and row[0]:
                        already_captioned.add(row[0])
        # Filter out already captioned and previously processed files
        processed_files = set(state['processed_files'])
        image_files = [f for f in all_image_files if f not in already_captioned and f not in processed_files]
        # Limit to max_images_today
        image_files = image_files[:max_images_today]
        print(f"Total images in category: {len(all_image_files)}")
        print(f"Already captioned: {len(already_captioned)}")
        print(f"Already processed: {len(processed_files)}")
        print(f"Remaining to process: {len(image_files)}")
        print(f"Processing today: {len(image_files)} (limit: {max_images_today})")
        if len(image_files) == 0:
            print("[INFO] No images to process")
            return self.images_processed_today, 0
        # Prepare CSV file
        csv_exists = os.path.exists(csv_output_path)
        processed = 0
        errors = 0
        # Open CSV with a short retry loop to handle transient Windows permission locks
        attempts = 0
        csvfile = None
        while attempts < 5:
            try:
                csvfile = open(csv_output_path, 'a', newline='', encoding='utf-8')
                break
            except PermissionError:
                attempts += 1
                time.sleep(0.2)
        if csvfile is None:
            print(f"[ERROR] Could not open CSV file for writing after retries: {csv_output_path}")
            return 0, 1

        writer = csv.writer(csvfile)
        if not csv_exists:
            writer.writerow(['filename', 'caption'])

        for image_file in tqdm(image_files, desc=f"Captioning {category_name}"):
                # Check daily limit
                if processed >= max_images_today:
                    print(f"\n[INFO] Daily limit reached ({max_images_today})")
                    break
                # Check if we need to rotate keys
                if self._should_rotate_key(batch_processed):
                    if not self._rotate_key():
                        print(f"\n[INFO] All API keys exhausted for today")
                        break
                    batch_processed = 0
                image_path = os.path.join(category_path, image_file)
                # Generate caption
                caption = None
                try:
                    caption = self.generate_caption(image_path, category_name)
                except Exception as e:
                    error_str = str(e).lower()
                    if "quota_exceeded" in error_str:
                        print(f"\n[INFO] Quota exceeded for API key #{self.current_key_index + 1}")
                        print(f"[INFO] Attempting to rotate to next API key...")
                        if self._rotate_key():
                            batch_processed = 0
                            print(f"[INFO] Retrying with new API key...")
                            try:
                                caption = self.generate_caption(image_path, category_name)
                            except Exception as retry_e:
                                print(f"\n[ERROR] Retry failed: {retry_e}")
                                caption = None
                        else:
                            print(f"\n[INFO] All API keys exhausted. Stopping processing.")
                            break
                    else:
                        print(f"\n[ERROR] Other API error: {e}")
                        errors += 1
                        continue
                if caption:
                    try:
                        writer.writerow([image_file, caption])
                        csvfile.flush()
                        processed += 1
                        self.images_processed_today += 1
                        batch_processed += 1
                        state['processed_files'].append(image_file)
                    except Exception as e:
                        print(f"\n[ERROR] Failed to write CSV row for {image_file}: {e}")
                        errors += 1
                else:
                    errors += 1
                state['processed'] = self.images_processed_today
                state['current_key_index'] = self.current_key_index
                state['batch_processed'] = batch_processed
                self.save_progress_state(category_name, state)
                time.sleep(self.wait_time)
        print(f"\n[OK] {category_name} Session Complete:")
        print(f"  - New captions: {processed}")
        print(f"  - Errors: {errors}")
        print(f"  - Total processed today: {self.images_processed_today}")
        print(f"  - API key used: #{self.current_key_index + 1}")
        return processed, errors


def main():
    parser = argparse.ArgumentParser(
        description='Generate fashion image captions using Google Gemini API with CSV output and batch processing'
    )
    parser.add_argument(
        '--api-keys',
        type=str,
        nargs='+',
        required=True,
        help='Google Gemini API keys (up to 8 keys)'
    )
    parser.add_argument(
        '--category',
        type=str,
        required=True,
        choices=['Winter_Men', 'Winter_Women', 'Summer_Men', 'Summer_Women'],
        help='Category to process'
    )
    parser.add_argument(
        '--data-root',
        type=str,
        default='data_backup',
        help='Root directory of the dataset (default: data_backup)'
    )
    parser.add_argument(
        '--csv-output',
        type=str,
        default=None,
        help='CSV output file path (default: captions/captions_<category>.csv)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of images to process per API key (default: 100)'
    )
    parser.add_argument(
        '--daily-limit',
        type=int,
        default=None,
        help='Maximum images to process in one day (default: batch_size * num_keys)'
    )
    parser.add_argument(
        '--wait-time',
        type=float,
        default=0.5,
        help='Wait time between requests in seconds (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("FASHION IMAGE CAPTIONING - BATCH PROCESSING")
    print("=" * 60)
    print()
    
    # Validate API keys
    if not all(key and key != "YOUR_API_KEY_HERE" for key in args.api_keys):
        print("\n[ERROR] Please provide valid Gemini API keys!")
        print("Get your API keys from: https://aistudio.google.com/apikey")
        return
    
    # Initialize captioner
    captioner = BatchGeminiFashionCaptioner(
        api_keys=args.api_keys,
        batch_size=args.batch_size,
        wait_time=args.wait_time
    )
    
    # Set daily limit
    daily_limit = args.daily_limit or captioner.max_images_per_day
    
    # Set paths
    category_path = os.path.join(args.data_root, *args.category.split('_'))
    
    if args.csv_output:
        csv_output_path = args.csv_output
    else:
        # Use fixed filename without date for continuous appending
        csv_output_path = f"captions/captions_{args.category}.csv"
    
    # Process category
    processed, errors = captioner.process_category(
        category_name=args.category,
        category_path=category_path,
        csv_output_path=csv_output_path,
        max_images_today=daily_limit
    )
    
    # Final summary
    print("\n" + "=" * 60)
    print("SESSION COMPLETE")
    print("=" * 60)
    print(f"Images captioned today: {processed}")
    print(f"Errors: {errors}")
    print(f"CSV file: {csv_output_path}")
    
    if processed < daily_limit:
        print(f"\nRun again tomorrow to continue (daily limit: {daily_limit})")
    else:
        print(f"\nDaily limit reached ({daily_limit}). Continue tomorrow!")
    
    print("=" * 60)


if __name__ == "__main__":
    main()