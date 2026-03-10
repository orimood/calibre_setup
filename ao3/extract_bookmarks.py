"""Extract AO3 bookmark URLs using browser session cookie."""
import re
import time
import requests
from bs4 import BeautifulSoup

USERNAME = "orimood"
BASE = "https://archiveofourown.gay"
SESSION_COOKIE = "eyJfcmFpbHMiOnsibWVzc2FnZSI6ImV5SnpaWE56YVc5dVgybGtJam9pT0RsaU9ETm1ObVJqWXpneE5qYzRaR0U0WldObU1HSmtObVZoT0RKak1HWWlMQ0ozWVhKa1pXNHVkWE5sY2k1MWMyVnlMbXRsZVNJNlcxc3hNelUwT1RVM09WMHNJaVF5WVNReE5DUlNZbGxhTkRsSlVsTk5aMUY1TWk1clFtMURWbXQxSWwwc0lsOWpjM0ptWDNSdmEyVnVJam9pUVdkMFVHRkhka2RxVlZkd1JtbGZjbWQzZDFJM1IwOXFlV05KVjJ0T1MyTnZWVFpHVEVSTlltWk9NQ0o5IiwiZXhwIjoiMjAyNi0wMy0yM1QxODo1MzoyNi4wMTdaIiwicHVyIjoiY29va2llLl9vdHdhcmNoaXZlX3Nlc3Npb24ifX0%3D--70febeffd66056d47c1f051a107a2d5b8e879dfb"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
})
session.cookies.set("_otwarchive_session", SESSION_COOKIE, domain="archiveofourown.gay")
session.cookies.set("user_credentials", "1", domain="archiveofourown.gay")

urls = []
page = 1

while True:
    print(f"Fetching page {page}...")
    time.sleep(6)
    resp = session.get(f"{BASE}/users/{USERNAME}/bookmarks?page={page}", timeout=60)
    print(f"  Status: {resp.status_code}")

    if resp.status_code == 429:
        print("  Rate limited, waiting 5 min...")
        time.sleep(300)
        resp = session.get(f"{BASE}/users/{USERNAME}/bookmarks?page={page}", timeout=60)
        print(f"  Retry status: {resp.status_code}")
        if resp.status_code != 200:
            print("  Still blocked. Exiting.")
            break

    if resp.status_code != 200:
        print(f"  Error {resp.status_code}, stopping.")
        break

    soup = BeautifulSoup(resp.text, "html5lib")

    if page == 1:
        greeting = soup.find("li", class_="greeting")
        print(f"  Logged in: {greeting.get_text(strip=True) if greeting else 'NO'}")

    page_urls = []
    for link in soup.select("a[href*='/works/']"):
        href = link.get("href", "")
        m = re.match(r"(/works/\d+)", href)
        if m:
            url = f"https://archiveofourown.org{m.group(1)}"
            if url not in urls:
                urls.append(url)
                page_urls.append(url)

    print(f"  New: {len(page_urls)}, Total: {len(urls)}")

    if len(page_urls) == 0:
        print("  No more bookmarks. Done!")
        break

    page += 1

print(f"\nTotal: {len(urls)} unique work URLs")

if urls:
    with open("urls.txt", "w") as f:
        for url in urls:
            f.write(url + "\n")
    print("Saved to urls.txt")
