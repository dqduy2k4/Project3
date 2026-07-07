import json
import os

# Đường dẫn tới file dữ liệu cuối cùng của bạn
COMBINED_FILE = "data/vne_articles_labeled_combined.json"

def find_unlabeled_articles():
    if not os.path.exists(COMBINED_FILE):
        print(f"❌ Không tìm thấy file dữ liệu tại: {COMBINED_FILE}")
        return

    print(f"==> Đang đọc dữ liệu từ: {COMBINED_FILE}...")
    with open(COMBINED_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    unlabeled_list = []

    # Duyệt qua từng bài viết để kiểm tra nhãn
    for index, article in enumerate(articles):
        # Kiểm tra nếu trường 'label' không tồn tại, hoặc bằng None, hoặc là chuỗi rỗng
        label = article.get('label')
        if label is None or str(label).strip() == "":
            unlabeled_list.append(article)
            
            # In thử một vài bản ghi đầu tiên lên màn hình để kiểm tra nhanh
            if len(unlabeled_list) <= 5:
                print(f"\n[Bài viết chưa gán nhãn #{len(unlabeled_list)} - Index gốc: {index}]")
                print(f"- URL: {article.get('url')}")
                print(f"- Title: {article.get('title')}")
                print(f"- Category: {article.get('source_category')}")
                print("-" * 50)

    print(f"\n📊 BÁO CÁO THỐNG KÊ:")
    print(f"- Tổng số lượng bài viết trong file: {len(articles)}")
    print(f"- Số lượng bài viết CHƯA được gán nhãn: {len(unlabeled_list)}")
    print(f"- Tỷ lệ thiếu nhãn: {(len(unlabeled_list) / len(articles) * 100):.2f}%" if len(articles) > 0 else 0)

    # (Tùy chọn) Lưu các bản ghi chưa gán nhãn ra một file riêng để xử lý sau
    if unlabeled_list:
        OUTPUT_UNLABELED = "data/unlabeled_articles_backup.json"
        with open(OUTPUT_UNLABELED, 'w', encoding='utf-8') as f:
            json.dump(unlabeled_list, f, ensure_ascii=False, indent=4)
        print(f"💾 Đã lưu danh sách các bài viết chưa gán nhãn vào: {OUTPUT_UNLABELED}")

if __name__ == "__main__":
    find_unlabeled_articles()