#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import boto3
from pathlib import Path

S3_BUCKET = "lionrockws-openclaw"
S3_JSON_PREFIX = "hkma/news-and-media/insight/markdown"
S3_JSONL_PREFIX = "hkma/news-and-media/insight"

OUTPUT_DIR = Path("output")
LIBRARY_DIR = Path("../library/insight")
JSONL_FILE = Path("hkma_insight_list.jsonl")


def main():
    s3 = boto3.client("s3")
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

    json_files = list(OUTPUT_DIR.glob("*.json"))
    if not json_files:
        print("No JSON files found in output/")
    else:
        for f in json_files:
            s3_key = f"{S3_JSON_PREFIX}/{f.name}"
            print(f"Uploading {f.name} -> s3://{S3_BUCKET}/{s3_key}")
            s3.upload_file(str(f), S3_BUCKET, s3_key)

            dest = LIBRARY_DIR / f.name
            shutil.move(str(f), str(dest))
            print(f"  Moved to {dest}")

        print(f"\nProcessed {len(json_files)} file(s).")

    # Backup the JSONL list
    s3_jsonl_key = f"{S3_JSONL_PREFIX}/{JSONL_FILE.name}"
    print(f"\nUploading {JSONL_FILE} -> s3://{S3_BUCKET}/{s3_jsonl_key}")
    s3.upload_file(str(JSONL_FILE), S3_BUCKET, s3_jsonl_key)
    print("Done.")


if __name__ == "__main__":
    main()
