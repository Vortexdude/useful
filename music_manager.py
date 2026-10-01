#!/usr/bin/env python3
"""
Music Manager for Termux (Android)
───────────────────────────────────
A single-file tool with three commands:

  sync      Fetch a YouTube Music playlist, fuzzy-match with local files,
            tag missing metadata, rename to "Title - Artist.mp3", and
            create an M3U playlist for Phonograph.

  catalog   Scan local music directories, read ID3 tags from every .mp3,
            and write a CSV index (music_catalog.csv).

  organize  Read the catalog CSV, classify each song (Bollywood, Punjabi,
            English, South-Indian, Ghazal, Devotional, Other), and move
            files into an organized folder tree.

Usage:
  python music_manager.py sync     <playlist_url> [options]
  python music_manager.py catalog  [options]
  python music_manager.py organize [options]

Dependencies: ytmusicapi, mutagen  (auto-installed if missing)
"""

import os
import re
import sys
import csv
import shutil
import argparse
import unicodedata
from difflib import SequenceMatcher

# ═══════════════════════════════════════════════════════════════════════════
# Auto-install external packages (Termux-friendly)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from ytmusicapi import YTMusic
except ImportError:
    print("[*] ytmusicapi not found. Installing...")
    os.system(f"{sys.executable} -m pip install ytmusicapi")
    from ytmusicapi import YTMusic

try:
    from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC
    from mutagen.mp3 import MP3
except ImportError:
    print("[*] mutagen not found. Installing...")
    os.system(f"{sys.executable} -m pip install mutagen")
    from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC
    from mutagen.mp3 import MP3


# ═══════════════════════════════════════════════════════════════════════════
# Shared configuration
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_MUSIC_DIRS = [
    "/storage/emulated/0/Music",
    "/storage/emulated/0/Android/Music",
    "/storage/emulated/0/Download",
]
DEFAULT_OUTPUT_DIR  = "/storage/emulated/0/Music"
DEFAULT_CATALOG     = "/storage/emulated/0/Music/music_catalog.csv"
BASE_ORGANIZE_DIR   = "/storage/emulated/0/Music"

AUDIO_EXTENSIONS    = {".mp3"}
MATCH_THRESHOLD     = 0.50

CSV_FIELDS = [
    "filename", "title", "artist", "album",
    "year", "duration_sec", "size_kb", "path",
]

YEAR_RANGES = [
    (2020, 2025, "2020-2025"),
    (2015, 2019, "2015-2019"),
    (2010, 2014, "2010-2014"),
    (2005, 2009, "2005-2009"),
    (2000, 2004, "2000-2004"),
    (1990, 1999, "1990-1999"),
    (1980, 1989, "1980-1989"),
    (1970, 1979, "1970-1979"),
]
BEFORE_LABEL       = "Before-1970"
UNKNOWN_YEAR_LABEL = "Unknown-Year"

CATEGORIES = [
    "Bollywood", "Punjabi", "English",
    "South-Indian", "Ghazal", "Devotional", "Other",
]

# ─── genre / artist tables for classification ─────────────────────────────

GENRE_TAG_MAP = {
    "Bollywood":    ["bollywood", "hindi", "filmi", "indi pop", "indian pop",
                     "hindi pop", "hindi film"],
    "Punjabi":      ["punjabi", "bhangra"],
    "English":      ["pop", "rock", "hip hop", "hip-hop", "rap", "r&b", "rnb",
                     "edm", "electronic", "dance", "jazz", "blues", "country",
                     "metal", "alternative", "indie", "soul", "funk", "reggae",
                     "classical", "lo-fi", "lofi", "trap", "dubstep",
                     "synthwave", "house", "techno", "ambient"],
    "South-Indian": ["tamil", "telugu", "kannada", "malayalam", "south indian",
                     "kollywood", "tollywood", "sandalwood", "mollywood"],
    "Ghazal":       ["ghazal", "thumri", "dadra"],
    "Devotional":   ["devotional", "bhajan", "spiritual", "kirtan", "aarti",
                     "mantra", "sufi", "qawwali", "shabad", "gurbani",
                     "chalisa", "stuti"],
}

ARTIST_MAP = {
    "Bollywood": [
        "arijit singh", "shreya ghoshal", "sonu nigam", "lata mangeshkar",
        "asha bhosle", "kishore kumar", "mohammed rafi", "mukesh",
        "neha kakkar", "jubin nautiyal", "vishal mishra", "armaan malik",
        "darshan raval", "sachet tandon", "parampara tandon", "kumar sanu",
        "udit narayan", "alka yagnik", "sunidhi chauhan", "kk",
        "mohit chauhan", "himesh reshammiya", "mika singh",
        "honey singh", "yo yo honey singh", "badshah", "tulsi kumar",
        "palak muchhal", "ankit tiwari", "rahat fateh ali khan",
        "shaan", "shankar mahadevan", "sukhwinder singh",
        "ar rahman", "a.r. rahman", "a r rahman", "pritam",
        "vishal-shekhar", "vishal shekhar", "shankar ehsaan loy",
        "amit trivedi", "sachin-jigar", "sachin jigar", "tanishk bagchi",
        "salim-sulaiman", "salim sulaiman", "jatin-lalit", "jatin lalit",
        "anu malik", "nadeem-shravan", "nadeem shravan", "bappi lahiri",
        "r.d. burman", "r d burman", "rd burman", "s.d. burman",
        "sd burman", "o.p. nayyar", "kalyanji-anandji",
        "laxmikant-pyarelal", "laxmikant pyarelal",
        "b praak", "stebin ben", "papon", "monali thakur",
        "atif aslam", "rekha bhardwaj",
        "kanika kapoor", "dhvani bhanushali", "asees kaur",
        "dev negi", "jonita gandhi", "shilpa rao",
        "javed ali", "siddharth slathia",
    ],
    "Punjabi": [
        "diljit dosanjh", "ap dhillon", "sidhu moose wala",
        "sidhu moosewala", "karan aujla", "amrinder gill", "gurdas maan",
        "jazzy b", "babbu maan", "jassie gill", "parmish verma",
        "guru randhawa", "garry sandhu", "ammy virk", "harrdy sandhu",
        "hardy sandhu", "mankirt aulakh", "jasmine sandlas",
        "nimrat khaira", "kaur b", "sharry mann", "ranjit bawa",
        "ninja", "akhil", "r nait", "korala maan",
        "satinder sartaaj", "kulwinder billa", "jordan sandhu",
        "ikka", "bohemia",
    ],
    "South-Indian": [
        "sp balasubrahmanyam", "s.p. balasubrahmanyam", "spb",
        "ks chithra", "k.s. chithra", "ilaiyaraaja", "ilayaraja",
        "devi sri prasad", "dsp", "anirudh ravichander", "anirudh",
        "sid sriram", "vijay prakash", "harris jayaraj",
        "gv prakash", "g.v. prakash", "yuvan shankar raja", "yuvan",
        "thaman", "s thaman", "ss thaman", "santhosh narayanan",
        "d imman", "d. imman", "hiphop tamizha", "hip hop tamizha",
        "chinmayi", "haricharan", "benny dayal", "mangli",
    ],
    "Ghazal": [
        "jagjit singh", "ghulam ali", "mehdi hassan", "pankaj udhas",
        "talat aziz", "ahmed hussain", "mohammed hussain",
        "hariharan", "abida parveen", "farida khanum",
        "begum akhtar", "nusrat fateh ali khan",
    ],
    "Devotional": [
        "anuradha paudwal", "anup jalota", "gulshan kumar",
        "narendra chanchal", "lakhbir singh lakkha",
        "suresh wadkar", "ravindra jain", "hemant chauhan",
        "manoj tiwari",
    ],
}

_PRIORITY_ORDER = [
    "Bollywood", "Punjabi", "South-Indian",
    "Ghazal", "Devotional", "English", "Other",
]


# ═══════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════

def _safe_name(name: str) -> str:
    """Sanitize for FAT32 / Android filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name if name else "Unknown"


def _tag_text(tags, key: str) -> str:
    """Pull the first text value from an ID3 frame, or ''."""
    frame = tags.get(key)
    if frame and frame.text:
        return str(frame.text[0]).strip()
    return ""


def _parse_year(raw) -> int:
    if not raw:
        return 0
    m = re.search(r"(19|20)\d{2}", str(raw))
    return int(m.group()) if m else 0


def _year_range_folder(year: int) -> str:
    for lo, hi, label in YEAR_RANGES:
        if lo <= year <= hi:
            return label
    return BEFORE_LABEL if year < 1970 else UNKNOWN_YEAR_LABEL


def _is_known_artist(text: str) -> bool:
    """Check if text matches any known artist in ARTIST_MAP."""
    low = text.lower().strip()
    if not low:
        return False
    for artists in ARTIST_MAP.values():
        for a in artists:
            if a in low or low in a:
                return True
    return False


def _parse_filename(filename: str):
    """
    Extract (title, artist) from a filename when ID3 tags are missing.
    Handles patterns like:
      "Title - Artist.mp3", "Artist - Title.mp3",
      "01. Title - Artist.mp3", "Title (feat. X).mp3"
    """
    name = os.path.splitext(filename)[0]

    # Strip leading track numbers: "01. ", "01 - ", "1) ", "01 "
    name = re.sub(r"^\d{1,3}[\.\)\-\s]+\s*", "", name)

    # Strip quality / tag junk in brackets
    name = re.sub(
        r"\s*[\(\[]\s*("
        r"official\s*(audio|video|music\s*video)|"
        r"lyric(s|al)?\s*video|audio|hd|hq|full\s*song|"
        r"\d{2,3}\s*kbps|320|128|192|256"
        r")\s*[\)\]]",
        "", name, flags=re.I,
    )
    # Strip "(From <movie>)" but keep the movie name for later
    name = re.sub(r"\s*[\(\[]\s*from\s+.*?[\)\]]", "", name, flags=re.I)
    name = name.strip(" -_")

    title, artist = name, ""

    if " - " in name:
        left, right = name.split(" - ", 1)
        left, right = left.strip(), right.strip()

        # Determine which part is artist using known-artist lookup
        l_known = _is_known_artist(left)
        r_known = _is_known_artist(right)

        if r_known and not l_known:
            title, artist = left, right
        elif l_known and not r_known:
            title, artist = right, left
        else:
            # Default: user's naming standard is "Title - Artist"
            title, artist = left, right

    # Pull out "feat./ft." from title
    feat = re.search(r"\s*[\(\[]\s*(?:feat\.?|ft\.?)\s+(.+?)[\)\]]", title, re.I)
    if feat:
        if not artist:
            artist = feat.group(1).strip()
        title = title[:feat.start()].strip()

    return title.strip(), artist.strip()


def _enrich_entry(entry: dict, dry_run=False) -> bool:
    """
    If title or artist is missing in both catalog and ID3 tags, extract
    from the filename, fill the entry dict, and write tags into the mp3.
    Returns True if anything was enriched.
    """
    src = entry.get("path", "")
    if not src or not os.path.isfile(src):
        return False

    fn = entry.get("filename") or os.path.basename(src)
    has_title  = bool(entry.get("title", "").strip())
    has_artist = bool(entry.get("artist", "").strip())

    if has_title and has_artist:
        return False  # nothing to do

    parsed_title, parsed_artist = _parse_filename(fn)
    changed = False

    if not has_title and parsed_title:
        entry["title"] = parsed_title
        changed = True
    if not has_artist and parsed_artist:
        entry["artist"] = parsed_artist
        changed = True

    if not changed:
        return False

    if dry_run:
        parts = []
        if not has_title and parsed_title:   parts.append(f"title={parsed_title}")
        if not has_artist and parsed_artist: parts.append(f"artist={parsed_artist}")
        print(f"    Would enrich from filename: {', '.join(parts)}")
        return True

    # Write enriched data into the mp3 ID3 tags
    try:
        tags = ID3(src)
    except ID3NoHeaderError:
        tags = ID3()
    except Exception:
        return True  # entry updated but file write failed

    wrote = []
    if not has_title and parsed_title and not tags.get("TIT2"):
        tags.add(TIT2(encoding=3, text=[parsed_title]))
        wrote.append(f"title={parsed_title}")
    if not has_artist and parsed_artist and not tags.get("TPE1"):
        tags.add(TPE1(encoding=3, text=[parsed_artist]))
        wrote.append(f"artist={parsed_artist}")

    if wrote:
        try:
            tags.save(src)
            print(f"    Enriched from filename: {', '.join(wrote)}")
        except Exception as e:
            print(f"    Enrich write error: {e}")

    return True


def scan_music_files(music_dirs):
    """Walk directories and yield every mp3 path (sorted per dir)."""
    for d in music_dirs:
        if not os.path.isdir(d):
            print(f"  [!] Skipping (not found): {d}")
            continue
        for root, _, files in os.walk(d):
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() in AUDIO_EXTENSIONS:
                    yield os.path.join(root, fn)


def scan_music_list(music_dirs):
    """Return a list of dicts with path / dir / filename / name."""
    out = []
    for p in scan_music_files(music_dirs):
        fn = os.path.basename(p)
        out.append({
            "path": p,
            "dir": os.path.dirname(p),
            "filename": fn,
            "name": os.path.splitext(fn)[0],
        })
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  SYNC  — YouTube Music playlist → local match → tag → rename → M3U
# ═══════════════════════════════════════════════════════════════════════════

def _extract_playlist_id(url_or_id: str) -> str:
    for pat in (r"[?&]list=([a-zA-Z0-9_-]+)",
                r"playlist[/=]([a-zA-Z0-9_-]+)"):
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    return url_or_id


def _fetch_playlist(playlist_id: str):
    yt = YTMusic()
    data = yt.get_playlist(playlist_id, limit=None)
    songs = []
    for t in data.get("tracks", []):
        title = t.get("title", "").strip()
        artists = ", ".join(
            a.get("name", "") for a in t.get("artists", []) if a.get("name")
        )
        album_info = t.get("album") or {}
        album = album_info.get("name", "") if isinstance(album_info, dict) else ""
        year = str(t.get("year", "")).strip()
        if title:
            songs.append({"title": title, "artist": artists,
                          "album": album, "year": year})
    return data.get("title", "Playlist"), songs


# ── fuzzy matching ────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\[.*?\]", "", t)
    t = re.sub(r"feat\.?\s.*", "", t, flags=re.I)
    t = re.sub(r"ft\.?\s.*", "", t, flags=re.I)
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _find_best_match(song, local_files, threshold, used):
    title, artist = song["title"], song["artist"]
    combined  = f"{title} {artist}"
    dash_form = f"{title} - {artist}"
    best, best_score = None, 0.0

    for lf in local_files:
        if lf["path"] in used:
            continue
        name = lf["name"]
        scores = [_ratio(combined, name), _ratio(title, name),
                  _ratio(dash_form, name)]
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


# ── tagging ───────────────────────────────────────────────────────────────

def _tag_file(file_path, song, dry_run=False):
    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()
    except Exception as e:
        print(f"    Tag read error: {e}")
        return

    changed = False
    if not tags.get("TIT2") and song.get("title"):
        tags.add(TIT2(encoding=3, text=[song["title"]]));  changed = True
    if not tags.get("TPE1") and song.get("artist"):
        tags.add(TPE1(encoding=3, text=[song["artist"]])); changed = True
    if not tags.get("TALB") and song.get("album"):
        tags.add(TALB(encoding=3, text=[song["album"]]));  changed = True
    if not tags.get("TDRC") and song.get("year"):
        tags.add(TDRC(encoding=3, text=[song["year"]]));   changed = True

    if not changed:
        return

    if dry_run:
        missing = []
        try:
            orig = ID3(file_path)
        except (ID3NoHeaderError, Exception):
            orig = ID3()
        if not orig.get("TIT2") and song.get("title"):   missing.append("title")
        if not orig.get("TPE1") and song.get("artist"):  missing.append("artist")
        if not orig.get("TALB") and song.get("album"):   missing.append("album")
        if not orig.get("TDRC") and song.get("year"):    missing.append("year")
        if missing:
            print(f"    Would tag: {', '.join(missing)}")
        return

    try:
        tags.save(file_path)
        added = []
        if tags.get("TIT2"): added.append(f"title={song['title']}")
        if tags.get("TPE1"): added.append(f"artist={song['artist']}")
        if tags.get("TALB") and song.get("album"): added.append(f"album={song['album']}")
        if tags.get("TDRC") and song.get("year"):  added.append(f"year={song['year']}")
        print(f"    Tagged: {', '.join(added)}")
    except Exception as e:
        print(f"    Tag write error: {e}")


# ── renaming ──────────────────────────────────────────────────────────────

def _rename_file(local_file, song, dry_run=False):
    new_name = _safe_name(f"{song['title']} - {song['artist']}.mp3")
    new_path = os.path.join(local_file["dir"], new_name)
    old_path = local_file["path"]

    if os.path.normpath(old_path) == os.path.normpath(new_path):
        return new_path
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


# ── M3U ───────────────────────────────────────────────────────────────────

def _write_m3u(playlist_name, entries, output_dir, dry_run=False):
    safe = _safe_name(playlist_name)
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


def cmd_sync(args):
    """sync subcommand entry-point."""
    pid = _extract_playlist_id(args.playlist)
    print(f"[1/4] Fetching playlist: {pid}")
    try:
        playlist_name, songs = _fetch_playlist(pid)
    except Exception as e:
        sys.exit(f"Error fetching playlist: {e}")

    print(f"      Playlist : {playlist_name}")
    print(f"      Tracks   : {len(songs)}")
    if not songs:
        sys.exit("No tracks found in playlist.")

    print(f"\n[2/4] Scanning local music: {', '.join(args.music_dirs)}")
    local_files = scan_music_list(args.music_dirs)
    print(f"      Local files: {len(local_files)}")
    if not local_files:
        sys.exit("No .mp3 files found in the given directories.")

    print(f"\n[3/4] Matching (threshold {args.threshold:.0%})...\n")
    matched, unmatched = [], []
    used = set()

    for i, song in enumerate(songs, 1):
        tag = f"[{i}/{len(songs)}]"
        match, score = _find_best_match(song, local_files, args.threshold, used)
        if match:
            print(f"  {tag} MATCH ({score:.0%})  "
                  f"{song['title']} - {song['artist']}")
            print(f"       File: {match['filename']}")
            used.add(match["path"])
            if not args.no_tags:
                _tag_file(match["path"], song, dry_run=args.dry_run)
            if args.no_rename:
                final_path = match["path"]
            else:
                final_path = _rename_file(match, song, dry_run=args.dry_run)
            matched.append((song, final_path))
        else:
            print(f"  {tag} MISS         "
                  f"{song['title']} - {song['artist']}")
            unmatched.append(song)

    print(f"\n[4/4] Creating M3U playlist...")
    print(f"      Matched  : {len(matched)}/{len(songs)}")
    print(f"      Unmatched: {len(unmatched)}/{len(songs)}")
    if matched:
        m3u = _write_m3u(playlist_name, matched, args.output_dir,
                         dry_run=args.dry_run)
        print(f"      Playlist : {m3u}")
    else:
        print("      No matches — playlist not created.")

    if unmatched:
        print("\n--- Songs not found locally ---")
        for s in unmatched:
            print(f"  - {s['title']} - {s['artist']}")
    print("\nDone.")


# ═══════════════════════════════════════════════════════════════════════════
#  CATALOG  — scan local files → read ID3 → write CSV
# ═══════════════════════════════════════════════════════════════════════════

def _read_metadata(file_path):
    fn = os.path.basename(file_path)
    entry = {"filename": fn, "title": "", "artist": "", "album": "",
             "year": "", "duration_sec": "", "size_kb": "", "path": file_path}
    try:
        entry["size_kb"] = round(os.path.getsize(file_path) / 1024)
    except OSError:
        pass
    try:
        entry["duration_sec"] = round(MP3(file_path).info.length)
    except Exception:
        pass
    try:
        tags = ID3(file_path)
        entry["title"]  = _tag_text(tags, "TIT2")
        entry["artist"] = _tag_text(tags, "TPE1")
        entry["album"]  = _tag_text(tags, "TALB")
        entry["year"]   = _tag_text(tags, "TDRC")
    except ID3NoHeaderError:
        pass
    except Exception as e:
        print(f"  [!] Tag error: {fn} — {e}")
    return entry


def _write_catalog(entries, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(entries)


def cmd_catalog(args):
    """catalog subcommand entry-point."""
    print(f"[1/3] Scanning: {', '.join(args.music_dirs)}")
    paths = list(scan_music_files(args.music_dirs))
    print(f"      Found {len(paths)} mp3 file(s)")
    if not paths:
        sys.exit("No mp3 files found.")

    existing_paths, existing_entries = set(), []
    if args.append and os.path.isfile(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_entries.append(row)
                existing_paths.add(row.get("path", ""))
        print(f"      Existing catalog: {len(existing_entries)} entries")

    print(f"\n[2/3] Reading metadata...")
    entries = list(existing_entries)
    new_count = 0
    for p in paths:
        if p in existing_paths:
            continue
        entries.append(_read_metadata(p))
        new_count += 1
        if new_count % 50 == 0:
            print(f"      Processed {new_count} new files...")
    print(f"      New entries: {new_count}")

    print(f"\n[3/3] Writing catalog: {args.output}")
    _write_catalog(entries, args.output)
    print(f"      Total entries: {len(entries)}")

    total   = len(entries)
    tagged  = sum(1 for e in entries if e["title"])
    artists = len({e["artist"] for e in entries if e["artist"]})
    albums  = len({e["album"] for e in entries if e["album"]})
    print(f"\n--- Summary ---")
    print(f"  Total files : {total}")
    print(f"  With tags   : {tagged}")
    print(f"  Missing tags: {total - tagged}")
    print(f"  Artists     : {artists}")
    print(f"  Albums      : {albums}")

    if args.show_untagged:
        untagged = [e for e in entries if not e["title"]]
        if untagged:
            print(f"\n--- Untagged files ({len(untagged)}) ---")
            for e in untagged:
                print(f"  {e['filename']}")
                print(f"    {e['path']}")
    print("\nDone.")


# ═══════════════════════════════════════════════════════════════════════════
#  ORGANIZE  — read catalog → classify → move into folder tree
# ═══════════════════════════════════════════════════════════════════════════

def _read_genre(file_path: str) -> str:
    try:
        tags = ID3(file_path)
        frame = tags.get("TCON")
        if frame and frame.text:
            return str(frame.text[0]).strip()
    except (ID3NoHeaderError, Exception):
        pass
    return ""


def _has_devanagari(text):
    return any("DEVANAGARI" in unicodedata.name(c, "") for c in text)

def _has_gurmukhi(text):
    return any("GURMUKHI" in unicodedata.name(c, "") for c in text)

def _has_south_indian_script(text):
    scripts = ("TAMIL", "TELUGU", "KANNADA", "MALAYALAM")
    return any(any(s in unicodedata.name(c, "") for s in scripts) for c in text)

def _is_mostly_latin(text):
    if not text:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if ord(c) < 256) / len(letters) > 0.85


def _classify(entry: dict, genre_tag: str) -> str:
    genre_low  = genre_tag.lower()
    artist_low = entry.get("artist", "").lower().strip()
    album_low  = entry.get("album", "").lower().strip()
    title_low  = entry.get("title", "").lower().strip()
    combined   = f"{artist_low} {album_low} {title_low}"

    # Also include the filename in searchable text so songs with no
    # tags but descriptive filenames (e.g. "Tum Hi Ho - Arijit Singh.mp3")
    # are not blindly sent to English.
    fn_low = os.path.splitext(
        entry.get("filename", "")
    )[0].lower().strip()
    combined_with_fn = f"{combined} {fn_low}"

    # 1) Genre tag
    for cat, kws in GENRE_TAG_MAP.items():
        for kw in kws:
            if kw in genre_low:
                return cat

    # 2) Artist match — check both ID3 artist AND filename
    matched = []
    for cat, artists in ARTIST_MAP.items():
        for a in artists:
            if a in artist_low or a in fn_low:
                matched.append(cat)
                break
    if matched:
        for cat in _PRIORITY_ORDER:
            if cat in matched:
                return cat

    # 3) Keyword hints — also search filename
    for h in ("ghazal", "thumri", "dadra"):
        if h in combined_with_fn:
            return "Ghazal"
    for h in ("bhajan", "aarti", "chalisa", "mantra",
              "kirtan", "shabad", "path", "paath"):
        if h in combined_with_fn:
            return "Devotional"

    # 4) Unicode script — check metadata AND filename
    meta = f"{entry.get('title','')} {entry.get('artist','')} {entry.get('album','')} {fn_low}"
    if _has_gurmukhi(meta):            return "Punjabi"
    if _has_south_indian_script(meta): return "South-Indian"
    if _has_devanagari(meta):          return "Bollywood"

    # 5) Latin → English  (only if metadata has real content;
    #    do NOT classify based on a Latin filename alone)
    meta_tags = f"{entry.get('title','')} {entry.get('artist','')} {entry.get('album','')}".strip()
    if meta_tags and _is_mostly_latin(meta_tags):
        return "English"

    return "Other"


def _build_dest(base, category, entry, filename):
    if category == "Bollywood":
        year = _parse_year(entry.get("year", ""))
        yr  = _year_range_folder(year) if year else UNKNOWN_YEAR_LABEL
        alb = _safe_name(entry.get("album", "").strip())
        mov = alb if alb and alb != "Unknown" else "Other"
        return os.path.join(base, "Bollywood", yr, mov, filename)
    return os.path.join(base, category, filename)


def cmd_organize(args):
    """organize subcommand entry-point."""
    catalog_path = args.catalog
    base = args.output
    log_path = args.log or os.path.join(base, "move_log.csv")

    if not os.path.isfile(catalog_path):
        sys.exit(f"Catalog not found: {catalog_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        entries = list(csv.DictReader(f))
    print(f"[1/5] Loaded catalog: {len(entries)} entries")

    # ── enrich missing metadata from filenames ──
    print("[2/5] Enriching missing metadata from filenames...")
    enriched = 0
    for entry in entries:
        if _enrich_entry(entry, dry_run=args.dry_run):
            enriched += 1
    print(f"      Enriched: {enriched} file(s)")

    # ── classify ──
    print("[3/5] Classifying songs...")
    plan = []
    stats = {c: 0 for c in CATEGORIES}
    for entry in entries:
        src = entry.get("path", "")
        if not src:
            continue
        fn = os.path.basename(src)
        genre_tag = _read_genre(src) if os.path.isfile(src) else ""
        cat = _classify(entry, genre_tag)
        dest = _build_dest(base, cat, entry, fn)
        plan.append((entry, cat, src, dest))
        stats[cat] += 1

    print("      Classification breakdown:")
    for cat in CATEGORIES:
        print(f"        {cat:14s} : {stats[cat]}")

    # ── move files ──
    print(f"\n[4/5] {'Planning' if args.dry_run else 'Moving'} files...")
    moved, skipped, missing = 0, 0, 0
    log_rows = []
    # Track old→new path mapping for catalog update
    path_updates = {}

    for entry, cat, src, dest in plan:
        if not os.path.isfile(src):
            missing += 1
            continue

        dest_dir = os.path.dirname(dest)
        final = dest
        if os.path.exists(final) and os.path.abspath(src) != os.path.abspath(final):
            name, ext = os.path.splitext(os.path.basename(dest))
            c = 1
            while os.path.exists(final):
                final = os.path.join(dest_dir, f"{name} ({c}){ext}")
                c += 1

        if os.path.abspath(src) == os.path.abspath(final):
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [{cat}] {os.path.basename(src)}")
            print(f"    -> {final}")
        else:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(src, final)
            path_updates[src] = final

        log_rows.append({
            "category": cat, "filename": os.path.basename(src),
            "source": src, "destination": final,
            "title": entry.get("title", ""), "artist": entry.get("artist", ""),
            "album": entry.get("album", ""), "year": entry.get("year", ""),
        })
        moved += 1

    # ── write move log + update catalog ──
    print(f"\n[5/5] Writing move log & updating catalog...")
    if log_rows and not args.dry_run:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        fields = ["category", "filename", "source", "destination",
                  "title", "artist", "album", "year"]
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(log_rows)
        print(f"      Move log : {log_path}")
    elif args.dry_run:
        print("      (skipped — dry run)")

    # Update catalog CSV with new paths and enriched metadata
    if (path_updates or enriched) and not args.dry_run:
        for entry in entries:
            old_path = entry.get("path", "")
            if old_path in path_updates:
                new_path = path_updates[old_path]
                entry["path"] = new_path
                entry["filename"] = os.path.basename(new_path)
        _write_catalog(entries, catalog_path)
        print(f"      Catalog updated: {catalog_path}")

    dr = "[DRY RUN] " if args.dry_run else ""
    print(f"\n--- Results ---")
    print(f"  {dr}Enriched: {enriched}")
    print(f"  {dr}Moved   : {moved}")
    print(f"  {dr}Skipped : {skipped} (already in place)")
    print(f"  {dr}Missing : {missing} (source file not found)")
    print("\nDone.")


# ═══════════════════════════════════════════════════════════════════════════
#  CLI  — argparse with subcommands
# ═══════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        prog="music_manager",
        description="All-in-one music manager for Termux (Android)",
    )
    sub = ap.add_subparsers(dest="command", required=True,
                            help="Available commands")

    # ── sync ──────────────────────────────────────────────────────────────
    sp_sync = sub.add_parser(
        "sync",
        help="Sync a YouTube Music playlist with local files",
    )
    sp_sync.add_argument("playlist", help="YouTube Music playlist URL or ID")
    sp_sync.add_argument("-d", "--music-dirs", nargs="+",
                         default=DEFAULT_MUSIC_DIRS,
                         help="Local directories to search")
    sp_sync.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR,
                         help="Directory for the .m3u file")
    sp_sync.add_argument("-t", "--threshold", type=float,
                         default=MATCH_THRESHOLD,
                         help="Fuzzy match threshold 0.0-1.0 (default: 0.50)")
    sp_sync.add_argument("--no-rename", action="store_true",
                         help="Do not rename local files")
    sp_sync.add_argument("--no-tags", action="store_true",
                         help="Do not update ID3 metadata tags")
    sp_sync.add_argument("--dry-run", action="store_true",
                         help="Preview actions without making changes")

    # ── catalog ───────────────────────────────────────────────────────────
    sp_cat = sub.add_parser(
        "catalog",
        help="Build a CSV catalog of local music metadata",
    )
    sp_cat.add_argument("-d", "--music-dirs", nargs="+",
                        default=DEFAULT_MUSIC_DIRS,
                        help="Directories to scan")
    sp_cat.add_argument("-o", "--output", default=DEFAULT_CATALOG,
                        help="Output CSV path")
    sp_cat.add_argument("--append", action="store_true",
                        help="Append to existing catalog (skip known paths)")
    sp_cat.add_argument("--show-untagged", action="store_true",
                        help="Print files missing an ID3 title tag")

    # ── organize ──────────────────────────────────────────────────────────
    sp_org = sub.add_parser(
        "organize",
        help="Classify and move files into organized folders",
    )
    sp_org.add_argument("-c", "--catalog", default=DEFAULT_CATALOG,
                        help="Path to music_catalog.csv")
    sp_org.add_argument("-o", "--output", default=BASE_ORGANIZE_DIR,
                        help="Base output directory")
    sp_org.add_argument("--dry-run", action="store_true",
                        help="Show planned moves without touching files")
    sp_org.add_argument("--log", default=None,
                        help="Path for the move-log CSV")

    args = ap.parse_args()

    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "catalog":
        cmd_catalog(args)
    elif args.command == "organize":
        cmd_organize(args)


if __name__ == "__main__":
    main()
