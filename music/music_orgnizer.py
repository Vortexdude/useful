#!/usr/bin/env python3
"""
Music Organizer for Termux (Android)

Reads music_catalog.csv, classifies each song by category and era,
then moves files into an organized folder structure under
/storage/emulated/0/Android/Nitin/Music/.

Folder layout
─────────────
  Bollywood/{year-range}/{Movie Name}/song.mp3
  Bollywood/{year-range}/Other/song.mp3          (movie unknown)
  Punjabi/song.mp3
  English/song.mp3
  South-Indian/song.mp3
  Ghazal/song.mp3
  Devotional/song.mp3
  Other/song.mp3

Classification uses: ID3 genre tag, artist/album heuristics,
and Unicode script detection.  A move-log CSV is written so every
action can be reviewed or undone.

Dependencies: mutagen (auto-installed if missing)
"""

import os
import re
import sys
import csv
import shutil
import argparse
import unicodedata

try:
    from mutagen.id3 import ID3, ID3NoHeaderError
except ImportError:
    print("[*] mutagen not found. Installing...")
    os.system(f"{sys.executable} -m pip install mutagen")
    from mutagen.id3 import ID3, ID3NoHeaderError


# ===================== CONFIGURATION =======================================

DEFAULT_CATALOG = "/storage/emulated/0/Music/music_catalog.csv"
BASE_OUTPUT     = "/storage/emulated/0/Android/Nitin/Music"

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
BEFORE_LABEL = "Before-1970"
UNKNOWN_YEAR_LABEL = "Unknown-Year"

CATEGORIES = [
    "Bollywood",
    "Punjabi",
    "English",
    "South-Indian",
    "Ghazal",
    "Devotional",
    "Other",
]

# ─── keyword / artist tables for heuristic classification ─────────────────
# All matching is case-insensitive.  Extend these lists as needed.

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
        "atif aslam", "shreya ghoshal", "rekha bhardwaj",
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
        "shreya ghoshal",  # does south too but primarily bollywood
        "chinmayi", "haricharan", "benny dayal",
        "mangli", "armaan malik",  # overlap
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

# Artists that should NOT override a Bollywood match when they appear
# in multiple lists (priority tie-breaker)
_PRIORITY_ORDER = ["Bollywood", "Punjabi", "South-Indian",
                    "Ghazal", "Devotional", "English", "Other"]

# ===========================================================================


def _year_range_folder(year: int) -> str:
    """Map a year to its range folder name."""
    for lo, hi, label in YEAR_RANGES:
        if lo <= year <= hi:
            return label
    if year < 1970:
        return BEFORE_LABEL
    return UNKNOWN_YEAR_LABEL


def _parse_year(raw) -> int:
    """Try to pull a 4-digit year from a string like '2019' or '2019-05-10'."""
    if not raw:
        return 0
    m = re.search(r"(19|20)\d{2}", str(raw))
    return int(m.group()) if m else 0


def _safe(name: str) -> str:
    """Sanitize a string for use as a folder / file name."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name if name else "Unknown"


def _lower_set(text: str) -> str:
    return text.lower().strip()


# ─── genre tag reader ─────────────────────────────────────────────────────

def _read_genre(file_path: str) -> str:
    """Read the TCON (genre) ID3 frame from an mp3."""
    try:
        tags = ID3(file_path)
        frame = tags.get("TCON")
        if frame and frame.text:
            return str(frame.text[0]).strip()
    except (ID3NoHeaderError, Exception):
        pass
    return ""


# ─── Unicode-script helpers ───────────────────────────────────────────────

def _has_devanagari(text: str) -> bool:
    return any("DEVANAGARI" in unicodedata.name(c, "") for c in text)


def _has_gurmukhi(text: str) -> bool:
    return any("GURMUKHI" in unicodedata.name(c, "") for c in text)


def _has_south_indian_script(text: str) -> bool:
    scripts = ("TAMIL", "TELUGU", "KANNADA", "MALAYALAM")
    return any(
        any(s in unicodedata.name(c, "") for s in scripts)
        for c in text
    )


def _is_mostly_latin(text: str) -> bool:
    if not text:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if ord(c) < 256)
    return latin / len(letters) > 0.85


# ─── classification engine ────────────────────────────────────────────────

def classify(entry: dict, genre_tag: str) -> str:
    """
    Return one of the CATEGORIES for a catalog entry.
    Priority: genre-tag keywords > artist match > script detection > Other.
    """
    genre_low = genre_tag.lower()
    artist_low = _lower_set(entry.get("artist", ""))
    album_low  = _lower_set(entry.get("album", ""))
    title_low  = _lower_set(entry.get("title", ""))
    combined   = f"{artist_low} {album_low} {title_low}"

    # --- 1) Genre tag keywords ---
    for cat, keywords in GENRE_TAG_MAP.items():
        for kw in keywords:
            if kw in genre_low:
                return cat

    # --- 2) Artist match ---
    matched_cats = []
    for cat, artists in ARTIST_MAP.items():
        for a in artists:
            if a in artist_low:
                matched_cats.append(cat)
                break
    if matched_cats:
        # Use priority order to resolve ties
        for cat in _PRIORITY_ORDER:
            if cat in matched_cats:
                return cat

    # --- 3) Album / title keyword hints ---
    ghazal_hints = ["ghazal", "thumri", "dadra"]
    devotional_hints = ["bhajan", "aarti", "chalisa", "mantra",
                        "kirtan", "shabad", "path", "paath"]
    for h in ghazal_hints:
        if h in combined:
            return "Ghazal"
    for h in devotional_hints:
        if h in combined:
            return "Devotional"

    # --- 4) Unicode script detection ---
    meta_text = f"{entry.get('title','')} {entry.get('artist','')} {entry.get('album','')}"
    if _has_gurmukhi(meta_text):
        return "Punjabi"
    if _has_south_indian_script(meta_text):
        return "South-Indian"
    if _has_devanagari(meta_text):
        return "Bollywood"

    # --- 5) If metadata is mostly Latin / ASCII → English ---
    if _is_mostly_latin(meta_text):
        return "English"

    return "Other"


# ─── destination path builder ─────────────────────────────────────────────

def build_dest(base: str, category: str, entry: dict, filename: str) -> str:
    """
    Build the full destination path for a song file.

    Bollywood → base/Bollywood/{year-range}/{album|Other}/filename
    Others    → base/{category}/filename
    """
    if category == "Bollywood":
        year = _parse_year(entry.get("year", ""))
        yr_folder = _year_range_folder(year) if year else UNKNOWN_YEAR_LABEL

        album = _safe(entry.get("album", "").strip())
        movie_folder = album if album and album != "Unknown" else "Other"

        return os.path.join(base, "Bollywood", yr_folder, movie_folder, filename)

    return os.path.join(base, category, filename)


# ─── main ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Organize music files into categorized folders (Termux)"
    )
    ap.add_argument(
        "-c", "--catalog", default=DEFAULT_CATALOG,
        help=f"Path to music_catalog.csv (default: {DEFAULT_CATALOG})"
    )
    ap.add_argument(
        "-o", "--output", default=BASE_OUTPUT,
        help=f"Base output directory (default: {BASE_OUTPUT})"
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Show planned moves without touching files"
    )
    ap.add_argument(
        "--log", default=None,
        help="Path for the move-log CSV (default: <output>/move_log.csv)"
    )
    args = ap.parse_args()

    catalog_path = args.catalog
    base = args.output
    log_path = args.log or os.path.join(base, "move_log.csv")

    # ── read catalog ──
    if not os.path.isfile(catalog_path):
        sys.exit(f"Catalog not found: {catalog_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        entries = list(csv.DictReader(f))

    print(f"[1/4] Loaded catalog: {len(entries)} entries")

    # ── classify every entry ──
    print("[2/4] Classifying songs...")
    plan = []          # (entry, category, src, dest)
    stats = {c: 0 for c in CATEGORIES}

    for entry in entries:
        src = entry.get("path", "")
        if not src:
            continue

        filename = os.path.basename(src)
        genre_tag = _read_genre(src) if os.path.isfile(src) else ""
        category = classify(entry, genre_tag)
        dest = build_dest(base, category, entry, filename)

        plan.append((entry, category, src, dest))
        stats[category] += 1

    print("      Classification breakdown:")
    for cat in CATEGORIES:
        print(f"        {cat:14s} : {stats[cat]}")

    # ── create folders & move ──
    print(f"\n[3/4] {'Planning' if args.dry_run else 'Moving'} files...")

    moved, skipped, missing = 0, 0, 0
    log_rows = []

    for entry, category, src, dest in plan:
        if not os.path.isfile(src):
            missing += 1
            continue

        dest_dir = os.path.dirname(dest)

        # Handle duplicate filenames at destination
        final_dest = dest
        if os.path.exists(final_dest) and os.path.abspath(src) != os.path.abspath(final_dest):
            name, ext = os.path.splitext(os.path.basename(dest))
            counter = 1
            while os.path.exists(final_dest):
                final_dest = os.path.join(dest_dir, f"{name} ({counter}){ext}")
                counter += 1

        if os.path.abspath(src) == os.path.abspath(final_dest):
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [{category}] {os.path.basename(src)}")
            print(f"    -> {final_dest}")
        else:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(src, final_dest)

        log_rows.append({
            "category": category,
            "filename": os.path.basename(src),
            "source": src,
            "destination": final_dest,
            "title": entry.get("title", ""),
            "artist": entry.get("artist", ""),
            "album": entry.get("album", ""),
            "year": entry.get("year", ""),
        })
        moved += 1

    # ── write move log ──
    print(f"\n[4/4] Writing move log: {log_path}")
    if log_rows and not args.dry_run:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        log_fields = ["category", "filename", "source", "destination",
                       "title", "artist", "album", "year"]
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=log_fields)
            w.writeheader()
            w.writerows(log_rows)
    elif args.dry_run:
        print("      (skipped — dry run)")

    # ── summary ──
    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"\n--- Results ---")
    print(f"  {tag}Moved   : {moved}")
    print(f"  {tag}Skipped : {skipped} (already in place)")
    print(f"  {tag}Missing : {missing} (source file not found)")
    if not args.dry_run and log_rows:
        print(f"  Move log : {log_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
