import requests
from bs4 import BeautifulSoup
import json
import time
import os
from config import DATA_DIR

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

REQUEST_RETRIES = 3
BACKOFF_FACTOR = 1.0

def safe_get(session, url, max_retries=REQUEST_RETRIES, backoff_factor=BACKOFF_FACTOR, timeout=10):
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=timeout)
            # QUAN TRỌNG: Ném lỗi nếu gặp mã 4xx hoặc 5xx để kích hoạt cơ chế retry
            response.raise_for_status() 
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                print(f"   [!] Thất bại hoàn toàn sau {max_retries} lần thử: {url} | Lỗi: {e}")
                return None
            delay = backoff_factor * (2 ** (attempt - 1))
            print(f"   [!] Lỗi kết nối/HTTP, sẽ thử lại {attempt}/{max_retries} sau {delay:.1f}s: {e}")
            time.sleep(delay)

CATEGORY_QUOTAS = {
    "giao-duc": 600,
    "khoa-hoc-cong-nghe": 350,
    "kinh-doanh": 150,
    "doi-song": 300,
    "thoi-su": 300,
    "phap-luat": 300,
}

# Tối ưu 1: Truyền session vào hàm để tái sử dụng kết nối
def get_article_content(session, url):
    response = safe_get(session, url)
    if response is None:
        return None

    try:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p', class_='Normal')
            if paragraphs:
                return "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
    except Exception:
        pass
    return None

# Tối ưu 2: Tách hàm lưu dữ liệu để gọi liên tục
def save_data(output_file, data):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl_to_json(quotas, output_file):
    all_articles = []
    crawled_urls = set()

    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                all_articles = json.load(f)
                crawled_urls = {item['url'] for item in all_articles if 'url' in item}
            print(f"📦 Đã nạp thành công {len(crawled_urls)} URL cũ từ file để chống trùng.")
        except Exception as e:
            print(f"⚠️ Khởi tạo file mới do lỗi đọc file cũ: {e}")

    total_new_count = 0
    
    # Khởi tạo Session của requests để tối ưu tốc độ
    session = requests.Session()

    for cat, max_articles in quotas.items():
        cat_already_have = sum(1 for item in all_articles if item.get('source_category') == cat)
        
        print(f"\n=======================================================")
        print(f"🚀 MỤC: [{cat.upper()}] | Đã có: {cat_already_have} bài | Mục tiêu: {max_articles} bài")
        print(f"=======================================================")

        if cat_already_have >= max_articles:
            print(f"✅ Mục [{cat.upper()}] đã đạt chỉ tiêu. Bỏ qua.")
            continue

        cat_collected = cat_already_have
        page = 1

        while cat_collected < max_articles:
            url = f"https://vnexpress.net/{cat}-p{page}"
            print(f"📄 Đang quét [{cat.upper()}] -> Trang {page}...")
            
            try:
                response = safe_get(session, url)
                # Nếu đã nâng cấp safe_get có raise_for_status, response trả về chỉ có thể là 200 hoặc None
                if response is None:
                    print(f"   [!] Bỏ qua trang {page} do lỗi liên tục. Chuyển sang trang tiếp theo.")
                    page += 1
                    continue

                if response.url != url:
                    if page == 1 and response.url.rstrip('/') == f"https://vnexpress.net/{cat}":
                        pass
                    elif f"-p{page}" not in response.url:
                        print(f"   [!] Trang {page} bị chuyển hướng. Hết dữ liệu mới. Dừng mục.")
                        break

                soup = BeautifulSoup(response.text, 'html.parser')
                main_content = soup.find('section', class_='section_container') or \
                               soup.find('div', class_='col-left') or \
                               soup
                
                articles = main_content.find_all('article', class_='item-news')

                if not articles:
                    print(f"   [!] Không tìm thấy bài viết nào ở trang {page}.")
                    break

                page_articles_count = len(articles)
                page_duplicate_count = 0

                for article in articles:
                    if cat_collected >= max_articles:
                        break

                    if article.find('span', class_='ico-ads'):
                        continue

                    title_tag = article.find(['h2', 'h3', 'h4'], class_='title-news') or article.find(class_='title-news')
                    title = title_tag.text.strip() if title_tag else None

                    article_url = None
                    if title_tag:
                        a_tag = title_tag.find('a')
                        if a_tag and a_tag.has_attr('href'):
                            article_url = a_tag['href']

                    desc_tag = article.find('p', class_='description')
                    if desc_tag:
                        # Sao chép lại tag để tránh làm ảnh hưởng đến cấu trúc soup gốc nếu dùng lại
                        import copy
                        temp_desc_tag = copy.copy(desc_tag)
                        
                        # Tìm và xóa thẻ span chứa địa điểm (nếu có)
                        location_tag = temp_desc_tag.find('span', class_='location-stamp')
                        if location_tag:
                            location_tag.decompose() # Xóa thẻ span này khỏi đoạn text
                            
                        desc = temp_desc_tag.get_text(strip=True)
                    else:
                        desc = ""
                    
                    if title and article_url:
                        if article_url in crawled_urls:
                            page_duplicate_count += 1
                            continue # Bỏ qua bài trùng, kiểm tra bài tiếp theo trong trang
                        
                        # Cào nội dung chi tiết bài mới
                        content = get_article_content(session, article_url)
                        if content and len(content) > 100:
                            item = {
                                "url": article_url,
                                "title": title,
                                "description": desc,
                                "content": content,
                                "source_category": cat
                            }
                            all_articles.append(item)
                            crawled_urls.add(article_url)
                            cat_collected += 1
                            total_new_count += 1

                            print(f"   ✅ [{cat_collected}/{max_articles}] Thành công: {title[:40]}...")
                            time.sleep(0.5) # Delay nhỏ tránh kích hoạt bot detection của tòa soạn
                        else:
                            reason = "Không lấy được nội dung" if not content else "Nội dung quá ngắn"
                            print(f"   ⚠️ Bỏ qua bài: {title[:30]}... ({reason})")

                print(f"📝 Kết thúc trang {page}. (Trùng cũ: {page_duplicate_count}/{page_articles_count} bài).")

                # TỐI ƯU 3 SỬA ĐỔI: Không dùng break khi trùng ở những trang đầu tiên để tránh lỗi khi resume
                # if page_duplicate_count == page_articles_count and page_articles_count > 0:
                #     if page <= 2: 
                #         print(f"⏭️ Trang {page} trùng 100% do chạy lại code, lật tiếp sang trang sau tìm bài mới...")
                #     else:
                #         print(f"🛑 [Dừng Sớm] Đã chạm đến vùng dữ liệu cũ hoàn toàn ở trang sâu {page}. Dừng mục.")
                #         break
                if page_duplicate_count == page_articles_count and page_articles_count > 0:
                    print(f"⏭️ Trang {page} trùng 100% dữ liệu cũ, đang lật tiếp sang trang sau để tìm bài mới...")

                page += 1
                time.sleep(1.0)

            except Exception as e:
                print(f"   [Lỗi Hệ Thống] Tại trang {page}: {e}")
                page += 1 # Đảm bảo không bị treo vô hạn tại một trang nếu có lỗi lạ
                continue
        
        # Tối ưu 4: Lưu dữ liệu ngay sau khi hoàn thành ĐỒNG THỜI mỗi danh mục (An toàn dữ liệu)
        save_data(output_file, all_articles)
        print(f"💾 Đã lưu tiến trình danh mục [{cat.upper()}] vào file.")

    print(f"\n🎉 HOÀN THÀNH!")
    print(f"📊 Thu thập thêm được {total_new_count} bài mới. Tổng Dataset hiện tại: {len(all_articles)} bài.")
    
if __name__ == "__main__":
    output_filename = f"{DATA_DIR}/vnexpress_articles_raw.json"
    crawl_to_json(CATEGORY_QUOTAS, output_filename)