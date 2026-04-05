# HKMA News Media Scraper

Scrapes and archives HKMA speeches and insights to S3.

## Project Structure

```
hkma-news-media/
├── insight/
│   ├── output/                         # (gitignored) scraped JSON files
│   ├── hkma_insight_list.jsonl         # (gitignored) tracking list
│   ├── hkma-insight-list-scraping-initial.py   # fetch new listing entries
│   ├── hkma-insight-scraper.py         # scrape each insight page
│   └── hkma-insight-backup.py          # upload to S3 and move to library
├── speech/
│   ├── output/                         # (gitignored) scraped JSON files
│   ├── hkma_speech_list.jsonl          # (gitignored) tracking list
│   ├── hkma-speech-list-scraping-initial.py    # fetch new listing entries
│   ├── hkma-speech-scraper.py          # scrape each speech page
│   └── hkma-speech-backup.py           # upload to S3 and move to library
├── library/                            # (gitignored) archived JSON files
│   ├── insight/
│   └── speech/
├── requirements.txt
├── setup.sh
└── run.sh
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

- `insight/hkma_insight_list.jsonl`
- `speech/hkma_speech_list.jsonl`
- `library/` (if you want to preserve the archive locally)

Copy them via `scp` or any file transfer method:

```bash
scp -r /path/to/old/insight/hkma_insight_list.jsonl user@ubuntu-host:~/hkma-news-media/insight/
scp -r /path/to/old/speech/hkma_speech_list.jsonl user@ubuntu-host:~/hkma-news-media/speech/
```

### 3. Run setup

```bash
chmod +x setup.sh run.sh
bash setup.sh
```

This will:
- Create a Python virtual environment at `.venv/`
- Install all dependencies (`requests`, `beautifulsoup4`, `boto3`)
- Create required directories (`insight/output`, `speech/output`, `library/insight`, `library/speech`)

### 4. Configure AWS credentials

The backup scripts upload to S3 bucket `lionrockws-openclaw`. Configure credentials before running:

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

### 6. Run the pipeline

```bash
bash run.sh
```

The pipeline runs in this order:

1. `speech/hkma-speech-list-scraping-initial.py` — fetch new speech listing entries
2. `speech/hkma-speech-scraper.py` — scrape each speech page
3. `speech/hkma-speech-backup.py` — upload to S3, move to `library/speech/`
4. `insight/hkma-insight-list-scraping-initial.py` — fetch new insight listing entries
5. `insight/hkma-insight-scraper.py` — scrape each insight page
6. `insight/hkma-insight-backup.py` — upload to S3, move to `library/insight/`

## Running on a Schedule (optional)

To run the pipeline daily via cron:

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/hkma-news-media && source .venv/bin/activate && bash run.sh >> logs/run.log 2>&1
```

Create the logs directory first:

```bash
mkdir -p logs
```
