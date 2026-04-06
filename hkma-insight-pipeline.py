#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import shutil
import time
import boto3
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://www.hkma.gov.hk"
LISTING_URL = "https://www.hkma.gov.hk/eng/news-and-media/insight/"
JSONL_FILE = Path("hkma_insight_list.jsonl")
OUTPUT_DIR = Path("output/insight")
LIBRARY_DIR = Path("library/insight")
S3_BUCKET = "lionrockws-openclaw"
S3_JSON_PREFIX = "hkma/news-and-media/insight/markdown"
S3_JSONL_PREFIX = "hkma/news-and-media/insight"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ── Step 1: Fetch new listing entries ────────────────────────────────────────

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


def fetch_listing():
    existing = load_existing()
    print(f"Existing entries: {len(existing)}")

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
        entries.append({"title": title, "url": url, "date": parse_date(date_str), "processed": False, "skipped": False})

    new_entries = [e for e in entries if (e["title"], e["date"]) not in existing]
    print(f"New entries: {len(new_entries)}")

    if new_entries:
        with open(JSONL_FILE, "a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        for e in new_entries:
            print(f"  + [{e['date']}] {e['title'][:80]}")


# ── Step 2: Scrape each insight page ─────────────────────────────────────────

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


def safe_filename(date: str, title: str) -> str:
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:100]
    return f"{date.replace('-', '')}_{safe_title}.json"


def extract_author(list_title: str) -> str:
    m = re.match(r"^(.+?)\s+on\s+", list_title)
    return m.group(1).strip() if m else ""


def parse_insight(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h3", class_="press-release-title")
    title = title_tag.get_text(strip=True) if title_tag else ""

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
    return {"title": title, "content": content}


def fetch_url(url: str) -> str:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(2 ** attempt)
    raise Exception(f"Failed to fetch {url} after 3 attempts")


def upload_and_archive(s3, f: Path):
    s3_key = f"{S3_JSON_PREFIX}/{f.name}"
    s3.upload_file(str(f), S3_BUCKET, s3_key)
    dest = LIBRARY_DIR / f.name
    shutil.move(str(f), str(dest))
    print(f"  Uploaded & moved to {dest}")


def scrape_insights():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client("s3")

    while True:
        entries = load_entries()
        idx, entry = next(
            ((i, e) for i, e in enumerate(entries) if not e.get("processed") and not e.get("skipped")),
            (None, None)
        )
        if entry is None:
            print("All entries processed.")
            break

        pending = sum(1 for e in entries if not e.get("processed") and not e.get("skipped"))
        print(f"\n[{len(entries) - pending + 1}/{len(entries)}] [{entry['date']}] {entry['title'][:70]}")

        try:
            parsed = parse_insight(fetch_url(entry["url"]))
            result = {
                "title": parsed["title"] or entry["title"],
                "date": entry["date"],
                "author": extract_author(entry["title"]),
                "content": parsed["content"],
                "url": entry["url"],
            }
            out_path = OUTPUT_DIR / safe_filename(entry["date"], result["title"])
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  Saved: {out_path}")
            upload_and_archive(s3, out_path)
            entries[idx]["processed"] = True
        except Exception as e:
            print(f"  Failed: {e}")
            entries[idx]["skipped"] = True

        save_entries(entries)
        print("  Sleeping 10 seconds...")
        time.sleep(10)


# ── Step 3: Backup JSONL to S3 ───────────────────────────────────────────────

def backup_jsonl():
    s3 = boto3.client("s3")
    s3_jsonl_key = f"{S3_JSONL_PREFIX}/{JSONL_FILE.name}"
    print(f"Uploading {JSONL_FILE} -> s3://{S3_BUCKET}/{s3_jsonl_key}")
    s3.upload_file(str(JSONL_FILE), S3_BUCKET, s3_jsonl_key)
    print("Done.")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Step 1: Fetch new listing entries ===")
    fetch_listing()

    print("\n=== Step 2: Scrape insight pages ===")
    scrape_insights()

    print("\n=== Step 3: Backup JSONL to S3 ===")
    backup_jsonl()
