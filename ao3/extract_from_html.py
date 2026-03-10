"""Extract AO3 work URLs from saved bookmark HTML files."""
import re
import glob
from bs4 import BeautifulSoup

html_files = sorted(glob.glob("D:/Projects/calibre/ao3/bookmarks/*.html"))
print(f"Found {len(html_files)} HTML files")

urls = []
for f in html_files:
    print(f"\n{f}")
    with open(f, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "html5lib")

    page_urls = []
    for link in soup.select("a[href*='/works/']"):
        href = link.get("href", "")
        m = re.match(r".*(/works/\d+)", href)
        if m:
            url = f"https://archiveofourown.org{m.group(1)}"
            if url not in urls:
                urls.append(url)
                page_urls.append(url)
    print(f"  New: {len(page_urls)}, Total: {len(urls)}")

print(f"\nTotal: {len(urls)} unique work URLs from {len(html_files)} pages")
print(f"Missing pages 6, 10 (and 12-17)")

with open("D:/Projects/calibre/ao3/urls.txt", "w") as f:
    for url in urls:
        f.write(url + "\n")
print("Saved to urls.txt")
