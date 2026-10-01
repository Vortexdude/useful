#!/usr/bin/env python3
"""
YouTube Music Playlist Sync for Termux (Android)

Fetches a YouTube Music playlist by URL, fuzzy-matches songs against
local .mp3 files, renames them to "Title - Artist.mp3", and creates
an M3U playlist for Phonograph.

Dependencies: ytmusicapi, mutagen (auto-installed if missing)
Standard lib only: os, sys, re, argparse, difflib, pathlib
"""

import os
import re
import sys
import argparse
from difflib import SequenceMatcher
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-install ytmusicapi if missing (Termux-friendly)
# ---------------------------------------------------------------------------
try:
    from ytmusicapi import YTMusic
except ImportError:
    print("[*] ytmusicapi not found. Installing...")
    os.system(f"{sys.executable} -m pip install ytmusicapi")
    from ytmusicapi import YTMusic

try:
    from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC
except ImportError:
    print("[*] mutagen not found. Installing...")
    os.system(f"{sys.executable} -m pip install mutagen")
    from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC


# ===================== CONFIGURATION DEFAULTS ==============================

DEFAULT_MUSIC_DIRS = [
    "/storage/emulated/0/Music",
    "/storage/emulated/0/Android/Music",
    "/storage/emulated/0/Download",
]
DEFAULT_OUTPUT_DIR = "/storage/emulated/0/Music"
MATCH_THRESHOLD = 0.50          # minimum fuzzy score to accept a match
AUDIO_EXTENSIONS = {".mp3"}     # extend if needed later

# ===========================================================================


def extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from a YouTube Music URL, or return as-is."""
    for pattern in (
        r"[?&]list=([a-zA-Z0-9_-]+)",
        r"playlist[/=]([a-zA-Z0-9_-]+)",
    ):
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)
    return url_or_id


def fetch_playlist(playlist_id: str):
    """Return (playlist_name, [{'title', 'artist', 'album', 'year'}, ...])."""
    yt = YTMusic()
    data = yt.get_playlist(playlist_id, limit=None)
    songs = []
    for track in data.get("tracks", []):
        title = track.get("title", "").strip()
        artists = ", ".join(
            a.get("name", "") for a in track.get("artists", []) if a.get("name")
        )
        album_info = track.get("album") or {}
        album = album_info.get("name", "") if isinstance(album_info, dict) else ""
        year = str(track.get("year", "")).strip()
        if title:
            songs.append({
                "title": title,
                "artist": artists,
                "album": album,
                "year": year,
            })
    return data.get("title", "Playlist"), songs


# --------------- fuzzy matching helpers ------------------------------------

def _normalize(text: str) -> str:
    """Lower-case, strip brackets/feat/ft, remove special chars."""
    t = text.lower().strip()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\[.*?\]", "", t)
    t = re.sub(r"feat\.?\s.*", "", t, flags=re.I)
    t = re.sub(r"ft\.?\s.*", "", t, flags=re.I)
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def find_best_match(song, local_files, threshold, used):
    """Return (local_file_dict, score) or (None, 0)."""
    title, artist = song["title"], song["artist"]
    combined = f"{title} {artist}"
    dash_form = f"{title} - {artist}"

    best, best_score = None, 0.0

    for lf in local_files:
        if lf["path"] in used:
            continue
        name = lf["name"]  # filename without extension

        scores = [
            _ratio(combined, name),
            _ratio(title, name),
            _ratio(dash_form, name),
        ]

        # If local name has " - ", try both orderings
        if " - " in name:
            left, right = name.split(" - ", 1)
            scores += [
                _ratio(title, left.strip()),
                _ratio(title, right.strip()),
                0.5 * _ratio(artist, left) + 0.5 * _ratio(title, right),
                0.5 * _ratio(artist, right) + 0.5 * _ratio(title, left),
            ]

        score = max(scores)
        if score > best_score:
            best_score, best = score, lf

    return (best, best_score) if best_score >= threshold else (None, 0.0)


# --------------- local file scanning --------------------------------------

def scan_local_music(music_dirs):
    """Walk directories and collect mp3 file metadata."""
    files = []
    for d in music_dirs:
        if not os.path.isdir(d):
            print(f"  [!] Skipping (not found): {d}")
            continue
        for root, _, names in os.walk(d):
            for fn in names:
                ext = os.path.splitext(fn)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    full = os.path.join(root, fn)
                    files.append({
                        "path": full,
                        "dir": root,
                        "filename": fn,
                        "name": os.path.splitext(fn)[0],
                    })
    return files


# --------------- ID3 metadata tagging -------------------------------------

def tag_file(file_path, song, dry_run=False):
    """
    Check ID3 tags on an mp3 file and fill in any missing fields
    (title, artist, album, year) using data from YouTube Music.
    """
    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()
    except Exception as e:
        print(f"    Tag read error: {e}")
        return

    changed = False

    # Title (TIT2)
    if not tags.get("TIT2") and song.get("title"):
        tags.add(TIT2(encoding=3, text=[song["title"]]))
        changed = True

    # Artist (TPE1)
    if not tags.get("TPE1") and song.get("artist"):
        tags.add(TPE1(encoding=3, text=[song["artist"]]))
        changed = True

    # Album (TALB)
    if not tags.get("TALB") and song.get("album"):
        tags.add(TALB(encoding=3, text=[song["album"]]))
        changed = True

    # Year (TDRC)
    if not tags.get("TDRC") and song.get("year"):
        tags.add(TDRC(encoding=3, text=[song["year"]]))
        changed = True

    if not changed:
        return

    if dry_run:
        missing = []
        if not ID3(file_path).get("TIT2") and song.get("title"):
            missing.append("title")
        if not ID3(file_path).get("TPE1") and song.get("artist"):
            missing.append("artist")
        if not ID3(file_path).get("TALB") and song.get("album"):
            missing.append("album")
        if not ID3(file_path).get("TDRC") and song.get("year"):
            missing.append("year")
        if missing:
            print(f"    Would tag: {', '.join(missing)}")
        return

    try:
        tags.save(file_path)
        added = []
        if tags.get("TIT2"):
            added.append(f"title={song['title']}")
        if tags.get("TPE1"):
            added.append(f"artist={song['artist']}")
        if tags.get("TALB") and song.get("album"):
            added.append(f"album={song['album']}")
        if tags.get("TDRC") and song.get("year"):
            added.append(f"year={song['year']}")
        print(f"    Tagged: {', '.join(added)}")
    except Exception as e:
        print(f"    Tag write error: {e}")


# --------------- renaming -------------------------------------------------

def _safe_filename(name: str) -> str:
    """Remove characters illegal in FAT32 / Android filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip(". ")


def rename_file(local_file, song, dry_run=False):
    """Rename to 'Title - Artist.mp3'.  Returns the final path."""
    new_name = _safe_filename(f"{song['title']} - {song['artist']}.mp3")
    new_path = os.path.join(local_file["dir"], new_name)
    old_path = local_file["path"]

    if os.path.normpath(old_path) == os.path.normpath(new_path):
        return new_path  # already correct

    if dry_run:
        print(f"    Would rename -> {new_name}")
        return old_path

    if os.path.exists(new_path):
        print(f"    Skip rename (target exists): {new_name}")
        return old_path

    try:
        os.rename(old_path, new_path)
        print(f"    Renamed -> {new_name}")
        return new_path
    except OSError as e:
        print(f"    Rename failed: {e}")
        return old_path


# --------------- M3U generation -------------------------------------------

def write_m3u(playlist_name, entries, output_dir, dry_run=False):
    """
    Write a standard M3U playlist.
    entries = [(song_dict, absolute_path), ...]
    """
    safe = _safe_filename(playlist_name)
    m3u_path = os.path.join(output_dir, f"{safe}.m3u")

    if dry_run:
        print(f"\n[DRY RUN] Would create: {m3u_path}")
        return m3u_path

    os.makedirs(output_dir, exist_ok=True)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"#PLAYLIST:{playlist_name}\n")
        for song, path in entries:
            f.write(f"#EXTINF:-1,{song['title']} - {song['artist']}\n")
            f.write(f"{path}\n")
    return m3u_path


# --------------- main ------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Sync a YouTube Music playlist with local files (Termux)"
    )
    ap.add_argument("playlist", help="YouTube Music playlist URL or ID")
    ap.add_argument(
        "-d", "--music-dirs", nargs="+", default=DEFAULT_MUSIC_DIRS,
        help="Local directories to search (default: /storage/emulated/0/Music)"
    )
    ap.add_argument(
        "-o", "--output-dir", default=DEFAULT_OUTPUT_DIR,
        help="Directory for the .m3u file (default: /storage/emulated/0/Music)"
    )
    ap.add_argument(
        "-t", "--threshold", type=float, default=MATCH_THRESHOLD,
        help="Fuzzy match threshold 0.0-1.0 (default: 0.50)"
    )
    ap.add_argument("--no-rename", action="store_true",
                     help="Do not rename local files")
    ap.add_argument("--no-tags", action="store_true",
                     help="Do not update ID3 metadata tags")
    ap.add_argument("--dry-run", action="store_true",
                     help="Preview actions without making changes")
    args = ap.parse_args()

    # ---------- fetch playlist ----------
    pid = extract_playlist_id(args.playlist)
    print(f"[1/4] Fetching playlist: {pid}")
    try:
        playlist_name, songs = fetch_playlist(pid)
    except Exception as e:
        sys.exit(f"Error fetching playlist: {e}")

    print(f"      Playlist : {playlist_name}")
    print(f"      Tracks   : {len(songs)}")

    if not songs:
        sys.exit("No tracks found in playlist.")

    # ---------- scan local files ----------
    print(f"\n[2/4] Scanning local music: {', '.join(args.music_dirs)}")
    local_files = scan_local_music(args.music_dirs)
    print(f"      Local files: {len(local_files)}")

    if not local_files:
        sys.exit("No .mp3 files found in the given directories.")

    # ---------- match & rename ----------
    print(f"\n[3/4] Matching (threshold {args.threshold:.0%})...\n")
    matched, unmatched = [], []
    used = set()

    for i, song in enumerate(songs, 1):
        tag = f"[{i}/{len(songs)}]"
        match, score = find_best_match(song, local_files, args.threshold, used)

        if match:
            print(f"  {tag} MATCH ({score:.0%})  "
                  f"{song['title']} - {song['artist']}")
            print(f"       File: {match['filename']}")
            used.add(match["path"])

            # Fill missing ID3 tags before renaming
            if not args.no_tags:
                tag_file(match["path"], song, dry_run=args.dry_run)

            if args.no_rename:
                final_path = match["path"]
            else:
                final_path = rename_file(match, song, dry_run=args.dry_run)

            matched.append((song, final_path))
        else:
            print(f"  {tag} MISS         "
                  f"{song['title']} - {song['artist']}")
            unmatched.append(song)

    # ---------- write M3U ----------
    print(f"\n[4/4] Creating M3U playlist...")
    print(f"      Matched  : {len(matched)}/{len(songs)}")
    print(f"      Unmatched: {len(unmatched)}/{len(songs)}")

    if matched:
        m3u = write_m3u(playlist_name, matched, args.output_dir,
                        dry_run=args.dry_run)
        print(f"      Playlist : {m3u}")
    else:
        print("      No matches — playlist not created.")

    # ---------- summary of misses ----------
    if unmatched:
        print("\n--- Songs not found locally ---")
        for s in unmatched:
            print(f"  - {s['title']} - {s['artist']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
