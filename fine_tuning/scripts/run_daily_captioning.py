"""
Daily Caption Processing Runner
Runs the batch captioning process daily for all categories
"""

import os
import sys
import subprocess
from datetime import date
from dotenv import load_dotenv

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
        "--batch-size", "125",
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
    print("DAILY CAPTION PROCESSING RUNNER")
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
    BATCH_SIZE = 100
    
    # Validate API keys
    valid_keys = [key for key in API_KEYS if key and key != "YOUR_API_KEY_1_HERE" and "YOUR_API_KEY" not in key]
    
    if not valid_keys:
        print("\n[ERROR] No valid API keys configured!")
        print("Please edit this script and add your Gemini API keys.")
        print("Get your keys from: https://aistudio.google.com/apikey")
        return
    
    print(f"Using {len(valid_keys)} API key(s)")
    print(f"Batch size: {BATCH_SIZE} images per key")
    print(f"Max images per category today: {len(valid_keys) * BATCH_SIZE}")
    print()
    
    # Process each category
    success_count = 0
    
    for category in CATEGORIES:
        success = run_captioning_for_category(
            category=category,
            api_keys=valid_keys,
            data_root=DATA_ROOT,
            batch_size=BATCH_SIZE
        )
        
        if success:
            success_count += 1
    
    # Final summary
    print("\n" + "=" * 60)
    print("DAILY RUN COMPLETE")
    print("=" * 60)
    print(f"Categories processed successfully: {success_count}/{len(CATEGORIES)}")
    print(f"Failed categories: {len(CATEGORIES) - success_count}")
    
    if success_count == len(CATEGORIES):
        print("\n[SUCCESS] All categories processed!")
    else:
        print(f"\n[WARNING] Some categories failed. Check logs above.")
    
    print(f"\nRun this script again tomorrow to continue processing.")
    print("CSV files are saved with date stamps for tracking progress.")
    print("=" * 60)


if __name__ == "__main__":
    main()