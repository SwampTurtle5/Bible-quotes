#!/usr/bin/env python3
"""
Daily Bible Verse Discord Bot
------------------------------
Picks a random verse from a curated list of popular/inspirational
references, fetches the text from bible-api.com (free, no key needed),
and posts it to a Discord channel via webhook.

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
import sys
from pathlib import Path

import requests

from verses import VERSES

HISTORY_PATH = Path(__file__).parent / "history.json"
BIBLE_API_BASE = "https://bible-api.com"
TRANSLATION = os.environ.get("BIBLE_TRANSLATION", "kjv")  # kjv, web, bbe, etc.


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
    Query bible-api.com for the verse text. Returns a dict with
    'reference' and 'text' keys. Raises on failure.
    """
    url = f"{BIBLE_API_BASE}/{reference}"
    resp = requests.get(url, params={"translation": TRANSLATION}, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    text = data.get("text", "").strip().replace("\n", " ")
    # Collapse double spaces that sometimes appear in API output
    while "  " in text:
        text = text.replace("  ", " ")

    return {
        "reference": data.get("reference", reference),
        "text": text,
        "translation": data.get("translation_id", TRANSLATION).upper(),
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
        print(f"ERROR: failed to fetch verse '{reference}' from bible-api.com: {e}", file=sys.stderr)
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
