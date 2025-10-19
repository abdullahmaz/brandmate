"""
Daily Caption Processing Runner
Runs the batch captioning process daily for all categories
"""

import os
import sys
import subprocess
from datetime import date
from dotenv import load_dotenv
import csv

def find_latest_csv_for_category(category):
    """Find the CSV file for a category (fixed filename without date)"""
    csv_file = f"captions/captions_{category}.csv"
    
    if not os.path.exists(csv_file):
        return None, 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Subtract 1 for header row
            count = sum(1 for row in reader) - 1
            return csv_file, max(0, count)  # Ensure non-negative
    except Exception as e:
        print(f"Warning: Could not read {csv_file}: {e}")
        return csv_file, 0

def get_category_caption_count(category):
    """Get the current number of captions for a category from latest CSV file"""
    latest_file, count = find_latest_csv_for_category(category)
    return count

def analyze_caption_balance(categories):
    """Analyze caption distribution and calculate priority order"""
    print("🔍 Analyzing caption balance across categories...")
    print("=" * 60)
    
    category_counts = {}
    for category in categories:
        count = get_category_caption_count(category)
        category_counts[category] = count
        print(f"{category:15}: {count:4} captions")
    
    # Calculate statistics
    total_captions = sum(category_counts.values())
    min_count = min(category_counts.values())
    max_count = max(category_counts.values())
    avg_count = total_captions / len(categories)
    imbalance = max_count - min_count
    
    print(f"\n📊 Balance Analysis:")
    print(f"Total captions: {total_captions}")
    print(f"Average per category: {avg_count:.1f}")
    print(f"Range: {min_count} - {max_count} (imbalance: {imbalance})")
    
    # Sort categories by count (least to most) for priority processing
    sorted_categories = sorted(categories, key=lambda x: category_counts[x])
    
    print(f"\n🎯 Processing Priority (least to most captions):")
    for i, category in enumerate(sorted_categories, 1):
        count = category_counts[category]
        gap = max_count - count
        print(f"{i}. {category:15}: {count:4} captions (gap: {gap})")
    
    return sorted_categories, category_counts, imbalance

def calculate_target_distribution(category_counts, available_quota):
    """Calculate how many captions each category should get"""
    current_counts = list(category_counts.values())
    categories = list(category_counts.keys())
    
    # Target: bring all categories up to the same level
    max_current = max(current_counts)
    
    # Calculate gaps
    gaps = {cat: max_current - count for cat, count in category_counts.items()}
    total_gap = sum(gaps.values())
    
    if total_gap == 0:
        # Already balanced, distribute evenly
        per_category = available_quota // len(categories)
        targets = {cat: per_category for cat in categories}
    elif total_gap <= available_quota:
        # Can close all gaps and distribute remaining evenly
        remaining = available_quota - total_gap
        per_category_bonus = remaining // len(categories)
        targets = {cat: gaps[cat] + per_category_bonus for cat in categories}
    else:
        # Prioritize closing gaps proportionally
        targets = {}
        for cat in categories:
            proportion = gaps[cat] / total_gap
            targets[cat] = int(available_quota * proportion)
    
    return targets

def estimate_available_quota(api_keys):
    """Estimate available quota by testing API keys"""
    print("🔍 Checking API key status...")
    
    # Test each API key to see if it's working
    valid_working_keys = []
    
    for i, key in enumerate(api_keys, 1):
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Test with a simple prompt
            response = model.generate_content("Test")
            if response and response.text:
                valid_working_keys.append(key)
                print(f"  Key #{i}: ✅ Working")
            else:
                print(f"  Key #{i}: ❌ No response")
        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                print(f"  Key #{i}: ❌ Quota exhausted")
            else:
                print(f"  Key #{i}: ❌ Error: {str(e)[:50]}...")
    
    # Estimate quota: ~40 images per working key
    estimated_quota = len(valid_working_keys) * 40
    print(f"📊 Working keys: {len(valid_working_keys)}/{len(api_keys)}")
    print(f"📊 Estimated available quota: ~{estimated_quota} images")
    
    return estimated_quota, valid_working_keys

def load_api_keys_from_env():
    """Load API keys from .env file"""
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
    
    api_keys = []
    for i in range(1, 6):  # Load up to 5 API keys
        key = os.getenv(f'GEMINI_API_KEY_{i}')
        if key:
            api_keys.append(key)
    
    return api_keys

def run_captioning_for_category(category, api_keys, data_root="data_backup", batch_size=100):
    """Run captioning for a single category"""
    
    print(f"\n{'=' * 50}")
    print(f"Processing: {category}")
    print(f"{'=' * 50}")
    print(f"Using {len(api_keys)} API key(s)")
    print(f"Batch size: {batch_size} images per key")
    # Construct command
    script_dir = os.path.dirname(os.path.abspath(__file__))
    batch_script = os.path.join(script_dir, "gemini_caption_csv_batch.py")
    cmd = [
        sys.executable,
        batch_script,
        "--category", category,
        "--data-root", data_root,
        "--batch-size", str(batch_size),
        "--api-keys"
    ] + api_keys
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to process {category}:")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error processing {category}: {e}")
        return False


def main():
    print("=" * 60)
    print("DAILY CAPTION PROCESSING RUNNER - BALANCED")
    print(f"Date: {date.today()}")
    print("=" * 60)
    
    # Load API keys from .env file
    API_KEYS = load_api_keys_from_env()
    
    if not API_KEYS:
        print("❌ No API keys found in .env file!")
        print("Please check your .env file contains GEMINI_API_KEY_1, etc.")
        return
    
    CATEGORIES = [
        "Summer_Men",
        "Summer_Women", 
        "Winter_Men",
        "Winter_Women"
    ]
    
    DATA_ROOT = "data_backup"
    
    # Validate API keys
    valid_keys = [key for key in API_KEYS if key and key != "YOUR_API_KEY_1_HERE" and "YOUR_API_KEY" not in key]
    
    if not valid_keys:
        print("\n[ERROR] No valid API keys configured!")
        print("Please edit your .env file and add your Gemini API keys.")
        print("Get your keys from: https://aistudio.google.com/apikey")
        return
    
    print(f"Using {len(valid_keys)} API key(s)")
    
    # Get dynamic quota estimation
    estimated_quota, working_keys = estimate_available_quota(valid_keys)
    
    if estimated_quota == 0:
        print("\n❌ No working API keys available!")
        print("All keys appear to be exhausted. Please try again later.")
        return
    
    # Analyze current caption balance
    priority_categories, category_counts, imbalance = analyze_caption_balance(CATEGORIES)
    
    if imbalance == 0:
        print("\n✅ Categories are perfectly balanced!")
        print("🎯 Processing all categories equally...")
        processing_order = CATEGORIES
    else:
        print(f"\n⚖️ Imbalance detected: {imbalance} captions")
        print("🎯 Prioritizing categories with fewer captions...")
        processing_order = priority_categories
    
    # Calculate target distribution using dynamic quota
    targets = calculate_target_distribution(category_counts, estimated_quota)
    
    print(f"\n🎯 Target Distribution:")
    for category in processing_order:
        current = category_counts[category]
        target = targets[category]
        print(f"{category:15}: {current:4} → {current + target:4} (+{target})")
    
    total_target = sum(targets.values())
    print(f"Total planned: {total_target} new captions")
    
    # Process categories in priority order
    total_processed = 0
    successful_categories = 0
    
    for category in processing_order:
        target_for_category = targets[category]
        
        if target_for_category <= 0:
            print(f"\n⏭️ Skipping {category} (already at target)")
            continue
            
        print(f"\n{'=' * 50}")
        print(f"Processing: {category} (Target: +{target_for_category})")
        print(f"Priority: {processing_order.index(category) + 1}/{len(processing_order)}")
        print(f"{'=' * 50}")
        
        # Dynamic batch size: conservative per-key limit based on working keys
        per_key_quota = 40 if len(working_keys) > 0 else 20
        dynamic_batch_size = min(target_for_category, per_key_quota)
        
        success = run_captioning_for_category(
            category=category,
            api_keys=working_keys,  # Use only working keys
            data_root=DATA_ROOT,
            batch_size=dynamic_batch_size
        )
        
        if success:
            successful_categories += 1
            # Get actual count after processing
            new_count = get_category_caption_count(category)
            processed_this_category = new_count - category_counts[category]
            total_processed += processed_this_category
            print(f"✅ {category}: +{processed_this_category} captions (now {new_count})")
        else:
            print(f"❌ {category}: Processing failed")
            # If a category fails, others might still work, so continue
    
    # Final balance report
    print(f"\n{'=' * 60}")
    print("📊 FINAL BALANCE REPORT")
    print(f"{'=' * 60}")
    
    print("Updated caption counts:")
    final_counts = {}
    for category in CATEGORIES:
        count = get_category_caption_count(category)
        final_counts[category] = count
        change = count - category_counts[category]
        change_str = f"(+{change})" if change > 0 else f"({change})" if change < 0 else "(no change)"
        print(f"{category:15}: {count:4} captions {change_str}")
    
    # Calculate final balance
    final_min = min(final_counts.values())
    final_max = max(final_counts.values())
    final_imbalance = final_max - final_min
    final_total = sum(final_counts.values())
    
    print(f"\nBalance Summary:")
    print(f"Total captions: {final_total} (+{total_processed})")
    print(f"Range: {final_min} - {final_max}")
    print(f"Imbalance: {final_imbalance} (was {imbalance})")
    
    if final_imbalance == 0:
        print("🎉 Perfect balance achieved!")
    elif final_imbalance < imbalance:
        improvement = imbalance - final_imbalance
        print(f"📈 Balance improved by {improvement} captions!")
    else:
        print("⚠️ Balance unchanged or worsened")
    
    print(f"\nProcessed {successful_categories}/{len(CATEGORIES)} categories successfully")
    
    if successful_categories > 0:
        print("\n💡 Run again tomorrow to continue balancing with fresh quotas!")
    else:
        print("\n⚠️ No categories processed - check API quotas or connectivity")


if __name__ == "__main__":
    main()