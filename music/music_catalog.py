#!/usr/bin/env python3
"""
Local Music Catalog Builder for Termux (Android)

Scans local music directories, reads ID3 metadata from every .mp3 file,
and writes a CSV index file.  Use this catalog to:
  - Know exactly which songs are on the device without re-scanning
  - Avoid duplicate downloads
  - Feed into playlist generators or the yt_music_sync script

Dependencies: mutagen (auto-installed if missing)
"""

import os
import sys
import csv
import argparse
from datetime import datetime

try:
    from mutagen.id3 import ID3, ID3NoHeaderError
except ImportError:
    print("[*] mutagen not found. Installing...")
    os.system(f"{sys.executable} -m pip install mutagen")
    from mutagen.id3 import ID3, ID3NoHeaderError

try:
    from mutagen.mp3 import MP3
except ImportError:
    from mutagen.mp3 import MP3          # already installed above


# ===================== CONFIGURATION DEFAULTS ==============================

DEFAULT_MUSIC_DIRS = [
    "/storage/emulated/0/Music",
    "/storage/emulated/0/Android/Music",
    "/storage/emulated/0/Download",
]
DEFAULT_CATALOG = "/storage/emulated/0/Music/music_catalog.csv"
AUDIO_EXTENSIONS = {".mp3"}

CSV_FIELDS = [
    "filename",
    "title",
    "artist",
    "album",
    "year",
    "duration_sec",
    "size_kb",
    "path",
]

# ===========================================================================


def _tag_text(tags, key):
    """Safely pull the first text value from an ID3 frame, or ''."""
    frame = tags.get(key)
    if frame and frame.text:
        return str(frame.text[0]).strip()
    return ""


def read_metadata(file_path):
    """Return a dict of metadata for a single mp3 file."""
    filename = os.path.basename(file_path)
    entry = {
        "filename": filename,
        "title": "",
        "artist": "",
        "album": "",
        "year": "",
        "duration_sec": "",
        "size_kb": "",
        "path": file_path,
    }

    # File size
    try:
        entry["size_kb"] = round(os.path.getsize(file_path) / 1024)
    except OSError:
        pass

    # Duration
    try:
        audio = MP3(file_path)
        entry["duration_sec"] = round(audio.info.length)
    except Exception:
        pass

    # ID3 tags
    try:
        tags = ID3(file_path)
        entry["title"]  = _tag_text(tags, "TIT2")
        entry["artist"] = _tag_text(tags, "TPE1")
        entry["album"]  = _tag_text(tags, "TALB")
        entry["year"]   = _tag_text(tags, "TDRC")
    except ID3NoHeaderError:
        pass
    except Exception as e:
        print(f"  [!] Tag error: {filename} — {e}")

    return entry


def scan_directories(music_dirs):
    """Walk directories and yield every mp3 path."""
    for d in music_dirs:
        if not os.path.isdir(d):
            print(f"  [!] Skipping (not found): {d}")
            continue
        for root, _, files in os.walk(d):
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() in AUDIO_EXTENSIONS:
                    yield os.path.join(root, fn)


def write_catalog(entries, output_path):
    """Write the catalog as a UTF-8 CSV file."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for e in entries:
            writer.writerow(e)


def print_summary(entries):
    """Print a quick summary to the terminal."""
    total    = len(entries)
    tagged   = sum(1 for e in entries if e["title"])
    untagged = total - tagged
    artists  = len({e["artist"] for e in entries if e["artist"]})
    albums   = len({e["album"] for e in entries if e["album"]})
    print(f"\n--- Summary ---")
    print(f"  Total files : {total}")
    print(f"  With tags   : {tagged}")
    print(f"  Missing tags: {untagged}")
    print(f"  Artists     : {artists}")
    print(f"  Albums      : {albums}")


def main():
    ap = argparse.ArgumentParser(
        description="Build a CSV catalog of local music metadata (Termux)"
    )
    ap.add_argument(
        "-d", "--music-dirs", nargs="+", default=DEFAULT_MUSIC_DIRS,
        help="Directories to scan (default: Music, Android/Music, Download)"
    )
    ap.add_argument(
        "-o", "--output", default=DEFAULT_CATALOG,
        help=f"Output CSV path (default: {DEFAULT_CATALOG})"
    )
    ap.add_argument(
        "--append", action="store_true",
        help="Append to an existing catalog instead of overwriting"
    )
    ap.add_argument(
        "--show-untagged", action="store_true",
        help="Print files that have no ID3 title tag"
    )
    args = ap.parse_args()

    print(f"[1/3] Scanning: {', '.join(args.music_dirs)}")
    paths = list(scan_directories(args.music_dirs))
    print(f"      Found {len(paths)} mp3 file(s)")

    if not paths:
        sys.exit("No mp3 files found.")

    # If appending, load existing entries to avoid duplicates
    existing_paths = set()
    existing_entries = []
    if args.append and os.path.isfile(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_entries.append(row)
                existing_paths.add(row.get("path", ""))
        print(f"      Existing catalog: {len(existing_entries)} entries")

    print(f"\n[2/3] Reading metadata...")
    entries = list(existing_entries)
    new_count = 0
    for i, p in enumerate(paths, 1):
        if p in existing_paths:
            continue
        entry = read_metadata(p)
        entries.append(entry)
        new_count += 1
        # Progress every 50 files
        if new_count % 50 == 0:
            print(f"      Processed {new_count} new files...")

    print(f"      New entries: {new_count}")

    print(f"\n[3/3] Writing catalog: {args.output}")
    write_catalog(entries, args.output)
    print(f"      Total entries: {len(entries)}")

    print_summary(entries)

    if args.show_untagged:
        untagged = [e for e in entries if not e["title"]]
        if untagged:
            print(f"\n--- Untagged files ({len(untagged)}) ---")
            for e in untagged:
                print(f"  {e['filename']}")
                print(f"    {e['path']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
