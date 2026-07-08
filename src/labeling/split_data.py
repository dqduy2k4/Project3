import json
from src.config import DATA_DIR

# 1. Cấu hình tên file và số lượng bằng Pathlib
VNE_DATA = DATA_DIR / "vne_articles_clean.json"
VNE_OUTPUT = DATA_DIR / "vne_articles_split"

RSS_DATA = DATA_DIR / "rss_articles_clean.json"
RSS_OUTPUT = DATA_DIR / "rss_articles_split"

CURRENT_DATA_FILE = RSS_DATA  # Hoặc VNE_DATA nếu muốn chia file VNE
CURRENT_OUTPUT = RSS_OUTPUT  # Hoặc VNE_OUTPUT nếu muốn chia file VNE

SO_BAN_GHI_MOI_FILE = 60

# Tự động tạo thư mục chứa các file con nếu chưa có
VNE_OUTPUT.mkdir(parents=True, exist_ok=True)
RSS_OUTPUT.mkdir(parents=True, exist_ok=True)

# Đọc file gốc đầy đủ thông tin
with open(CURRENT_DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Tổng số bản ghi trong file gốc: {len(data)}")

# Tiến hành chia nhỏ và rút gọn trường thông tin
for i in range(0, len(data), SO_BAN_GHI_MOI_FILE):
    chunk = data[i:i + SO_BAN_GHI_MOI_FILE]
    chunk_rut_gon = []
    
    for item in chunk:
        # Lấy trực tiếp trường 'url', mặc định là chuỗi rỗng nếu không tìm thấy
        url_dinh_danh = item.get('url', '') 
        
        chunk_rut_gon.append({
            "url": url_dinh_danh, 
            "title": item.get('title', ''),
            "description": item.get('description', '')
        })
    
    # Đặt tên file con bằng toán tử '/' của Pathlib
    so_thu_tu_file = (i // SO_BAN_GHI_MOI_FILE) + 1
    ten_file_moi = CURRENT_OUTPUT / f'split_{so_thu_tu_file}.json'
    
    with open(ten_file_moi, 'w', encoding='utf-8') as f_out:
        json.dump(chunk_rut_gon, f_out, ensure_ascii=False, indent=4)

print(f"🎉 Thành công! Đã chia thành các file con trong thư mục: '{CURRENT_OUTPUT}'")