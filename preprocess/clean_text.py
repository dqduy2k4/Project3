import re
import unicodedata
from underthesea import word_tokenize

def standardize_hust_keywords(text):
    # Gom cụm các biến thể của Bách Khoa HN
    patterns = [r'đại học bách khoa hà nội', r'đhbk hn', r'bách khoa hn', r'hust']
    for p in patterns:
        text = re.sub(p, 'đại_học_bách_khoa_hà_nội', text, flags=re.IGNORECASE)
    return text

def standardize_numbers(text):
    # Regex này tìm các con số có dạng 1.000, 10.000.000
    # Và xóa dấu chấm ở giữa chúng: 1.000 -> 1000
    return re.sub(r'(?<=\d)\.(?=\d)', '', text)

def standardize_currency(text):
    # 1. Thống nhất tỷ/tỉ (chọn 'tỉ' theo chuẩn từ điển hoặc 'tỷ' tùy bạn, ở đây chọn 'tỉ')
    text = text.replace('tỷ', 'tỉ')
    
    # 2. Đưa các ký hiệu tiền tệ về chữ 'đồng'
    # Regex này tìm các chữ vnđ, vnd, đ khi nó đứng độc lập sau con số
    text = re.sub(r'\b(vnđ|vnd|đ)\b', 'đồng', text)
    
    # 3. Gom cụm các đơn vị tiền tệ quan trọng để không bị tokenizer tách rời
    # Ví dụ: "tỉ đồng" -> "tỉ_đồng", "triệu đồng" -> "triệu_đồng"
    currency_units = {
        'tỉ đồng': 'tỉ_đồng',
        'triệu đồng': 'triệu_đồng',
        'nghìn đồng': 'nghìn_đồng',
        'ngàn đồng': 'nghìn_đồng'
    }
    for unit, replacement in currency_units.items():
        text = text.replace(unit, replacement)
    
    return text

def preprocess_text(text):
    if not text: return ""
    
    # 1. Chuẩn hóa Unicode & Viết thường
    text = unicodedata.normalize('NFC', text).lower()
    
    # 2. Xử lý tỷ/tỉ và đơn vị tiền tệ
    text = standardize_currency(text)
    
    # 3. Xử lý số (xóa dấu chấm phân cách hàng nghìn)
    text = standardize_numbers(text)
    
    # 4. Chuẩn hóa từ khóa HUST (Đại học Bách khoa Hà Nội)
    # Hàm này bạn đã có ở bước trước, hãy đảm bảo nó chạy sau khi đã lowercase
    text = standardize_hust_keywords(text)
    
    # 5. Tách dấu câu (trừ dấu _ và các ký tự chữ số)
    # Tách các dấu như , . ! ? " ( ) ra khỏi từ
    text = re.sub(r'([^\w\s_])', r' \1 ', text)
    
    # 6. Xóa khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 7. Tách từ bằng underthesea
    # Lưu ý: underthesea sẽ tôn trọng các từ có dấu _ mình đã tạo ở bước trên
    text = word_tokenize(text, format="text") 
    
    return text

  
def process_article_data(data_item):
    """
    Nhận vào 1 dictionary chứa dữ liệu raw của 1 bài báo
    Trả về dictionary đã được bổ sung các trường văn bản sạch.
    """
    # Tạo một bản sao để tránh làm thay đổi trực tiếp (mutate) dữ liệu gốc nếu không cần thiết
    processed_item = data_item.copy()
    
    # Áp dụng tiền xử lý cho Title, Summary và Content
    processed_item['Cleaned_Title'] = preprocess_text(data_item.get('Title', ''))
    processed_item['Cleaned_Summary'] = preprocess_text(data_item.get('Summary', ''))
    processed_item['Cleaned_Content'] = preprocess_text(data_item.get('Content', ''))
    
    # Bạn cũng có thể nối cả 3 trường này lại thành 1 chuỗi duy nhất để đưa vào mô hình cho tiện
    # Tùy thuộc vào chiến lược huấn luyện của bạn
    processed_item['Combined_Text'] = f"{processed_item['Cleaned_Title']} {processed_item['Cleaned_Summary']} {processed_item['Cleaned_Content']}".strip()
    
    return processed_item
  
# print("Đang tiến hành tiền xử lý ngôn ngữ (NLP)...")
# final_data = [process_article_data(item) for item in crawled_data]

# # Lưu final_data vào file JSON (đã có cả raw text và cleaned text)
# with open(file_path, 'w', encoding='utf-8') as f:
#     json.dump(existing_data + final_data, f, ensure_ascii=False, indent=4)
# print("Đã lưu dữ liệu thành công!")