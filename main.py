import os
import re
import csv
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# === CONFIGURATION ===

start_url = os.getenv("PAGE_URL")
if not start_url:
    raise ValueError("PAGE_URL environment variable is not set.")
base_folder = "./downloaded_media"
allowed_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.mp4', '.mp3', '.txt')

# === HELPER FUNCTIONS ===

def get_subfolder_from_url(url):
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if not path_parts:
        return "root"
    return os.path.join(*path_parts)

def is_valid_media_link(url):
    url = url.lower()
    return re.search(r"/sites/default/files/\d{4}-\d{2}/[^/]+\.(pdf|jpe?g|png|docx?|xlsx?|pptx?|mp3?|mp4?|txt?)$", url)

def get_file_name_from_url(url):
    return os.path.basename(urlparse(url).path)

def download_file(file_url, page_url, base_folder, log_writer):
    file_name = get_file_name_from_url(file_url)

    # Create subfolder based on the page the file was found on
    page_subfolder = get_subfolder_from_url(page_url)
    target_folder = os.path.join(base_folder, page_subfolder)
    os.makedirs(target_folder, exist_ok=True)

    dest_path = os.path.join(target_folder, file_name)

    if os.path.exists(dest_path):
        print(f"✅ Already downloaded: {file_name} (from {page_subfolder})")
        return

    try:
        print(f"⬇️  Downloading: {file_name} → {page_subfolder}")
        response = requests.get(file_url)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Saved to: {dest_path}")
        log_writer.writerow([file_url, page_url])
    except Exception as e:
        print(f"❌ Failed to download {file_url}: {e}")


def is_internal_link(link_url, base_domain, base_path):
    parsed = urlparse(link_url)
    return (parsed.netloc == "" or parsed.netloc == base_domain) and parsed.path.startswith(base_path)

# === MAIN CRAWLER ===

def crawl_site(start_url):
    visited_pages = set()
    found_files = dict()

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    base_path = parsed_start.path.rstrip("/")

    def crawl(url):
        if url in visited_pages:
            return
        visited_pages.add(url)

        print(f"\n🔍 Crawling: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Failed to fetch {url}: {e}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Collect media links
        for tag in soup.find_all(['a', 'img', 'source'], href=True) + soup.find_all(['img', 'source'], src=True):
            media_url = tag.get('href') or tag.get('src')
            full_url = urljoin(url, media_url)
            if is_valid_media_link(full_url):
                found_files[full_url] = url  # map: file_url -> page_url

        # Follow internal links
        for tag in soup.find_all('a', href=True):
            link = tag['href']
            full_link = urljoin(url, link)
            if is_internal_link(full_link, base_domain, base_path):
                crawl(full_link)

        for tag in soup.find_all('a', href=True):
            link = tag['href']
            full_link = urljoin(url, link)
            if is_internal_link(full_link, base_domain, base_path):
                crawl(full_link)

    crawl(start_url)
    return found_files

# === DOWNLOAD & LOG ===

def main():
    subfolder = get_subfolder_from_url(start_url)
    download_folder = os.path.join(base_folder, subfolder)
    os.makedirs(download_folder, exist_ok=True)

    log_path = os.path.join(download_folder, "file_log.csv")
    with open(log_path, 'w', newline='', encoding='utf-8') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["file_url", "found_on_page"])

        all_files = crawl_site(start_url)
        print(f"\n🔗 Found {len(all_files)} files to download.")

        if not all_files:
            print("😕 No matching files found.")
            return

        choice = input("\n👉 Download all of these files? (y/n): ").strip().lower()
        if choice == 'y':
            for file_url, page_url in all_files.items():
                download_file(file_url, page_url, download_folder, log_writer)
        else:
            print("⏭ Skipping downloads.")

if __name__ == "__main__":
    main()
