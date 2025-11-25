"""
Test script to preview augmentation effects on sample images
Run this before full augmentation to see the results
"""

import os
from PIL import Image, ImageEnhance, ImageFilter
import random

class AugmentationPreviewer:
    def __init__(self, sample_image_path, output_dir="./augmentation_preview"):
        self.sample_image_path = sample_image_path
        self.output_dir = output_dir
        
        # Create output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _zoom_in(self, image):
        """Zoom in by 15% (crop center and resize)"""
        width, height = image.size
        crop_percent = 0.85
        left = int(width * (1 - crop_percent) / 2)
        top = int(height * (1 - crop_percent) / 2)
        right = int(width * (1 + crop_percent) / 2)
        bottom = int(height * (1 + crop_percent) / 2)
        
        cropped = image.crop((left, top, right, bottom))
        return cropped.resize((width, height), Image.LANCZOS)
    
    def _zoom_out(self, image):
        """Zoom out by adding border"""
        width, height = image.size
        new_size = int(width * 0.85), int(height * 0.85)
        resized = image.resize(new_size, Image.LANCZOS)
        
        # Create white canvas and paste resized image in center
        canvas = Image.new('RGB', (width, height), (255, 255, 255))
        offset = ((width - new_size[0]) // 2, (height - new_size[1]) // 2)
        canvas.paste(resized, offset)
        return canvas
    
    def _center_crop(self, image):
        """Crop to center 80%"""
        width, height = image.size
        crop_percent = 0.80
        left = int(width * (1 - crop_percent) / 2)
        top = int(height * (1 - crop_percent) / 2)
        right = int(width * (1 + crop_percent) / 2)
        bottom = int(height * (1 + crop_percent) / 2)
        
        cropped = image.crop((left, top, right, bottom))
        return cropped.resize((width, height), Image.LANCZOS)
    
    def _warm_tone(self, image):
        """Add warm color temperature (more red/yellow)"""
        enhancer = ImageEnhance.Color(image)
        colored = enhancer.enhance(1.2)
        
        r, g, b = colored.split()
        r = ImageEnhance.Brightness(r).enhance(1.15)
        g = ImageEnhance.Brightness(g).enhance(1.05)
        
        return Image.merge('RGB', (r, g, b))
    
    def _cool_tone(self, image):
        """Add cool color temperature (more blue)"""
        enhancer = ImageEnhance.Color(image)
        colored = enhancer.enhance(1.1)
        
        r, g, b = colored.split()
        b = ImageEnhance.Brightness(b).enhance(1.15)
        g = ImageEnhance.Brightness(g).enhance(1.05)
        
        return Image.merge('RGB', (r, g, b))
    
    def get_augmentation_pipeline(self, image, augmentation_type):
        """Apply augmentation"""
        
        augmentations = {
            # Basic transformations
            "original": lambda img: img,
            "horizontal_flip": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
            
            # Brightness variations
            "brightness_high": lambda img: ImageEnhance.Brightness(img).enhance(1.35),
            "brightness_low": lambda img: ImageEnhance.Brightness(img).enhance(0.65),
            
            # Contrast variations
            "contrast_high": lambda img: ImageEnhance.Contrast(img).enhance(1.5),
            "contrast_low": lambda img: ImageEnhance.Contrast(img).enhance(0.5),
            
            # Saturation variations
            "saturation_boost": lambda img: ImageEnhance.Color(img).enhance(1.6),
            "desaturate": lambda img: ImageEnhance.Color(img).enhance(0.4),
            
            # Sharpness and blur
            "sharp": lambda img: ImageEnhance.Sharpness(img).enhance(2.0),
            "blur_medium": lambda img: img.filter(ImageFilter.GaussianBlur(radius=2.5)),
            
            # Rotation
            "rotate_10": lambda img: img.rotate(10, expand=False, fillcolor=(255, 255, 255)),
            "rotate_minus_10": lambda img: img.rotate(-10, expand=False, fillcolor=(255, 255, 255)),
            
            # Zoom
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "center_crop": self._center_crop,
            
            # Color temperature
            "warm_tone": self._warm_tone,
            "cool_tone": self._cool_tone,
            
            # Combined
            "flip_bright_high": lambda img: ImageEnhance.Brightness(
                img.transpose(Image.FLIP_LEFT_RIGHT)
            ).enhance(1.3),
            
            "flip_saturate": lambda img: ImageEnhance.Color(
                img.transpose(Image.FLIP_LEFT_RIGHT)
            ).enhance(1.5),
            
            "rotate_bright": lambda img: ImageEnhance.Brightness(
                img.rotate(8, expand=False, fillcolor=(255, 255, 255))
            ).enhance(1.25),
            
            "zoom_saturate": lambda img: ImageEnhance.Color(
                self._zoom_in(img)
            ).enhance(1.3),
            
            "flip_rotate_bright": lambda img: ImageEnhance.Brightness(
                img.transpose(Image.FLIP_LEFT_RIGHT).rotate(6, expand=False, fillcolor=(255, 255, 255))
            ).enhance(1.25),
        }
        
        return augmentations[augmentation_type](image)
    
    def preview_all_augmentations(self):
        """Generate previews of all augmentation types"""
        
        print(f"\nLoading sample image: {self.sample_image_path}")
        
        if not os.path.exists(self.sample_image_path):
            print(f"ERROR: Sample image not found!")
            return
        
        # Load original image
        original_image = Image.open(self.sample_image_path).convert("RGB")
        
        # List of augmentations to preview
        augmentation_types = [
            "original",
            "horizontal_flip",
            "brightness_high", "brightness_low",
            "contrast_high", "contrast_low",
            "saturation_boost", "desaturate",
            "sharp", "blur_medium",
            "rotate_10", "rotate_minus_10",
            "zoom_in", "zoom_out", "center_crop",
            "warm_tone", "cool_tone",
            "flip_bright_high", "flip_saturate",
            "rotate_bright", "zoom_saturate",
            "flip_rotate_bright",
        ]
        
        print(f"\nGenerating {len(augmentation_types)} preview images...")
        print(f"Output directory: {os.path.abspath(self.output_dir)}")
        print("="*60)
        
        for i, aug_type in enumerate(augmentation_types, 1):
            try:
                # Apply augmentation
                augmented = self.get_augmentation_pipeline(original_image, aug_type)
                
                # Save preview
                output_path = os.path.join(self.output_dir, f"{i:02d}_{aug_type}.jpg")
                augmented.save(output_path, quality=95)
                
                print(f"[{i:2d}/{len(augmentation_types)}] [OK] {aug_type}")
                
            except Exception as e:
                print(f"[{i:2d}/{len(augmentation_types)}] [ERROR] {aug_type}: {str(e)}")
        
        print("="*60)
        print(f"\n[SUCCESS] Preview complete! Check the '{self.output_dir}' folder.")
        print(f"  Compare the augmented images with the original to see the strength.")

def main():
    """Main function to run augmentation preview"""
    
    print("\n" + "="*60)
    print("AUGMENTATION PREVIEW TOOL")
    print("="*60)
    
    # Find a sample image from your dataset
    data_root = "./data"
    sample_image = None
    
    # Try to find an image from Winter/Men
    for category in ["Winter/Men", "Winter/Women", "Summer/Men", "Summer/Women"]:
        category_path = os.path.join(data_root, category)
        if os.path.exists(category_path):
            files = os.listdir(category_path)
            image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if image_files:
                # Pick a non-augmented image (doesn't contain 'aug' in name)
                original_files = [f for f in image_files if 'aug' not in f.lower()]
                if original_files:
                    sample_image = os.path.join(category_path, original_files[0])
                    break
    
    if not sample_image:
        print("\nERROR: No sample image found in data folder!")
        print("Please make sure you have images in data/Winter/Men or other categories.")
        return
    
    print(f"\nUsing sample image: {sample_image}")
    
    # Create previewer and generate samples
    previewer = AugmentationPreviewer(sample_image)
    previewer.preview_all_augmentations()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Open the 'augmentation_preview' folder")
    print("2. Compare the augmented images with '01_original.jpg'")
    print("3. If the augmentations look good, run: py -3 augment_dataset.py")
    print("4. If too strong/weak, adjust the enhancement values in augment_dataset.py")
    print("="*60)

if __name__ == "__main__":
    main()

