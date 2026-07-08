import feedparser
import urllib.parse
from newspaper import Article, Config
import time
from datetime import datetime
from googlenewsdecoder import gnewsdecoder
import json
import os
import requests  # Dùng requests để tránh bị Google RSS chặn bot
from src.config import DATA_DIR

# --- CẤU HÌNH CƠ BẢN ---
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 15

# Hàm chia nhỏ thời gian theo từng năm một cách ngắn gọn
def get_yearly_chunks(start_year, end_year):
    chunks = []
    for year in range(start_year, end_year + 1):
        after = f"{year}-01-01"
        before = f"{year}-12-31"
        chunks.append((after, before))
    return chunks

# Cấu hình từ khóa và thời gian (Quét từ 2020 đến năm 2026 hiện tại)
keyword = 'đại học phốt' 
current_year = datetime.now().year # Tự động lấy năm 2026 hiện tại
period_chunks = get_yearly_chunks(2015, current_year)

file_path = os.path.join(DATA_DIR, 'rss_articles_raw.json')

# --- 1. ĐỌC DỮ LIỆU CŨ VÀ TẠO BỘ LỌC TRÙNG LẶP ---
existing_data = []
crawled_urls = set()

if os.path.exists(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            for item in existing_data:
                crawled_urls.add(item['Url'])
        print(f"📂 Đã tải {len(existing_data)} bài báo cũ từ cơ sở dữ liệu.")
    except Exception as e:
        print(f"⚠️ Lỗi đọc file cũ: {e}")

crawled_data = []
headers = {'User-Agent': USER_AGENT}

print("🚀 BẮT ĐẦU QUÁ TRÌNH CRAWL DỮ LIỆU QUA GOOGLE NEWS RSS...\n")

# --- 2. VÒNG LẶP THEO TỪNG NĂM (ĐÃ BỎ LỌC SITE) ---
for after, before in period_chunks:
    print(f"\n📅 Đang quét dữ liệu năm: {after[:4]} (Từ {after} đến {before})")
    
    # Tạo query tìm kiếm toàn sàn Google News, không giới hạn site nào
    query_str = f'{keyword} after:{after} before:{before}'
    query_encoded = urllib.parse.quote(query_str)
    rss_url = f"https://news.google.com/rss/search?q={query_encoded}&hl=vi&gl=VN&ceid=VN:vi"
    
    entries = []
    try:
        # Gửi request có kèm User-Agent để bypass qua hệ thống chặn của Google
        response = requests.get(rss_url, headers=headers, timeout=15)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            entries = feed.entries[:100]  # Lấy tối đa 100 bài (Giới hạn tối đa của 1 request Google RSS)
        else:
            print(f"    ❌ Google từ chối request cho năm {after[:4]} (Status code: {response.status_code})")
            time.sleep(5)
            continue
    except Exception as e:
        print(f"    ❌ Lỗi kết nối mạng khi tải RSS: {e}")
        continue

    if not entries:
        print(f"    ℹ️ Không tìm thấy bài viết nào trong năm {after[:4]}.")
        continue

    print(f"    🔍 Tìm thấy {len(entries)} bài viết tiềm năng. Bắt đầu bóc tách...")

    for entry in entries:
        url = entry.link
        rss_title = entry.title

        # Giải mã link redirect của Google News
        try:
            decoded_url = gnewsdecoder(url)
            original_url = decoded_url['decoded_url'] if decoded_url.get('status') else url
        except:
            original_url = url

        # Kiểm tra trùng lặp bài viết
        if original_url in crawled_urls:
            continue

        print(f"  -> Đang bóc tách bài MỚI: {rss_title}")

        try:
            article = Article(original_url, config=config, language='vi')
            article.download()
            article.parse()

            meta = article.meta_data
            summary = meta.get('description') or \
                      meta.get('og', {}).get('description') or \
                      meta.get('twitter', {}).get('description')

            # Tự động tách domain từ URL để làm nguồn (Source)
            source_domain = urllib.parse.urlparse(original_url).netloc

            data = {
                'url': original_url,
                'title': article.title if article.title else rss_title,
                'description': summary,
                'content': article.text,
                'source': source_domain,
            }
            crawled_data.append(data)
            crawled_urls.add(original_url)

            time.sleep(2) # Delay an toàn để không bị các trang báo block IP

        except Exception as e:
            print(f"    ❌ Lỗi bóc tách nội dung bài viết: {e}")

# --- 3. LƯU GỘP DỮ LIỆU ---
print("\n" + "="*60)
print(f"✅ ĐÃ CRAWL THÊM THÀNH CÔNG {len(crawled_data)} BÀI BÁO MỚI")
print("="*60)

if crawled_data:
    final_data = existing_data + crawled_data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Đã lưu tổng cộng {len(final_data)} bài báo vào file {file_path}")
else:
    print("\n✅ Không có bài báo mới nào được tìm thấy. Giữ nguyên dữ liệu cũ.")