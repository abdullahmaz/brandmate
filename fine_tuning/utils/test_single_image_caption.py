"""
Simple test script to caption one image and verify CSV output
Tests API functionality, CSV formatting, and caption quality
"""

import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install google-generativeai Pillow")
    exit(1)


class SimpleCaptionTester:
    def __init__(self, api_key):
        """Initialize Gemini API with single key"""
        print("Initializing Gemini API...")
        
        if not api_key:
            print("[ERROR] Please provide a valid API key")
            exit(1)
            
        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.0-flash-exp"  # Using experimental model like in main script
        
        print(f"[OK] Using model: {self.model_name}")
        print(f"[OK] API configured")
    
    def get_system_instruction(self, category):
        """Get optimized system instruction for clothing-first captions"""
        
        base_instruction = (
            "You are a fashion image captioning expert. Generate concise, accurate captions "
            "focusing on clothing and fashion details first, then model and background. "
            "CRITICAL RULES: "
            "1. ALWAYS start with clothing description (fabric, color, style, patterns) "
            "2. Then briefly mention model pose and background "
            "3. Write exactly 2-3 sentences in one continuous paragraph "
            "4. NO line breaks or newlines in your response "
            "5. DO NOT start with phrases like 'Here is a caption' or 'This image shows' "
        )
        
        category_instructions = {
            "Summer_Men": (
                "Focus on Pakistani men's summer wear: shalwar kameez, kurta, lawn fabric, "
                "cotton clothing, colors, patterns, collar styles, and casual eastern wear. "
            ),
            "Summer_Women": (
                "Focus on Pakistani women's summer wear: lawn suits, unstitched fabric, "
                "three-piece sets, dupatta, printed fabrics, floral patterns, summer collections. "
            ),
            "Winter_Men": (
                "Focus on Pakistani men's winter wear: waistcoats, sherwanis, formal suits, "
                "wool fabric, khaddar, embroidery, buttons, winter formal clothing. "
            ),
            "Winter_Women": (
                "Focus on Pakistani women's winter wear: khaddar suits, shawls, wool fabric, "
                "winter patterns, three-piece winter sets, embroidered clothing. "
            )
        }
        
        specific = category_instructions.get(category, "Focus on the clothing details.")
        
        format_instruction = (
            "\n\nFormat: Write 2-3 sentences as one continuous paragraph. "
            "Sentence 1-2: Describe clothing (fabric, color, style, cut, patterns). "
            "Sentence 3: Mention model and background briefly. "
            "No newlines, no introductory phrases."
        )
        
        return base_instruction + specific + format_instruction
    
    def generate_caption(self, image_path, category):
        """Generate caption for single image"""
        try:
            print(f"\n[INFO] Processing image: {os.path.basename(image_path)}")
            
            # Load image
            img = Image.open(image_path)
            print(f"[OK] Image loaded: {img.size}")
            
            # Get system instruction
            system_instruction = self.get_system_instruction(category)
            
            # Create model
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            print("[INFO] Generating caption...")
            
            # Generate caption
            response = model.generate_content(
                ["Describe this fashion image following the instructions.", img],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=150
                )
            )
            
            # Extract and clean caption
            caption = response.text.strip()
            
            # Remove any newlines and extra whitespace
            caption = caption.replace('\n', ' ').replace('\r', ' ')
            caption = ' '.join(caption.split())  # Normalize whitespace
            
            # Remove common preambles if present
            preambles = [
                "Here is a caption for the image:",
                "Here is a caption:",
                "Here's a caption for the image:",
                "Here's a caption:",
                "Caption:",
                "This image shows:",
                "The image shows:",
            ]
            
            for preamble in preambles:
                if caption.lower().startswith(preamble.lower()):
                    caption = caption[len(preamble):].strip()
                    break
            
            print(f"[OK] Caption generated ({len(caption)} characters)")
            print(f"[PREVIEW] {caption[:100]}...")
            
            return caption
            
        except Exception as e:
            print(f"[ERROR] Failed to generate caption: {e}")
            return None
    
    def save_to_csv(self, image_filename, caption, csv_path):
        """Save filename and caption to CSV file"""
        try:
            print(f"\n[INFO] Saving to CSV: {csv_path}")
            
            # Check if CSV exists
            file_exists = os.path.exists(csv_path)
            
            # Write to CSV with proper escaping
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
                
                # Write header if new file
                if not file_exists:
                    writer.writerow(['filename', 'caption'])
                    print("[OK] CSV header created")
                
                # Write data row
                writer.writerow([image_filename, caption])
                print("[OK] Data row written")
            
            # Verify the CSV content
            print("\n[VERIFICATION] CSV Content:")
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for i, row in enumerate(reader):
                    if i == 0:
                        print(f"Header: {row}")
                    else:
                        print(f"Row {i}: filename='{row[0]}', caption_length={len(row[1]) if len(row) > 1 else 0}")
                        if len(row) > 1 and row[1]:
                            print(f"Caption: {row[1][:100]}...")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save CSV: {e}")
            return False


def find_sample_image(category):
    """Find a sample image from the specified category"""
    # Map category to folder path
    category_paths = {
        "Summer_Men": os.path.join("data_backup", "Summer", "Men"),
        "Summer_Women": os.path.join("data_backup", "Summer", "Women"),
        "Winter_Men": os.path.join("data_backup", "Winter", "Men"),
        "Winter_Women": os.path.join("data_backup", "Winter", "Women")
    }
    
    category_path = category_paths.get(category)
    if not category_path or not os.path.exists(category_path):
        return None
    
    # Find first image file
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    for filename in os.listdir(category_path):
        if os.path.splitext(filename.lower())[1] in image_extensions:
            return os.path.join(category_path, filename)
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Test single image captioning")
    parser.add_argument('--api-key', required=True, help='Gemini API key')
    parser.add_argument('--category', choices=['Summer_Men', 'Summer_Women', 'Winter_Men', 'Winter_Women'], 
                       default='Summer_Men', help='Category to test')
    parser.add_argument('--image', help='Specific image path (optional)')
    parser.add_argument('--csv-output', help='CSV output file (optional)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SINGLE IMAGE CAPTION TEST")
    print("=" * 60)
    
    # Initialize captioner
    captioner = SimpleCaptionTester(args.api_key)
    
    # Find image to test
    if args.image and os.path.exists(args.image):
        image_path = args.image
        print(f"[OK] Using specified image: {image_path}")
    else:
        image_path = find_sample_image(args.category)
        if not image_path:
            print(f"[ERROR] No sample image found for category: {args.category}")
            exit(1)
        print(f"[OK] Using sample image: {image_path}")
    
    # Set CSV output path
    if args.csv_output:
        csv_path = args.csv_output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"test_single_caption_{args.category}_{timestamp}.csv"
    
    # Generate caption
    caption = captioner.generate_caption(image_path, args.category)
    
    if not caption:
        print("[ERROR] Caption generation failed")
        exit(1)
    
    # Save to CSV
    image_filename = os.path.basename(image_path)
    success = captioner.save_to_csv(image_filename, caption, csv_path)
    
    if success:
        print("\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Image: {image_filename}")
        print(f"Caption: {caption}")
        print(f"CSV: {csv_path}")
    else:
        print("\n[ERROR] Test failed during CSV save")
        exit(1)


if __name__ == '__main__':
    main()