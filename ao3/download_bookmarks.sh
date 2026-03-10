#!/bin/bash
# Download all AO3 bookmarks for user orimood
# 333 bookmarks = 17 pages (20 per page)

cd "$(dirname "$0")"

echo "=== Extracting bookmark URLs from 17 pages ==="
> urls.txt  # clear file

for page in $(seq 1 17); do
    echo "Fetching page $page/17..."
    fanficfare -l "https://archiveofourown.org/users/orimood/bookmarks?page=$page" >> urls.txt
done

total=$(wc -l < urls.txt)
echo "=== Found $total URLs ==="

echo "=== Downloading all fics ==="
fanficfare -i urls.txt
