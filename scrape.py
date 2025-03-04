import concurrent.futures
import os
import concurrent
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

STARTING_OFFSET = 0
BASE_URL = "https://www.website.com"
LIST_BASE_URL = f"{BASE_URL}/kasutatud/nimekiri.php"
OUTPUT_DIR = ".\output"

params = {
    "bn": "2",
    "a": "100",
    "ssid": "226073022",
    "j[0]": "1",
    "j[1]": "2",
    "j[2]": "3",
    "j[3]": "4",
    "j[4]": "5",
    "j[5]": "6",
    "j[6]": "61",
    "ae": "1",
    "af": "100",
    "otsi": "otsi",
    "ak": "0"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

chrome_options = Options()
chrome_options.add_argument("--log-level=3")
driver = webdriver.Chrome(options=chrome_options)

def load_page(url):
    driver.get(url)
    return driver.page_source

def get_listing_page(offset):
    params["ak"] = str(offset)
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{LIST_BASE_URL}?{query}"
    return load_page(url)

def extract_detail_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for tag in soup.find_all(class_="row-link"):
        href = tag.get("href")
        if href:
            if href.startswith("/"):
                href = BASE_URL + href
            links.append(href)
    return links

def extract_images(detail_url):
    html = load_page(detail_url)
    soup = BeautifulSoup(html, 'html.parser')
    images = []
    container = soup.find("div", class_="topSection__images")
    if container:
        for a in container.find_all("a", class_="vImages__item"):
            img_href = a.get("href")
            if img_href:
                images.append(img_href)
    return images

def download_image(img_url, filename):
    try:
        resp = requests.get(img_url, headers=headers, stream=True)
        if resp.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            print(f"[+] Saved image: {filename}")
        else:
            print(f"[!] Failed to download image: {img_url}")
    except Exception as e:
        print(f"[!] Error downloading {img_url}: {e}")

def main():
    offset = STARTING_OFFSET
    seen_detail_links = set()
    detail_counter = STARTING_OFFSET
    tasks = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            print(f"[+] Scraping listing page with offset {offset}...")
            html = get_listing_page(offset)
            if not html:
                break

            links = extract_detail_links(html)
            if not links:
                print("[+] No detail links found; ending pagination.")
                break

            current_links_set = set(links)
            if seen_detail_links and current_links_set.issubset(seen_detail_links):
                print("[+] All links on this page have been seen before. Ending pagination.")
                break

            seen_detail_links.update(current_links_set)

            for link in links:
                detail_counter += 1
                print("[+] Scraping detail page:", link)
                imgs = extract_images(link)
                if imgs:
                    for idx, img_url in enumerate(imgs, start=1):
                        ext = os.path.splitext(img_url)[1] or ".jpg"
                        filename = os.path.join(OUTPUT_DIR, f"car_{detail_counter}_{idx}{ext}")
                        task = executor.submit(download_image, img_url, filename)
                        tasks.append(task)
                else:
                    print("[+] No images found on detail page:", link)

            offset += 100

        concurrent.futures.wait(tasks)

    driver.quit()

if __name__ == "__main__":
    main()