#!/usr/bin/env python3
"""
Daily Bible Verse Discord Bot
------------------------------
Picks a random verse from a curated list of popular/inspirational
references, fetches the text from the Bolls Bible API (free, no key
needed -- https://bolls.life/api/), and posts it to a Discord channel
via webhook.

Bolls is used instead of bible-api.com because bible-api.com only
serves public-domain translations and does not offer NLT. Bolls offers
NLT (and many other copyrighted-but-freely-served translations) for
free, no API key required.

"No redos": a history.json file (committed back to the repo by the
GitHub Action) tracks every reference already used. Once every verse in
verses.VERSES has been posted, history resets automatically so the
rotation starts over without ever repeating two days in a row -- in
fact it won't repeat *any* verse until the whole list has been used.

Run manually:  DISCORD_WEBHOOK_URL=... python bot.py
"""

import json
import os
import random
import re
import sys
from pathlib import Path

import requests

from verses import VERSES

HISTORY_PATH = Path(__file__).parent / "history.json"
BOLLS_API_BASE = "https://bolls.life"
TRANSLATION = os.environ.get("BIBLE_TRANSLATION", "NLT")  # NLT, KJV, NASB, ESV, NIV, etc.

# Bolls identifies books by number rather than name, so references like
# "John 3:16" need to be mapped to (book_id, chapter, verse_start, verse_end).
BOOK_IDS = {
    "genesis": 1, "exodus": 2, "leviticus": 3, "numbers": 4, "deuteronomy": 5,
    "joshua": 6, "judges": 7, "ruth": 8, "1 samuel": 9, "2 samuel": 10,
    "1 kings": 11, "2 kings": 12, "1 chronicles": 13, "2 chronicles": 14,
    "ezra": 15, "nehemiah": 16, "esther": 17, "job": 18, "psalm": 19,
    "psalms": 19, "proverbs": 20, "ecclesiastes": 21, "song of solomon": 22,
    "isaiah": 23, "jeremiah": 24, "lamentations": 25, "ezekiel": 26,
    "daniel": 27, "hosea": 28, "joel": 29, "amos": 30, "obadiah": 31,
    "jonah": 32, "micah": 33, "nahum": 34, "habakkuk": 35, "zephaniah": 36,
    "haggai": 37, "zechariah": 38, "malachi": 39,
    "matthew": 40, "mark": 41, "luke": 42, "john": 43, "acts": 44,
    "romans": 45, "1 corinthians": 46, "2 corinthians": 47, "galatians": 48,
    "ephesians": 49, "philippians": 50, "colossians": 51,
    "1 thessalonians": 52, "2 thessalonians": 53, "1 timothy": 54,
    "2 timothy": 55, "titus": 56, "philemon": 57, "hebrews": 58,
    "james": 59, "1 peter": 60, "2 peter": 61, "1 john": 62, "2 john": 63,
    "3 john": 64, "jude": 65, "revelation": 66,
}

# Matches things like "John 3:16", "1 Corinthians 13:4-7", "Psalm 23:1-3"
REFERENCE_RE = re.compile(
    r"^\s*((?:[1-3]\s+)?[A-Za-z. ]+?)\s+(\d+):(\d+)(?:-(\d+))?\s*$"
)


def parse_reference(reference: str) -> tuple[int, int, int, int]:
    """
    Parse a "Book Chapter:Verse" or "Book Chapter:Verse-Verse" string into
    (book_id, chapter, verse_start, verse_end) for use with the Bolls API.
    """
    match = REFERENCE_RE.match(reference)
    if not match:
        raise ValueError(f"Could not parse reference: '{reference}'")

    book_name, chapter, verse_start, verse_end = match.groups()
    book_id = BOOK_IDS.get(book_name.strip().lower())
    if book_id is None:
        raise ValueError(f"Unknown book name in reference: '{reference}'")

    chapter = int(chapter)
    verse_start = int(verse_start)
    verse_end = int(verse_end) if verse_end else verse_start

    return book_id, chapter, verse_start, verse_end


def load_history() -> list[str]:
    if HISTORY_PATH.exists():
        try:
            data = json.loads(HISTORY_PATH.read_text())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def save_history(history: list[str]) -> None:
    HISTORY_PATH.write_text(json.dumps(history, indent=2) + "\n")


def pick_next_reference(history: list[str]) -> str:
    """
    Pick a reference from VERSES that hasn't been used yet.
    If every reference has already been used, reset and start a new cycle.
    """
    unused = [v for v in VERSES if v not in history]

    if not unused:
        # Full cycle completed -- reset history and start fresh.
        history.clear()
        unused = list(VERSES)

    return random.choice(unused)


def fetch_verse_text(reference: str) -> dict:
    """
    Query the Bolls Bible API for the verse text. Returns a dict with
    'reference', 'text', and 'translation' keys. Raises on failure.
    """
    book_id, chapter, verse_start, verse_end = parse_reference(reference)

    if verse_start == verse_end:
        url = f"{BOLLS_API_BASE}/get-verse/{TRANSLATION}/{book_id}/{chapter}/{verse_start}/"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data or "text" not in data:
            raise ValueError(f"No verse data returned for '{reference}'")
        verses_data = [data]
    else:
        url = f"{BOLLS_API_BASE}/get-verses/"
        payload = [{
            "translation": TRANSLATION,
            "book": book_id,
            "chapter": chapter,
            "verses": list(range(verse_start, verse_end + 1)),
        }]
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if not result or not result[0]:
            raise ValueError(f"No verse data returned for '{reference}'")
        verses_data = result[0]

    # Strip any HTML tags Bolls sometimes includes (e.g. <i>, footnote markers)
    def clean(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = text.strip().replace("\n", " ")
        while "  " in text:
            text = text.replace("  ", " ")
        return text

    text = " ".join(clean(v["text"]) for v in verses_data)

    return {
        "reference": reference,
        "text": text,
        "translation": TRANSLATION.upper(),
    }


def post_to_discord(webhook_url: str, verse: dict) -> None:
    embed = {
        "title": f"📖 Verse of the Day — {verse['reference']}",
        "description": f"_{verse['text']}_",
        "footer": {"text": f"Translation: {verse['translation']}"},
        "color": 0x4B7BEC,
    }
    payload = {"embeds": [embed]}

    resp = requests.post(webhook_url, json=payload, timeout=15)
    resp.raise_for_status()


def main() -> int:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
        return 1

    history = load_history()
    reference = pick_next_reference(history)

    try:
        verse = fetch_verse_text(reference)
    except Exception as e:
        print(f"ERROR: failed to fetch verse '{reference}' from Bolls API: {e}", file=sys.stderr)
        return 1

    try:
        post_to_discord(webhook_url, verse)
    except Exception as e:
        print(f"ERROR: failed to post to Discord: {e}", file=sys.stderr)
        return 1

    history.append(reference)
    save_history(history)

    print(f"Posted {verse['reference']} ({verse['translation']}) successfully.")
    print(f"History size: {len(history)} / {len(VERSES)} verses used this cycle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
