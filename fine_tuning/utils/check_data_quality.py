#!/usr/bin/env python3
"""
Data Quality Checker for Fine-Tuning
====================================
Checks image dimensions, formats, and dataset balance
"""

import os
from pathlib import Path
from PIL import Image
import csv

def check_images(data_root="data_backup"):
    """Check image quality and dimensions with detailed analysis"""
    categories = ["Summer/Men", "Summer/Women", "Winter/Men", "Winter/Women"]
    
    print("🔍 DETAILED IMAGE ANALYSIS")
    print("=" * 50)
    
    total_issues = 0
    all_dimensions = []
    
    for category in categories:
        cat_path = Path(data_root) / category
        if not cat_path.exists():
            print(f"❌ {category}: Directory not found")
            continue
            
        images = list(cat_path.glob("*.jpg")) + list(cat_path.glob("*.png"))
        
        # Counters for different size categories
        tiny_images = 0      # < 256px
        small_images = 0     # 256-511px  
        good_images = 0      # 512-1023px
        large_images = 0     # 1024-2047px
        huge_images = 0      # >= 2048px
        format_issues = 0
        aspect_issues = 0
        
        dimensions_list = []
        aspect_ratios = []
        
        sample_size = min(20, len(images))  # Check more images for better analysis
        
        print(f"\n📁 {category}:")
        print(f"   Total images: {len(images)}")
        
        for i, img_path in enumerate(images[:sample_size]):
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    dimensions_list.append((width, height))
                    all_dimensions.append((width, height))
                    
                    # Calculate aspect ratio
                    aspect_ratio = width / height
                    aspect_ratios.append(aspect_ratio)
                    
                    if i < 3:  # Show first 3 images as samples
                        print(f"   Sample {i+1}: {img_path.name} - {width}x{height} - {img.mode} - AR: {aspect_ratio:.2f}")
                    
                    # Categorize by size
                    min_dim = min(width, height)
                    max_dim = max(width, height)
                    
                    if min_dim < 256:
                        tiny_images += 1
                    elif min_dim < 512:
                        small_images += 1
                    elif max_dim < 1024:
                        good_images += 1
                    elif max_dim < 2048:
                        large_images += 1
                    else:
                        huge_images += 1
                    
                    # Check aspect ratio (too extreme ratios can cause issues)
                    if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                        aspect_issues += 1
                    
                    # Check format
                    if img.mode not in ['RGB', 'RGBA']:
                        format_issues += 1
                        
            except Exception as e:
                format_issues += 1
                print(f"   ❌ Error reading {img_path.name}: {e}")
        
        # Calculate statistics
        if dimensions_list:
            avg_width = sum(d[0] for d in dimensions_list) / len(dimensions_list)
            avg_height = sum(d[1] for d in dimensions_list) / len(dimensions_list)
            avg_aspect = sum(aspect_ratios) / len(aspect_ratios)
            
            print(f"   📏 Average size: {avg_width:.0f}x{avg_height:.0f} (AR: {avg_aspect:.2f})")
        
        # Size distribution
        print(f"   📊 Size Distribution (of {sample_size} checked):")
        if tiny_images > 0:
            print(f"      🔴 Tiny (<256px):     {tiny_images:2} - ❌ Too small for training")
            total_issues += tiny_images
        if small_images > 0:
            print(f"      🟡 Small (256-511px): {small_images:2} - ⚠️  Will be upscaled")
        if good_images > 0:
            print(f"      🟢 Good (512-1023px): {good_images:2} - ✅ Perfect for training")
        if large_images > 0:
            print(f"      🔵 Large (1024-2047px):{large_images:2} - ✅ Great quality")
        if huge_images > 0:
            print(f"      🟣 Huge (≥2048px):    {huge_images:2} - ℹ️  Will be downscaled")
            
        # Report other issues
        if aspect_issues > 0:
            print(f"   ⚠️  {aspect_issues}/{sample_size} images have extreme aspect ratios (very tall/wide)")
            
        if format_issues > 0:
            print(f"   ❌ {format_issues}/{sample_size} images have format issues")
            total_issues += format_issues
    
    return total_issues, all_dimensions

def check_captions(captions_root="captions"):
    """Check caption quality and balance"""
    print(f"\n📝 CAPTION ANALYSIS")
    print("=" * 50)
    
    categories = ["Summer_Men", "Summer_Women", "Winter_Men", "Winter_Women"]
    caption_counts = {}
    
    for category in categories:
        csv_file = Path(captions_root) / f"captions_{category}.csv"
        
        if not csv_file.exists():
            print(f"❌ {category}: Caption file not found")
            caption_counts[category] = 0
            continue
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                captions = list(reader)
                count = len(captions)
                caption_counts[category] = count
                
                # Sample caption quality
                if captions:
                    sample_caption = captions[0]['caption']
                    print(f"{category:15}: {count:3} captions")
                    print(f"{'':15}   Sample: \"{sample_caption[:60]}...\"")
                    
                    # Check format
                    if sample_caption.startswith(("A man wearing", "A woman wearing")):
                        print(f"{'':15}   ✅ Good format")
                    else:
                        print(f"{'':15}   ⚠️  Format needs improvement")
                else:
                    print(f"{category:15}: {count:3} captions (EMPTY)")
                    
        except Exception as e:
            print(f"❌ Error reading {category}: {e}")
            caption_counts[category] = 0
    
    # Balance analysis
    print(f"\n📊 DATASET BALANCE:")
    total = sum(caption_counts.values())
    min_count = min(caption_counts.values())
    max_count = max(caption_counts.values())
    
    print(f"   Total captions: {total}")
    print(f"   Range: {min_count} - {max_count}")
    print(f"   Imbalance: {max_count - min_count}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    for category, count in caption_counts.items():
        if count < 50:
            print(f"   ⚠️  {category}: Add {50-count}+ more images/captions")
        elif count < 100:
            print(f"   ℹ️  {category}: Could benefit from {100-count}+ more samples")
        else:
            print(f"   ✅ {category}: Good sample count")
    
    return caption_counts

def check_requirements():
    """Check system requirements"""
    print(f"\n💻 SYSTEM REQUIREMENTS")
    print("=" * 50)
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"   ✅ GPU: {gpu_name}")
            print(f"   ✅ VRAM: {gpu_memory:.1f}GB")
            
            if gpu_memory < 8:
                print(f"   ⚠️  Recommended: 8GB+ VRAM for stable training")
            else:
                print(f"   ✅ VRAM sufficient for training")
        else:
            print(f"   ❌ CUDA not available - GPU required for fine-tuning")
    except ImportError:
        print(f"   ❌ PyTorch not installed")
    
    # Check other requirements
    required_packages = ['diffusers', 'transformers', 'peft', 'accelerate']
    missing = []
    
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"   ✅ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"   ❌ {pkg}")
    
    if missing:
        print(f"\n   Install missing packages:")
        print(f"   pip install {' '.join(missing)}")

def explain_image_sizing():
    """Explain how image sizing works in fine-tuning"""
    print(f"\n📐 IMAGE SIZING FOR FINE-TUNING - EXPLAINED")
    print("=" * 60)
    
    print("❓ DO ALL IMAGES NEED TO BE THE SAME SIZE?")
    print("   ✅ NO! Images can have different dimensions")
    print("   ✅ The training script automatically resizes ALL images to 512x512")
    print("   ✅ This happens during training, your original files are unchanged")
    
    print(f"\n🎯 WHAT HAPPENS TO DIFFERENT SIZED IMAGES:")
    print("   📱 Small (400x600)    → Upscaled to 512x512    → ⚠️  May lose quality")
    print("   💻 Medium (600x800)   → Resized to 512x512     → ✅ Good quality")  
    print("   🖥️  Large (1200x1600) → Downscaled to 512x512  → ✅ Excellent quality")
    print("   📺 Huge (2400x3200)   → Downscaled to 512x512  → ✅ Great (but slower)")
    
    print(f"\n🎨 ASPECT RATIO HANDLING:")
    print("   📏 Original: 600x900 (2:3 ratio) → Resized: 512x512 (1:1 ratio)")
    print("   ⚠️  Aspect ratio changes during training!")
    print("   ✅ This is NORMAL and expected in Stable Diffusion training")
    print("   ✅ The model learns to generate square images (512x512)")
    
    print(f"\n💡 RECOMMENDATIONS BY SOURCE SIZE:")
    print("   🔴 < 256px:     ❌ Avoid - Too small, will be very blurry")
    print("   🟡 256-511px:   ⚠️  OK but not ideal - Will be upscaled")  
    print("   🟢 512-1023px:  ✅ Perfect - Minimal processing needed")
    print("   🔵 1024-2047px: ✅ Excellent - High quality after downscale")
    print("   🟣 ≥2048px:     ✅ Great but unnecessary - Wastes processing time")
    
    print(f"\n🚀 BOTTOM LINE:")
    print("   ✅ Your images can be ANY size - the system handles it!")
    print("   ✅ Bigger source images = Better training quality")
    print("   ✅ Mix of sizes is totally fine")
    print("   ❌ Just avoid tiny images (<256px)")

def main():
    print("🎨 FINE-TUNING DATA QUALITY CHECKER")
    print("=" * 60)
    
    # Check images with detailed analysis
    image_issues, all_dimensions = check_images()
    
    # Show sizing explanation
    explain_image_sizing()
    
    # Analyze overall dimension statistics
    if all_dimensions:
        print(f"\n📊 OVERALL DATASET STATISTICS")
        print("=" * 50)
        
        widths = [d[0] for d in all_dimensions]
        heights = [d[1] for d in all_dimensions]
        
        print(f"   📏 Width range:  {min(widths)} - {max(widths)}px")
        print(f"   📏 Height range: {min(heights)} - {max(heights)}px") 
        print(f"   📏 Average size: {sum(widths)/len(widths):.0f}x{sum(heights)/len(heights):.0f}px")
        
        # Count size categories across all images
        tiny = sum(1 for w, h in all_dimensions if min(w, h) < 256)
        small = sum(1 for w, h in all_dimensions if 256 <= min(w, h) < 512)
        good = sum(1 for w, h in all_dimensions if 512 <= max(w, h) < 1024)
        large = sum(1 for w, h in all_dimensions if 1024 <= max(w, h) < 2048)
        huge = sum(1 for w, h in all_dimensions if max(w, h) >= 2048)
        
        total_checked = len(all_dimensions)
        print(f"\n   📈 Size Distribution Summary ({total_checked} samples):")
        if tiny > 0:
            print(f"      🔴 Too small:  {tiny:3} ({tiny/total_checked*100:.1f}%) - ❌ Consider replacing")
        if small > 0:
            print(f"      🟡 Small:      {small:3} ({small/total_checked*100:.1f}%) - ⚠️  Will be upscaled")
        if good > 0:
            print(f"      🟢 Perfect:    {good:3} ({good/total_checked*100:.1f}%) - ✅ Ideal for training")
        if large > 0:
            print(f"      🔵 Large:      {large:3} ({large/total_checked*100:.1f}%) - ✅ Excellent quality")
        if huge > 0:
            print(f"      🟣 Very large: {huge:3} ({huge/total_checked*100:.1f}%) - ✅ Great (overkill)")
    
    # Check captions
    caption_counts = check_captions()
    
    # Check system requirements
    check_requirements()
    
    # Final assessment
    print(f"\n🎯 READINESS ASSESSMENT")
    print("=" * 50)
    
    total_captions = sum(caption_counts.values())
    min_captions = min(caption_counts.values()) if caption_counts.values() else 0
    
    ready = True
    issues = []
    
    if total_captions < 200:
        issues.append("Dataset too small (need 200+ total captions)")
        ready = False
    elif min_captions < 30:
        issues.append("Some categories have too few samples")
        ready = False
    
    if image_issues > 10:
        issues.append("Significant image quality issues detected")
        ready = False
    
    # Check for tiny images specifically
    if all_dimensions:
        tiny_count = sum(1 for w, h in all_dimensions if min(w, h) < 256)
        if tiny_count > len(all_dimensions) * 0.1:  # More than 10% tiny
            issues.append(f"Too many tiny images ({tiny_count})")
            ready = False
    
    if ready:
        print("✅ Dataset ready for fine-tuning!")
        print("🚀 Run: cd training && python launch_training.py")
        
        # Give optimization tips
        print(f"\n💡 OPTIMIZATION TIPS:")
        print("   🎯 Your dataset will work great as-is!")
        print("   ⚡ Training will auto-resize all images to 512x512")
        print("   📈 Larger source images will give better results")
        print("   🔄 Different sizes are perfectly fine - no need to pre-resize")
        
    else:
        print("⚠️  Dataset needs attention before training")
        for issue in issues:
            print(f"   ❌ {issue}")
        print("\n📝 Address the issues above, then re-run this checker")

if __name__ == "__main__":
    main()