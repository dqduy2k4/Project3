import os
import glob
import json
from src.config import DATA_DIR

# Cấu hình đường dẫn (bạn có thể thay đổi cho đúng với thư mục của mình)
LABELED_DIR = os.path.join(DATA_DIR, "labeled_articles_split")
ORIGINAL_FILE = os.path.join(DATA_DIR, "vne_articles_clean.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "vne_articles_labeled_combined.json")

def merge_labeled_data():
    url_to_label = {}
    
    # --- BƯỚC 1: Đọc và gom tất cả dữ liệu từ các file nhãn từ 1 đến 51 ---
    # Sử dụng glob để quét toàn bộ file có tên dạng labeled_*.json
    label_files = glob.glob(os.path.join(LABELED_DIR, "labeled_*.json"))
    print(f"==> Tìm thấy {len(label_files)} file nhãn trong thư mục.")

    for file_path in label_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = json.load(f)
                
                # Trường hợp 1: File là danh sách các bài viết dạng [{"url": "...", "label": "..."}]
                if isinstance(content, list):
                    for item in content:
                        url = item.get('url')
                        label = item.get('label')
                        if url:
                            url_to_label[url] = label
                            
                # Trường hợp 2: File là một dictionary map thẳng {"url_1": "label_1", "url_2": "label_2"}
                elif isinstance(content, dict):
                    if 'url' in content and 'label' in content:  # Nếu chỉ chứa 1 object duy nhất
                        url_to_label[content['url']] = content['label']
                    else:
                        for url, label in content.items():
                            url_to_label[url] = label
            except Exception as e:
                print(f"Lỗi khi đọc file {file_path}: {e}")

    print(f"==> Tổng số URL đã được gán nhãn thu thập được: {len(url_to_label)}")

    # --- BƯỚC 2: Đọc file gốc và map nhãn dựa vào URL ---
    if not os.path.exists(ORIGINAL_FILE):
        print(f"❌ Không tìm thấy file gốc tại đường dẫn: {ORIGINAL_FILE}")
        return

    print(f"==> Đang đọc file gốc: {ORIGINAL_FILE}...")
    with open(ORIGINAL_FILE, 'r', encoding='utf-8') as f:
        original_articles = json.load(f)

    labeled_articles_result = []

    for article in original_articles:
        url = article.get('url')
        # Nếu URL của bài viết gốc nằm trong danh sách đã gán nhãn
        if url in url_to_label:
            # Sao chép dict cũ và thêm trường 'label' vào
            updated_article = article.copy()
            updated_article['label'] = url_to_label[url]
            labeled_articles_result.append(updated_article)

    print(f"==> Số lượng bài viết kết hợp thành công (đầy đủ thông tin + nhãn): {len(labeled_articles_result)}")

    # --- BƯỚC 3: Ghi dữ liệu đã có nhãn ra file mới ---
    # Tạo thư mục cha nếu chưa tồn tại
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # bảo toàn tiếng Việt bằng ensure_ascii=False
        json.dump(labeled_articles_result, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 Đã lưu file kết quả thành công tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_labeled_data()