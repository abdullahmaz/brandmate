"""
Rename images in fine_tuning/data_backup into consistent short prefixes.

Mapping (final names):
- Summer/Men   -> sm_1.jpg, sm_2.jpg, ...
- Summer/Women -> sw_1.jpg, sw_2.jpg, ...
- Winter/Men   -> wm_1.jpg, wm_2.jpg, ...
- Winter/Women -> ww_1.jpg, ww_2.jpg, ...

The script performs a two-phase rename to avoid collisions: first renames originals to a temporary name, then renames temporaries to final names.

Usage:
  python rename_images.py --root "<path to fine_tuning/data_backup>" [--execute] [--dry-run]

By default it shows a dry-run. Use --execute to actually rename files.
"""

import argparse
import os
import uuid
from pathlib import Path

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}

PREFIX_MAP = {
    ('Summer', 'Men'): 'sm',
    ('Summer', 'Women'): 'sw',
    ('Winter', 'Men'): 'wm',
    ('Winter', 'Women'): 'ww',
}


def gather_image_files(root: Path):
    """Return dict mapping (season, gender) -> list[Path] of images"""
    result = {}
    for season in ('Summer', 'Winter'):
        for gender in ('Men', 'Women'):
            p = root / season / gender
            files = []
            if p.exists() and p.is_dir():
                for entry in sorted(p.iterdir(), key=lambda x: x.name.lower()):
                    if entry.is_file() and entry.suffix.lower() in IMAGE_EXTS:
                        files.append(entry)
            result[(season, gender)] = files
    return result


def plan_new_names(files, prefix):
    """Given a list of Path, return mapping old->new Path (same parent)
    with numbering starting at 1 and preserving extension.
    """
    mapping = {}
    used = set()
    i = 1
    for f in files:
        ext = f.suffix.lower()
        candidate = f.parent / f"{prefix}_{i}{ext}"
        # avoid duplicates: if candidate already used, increment until free
        while str(candidate).lower() in used or candidate.exists():
            i += 1
            candidate = f.parent / f"{prefix}_{i}{ext}"
        mapping[f] = candidate
        used.add(str(candidate).lower())
        i += 1
    return mapping


def two_phase_rename(mapping, execute=False):
    """Rename files using temporary intermediate names then to final names.
    mapping: dict old_path -> final_path
    If execute False, just print the planned changes.
    """
    if not mapping:
        return {'renamed': 0, 'skipped': 0}

    # Phase 0: show dry-run
    if not execute:
        print("Dry-run planned renames:")
        for old, new in mapping.items():
            print(f"  {old.name} -> {new.name}")
        print(f"Total: {len(mapping)} files would be renamed.")
        return {'renamed': 0, 'skipped': 0}

    # Phase 1: rename to temp names
    temp_map = {}
    for old in mapping.keys():
        unique = f".tmprename_{uuid.uuid4().hex}{old.suffix}"
        temp_path = old.parent / unique
        try:
            os.rename(old, temp_path)
            temp_map[temp_path] = mapping[old]
        except Exception as e:
            print(f"[ERROR] failed to rename {old} -> {temp_path}: {e}")

    # Phase 2: rename temps to final names
    renamed = 0
    skipped = 0
    for temp, final in temp_map.items():
        try:
            if final.exists():
                # if final already exists (unlikely), add a suffix
                base = final.stem
                ext = final.suffix
                j = 1
                candidate = final.parent / f"{base}_dup{j}{ext}"
                while candidate.exists():
                    j += 1
                    candidate = final.parent / f"{base}_dup{j}{ext}"
                final = candidate
            os.rename(temp, final)
            print(f"RENAMED: {temp.name} -> {final.name}")
            renamed += 1
        except Exception as e:
            print(f"[ERROR] failed to rename {temp} -> {final}: {e}")
            try:
                # attempt to move back
                original_name = temp.name
                print(f"[WARN] leaving temp file: {original_name}")
            except:
                pass
            skipped += 1

    return {'renamed': renamed, 'skipped': skipped}


def main():
    parser = argparse.ArgumentParser(description='Rename images in data_backup to compact prefixes')
    parser.add_argument('--root', type=str, default='data_backup', help='Path to data_backup folder')
    parser.add_argument('--execute', action='store_true', help='Actually perform renames (default: dry-run)')
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        # try relative to this script
        root = Path(__file__).resolve().parent / args.root

    if not root.exists():
        print(f"[ERROR] Root path does not exist: {args.root} (tried {root})")
        return

    print(f"Scanning root: {root}")
    files_by_cat = gather_image_files(root)

    total_to_rename = 0
    overall_mapping = {}

    for (season, gender), files in files_by_cat.items():
        prefix = PREFIX_MAP.get((season, gender))
        if not prefix:
            print(f"Skipping unknown category: {season}/{gender}")
            continue
        if not files:
            print(f"No images found in: {season}/{gender}")
            continue
        mapping = plan_new_names(files, prefix)
        total_to_rename += len(mapping)
        overall_mapping.update(mapping)
        print(f"Planned {len(mapping)} renames for {season}/{gender} -> prefix '{prefix}_'")

    if not overall_mapping:
        print("Nothing to rename.")
        return

    print(f"\nTOTAL planned renames: {total_to_rename}\n")

    result = two_phase_rename(overall_mapping, execute=args.execute)
    print(f"\nSummary: renamed={result.get('renamed',0)} skipped={result.get('skipped',0)}")


if __name__ == '__main__':
    main()
