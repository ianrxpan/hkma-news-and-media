# HKMA News Media Scraper

Scrapes and archives HKMA speeches and insights to S3.

## Project Structure

```
hkma-news-media/
├── hkma-speech-pipeline.py             # speech pipeline (list → scrape → S3)
├── hkma-insight-pipeline.py            # insight pipeline (list → scrape → S3)
├── hkma_speech_list.jsonl              # (gitignored) speech tracking list
├── hkma_insight_list.jsonl             # (gitignored) insight tracking list
├── output/
│   ├── speech/                         # (gitignored) temporary scraped JSON files
│   └── insight/                        # (gitignored) temporary scraped JSON files
├── library/                            # (gitignored) archived JSON files
│   ├── speech/
│   └── insight/
├── speech/                             # legacy scripts (can be removed)
├── insight/                            # legacy scripts (can be removed)
├── requirements.txt
└── setup.sh
```

## Migration to Ubuntu

### Prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd hkma-news-media
```

### 2. Restore gitignored data files

The following files are not committed and must be transferred manually from the previous machine:

- `hkma_insight_list.jsonl`
- `hkma_speech_list.jsonl`
- `library/` (if you want to preserve the archive locally)

Copy them via `scp` or any file transfer method:

```bash
scp /path/to/old/hkma_insight_list.jsonl user@ubuntu-host:~/hkma-news-media/
scp /path/to/old/hkma_speech_list.jsonl user@ubuntu-host:~/hkma-news-media/
```

### 3. Run setup

```bash
chmod +x setup.sh
bash setup.sh
```

This will:
- Create a Python virtual environment at `.venv/`
- Install all dependencies (`requests`, `beautifulsoup4`, `boto3`)
- Create required directories (`output/speech`, `output/insight`, `library/speech`, `library/insight`)

### 4. Configure AWS credentials

The pipelines upload to S3 bucket `lionrockws-openclaw`. Configure credentials before running:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=<your-region>
```

### 5. Activate the virtual environment

```bash
source .venv/bin/activate
```

### 6. Run the pipelines

Each pipeline runs three steps in sequence:
1. Check the HKMA listing page for new URLs and append them to the tracking JSONL
2. Scrape each unprocessed page, generate a JSON file, and upload it to S3 immediately
3. Upload the updated tracking JSONL to S3

```bash
python hkma-speech-pipeline.py
python hkma-insight-pipeline.py
```

## Running on a Schedule (optional)

To run both pipelines daily via cron:

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/hkma-news-media && source .venv/bin/activate && python hkma-speech-pipeline.py >> logs/speech.log 2>&1 && python hkma-insight-pipeline.py >> logs/insight.log 2>&1
```

Create the logs directory first:

```bash
mkdir -p logs
```
