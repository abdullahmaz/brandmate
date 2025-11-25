import os
from PIL import Image, ImageEnhance, ImageFilter
import random
from tqdm import tqdm
import shutil

class DatasetBalancer:
    def __init__(self, data_root="./data", target_count=2000):
        self.data_root = data_root
        self.target_count = target_count
        self.categories = ["Winter/Men", "Winter/Women", "Summer/Men", "Summer/Women"]
    
    def get_augmentation_pipeline(self, image, augmentation_type):
        """Apply different augmentation techniques with stronger variations"""
        
        augmentations = {
            # Basic transformations
            "horizontal_flip": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
            
            # Stronger brightness variations (±35%)
            "brightness_high": lambda img: ImageEnhance.Brightness(img).enhance(1.35),
            "brightness_low": lambda img: ImageEnhance.Brightness(img).enhance(0.65),
            "brightness_medium_high": lambda img: ImageEnhance.Brightness(img).enhance(1.25),
            "brightness_medium_low": lambda img: ImageEnhance.Brightness(img).enhance(0.75),
            
            # Stronger contrast variations (±50%)
            "contrast_high": lambda img: ImageEnhance.Contrast(img).enhance(1.5),
            "contrast_low": lambda img: ImageEnhance.Contrast(img).enhance(0.5),
            "contrast_medium": lambda img: ImageEnhance.Contrast(img).enhance(1.3),
            
            # Color/Saturation variations (±40%)
            "saturation_high": lambda img: ImageEnhance.Color(img).enhance(1.4),
            "saturation_low": lambda img: ImageEnhance.Color(img).enhance(0.6),
            "saturation_boost": lambda img: ImageEnhance.Color(img).enhance(1.6),
            "desaturate": lambda img: ImageEnhance.Color(img).enhance(0.4),
            
            # Sharpness and blur
            "sharp": lambda img: ImageEnhance.Sharpness(img).enhance(2.0),
            "blur_light": lambda img: img.filter(ImageFilter.GaussianBlur(radius=1.5)),
            "blur_medium": lambda img: img.filter(ImageFilter.GaussianBlur(radius=2.5)),
            
            # Rotation variations (±10 degrees)
            "rotate_10": lambda img: img.rotate(10, expand=False, fillcolor=(255, 255, 255)),
            "rotate_minus_10": lambda img: img.rotate(-10, expand=False, fillcolor=(255, 255, 255)),
            "rotate_7": lambda img: img.rotate(7, expand=False, fillcolor=(255, 255, 255)),
            "rotate_minus_7": lambda img: img.rotate(-7, expand=False, fillcolor=(255, 255, 255)),
            
            # Zoom variations
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "center_crop": self._center_crop,
            
            # Color temperature shifts
            "warm_tone": self._warm_tone,
            "cool_tone": self._cool_tone,
            
            # Combined augmentations for more variety
            "flip_bright_high": lambda img: ImageEnhance.Brightness(
                img.transpose(Image.FLIP_LEFT_RIGHT)
            ).enhance(1.3),
            
            "flip_contrast_high": lambda img: ImageEnhance.Contrast(
                img.transpose(Image.FLIP_LEFT_RIGHT)
            ).enhance(1.4),
            
            "flip_saturate": lambda img: ImageEnhance.Color(
                img.transpose(Image.FLIP_LEFT_RIGHT)
            ).enhance(1.5),
            
            "rotate_bright": lambda img: ImageEnhance.Brightness(
                img.rotate(8, expand=False, fillcolor=(255, 255, 255))
            ).enhance(1.25),
            
            "rotate_contrast": lambda img: ImageEnhance.Contrast(
                img.rotate(-8, expand=False, fillcolor=(255, 255, 255))
            ).enhance(1.35),
            
            "zoom_saturate": lambda img: ImageEnhance.Color(
                self._zoom_in(img)
            ).enhance(1.3),
            
            "zoom_bright": lambda img: ImageEnhance.Brightness(
                self._zoom_in(img)
            ).enhance(1.2),
            
            # Triple combinations for strong variety
            "flip_rotate_bright": lambda img: ImageEnhance.Brightness(
                img.transpose(Image.FLIP_LEFT_RIGHT).rotate(6, expand=False, fillcolor=(255, 255, 255))
            ).enhance(1.25),
            
            "flip_zoom_contrast": lambda img: ImageEnhance.Contrast(
                self._zoom_in(img.transpose(Image.FLIP_LEFT_RIGHT))
            ).enhance(1.3),
        }
        
        return augmentations[augmentation_type](image)
    
    def _crop_and_zoom(self, image):
        """Crop center and zoom slightly"""
        width, height = image.size
        crop_percent = 0.9
        left = int(width * (1 - crop_percent) / 2)
        top = int(height * (1 - crop_percent) / 2)
        right = int(width * (1 + crop_percent) / 2)
        bottom = int(height * (1 + crop_percent) / 2)
        
        cropped = image.crop((left, top, right, bottom))
        return cropped.resize((width, height), Image.LANCZOS)
    
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
        # Increase red channel, slightly increase green
        enhancer = ImageEnhance.Color(image)
        colored = enhancer.enhance(1.2)
        
        # Convert to RGB and adjust channels
        r, g, b = colored.split()
        r = ImageEnhance.Brightness(r).enhance(1.15)
        g = ImageEnhance.Brightness(g).enhance(1.05)
        
        return Image.merge('RGB', (r, g, b))
    
    def _cool_tone(self, image):
        """Add cool color temperature (more blue)"""
        # Increase blue channel
        enhancer = ImageEnhance.Color(image)
        colored = enhancer.enhance(1.1)
        
        # Convert to RGB and adjust channels
        r, g, b = colored.split()
        b = ImageEnhance.Brightness(b).enhance(1.15)
        g = ImageEnhance.Brightness(g).enhance(1.05)
        
        return Image.merge('RGB', (r, g, b))
    
    def count_images(self, folder_path):
        """Count images in a folder"""
        if not os.path.exists(folder_path):
            print(f"Warning: {folder_path} does not exist!")
            return 0
        
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        count = 0
        
        try:
            files = os.listdir(folder_path)
            for f in files:
                if os.path.isfile(os.path.join(folder_path, f)):
                    if os.path.splitext(f.lower())[1] in valid_extensions:
                        count += 1
        except Exception as e:
            print(f"Error counting images in {folder_path}: {str(e)}")
            return 0
        
        return count
    
    def get_current_counts(self):
        """Get actual current counts from filesystem"""
        counts = {}
        for category in self.categories:
            folder_path = os.path.join(self.data_root, category)
            counts[category] = self.count_images(folder_path)
        return counts
    
    def verify_structure(self):
        """Verify the data folder structure"""
        print("\n" + "="*60)
        print("VERIFYING DATA STRUCTURE")
        print("="*60)
        
        print(f"\nData root: {os.path.abspath(self.data_root)}")
        
        if not os.path.exists(self.data_root):
            print(f"ERROR: Data root '{self.data_root}' does not exist!")
            return False
        
        all_exist = True
        for category in self.categories:
            folder_path = os.path.join(self.data_root, category)
            exists = os.path.exists(folder_path)
            status = "[OK]" if exists else "[MISSING]"
            print(f"{status} {folder_path}")
            if not exists:
                all_exist = False
        
        print("="*60)
        return all_exist
    
    def augment_category(self, category_path, num_to_generate):
        """Augment images in a specific category"""
        
        folder_path = os.path.join(self.data_root, category_path)
        
        if not os.path.exists(folder_path):
            print(f"Warning: {folder_path} does not exist!")
            return
        
        # Get all existing images
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_files = []
        
        try:
            files = os.listdir(folder_path)
            for f in files:
                full_path = os.path.join(folder_path, f)
                if os.path.isfile(full_path):
                    if os.path.splitext(f.lower())[1] in valid_extensions:
                        image_files.append(f)
        except Exception as e:
            print(f"Error reading folder {folder_path}: {str(e)}")
            return
        
        if not image_files:
            print(f"No images found in {folder_path}")
            return
        
        print(f"\n{'='*60}")
        print(f"Augmenting: {category_path}")
        print(f"Current images: {len(image_files)}")
        print(f"Need to generate: {num_to_generate}")
        print(f"{'='*60}")
        
        # List of stronger augmentation techniques (32 different transformations)
        augmentation_types = [
            # Basic
            "horizontal_flip",
            
            # Brightness (4 variations)
            "brightness_high", "brightness_low", 
            "brightness_medium_high", "brightness_medium_low",
            
            # Contrast (3 variations)
            "contrast_high", "contrast_low", "contrast_medium",
            
            # Saturation (4 variations)
            "saturation_high", "saturation_low", 
            "saturation_boost", "desaturate",
            
            # Sharpness/Blur (3 variations)
            "sharp", "blur_light", "blur_medium",
            
            # Rotation (4 variations)
            "rotate_10", "rotate_minus_10", 
            "rotate_7", "rotate_minus_7",
            
            # Zoom (3 variations)
            "zoom_in", "zoom_out", "center_crop",
            
            # Color temperature (2 variations)
            "warm_tone", "cool_tone",
            
            # Combined augmentations (10 variations)
            "flip_bright_high", "flip_contrast_high", "flip_saturate",
            "rotate_bright", "rotate_contrast",
            "zoom_saturate", "zoom_bright",
            "flip_rotate_bright", "flip_zoom_contrast",
        ]
        
        generated = 0
        attempts = 0
        max_attempts = num_to_generate * 2
        
        progress_bar = tqdm(total=num_to_generate, desc="Generating augmented images")
        
        while generated < num_to_generate and attempts < max_attempts:
            attempts += 1
            
            # Randomly select an image
            source_image_name = random.choice(image_files)
            source_image_path = os.path.join(folder_path, source_image_name)
            
            # Randomly select augmentation type
            aug_type = random.choice(augmentation_types)
            
            try:
                # Load and augment image
                img = Image.open(source_image_path).convert("RGB")
                augmented_img = self.get_augmentation_pipeline(img, aug_type)
                
                # Generate new filename
                base_name, ext = os.path.splitext(source_image_name)
                new_filename = f"{base_name}_aug_{generated}_{aug_type}{ext}"
                new_path = os.path.join(folder_path, new_filename)
                
                # Avoid overwriting existing files
                if os.path.exists(new_path):
                    continue
                
                # Save augmented image
                augmented_img.save(new_path, quality=95)
                generated += 1
                progress_bar.update(1)
                
            except Exception as e:
                print(f"\nError processing {source_image_name}: {str(e)}")
                continue
        
        progress_bar.close()
        print(f"[SUCCESS] Generated {generated} augmented images for {category_path}")
    
    def balance_dataset(self):
        """Balance entire dataset"""
        
        print("\n" + "="*60)
        print("DATASET BALANCING - Starting")
        print("="*60)
        
        # Get current counts
        current_counts = self.get_current_counts()
        
        print("\nCurrent Distribution:")
        print("-" * 60)
        total_current = 0
        for category in self.categories:
            count = current_counts.get(category, 0)
            needed = max(0, self.target_count - count)
            print(f"{category:20s}: {count:4d} images | Need: {needed:4d} more")
            total_current += count
        print("-" * 60)
        print(f"{'TOTAL':20s}: {total_current:4d} images")
        
        # Augment each category
        for category in self.categories:
            count = current_counts.get(category, 0)
            num_needed = self.target_count - count
            
            if num_needed > 0:
                self.augment_category(category, num_needed)
            else:
                print(f"\n[OK] {category} already has enough images ({count})")
        
        # Verify final counts
        print("\n" + "="*60)
        print("DATASET BALANCING - Complete")
        print("="*60)
        
        final_counts = self.get_current_counts()
        print("\nFinal Distribution:")
        print("-" * 60)
        total_final = 0
        for category in self.categories:
            count = final_counts.get(category, 0)
            print(f"{category:20s}: {count:4d} images")
            total_final += count
        print("-" * 60)
        print(f"{'TOTAL':20s}: {total_final:4d} images")
        print("="*60)
    
    def create_backup(self, backup_dir="./data_backup"):
        """Create backup before augmentation"""
        print(f"\n{'='*60}")
        print("CREATING BACKUP")
        print(f"{'='*60}")
        print(f"Backup location: {os.path.abspath(backup_dir)}")
        
        if os.path.exists(backup_dir):
            print("Backup already exists. Skipping...")
            return
        
        try:
            shutil.copytree(self.data_root, backup_dir)
            print("[SUCCESS] Backup created successfully!")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            print("Continuing without backup...")
        
        print("="*60)

def main():
    """Main execution function"""
    
    # Configuration
    DATA_ROOT = "./data"
    TARGET_COUNT = 2500
    CREATE_BACKUP = True
    
    # Initialize balancer
    balancer = DatasetBalancer(data_root=DATA_ROOT, target_count=TARGET_COUNT)
    
    # Verify structure first
    if not balancer.verify_structure():
        print("\nERROR: Some folders are missing. Please check your data structure.")
        print("\nExpected structure:")
        print("  data/")
        print("  ├── Winter/")
        print("  │   ├── Men/")
        print("  │   └── Women/")
        print("  └── Summer/")
        print("      ├── Men/")
        print("      └── Women/")
        return
    
    # Optional: Create backup
    if CREATE_BACKUP:
        balancer.create_backup()
    
    # Balance the dataset
    balancer.balance_dataset()
    
    print("\n[SUCCESS] Dataset balancing completed successfully!")
    print(f"All categories now have approximately {TARGET_COUNT} images each.")

if __name__ == "__main__":
    main()

