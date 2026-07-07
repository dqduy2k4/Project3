from pathlib import Path

# Định nghĩa các đường dẫn gốc dùng chung cho toàn dự án
BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"

# Tự động tạo các thư mục này nếu chúng chưa tồn tại khi ứng dụng khởi chạy
DATA_DIR.mkdir(parents=True, exist_ok=True)
