import json
from src.config import DATA_DIR

def filter_error_records(input_path, output_path):
    # 1. Đọc file JSON gốc
    with open(input_path, 'r', encoding='utf-8') as f:
        data_goc = json.load(f)
    
    total_initial = len(data_goc)
    data_clean = []
    removed_count = 0
    
    # 2. Tiến hành lọc dữ liệu rác/trống
    for item in data_goc:
        # Lấy title và description, đưa về chuỗi rỗng nếu bị trùng hoặc null, đồng thời xóa khoảng trắng thừa
        title = str(item.get('title', '')).strip()
        description = str(item.get('description', '')).strip()
        content = str(item.get('content', '')).strip()
        
        # Điều kiện lọc: Nếu title hoặc description trống rỗng -> Xác định là bản ghi lỗi
        if not title or not description:
            removed_count += 1
            continue
            
        # Nếu dữ liệu hợp lệ thì giữ lại
        data_clean.append(item)
        
    # 3. Ghi dữ liệu đã làm sạch ra file JSON mới
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_clean, f, ensure_ascii=False, indent=4)
        
    # In báo cáo kết quả
    print("=" * 40)
    print(f"📊 BÁO CÁO LỌC DỮ LIỆU:")
    print(f"  - Tổng số bản ghi ban đầu: {total_initial}")
    print(f"  - Số bản ghi trống/lỗi đã xóa: {removed_count}")
    print(f"  - Số bản ghi sạch còn lại: {len(data_clean)}")
    print(f"💾 Đã lưu file sạch tại: '{output_path}'")
    print("=" * 40)

# Tự động nối đường dẫn đến file JSON (Bất kể chạy trên Windows, Mac hay Linux)
input_path = DATA_DIR / "vne_articles_raw.json"
output_path = DATA_DIR / "vne_articles_clean.json"

# Chạy script
filter_error_records(input_path, output_path)