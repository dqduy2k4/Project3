import json
import os
import re
from src.config import DATA_DIR

def super_clean_description(text):
    if not text or not isinstance(text, str):
        return ""
    
    # 0. Chuẩn hóa khoảng trắng và loại bỏ ký tự escape nếu có
    text = text.replace('\\\"', '"').replace("\\\'", "'")
    text = re.sub(r'\s+', ' ', text).strip()
    
    # TẦNG 1: Xử lý phần đuôi (Suffix) ở CUỐI câu
    suffix_pattern = r'\s*[-–—]\s*([A-ZÀ-ỹ][A-Za-zÀ-ỹ0-9.\s]{2,20})$'
    text = re.sub(suffix_pattern, '', text).strip()
    
    # TẦNG 2: Xử lý tiền tố CÓ dấu gạch ngang ở ĐẦU câu
    prefix_hyphen_pattern = r'^(\([^)]+\)|[^–—\-:]{2,30})\s*[-–—:]\s*'
    
    match = re.match(prefix_hyphen_pattern, text)
    if match:
        prefix = match.group(1).strip()
        if prefix.startswith('(') and prefix.endswith(')'):
            text = re.sub(prefix_hyphen_pattern, '', text, count=1)
        else:
            words = prefix.split()
            if any(w[0].isupper() for w in words if w):
                text = re.sub(prefix_hyphen_pattern, '', text, count=1)
                
    # TẦNG 3: Xử lý tiền tố dạng ngoặc đơn KHÔNG có gạch ngang
    prefix_paren_only_pattern = r'^\(([A-ZÀ-ỹ0-9\s.]+)\)\s+'
    text = re.sub(prefix_paren_only_pattern, '', text)
    
    return text.strip()

# --- ÁP DỤNG VÀO FILE THỰC TẾ ---
file_path = DATA_DIR / "rss_articles_clean.json"

if os.path.exists(file_path):
    with open(file_path, encoding='utf-8') as f:
        records = json.load(f)

    print(f"Đang xử lý làm sạch {len(records)} bản ghi...")

    for item in records:
        if isinstance(item, dict):
            item['description'] = super_clean_description(item.get('description', ''))

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

    print("--- HOÀN TẤT LÀM SẠCH NÂNG CAO ---")
    for item in records[:10]:
        if isinstance(item, dict):
            print(f"Title: {item.get('title', '')}\nDescription: {item.get('description', '')}\n")
else:
    print(f"Không tìm thấy file tại: {file_path}")