#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

BASE_URL = "https://www.hkma.gov.hk"
SOURCE_FILE = "source.html"
OUTPUT_FILE = "hkma_speech_list.jsonl"


def parse_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str.strip()


def extract_speeches(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    result_div = soup.find("div", id="press-release-result")
    if not result_div:
        raise RuntimeError("Could not find #press-release-result in HTML")

    speeches = []
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

        speeches.append({
            "title": title,
            "url": url,
            "date": parse_date(date_str),
            "processed": False,
            "skipped": False,
        })

    return speeches


def main():
    with open(SOURCE_FILE, encoding="utf-8") as f:
        html = f.read()

    speeches = extract_speeches(html)
    print(f"Extracted {len(speeches)} speeches")

    # Deduplicate by URL
    seen = set()
    unique = []
    for s in speeches:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)

    if len(speeches) != len(unique):
        print(f"After dedup: {len(unique)} (removed {len(speeches) - len(unique)} duplicates)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in unique:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Written to {OUTPUT_FILE}")
    for i, s in enumerate(unique[:3], 1):
        print(f"  {i}. [{s['date']}] {s['title'][:80]}")


if __name__ == "__main__":
    main()
