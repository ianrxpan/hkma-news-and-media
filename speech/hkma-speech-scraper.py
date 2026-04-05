#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

JSONL_FILE = "hkma_speech_list.jsonl"
OUTPUT_DIR = Path("output")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def load_entries():
    entries = []
    with open(JSONL_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def save_entries(entries):
    with open(JSONL_FILE, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_next_entry(entries):
    for i, e in enumerate(entries):
        if not e.get("processed") and not e.get("skipped"):
            return i, e
    return None, None


def safe_filename(date: str, title: str) -> str:
    date_compact = date.replace("-", "")
    # Replace characters not safe for filenames
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    safe_title = safe_title.replace(" ", "_")
    # Truncate to avoid overly long filenames
    safe_title = safe_title[:100]
    return f"{date_compact}_{safe_title}.json"


def parse_speech(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    content_area = soup.find("div", class_="template-content-area")
    if not content_area:
        raise ValueError("Could not find .template-content-area")

    # Extract title
    title_tag = soup.find("h3", class_="press-release-title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract speaker — the <p> immediately after the h3
    speaker = ""
    if title_tag:
        next_p = title_tag.find_next_sibling("p")
        if next_p:
            speaker = next_p.get_text(strip=True)

    # Extract footnotes from .referNote div, then remove it from content
    footnote = ""
    refer_note = content_area.find("div", class_="referNote")
    if refer_note:
        footnote = refer_note.get_text(separator="\n", strip=True)
        refer_note.decompose()

    # Also remove the <hr> separator before footnote if present
    hr = content_area.find("hr")
    if hr:
        hr.decompose()

    # Extract main content text
    content = content_area.get_text(separator="\n", strip=True)
    # Clean up excessive blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return {
        "title": title,
        "speaker": speaker,
        "content": content,
        "footnote": footnote,
    }


def fetch_speech(url: str) -> str:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(2 ** attempt)
    raise Exception(f"Failed to fetch {url} after 3 attempts")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    entries = load_entries()

    idx, entry = get_next_entry(entries)
    if entry is None:
        print("No pending entries found.")
        return

    url = entry["url"]
    date = entry["date"]
    title = entry["title"]
    print(f"Processing: [{date}] {title[:70]}")
    print(f"  URL: {url}")

    try:
        html = fetch_speech(url)
        parsed = parse_speech(html)

        result = {
            "date": date,
            "title": parsed["title"] or title,
            "speaker": parsed["speaker"],
            "url": url,
            "content": parsed["content"],
            "footnote": parsed["footnote"],
        }

        filename = safe_filename(date, parsed["title"] or title)
        out_path = OUTPUT_DIR / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        entries[idx]["processed"] = True
        save_entries(entries)
        print(f"  Saved: {out_path}")

    except Exception as e:
        print(f"  Failed: {e}")
        entries[idx]["skipped"] = True
        save_entries(entries)
        print(f"  Marked as skipped in {JSONL_FILE}")


def run_all():
    while True:
        entries = load_entries()
        idx, entry = get_next_entry(entries)
        if entry is None:
            print("All entries processed.")
            break

        total = len(entries)
        pending = sum(1 for e in entries if not e.get("processed") and not e.get("skipped"))
        print(f"\n[{total - pending + 1}/{total}] Pending: {pending}")

        main()

        print("  Sleeping 10 seconds...")
        time.sleep(10)


if __name__ == "__main__":
    run_all()
