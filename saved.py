import os
import re
import csv
import requests
from bs4 import BeautifulSoup

BASE_URL = "" #add your base URL here
HTML_FOLDER = "./saved_pages"
OUTPUT_FOLDER = "./admin_files_downloaded"
LOG_FILE = "admin_files_log.csv"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def extract_file_urls_from_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    urls = []
    for td in soup.find_all('td', headers="view-uri-table-column"):
        if td.text.strip().startswith("/sites/default/files/"):
            rel_path = td.text.strip()
            full_url = BASE_URL + rel_path
            urls.append(full_url)
    return urls

def download_file(url, log_writer):
    filename = os.path.basename(url)
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    if os.path.exists(output_path):
        print(f"✅ Already downloaded: {filename}")
        return

    try:
        print(f"⬇️ Downloading: {filename}")
        r = requests.get(url)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(r.content)
        log_writer.writerow([filename, url])
        print(f"✅ Saved to: {output_path}")
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")

def main():
    html_files = sorted(f for f in os.listdir(HTML_FOLDER) if f.endswith(".html"))
    all_urls = set()

    for html_file in html_files:
        print(f"🔍 Processing {html_file}")
        file_path = os.path.join(HTML_FOLDER, html_file)
        urls = extract_file_urls_from_html(file_path)
        all_urls.update(urls)

    print(f"\n📎 Total unique files found: {len(all_urls)}\n")

    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as log_csv:
        writer = csv.writer(log_csv)
        writer.writerow(["filename", "url"])
        for url in sorted(all_urls):
            download_file(url, writer)

if __name__ == "__main__":
    main()
