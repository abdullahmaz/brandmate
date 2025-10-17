"""
Test runner: caption one image from each category to verify CSV output and progress tracking.
Usage:
  python test_caption_one_each.py --api-keys <key1> [<key2> ...] [--dry-run]

If --dry-run is passed, the script will only show which images would be processed (no API calls).
"""

import os
import sys
import subprocess
import argparse
from datetime import date

CATEGORIES = [
    "Summer_Men",
    "Summer_Women",
    "Winter_Men",
    "Winter_Women"
]

SCRIPT = os.path.join(os.path.dirname(__file__), "gemini_caption_csv_batch.py")


def run_test_for_category(category, api_keys, data_root="data_backup", dry_run=False):
    today = date.today().strftime('%Y%m%d')
    csv_filename = f"test_captions_{category}_{today}.csv"
    # place CSV inside the fine_tuning folder (same cwd used for subprocess)
    cwd = os.path.dirname(__file__)
    csv_output = os.path.join(cwd, csv_filename)

    cmd = [sys.executable, SCRIPT,
           "--category", category,
           "--data-root", data_root,
           "--csv-output", csv_output,
           "--batch-size", "1",
           "--daily-limit", "3",
           "--api-keys"] + api_keys

    if dry_run:
        print(f"DRY RUN: would run command: {' '.join(cmd)}")
        # Instead, print first uncaptioned image (absolute path)
        category_path = os.path.join(os.path.dirname(__file__), data_root, *category.split('_'))
        if not os.path.exists(category_path):
            print(f"[ERROR] Category path not found: {category_path}")
            return False
        imgs = [f for f in os.listdir(category_path) if os.path.splitext(f)[1].lower() in ('.jpg', '.jpeg', '.png', '.webp')]
        sample = imgs[:1]
        if sample:
            print(f"Sample image for {category}: {os.path.join(category_path, sample[0])}")
        else:
            print(f"No images found in {category_path}")
        return True

    print(f"Running test for {category} -> {csv_output}")
    try:
        # Run from the fine_tuning directory so relative paths inside the batch script resolve correctly
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=cwd)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Test for {category} failed:")
        print(e.stdout)
        print(e.stderr)
        return False

    # Print resulting CSV (first 5 lines)
    if os.path.exists(csv_output):
        print(f"\nCSV output ({csv_output}):")
        with open(csv_output, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                print(line.strip())
                if i >= 4:
                    break
    else:
        print(f"[ERROR] CSV file not created: {csv_output}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-keys', nargs='+', required=True)
    parser.add_argument('--data-root', default='data_backup')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print("Test caption: 1 image per category")
    successes = 0
    for cat in CATEGORIES:
        ok = run_test_for_category(cat, args.api_keys, data_root=args.data_root, dry_run=args.dry_run)
        if ok:
            successes += 1
    print(f"\nTests passed: {successes}/{len(CATEGORIES)}")

if __name__ == '__main__':
    main()
