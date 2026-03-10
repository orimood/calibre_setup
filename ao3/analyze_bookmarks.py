"""Analyze bookmark HTML files to find discrepancy between 333 bookmarks and 323 URLs."""
import re
import glob
from bs4 import BeautifulSoup

html_files = sorted(glob.glob("D:/Projects/calibre/ao3/bookmarks/*.html"),
                    key=lambda f: int(re.search(r'_(\d+)\.html', f).group(1)))

total_bookmarks = 0
work_urls = []
non_work_items = []

for f in html_files:
    page_num = int(re.search(r'_(\d+)\.html', f).group(1))
    with open(f, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "html5lib")

    # Count all bookmark list items
    bookmarks = soup.select("li.bookmark")
    total_bookmarks += len(bookmarks)

    for bm in bookmarks:
        heading = bm.select_one("h4.heading")
        if not heading:
            non_work_items.append(f"Page {page_num}: No heading found in bookmark")
            continue

        links = heading.select("a")
        href = links[0].get("href", "") if links else ""
        title = links[0].get_text(strip=True) if links else "Unknown"

        if "/works/" in href:
            m = re.match(r".*(/works/\d+)", href)
            if m:
                url = f"https://archiveofourown.org{m.group(1)}"
                if url not in work_urls:
                    work_urls.append(url)
        elif "/series/" in href:
            non_work_items.append(f"Page {page_num}: SERIES - {title} ({href})")
        elif "/external_works/" in href:
            non_work_items.append(f"Page {page_num}: EXTERNAL - {title} ({href})")
        else:
            non_work_items.append(f"Page {page_num}: OTHER - {title} ({href})")

    print(f"Page {page_num}: {len(bookmarks)} bookmarks")

print(f"\n=== Summary ===")
print(f"Total bookmark items across all pages: {total_bookmarks}")
print(f"Unique work URLs: {len(work_urls)}")
print(f"Non-work items: {len(non_work_items)}")

if non_work_items:
    print(f"\n=== Non-work bookmarks ===")
    for item in non_work_items:
        print(f"  {item}")
