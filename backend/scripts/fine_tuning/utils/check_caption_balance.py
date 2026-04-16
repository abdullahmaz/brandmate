"""
Caption Balance Checker
Analyzes the current balance of captions across all categories
"""

import os
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

def main():
    print("📊 CAPTION BALANCE ANALYSIS")
    print("=" * 50)
    
    CATEGORIES = [
        "Summer_Men",
        "Summer_Women", 
        "Winter_Men",
        "Winter_Women"
    ]
    
    print("Finding latest CSV files for each category...")
    category_counts = {}
    file_info = {}
    
    for category in CATEGORIES:
        latest_file, count = find_latest_csv_for_category(category)
        category_counts[category] = count
        if latest_file:
            file_info[category] = os.path.basename(latest_file)
        else:
            file_info[category] = "No file found"
    
    print("=" * 50)
    
    # Display counts and file info
    for category in CATEGORIES:
        count = category_counts[category]
        file_name = file_info[category]
        print(f"{category:15}: {count:4} captions ({file_name})")
    
    # Calculate statistics
    counts = list(category_counts.values())
    total_captions = sum(counts)
    
    if total_captions == 0:
        print(f"\n⚠️ No caption files found!")
        return
    
    min_count = min(counts)
    max_count = max(counts)
    avg_count = total_captions / len(CATEGORIES)
    imbalance = max_count - min_count
    
    print(f"\n📈 Statistics:")
    print(f"Total captions: {total_captions}")
    print(f"Average per category: {avg_count:.1f}")
    print(f"Min: {min_count} | Max: {max_count}")
    print(f"Imbalance: {imbalance}")
    
    # Balance assessment
    print(f"\n⚖️ Balance Assessment:")
    if imbalance == 0:
        print("✅ Perfect balance - all categories equal!")
    elif imbalance <= 5:
        print("🟢 Very well balanced")
    elif imbalance <= 20:
        print("🟡 Moderately balanced") 
    elif imbalance <= 50:
        print("🟠 Somewhat imbalanced")
    else:
        print("🔴 Significantly imbalanced")
    
    # Show gaps
    print(f"\n📊 Gaps from maximum ({max_count}):")
    for category, count in category_counts.items():
        gap = max_count - count
        if gap == 0:
            print(f"{category:15}: No gap (at maximum)")
        else:
            print(f"{category:15}: {gap:4} captions behind")
    
    # Recommendations
    total_gap = sum(max_count - count for count in counts)
    print(f"\n💡 Recommendations:")
    print(f"Total captions needed to balance: {total_gap}")
    
    if total_gap == 0:
        print("All categories are balanced. Continue with equal distribution.")
    else:
        print("Run the balanced captioning script to prioritize categories with fewer captions.")
        
        # Sort by priority (least captions first)
        sorted_categories = sorted(CATEGORIES, key=lambda x: category_counts[x])
        print(f"\nPriority order (least to most captions):")
        for i, category in enumerate(sorted_categories, 1):
            count = category_counts[category]
            gap = max_count - count
            print(f"{i}. {category:15}: {count:4} captions (gap: {gap})")

if __name__ == "__main__":
    main()