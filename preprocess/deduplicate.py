import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

def clean_title_for_embedding(title):
    title_lower = title.lower()
    
    # Danh sách stop phrases
    stop_phrases = [
        "trường đại học bách khoa hà nội", "đại học bách khoa hà nội",
        "trường bách khoa hà nội", "đhbk hà nội", "đhbk hn", "hust"
    ]
    
    # Sắp xếp danh sách theo độ dài giảm dần (quan trọng!)
    # Để nó xóa cụm dài trước (Đại học Bách khoa Hà Nội) rồi mới đến cụm ngắn (HUST)
    stop_phrases.sort(key=len, reverse=True)
    
    # Tạo Pattern với word boundary \b
    # re.escape giúp xử lý các ký tự đặc biệt nếu có trong cụm từ
    pattern = r'\b(' + '|'.join(map(re.escape, stop_phrases)) + r')\b'
    
    # Thay thế các cụm từ khớp pattern bằng khoảng trắng, sau đó dọn dẹp khoảng trắng thừa
    cleaned_title = re.sub(pattern, '', title_lower)
    
    # Xử lý khoảng trắng thừa (double space thành single space)
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    
    return cleaned_title

def get_important_numbers(text):
    """
    Chỉ trích xuất các số có khả năng là năm (2024, 2025, 2026) 
    hoặc số đợt thi (Đợt 1, Đợt 2).
    """
    # Tìm tất cả các số
    all_nums = re.findall(r'\d+', text)
    
    important_nums = set()
    for n in all_nums:
        # Ví dụ: Chỉ lấy số có 4 chữ số (năm) hoặc số nhỏ (đợt thi 1, 2, 3)
        if (len(n) == 4 and n.startswith('20')) or (int(n) < 10):
            important_nums.add(n)
            
    return important_nums

# 1. Đọc dữ liệu JSON
with open('D:\\Documents\\Project3\\data\\news_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 2. Vector hóa tiêu đề
print("🔄 Đang xử lý trùng lặp ngữ nghĩa...")
model = SentenceTransformer('keepitreal/vietnamese-sbert')

# TẠO TIÊU ĐỀ SẠCH ĐỂ ĐƯA VÀO MODEL
# Ví dụ: "Đại học Bách khoa Hà Nội công bố điểm sàn 2025" -> "công bố điểm sàn 2025"
clean_titles_for_model = [clean_title_for_embedding(item['Title']) for item in data]
embeddings = model.encode(clean_titles_for_model, show_progress_bar=True)

# 3. Tính toán độ tương đồng
cos_sim = cosine_similarity(embeddings)
THRESHOLD = 0.85 # Bạn có thể điều chỉnh ngưỡng này
duplicates_count = 0

for i in range(len(data)):
    if data[i]['Is Duplicate']:
        continue

    for j in range(i + 1, len(data)):
        if cos_sim[i][j] > THRESHOLD:
            title_i = data[i]['Title']
            title_j = data[j]['Title']
            
            nums_i = get_important_numbers(title_i)
            nums_j = get_important_numbers(title_j)

            final_score = cos_sim[i][j]

            # Nếu có số quan trọng (năm) mà lại khác nhau, trừ điểm nặng
            if len(nums_i) > 0 and len(nums_j) > 0 and len(nums_i.intersection(nums_j)) == 0:
                final_score -= 0.3  # Phạt vì lệch năm/đợt thi

            if final_score > THRESHOLD:
                data[j]['Is Duplicate'] = True
                duplicates_count += 1

            data[j]['Is Duplicate'] = True
            duplicates_count += 1

# 4. Lưu file JSON đã làm sạch (chỉ giữ lại bài không trùng)
clean_data = [item for item in data if not item['Is Duplicate']]

with open('D:\\Documents\\Project3\\data\\news_clean.json', 'w', encoding='utf-8') as f:
    json.dump(clean_data, f, ensure_ascii=False, indent=4)

print(f"✅ Hoàn tất! Phát hiện {duplicates_count} bài trùng lặp.")
print(f"📁 File sạch sẵn sàng đánh nhãn: hust_news_clean.json ({len(clean_data)} bài)")