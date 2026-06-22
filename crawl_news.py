import requests
import os
from bs4 import BeautifulSoup
import time
import json
import urllib.parse  # Thêm thư viện để mã hóa tiếng Việt có dấu trên URL

def get_article_links(query):
    page = 1
    all_links = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Mã hóa từ khóa (Ví dụ: "đạo văn" -> "%C4%91%E1%BA%A1o%20v%C4%83n") để không bị lỗi link
    encoded_query = urllib.parse.quote(query)

    while True:
        # 1. Tạo URL cho từng trang
        url = f"https://timkiem.vnexpress.net/?q={encoded_query}&media_type=all&fromdate=0&todate=0&latest=&cate_code=&search_f=title,tag_list&date_format=all&page={page}"
        print(f"  [Từ khóa: {query}] Đang kiểm tra trang {page}...")

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.content, 'html.parser')

            # 2. Tìm tất cả các thẻ article chứa bài báo
            articles = soup.select('article.item-news')

            # ĐIỀU KIỆN DỪNG: Nếu không tìm thấy thẻ article nào thì dừng lại
            if not articles:
                break

            # 3. Trích xuất link từ mỗi bài báo
            for art in articles:
                link = art.get('data-url')
                if link:
                    all_links.append(link)

            # Tăng số trang và nghỉ một chút để tránh bị chặn (Rate Limit)
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Lỗi tại trang {page}: {e}")
            break

    return list(set(all_links)) # Loại bỏ link trùng nội bộ của từ khóa đó

def crawl_content(url):
    """Hàm lấy nội dung chi tiết của một bài báo"""
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, 'html.parser')

        title = soup.select_one('h1.title-detail').get_text(strip=True) if soup.select_one('h1.title-detail') else ""
        description = ""
        desc_tag = soup.select_one('p.description')
        if desc_tag:
            # Tìm và xóa thẻ chứa địa danh (ví dụ: Đồng Tháp) nếu có
            location_tag = desc_tag.select_one('.location-stamp')
            if location_tag:
                location_tag.decompose()

            description = desc_tag.get_text(strip=True)
            
        # 1. Thử lấy theo cấu trúc bài viết thông thường trước (p.Normal)
        content_parts = [p.get_text(separator=" ", strip=True) for p in soup.select('article.fck_detail p.Normal')]
        # 2. Nếu không tìm thấy p.Normal (bài dạng Gallery/E-magazine), lấy tất cả thẻ p 
        # nhưng chủ động loại bỏ các thẻ p làm caption ảnh (class="Image")
        if not content_parts:
            all_p_tags = soup.select('article.fck_detail p')
            content_parts = [
                p.get_text(separator=" ", strip=True) 
                for p in all_p_tags 
                if not p.has_attr('class') or 'Image' not in p['class']
            ]

        full_content = "\n".join(content_parts)
        return {
            "url": url,
            "title": title,
            "description": description,
            "content": full_content
        }
    except:
        return None

# --- THỰC THI ---

# Thay đổi thành mảng danh sách các từ khóa cần quét
query_keywords = [
    "đại học bách khoa hà nội", #264
    "nghiên cứu khoa học",      #231
    "cơ sở vật chất",           #28
    "bằng cấp",                 #92
    "đạo văn",                  #44
    "gian lận thi cử",          #73
    "sai phạm",                 #301
    "buộc thôi học",            #16
    "bạo lực học đường",        #236
    #"kỷ luật",                  #440
    #"ngộ độc thực phẩm",        #307
    "thực phẩm bẩn",            #117
    "tăng học phí",             #116
    "xử phạt",                  #310
    #"vi phạm",                  #758
    "tệ nạn",                   #21
]

DATA_DIR = 'data'
FILE_NAME = 'vne_articles.json'
file_path = os.path.join(DATA_DIR, FILE_NAME) 

# BƯỚC 1: Đọc dữ liệu đã crawl từ trước (nếu có) để lấy danh sách URL cũ
existing_data = []
crawled_urls = set()

# Nếu file tồn tại thì đọc (thư mục data lúc này chắc chắn đã có hoặc chưa không quan trọng vì os.path.exists check được)
if os.path.exists(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            if isinstance(existing_data, list):
                crawled_urls = {item['url'] for item in existing_data if 'url' in item}
        print(f"[*] Tìm thấy {len(crawled_urls)} bài báo cũ đã lưu trong file.")
    except Exception as e:
        print(f"[!] File cũ bị lỗi cấu trúc hoặc rỗng ({e}). Sẽ tạo mới hoàn toàn.")
        existing_data = []

# BƯỚC 2: Tìm kiếm link từ các từ khóa
current_run_links = set()
for kw in query_keywords:
    print(f"\n---> Bắt đầu tìm kiếm với từ khóa: '{kw}'")
    links_for_kw = get_article_links(kw)
    print(f"==> Tìm thấy {len(links_for_kw)} bài viết cho từ khóa '{kw}'")
    current_run_links.update(links_for_kw)

# BƯỚC 3: LỌC TRÙNG LỊCH SỬ (Chỉ giữ lại các link CHƯA TỪNG CRAWL)
all_links = list(current_run_links)
links_to_crawl = [link for link in all_links if link not in crawled_urls]

print(f"\n{'='*50}")
print(f"Tổng số link tìm thấy: {len(all_links)}")
print(f"Số link ĐÃ CÓ trong file (Bỏ qua): {len(all_links) - len(links_to_crawl)}")
print(f"Số bài báo MỚI cần crawl: {len(links_to_crawl)}")
print(f"{'='*50}\n")

# BƯỚC 4: Chỉ tiến hành cào các bài báo MỚI
new_results = []
for i, link in enumerate(links_to_crawl):
    print(f"[{i+1}/{len(links_to_crawl)}] Đang thu thập nội dung mới: {link}")
    data = crawl_content(link)
    if data:
        new_results.append(data)
    time.sleep(0.5)

# BƯỚC 5: Gộp dữ liệu mới vào dữ liệu cũ và ghi đè file với mode 'w' để bảo toàn cấu trúc JSON
if new_results:
    existing_data.extend(new_results)  # Gộp list mới vào list cũ
    
    # --- THÀNH CÔNG: Tự động kiểm tra và tạo thư mục 'data' nếu máy mới chưa có ---
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"[*] Đã tự động tạo thư mục rỗng: {DATA_DIR}")
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
        
    print(f"\nHoàn thành! Đã crawl thêm {len(new_results)} bài mới. Tổng số bài hiện tại: {len(existing_data)}")
else:
    print("\nKhông có bài viết nào mới để cập nhật!")