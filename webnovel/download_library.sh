#!/bin/bash
# Download all novels from novelfire.net library
# Resumable - skips novels already in completed.txt
OUTDIR="D:/torents/books"
LOGFILE="$OUTDIR/download.log"
URLFILE="$OUTDIR/library_urls.txt"
DONEFILE="$OUTDIR/completed.txt"

# Ensure we're in the output directory
cd "$OUTDIR" || exit 1

# Create completed tracker if it doesn't exist
touch "$DONEFILE"

echo "Starting library download at $(date)" >> "$LOGFILE"
echo "Output directory: $(pwd)" >> "$LOGFILE"
echo "Total novels: $(wc -l < "$URLFILE")" >> "$LOGFILE"
echo "Already completed: $(wc -l < "$DONEFILE")" >> "$LOGFILE"
echo "---" >> "$LOGFILE"

count=0
skipped=0
total=$(wc -l < "$URLFILE")

while IFS= read -r url; do
    count=$((count + 1))

    # Skip if already completed
    if grep -qF "$url" "$DONEFILE" 2>/dev/null; then
        skipped=$((skipped + 1))
        echo "[$count/$total] SKIP (already done): $url" >> "$LOGFILE"
        continue
    fi

    echo "[$count/$total] Downloading: $url" >> "$LOGFILE"
    output=$(cd "$OUTDIR" && fanficfare --force "$url" 2>&1)
    exit_code=$?
    echo "$output" >> "$LOGFILE"

    if [ $exit_code -eq 0 ]; then
        echo "$url" >> "$DONEFILE"
        echo "[$count/$total] DONE: $url" >> "$LOGFILE"
    else
        echo "[$count/$total] FAILED (exit $exit_code): $url" >> "$LOGFILE"
    fi
    echo "" >> "$LOGFILE"
done < "$URLFILE"

echo "---" >> "$LOGFILE"
echo "Finished at $(date)" >> "$LOGFILE"
echo "Downloaded: $((count - skipped)) | Skipped: $skipped | Total: $total" >> "$LOGFILE"
