"""
Test Gemini caption generation on a single image
"""

import os
import sys

# Check if required packages are installed
try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print("\n" + "=" * 60)
    print("ERROR: Required package not installed!")
    print("=" * 60)
    print(f"\n{e}")
    print("\nPlease install using:")
    print("  pip install google-generativeai Pillow")
    print("=" * 60)
    sys.exit(1)


def test_single_image(api_key, image_path=None):
    """Test caption generation on a single image"""
    
    print("\n" + "=" * 60)
    print("TESTING GEMINI CAPTION GENERATION")
    print("=" * 60)
    print()
    
    # Find a sample image if not provided
    if not image_path:
        sample_paths = [
            os.path.join("data", "Summer", "Men"),
            os.path.join("data", "Winter", "Men"),
            os.path.join("data", "Winter", "Women"),
            os.path.join("data", "Summer", "Women"),
        ]
        
        print("Looking for sample image...")
        for path in sample_paths:
            if os.path.exists(path):
                image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
                images = [f for f in os.listdir(path) 
                         if os.path.splitext(f.lower())[1] in image_extensions]
                if images:
                    image_path = os.path.join(path, images[0])
                    break
        
        if not image_path:
            print("\n[ERROR] No images found in data folder!")
            return
    
    # Determine category from path
    if "Winter" in image_path and "Men" in image_path:
        category = "Winter_Men"
    elif "Winter" in image_path and "Women" in image_path:
        category = "Winter_Women"
    elif "Summer" in image_path and "Men" in image_path:
        category = "Summer_Men"
    elif "Summer" in image_path and "Women" in image_path:
        category = "Summer_Women"
    else:
        category = "Unknown"
    
    print(f"[OK] Sample image: {image_path}")
    print(f"[OK] Category: {category}")
    print()
    
    # Initialize Gemini
    print("Initializing Gemini API...")
    genai.configure(api_key=api_key)
    print("[OK] API configured\n")
    
    # Category-specific system instructions
    system_instructions = {
        "Winter_Men": (
            "You are an expert fashion image captioning assistant specializing in Pakistani clothing. "
            "Generate precise, detailed captions for model fine-tuning. "
            "Focus primarily on the CLOTHING and FASHION details, then mention other visible elements. "
            "This image shows Pakistani men's winter formal wear. "
            "Describe the type of clothing (waistcoat, coat, sherwani, suit, shalwar kameez), "
            "fabric type (wool, khaddar, blended), colors, patterns (plain, embroidered, printed), "
            "fit (slim, regular, loose), styling details (buttons, collar, pockets, embroidery). "
            "Then briefly mention the model's pose, background, and any accessories (shoes, watch). "
            "Use terms like: waistcoat, sherwani, shalwar kameez, kurta, formal wear, winter clothing. "
            "\n\nFormat: Write 2-4 sentences. "
            "Start with clothing description (1-2 sentences), then add context (1-2 sentences). "
            "Use clear, factual language. Avoid artistic or subjective phrases. "
            "Be specific about colors, fabrics, and clothing types."
        ),
        "Summer_Men": (
            "You are an expert fashion image captioning assistant specializing in Pakistani clothing. "
            "Generate precise, detailed captions for model fine-tuning. "
            "Focus primarily on the CLOTHING and FASHION details, then mention other visible elements. "
            "This image shows Pakistani men's summer eastern wear. "
            "Describe the type of clothing (kurta, shalwar kameez, casual eastern wear), "
            "fabric type (lawn, cotton, linen, cambric), colors, patterns, fit, collar style. "
            "Then mention the model's styling, pose, and background. "
            "Use terms like: shalwar kameez, kurta, lawn fabric, summer wear, eastern clothing, casual. "
            "\n\nFormat: Write 2-4 sentences. "
            "Start with clothing description (1-2 sentences), then add context (1-2 sentences). "
            "Use clear, factual language. Avoid artistic or subjective phrases. "
            "Be specific about colors, fabrics, and clothing types."
        ),
        "Winter_Women": (
            "You are an expert fashion image captioning assistant specializing in Pakistani clothing. "
            "Generate precise, detailed captions for model fine-tuning. "
            "Focus primarily on the CLOTHING and FASHION details, then mention other visible elements. "
            "This image shows Pakistani women's winter clothing. "
            "Describe the type of outfit (khaddar suit, shawl, printed fabric, three-piece unstitched), "
            "fabric type (khaddar, karandi, linen, wool), colors, print patterns (floral, geometric, striped), "
            "embroidery details, styling. Then mention the model's appearance, pose, and background. "
            "Use terms like: khaddar, three-piece, unstitched, dupatta, printed, embroidered, winter collection. "
            "\n\nFormat: Write 2-4 sentences. "
            "Start with clothing description (1-2 sentences), then add context (1-2 sentences). "
            "Use clear, factual language. Avoid artistic or subjective phrases. "
            "Be specific about colors, fabrics, and clothing types."
        ),
        "Summer_Women": (
            "You are an expert fashion image captioning assistant specializing in Pakistani clothing. "
            "Generate precise, detailed captions for model fine-tuning. "
            "Focus primarily on the CLOTHING and FASHION details, then mention other visible elements. "
            "This image shows Pakistani women's summer lawn clothing. "
            "Describe the outfit type (lawn suit, unstitched fabric, three-piece, printed lawn), "
            "fabric quality (lawn, cotton, silk blend), colors, print style (floral, abstract, traditional), "
            "design details, embroidery or embellishments. Then mention styling and background. "
            "Use terms like: lawn fabric, unstitched, three-piece suit, printed, summer collection, dupatta. "
            "\n\nFormat: Write 2-4 sentences. "
            "Start with clothing description (1-2 sentences), then add context (1-2 sentences). "
            "Use clear, factual language. Avoid artistic or subjective phrases. "
            "Be specific about colors, fabrics, and clothing types."
        )
    }
    
    system_instruction = system_instructions.get(category, system_instructions["Summer_Men"])
    
    # Generate caption
    print("-" * 60)
    print("GENERATING CAPTION...")
    print("-" * 60)
    print()
    
    try:
        # Load image
        img = Image.open(image_path)
        
        # Create model with system instruction
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp',
            system_instruction=system_instruction
        )
        
        # Generate caption
        response = model.generate_content([
            "Caption this image following the instructions.",
            img
        ], generation_config=genai.types.GenerationConfig(temperature=0.4))
        
        caption = response.text.strip()
        
        print("Generated Caption:")
        print("-" * 60)
        print(caption)
        print("-" * 60)
        print()
        
        # Show what it will look like in file
        caption_file = os.path.splitext(image_path)[0] + ".txt"
        print(f"This will be saved to:")
        print(f"  {caption_file}")
        print()
        
        print("[SUCCESS] Caption generated successfully!")
        print()
        print("If you're happy with this quality, run one category (5 images test):")
        print(f'  py -3 gemini_caption_generator.py --api-key {api_key} --category {category} --test 5')
        print()
        print("Or process a full category:")
        print(f'  py -3 gemini_caption_generator.py --api-key {api_key} --category {category}')
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to generate caption: {e}")
        print("\nPlease check:")
        print("1. API key is valid")
        print("2. Internet connection is working")
        print("3. Image file is valid")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage: py -3 test_gemini_caption.py YOUR_API_KEY [image_path]")
        print("\nExample:")
        print("  py -3 test_gemini_caption.py AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo")
        print("  py -3 test_gemini_caption.py YOUR_API_KEY data/Winter/Men/Winter_Men_0001.jpg")
        print()
        sys.exit(1)
    
    api_key = sys.argv[1]
    image_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_single_image(api_key, image_path)
