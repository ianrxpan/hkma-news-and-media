#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python3"

echo "Root directory: $ROOT"
echo "Python path: $PYTHON"
echo ""

run() {
    local dir=$1
    local script=$2
    echo ">>> Starting: $dir/$script"
    cd "$ROOT/$dir"
    
    # 檢查腳本是否存在
    if [ ! -f "$script" ]; then
        echo "  ERROR: Script $script not found!"
        cd "$ROOT"
        return 1
    fi
    
    # 執行腳本
    if "$PYTHON" "$script"; then
        echo "  SUCCESS: $script completed"
    else
        echo "  WARNING: $script had issues (exit code: $?)"
    fi
    
    cd "$ROOT"
    echo "<<< Done: $dir/$script"
    echo
}

# 檢查目錄是否存在
check_dir() {
    local dir=$1
    if [ ! -d "$ROOT/$dir" ]; then
        echo "ERROR: Directory $dir not found!"
        return 1
    fi
    return 0
}

echo "=== 檢查目錄結構 ==="
check_dir "speech" || exit 1
check_dir "insight" || exit 1
echo ""

echo "=== 開始執行HKMA數據處理流程 ==="
echo ""

# Speech處理流程
echo "--- Speech處理 ---"
run "speech"  "hkma-speech-list-scraping-initial.py"
run "speech"  "hkma-speech-scraper.py"

# 檢查是否有文件需要備份
if [ -d "$ROOT/speech/output" ] && [ "$(ls -A "$ROOT/speech/output" 2>/dev/null)" ]; then
    run "speech"  "hkma-speech-backup.py"
else
    echo ">>> Skipping: speech/hkma-speech-backup.py (output directory is empty)"
    echo ""
fi

# Insight處理流程
echo "--- Insight處理 ---"
run "insight" "hkma-insight-list-scraping-initial.py"
run "insight" "hkma-insight-scraper.py"

# 檢查是否有文件需要備份
if [ -d "$ROOT/insight/output" ] && [ "$(ls -A "$ROOT/insight/output" 2>/dev/null)" ]; then
    run "insight" "hkma-insight-backup.py"
else
    echo ">>> Skipping: insight/hkma-insight-backup.py (output directory is empty)"
    echo ""
fi

echo "=== 所有流程完成 ==="
echo ""
echo "📊 數據統計:"
echo "Speech文件: $(ls -1 "$ROOT/library/speech"/*.json 2>/dev/null | wc -l 2>/dev/null || echo 0)"
echo "Insight文件: $(ls -1 "$ROOT/library/insight"/*.json 2>/dev/null | wc -l 2>/dev/null || echo 0)"

