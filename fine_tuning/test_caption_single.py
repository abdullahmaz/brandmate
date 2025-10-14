"""
Test caption generation on a single image using GIT model
Based on: https://huggingface.co/docs/transformers/main/tasks/image_captioning
"""

import os
import sys
from PIL import Image

# Check if required packages are installed
try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    from accelerate import Accelerator
    import torch
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: Required packages not installed!")
    print("=" * 60)
    print("\nPlease install them using:")
    print("  pip install transformers accelerate torch Pillow")
    print("=" * 60)
    sys.exit(1)


def test_single_image():
    """Test caption generation on a single sample image"""
    
    print("\n" + "=" * 60)
    print("TESTING CAPTION GENERATION - GIT Model")
    print("=" * 60)
    print()
    
    # Find a sample image
    sample_paths = [
        os.path.join("data", "Winter", "Men"),
        os.path.join("data", "Winter", "Women"),
        os.path.join("data", "Summer", "Men"),
        os.path.join("data", "Summer", "Women"),
    ]
    
    sample_image = None
    category = None
    
    print("Looking for sample image...")
    for path in sample_paths:
        if os.path.exists(path):
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
            images = [f for f in os.listdir(path) 
                     if os.path.splitext(f.lower())[1] in image_extensions]
            if images:
                sample_image = os.path.join(path, images[0])
                category_name = os.path.basename(path)  # Men/Women
                season = os.path.basename(os.path.dirname(path))  # Winter/Summer
                category = f"{season}_{category_name}"
                break
    
    if not sample_image:
        print("\n[ERROR] No images found in data folder!")
        print("Please make sure your images are in:")
        print("  - data/Winter/Men/")
        print("  - data/Winter/Women/")
        print("  - data/Summer/Men/")
        print("  - data/Summer/Women/")
        return
    
    print(f"[OK] Found sample: {sample_image}")
    print(f"[OK] Category: {category}")
    print()
    
    # Load model
    print("Loading GIT model (microsoft/git-base)...")
    print("(This may take a few minutes on first run)")
    print()
    
    device = Accelerator().device
    print(f"Using device: {device}")
    
    if device.type == "cpu":
        print("NOTE: Running on CPU (slower). Consider using GPU for full dataset.")
    
    print()
    
    try:
        processor = AutoProcessor.from_pretrained("microsoft/git-base")
        model = AutoModelForCausalLM.from_pretrained("microsoft/git-base").to(device)
        
        print("[OK] Model loaded successfully!")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to load model: {e}")
        print("\nPossible solutions:")
        print("1. Check internet connection (model downloads on first run)")
        print("2. Install transformers: pip install transformers")
        print("3. Try running on Google Colab with GPU")
        return
    
    # Generate caption
    print("-" * 60)
    print("GENERATING CAPTION")
    print("-" * 60)
    
    try:
        # Load and process image
        image = Image.open(sample_image).convert('RGB')
        print(f"Image size: {image.size}")
        
        # Prepare image for the model
        inputs = processor(images=image, return_tensors="pt").to(device)
        pixel_values = inputs.pixel_values
        
        # Generate caption
        generated_ids = model.generate(pixel_values=pixel_values, max_length=50)
        base_caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        print(f"\nBase caption: {base_caption}")
        
        # Add category enhancement
        category_keywords = {
            "Winter_Men": "pakistani winter men's formal wear, waistcoat,",
            "Winter_Women": "pakistani winter women's clothing, khaddar fabric,",
            "Summer_Men": "pakistani summer men's eastern wear, kurta,",
            "Summer_Women": "pakistani summer women's lawn fabric, unstitched,"
        }
        
        enhancement = category_keywords.get(category, "")
        enhanced_caption = f"{enhancement} {base_caption}"
        
        print(f"\nEnhanced caption:")
        print(f"  {enhanced_caption}")
        
        print()
        print("-" * 60)
        print("[SUCCESS] Caption generation test complete!")
        print("-" * 60)
        print()
        print("What this caption will look like in the .txt file:")
        print(f"\n{os.path.splitext(sample_image)[0]}.txt:")
        print(f'"{enhanced_caption}"')
        print()
        print("If you're happy with this quality, run:")
        print("  py -3 caption_generator.py --test 10")
        print()
        print("To process the full dataset, run:")
        print("  py -3 caption_generator.py")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to generate caption: {e}")
        print("\nPlease check:")
        print("1. Image file is valid")
        print("2. Enough memory available")
        print("3. All packages installed correctly")
        return


if __name__ == "__main__":
    test_single_image()

