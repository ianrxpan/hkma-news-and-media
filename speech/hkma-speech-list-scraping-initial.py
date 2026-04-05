#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://www.hkma.gov.hk"
LISTING_URL = "https://www.hkma.gov.hk/eng/news-and-media/speeches/"
JSONL_FILE = Path("hkma_speech_list.jsonl")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def parse_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str.strip()


def load_existing() -> set:
    if not JSONL_FILE.exists():
        return set()
    seen = set()
    with open(JSONL_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                seen.add((entry.get("title", ""), entry.get("date", "")))
    return seen


def scrape_listing() -> list:
    r = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    result_div = soup.find("div", id="press-release-result")
    if not result_div:
        raise RuntimeError("Could not find #press-release-result in page")

    entries = []
    for ul in result_div.find_all("ul"):
        items = ul.find_all("li", recursive=False)
        if len(items) < 2:
            continue

        date_str = items[0].get_text(strip=True)
        if not re.match(r"\d{1,2}\s+\w{3}\s+\d{4}", date_str):
            continue

        link = items[1].find("a")
        if not link:
            continue

        title = link.get_text(strip=True)
        href = link.get("href", "").strip()
        if not href:
            continue

        url = href if href.startswith("http") else BASE_URL + href
        entries.append({
            "title": title,
            "url": url,
            "date": parse_date(date_str),
            "processed": False,
            "skipped": False,
        })

    return entries


def main():
    existing = load_existing()
    print(f"Existing entries: {len(existing)}")

    entries = scrape_listing()
    print(f"Scraped {len(entries)} entries from listing page")

    new_entries = [
        e for e in entries
        if (e["title"], e["date"]) not in existing
    ]
    print(f"New entries to append: {len(new_entries)}")

    if new_entries:
        with open(JSONL_FILE, "a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        for e in new_entries:
            print(f"  + [{e['date']}] {e['title'][:80]}")

    print("Done.")


if __name__ == "__main__":
    main()
