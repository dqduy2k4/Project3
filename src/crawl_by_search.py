import requests
import os
import time
import json
import urllib.parse
from bs4 import BeautifulSoup
from src.config import DATA_DIR

def safe_get(url, headers=None, timeout=10, max_retries=3, backoff_factor=2):
    """
    Hàm gửi request GET an toàn, tự động retry nếu gặp lỗi mạng hoặc server.
    Thực hiện cơ chế Exponential Backoff (chờ lâu hơn sau mỗi lần thử lại).
    """
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=timeout)
            # Nếu status_code thuộc nhóm 5xx (Server lỗi) hoặc 429 (Too Many Requests), có thể retry
            if res.status_code == 200:
                return res
            
            print(f"  [!] HTTP {res.status_code} tại {url}. Thử lại lần {attempt}/{max_retries}...")
        except requests.RequestException as e:
            print(f"  [!] Lỗi mạng ({e}) tại {url}. Thử lại lần {attempt}/{max_retries}...")
        
        # Nếu chưa phải lần thử cuối cùng, ngủ một lát trước khi thử lại
        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            time.sleep(sleep_time)
            
    return None # Trả về None nếu tất cả các lần thử đều thất bại

def get_article_links(query, crawled_urls=None, max_links=None):
    """Lấy danh sách link bài viết từ từ khóa (Đã tích hợp safe_get)"""
    page = 1
    all_links = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    crawled_urls = crawled_urls or set()
    encoded_query = urllib.parse.quote(query)

    while True:
        url = f"https://timkiem.vnexpress.net/?q={encoded_query}&media_type=all&fromdate=0&todate=0&latest=1&cate_code=&search_f=title,tag_list&date_format=all&page={page}"
        print(f"  [Từ khóa: {query}] Đang kiểm tra trang {page}...")

        # Thay thế requests.get bằng safe_get
        response = safe_get(url, headers=headers, timeout=10, max_retries=3)
        if response is None:
            print(f"  [->] Bỏ qua trang {page} do lỗi mạng liên tục.")
            page += 1 # Hoặc dùng 'break' nếu bạn muốn dừng hẳn khi lỗi hệ thống tìm kiếm
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.select('article.item-news')

        if not articles:
            break

        page_new_links = 0
        for art in articles:
            link = art.get('data-url')
            if link:
                if link not in crawled_urls:
                    if link not in all_links:
                        all_links.append(link)
                        page_new_links += 1
                        
                        if max_links is not None and len(all_links) >= max_links:
                            print(f"  [->] Đã thu thập đủ giới hạn {max_links} link. Dừng tìm kiếm!")
                            return all_links

        # if page_new_links == 0 and len(articles) > 0:
        #     print(f"  [->] Trang {page} toàn bộ là bài viết đã có. Dừng tìm kiếm sớm!")
        #     break

        page += 1
        time.sleep(1)

    return all_links


def crawl_content(url):
    """Hàm lấy nội dung chi tiết (Đã tích hợp safe_get)"""
    # Thay thế requests.get bằng safe_get
    res = safe_get(url, timeout=10, max_retries=3)
    if res is None:
        return None
        
    try:
        soup = BeautifulSoup(res.content, 'html.parser')

        title = soup.select_one('h1.title-detail').get_text(strip=True) if soup.select_one('h1.title-detail') else ""
        description = ""
        desc_tag = soup.select_one('p.description')
        if desc_tag:
            location_tag = desc_tag.select_one('.location-stamp')
            if location_tag:
                location_tag.decompose()
            description = desc_tag.get_text(strip=True)
            
        content_parts = [p.get_text(separator=" ", strip=True) for p in soup.select('article.fck_detail p.Normal')]
        if not content_parts:
            all_p_tags = soup.select('article.fck_detail p')
            content_parts = [
                p.get_text(separator=" ", strip=True) 
                for p in all_p_tags 
                if not p.has_attr('class') or 'Image' not in p['class']
            ]

        full_content = "\n".join(content_parts)

        # ================= TRÍCH XUẤT CATEGORY =================
        source_category = ""
        breadcrumb_tags = soup.select('ul.breadcrumb li a') or soup.select('.breadcrumb a')
        if breadcrumb_tags:
            href_value = breadcrumb_tags[0].get('href', '')
            path_parts = [part for part in href_value.split('/') if part]
            if path_parts:
                source_category = path_parts[0]
            
        if not source_category:
            meta_section = soup.find('meta', property='article:section') or soup.find('meta', itemprop='articleSection')
            text_cate = ""
            if meta_section and meta_section.get('content'):
                text_cate = meta_section.get('content').strip()
            else:
                category_tag = soup.select_one('a[data-medium^="Menu-"]')
                if category_tag:
                    text_cate = category_tag.get_text(strip=True)
            
            if text_cate:
                import unicodedata
                import re
                text_cate = unicodedata.normalize('NFKD', text_cate).encode('ascii', 'ignore').decode('utf-8')
                source_category = re.sub(r'[^a-z0-9\s-]', '', text_cate.lower())
                source_category = re.sub(r'[\s-]+', '-', source_category).strip('-')
        # ================================================================================

        return {
            "url": url,
            "title": title,
            "description": description,
            "content": full_content,
            "source_category": source_category
        }
    except Exception as e:
        print(f"Lỗi khi parse nội dung bài {url}: {e}")
        return None

def save_json_atomic(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temp_path = f"{file_path}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(temp_path, file_path)


# --- THỰC THI (Giữ nguyên logic của bạn) ---
if __name__ == "__main__":
    query_keywords = [
        # "đại học bách khoa",
        # "đại học quốc gia",
        # "đại học y",
        # "đại học kinh tế quốc dân",
        # "đại học ngoại thương",
        # "đại học fpt",
        "đại học"
    ]
    input_file = f"{DATA_DIR}/vne_articles_raw.json"
    output_file = f"{DATA_DIR}/vne_articles_raw.json"
    # Giới hạn tổng số bài viết cào được (None = không giới hạn)
    MAX_TOTAL_RECORDS = None

    existing_data = []
    crawled_urls = set()

    if os.path.exists(input_file):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    crawled_urls = {item['url'] for item in existing_data if 'url' in item}
            print(f"[*] Tìm thấy {len(crawled_urls)} bài báo cũ đã lưu.")
        except Exception as e:
            print(f"[!] Không thể đọc file nguồn ({e}).")
            existing_data = []
    else:
        print(f"[!] File nguồn không tồn tại: {input_file}.")

    links_to_crawl = set()
    for kw in query_keywords:
        print(f"\n---> Bắt đầu tìm kiếm với từ khóa: '{kw}'")

        if MAX_TOTAL_RECORDS is not None:
            current_total = len(crawled_urls) + len(links_to_crawl)
            remaining_slots = MAX_TOTAL_RECORDS - current_total

            if remaining_slots <= 0:
                print(f"--> Hệ thống đã đạt mốc {MAX_TOTAL_RECORDS}. Dừng tìm kiếm!")
                break

            max_links = remaining_slots
        else:
            max_links = None

        new_links_found = get_article_links(kw, crawled_urls=crawled_urls, max_links=max_links)

        print(f"==> Tìm thấy {len(new_links_found)} bài viết MỚI cho từ khóa '{kw}'")
        links_to_crawl.update(new_links_found)

    links_to_crawl = list(links_to_crawl)
    print(f"\nTổng số bài báo THỰC SỰ MỚI cần crawl: {len(links_to_crawl)}")

    new_results = []
    if links_to_crawl:
        for i, link in enumerate(links_to_crawl):
            print(f"[{i+1}/{len(links_to_crawl)}] Đang cào: {link}")
            data = crawl_content(link)
            if data:
                new_results.append(data)
            time.sleep(0.5)

    updated_data = existing_data + new_results
    save_json_atomic(output_file, updated_data)

    if new_results:
        print(f"\nHoàn thành! Đã cào thêm {len(new_results)} bài mới.")
    else:
        print(f"\nKhông có bài mới.")