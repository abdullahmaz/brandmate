import os

categories = ["Winter/Men", "Winter/Women", "Summer/Men", "Summer/Women"]

print("\nRestored Dataset Counts:")
print("-" * 40)

total = 0
for cat in categories:
    cat_path = os.path.join("data", cat)
    if os.path.exists(cat_path):
        files = os.listdir(cat_path)
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        count = len(image_files)
        print(f"{cat:20s}: {count} images")
        total += count

print("-" * 40)
print(f"TOTAL:               {total} images\n")

