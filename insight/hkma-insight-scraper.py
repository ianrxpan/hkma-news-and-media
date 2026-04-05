#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

JSONL_FILE = "hkma_insight_list.jsonl"
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
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:100]
    return f"{date_compact}_{safe_title}.json"


def extract_author(list_title: str) -> str:
    """Extract author from list title pattern 'Name on Topic'."""
    m = re.match(r"^(.+?)\s+on\s+", list_title)
    return m.group(1).strip() if m else ""


def parse_insight(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h3", class_="press-release-title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    date_tag = soup.find("div", class_="date")
    date_raw = date_tag.get_text(strip=True) if date_tag else ""

    ca = soup.find("div", class_="template-content-area")
    if not ca:
        raise ValueError("Could not find .template-content-area")

    refer_note = ca.find("div", class_="referNote")
    if refer_note:
        refer_note.decompose()
    hr = ca.find("hr")
    if hr:
        hr.decompose()

    content = re.sub(r"\n{3,}", "\n\n", ca.get_text(separator="\n", strip=True))

    return {"title": title, "date_raw": date_raw, "content": content}


def fetch_page(url: str) -> str:
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
    list_title = entry["title"]
    author = extract_author(list_title)
    print(f"Processing: [{date}] {list_title[:70]}")
    print(f"  URL: {url}")

    try:
        html = fetch_page(url)
        parsed = parse_insight(html)

        result = {
            "title": parsed["title"] or list_title,
            "date": date,
            "author": author,
            "content": parsed["content"],
            "url": url,
        }

        filename = safe_filename(date, parsed["title"] or list_title)
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
        print(f"  Marked as skipped.")


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
        time.sleep(1)


if __name__ == "__main__":
    run_all()
