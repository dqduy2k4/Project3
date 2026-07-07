import json
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "vne_articles_labeled_combined.json"
OUTPUT_DIR = ROOT_DIR / "reports" / "eda"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("data", [])

    df = pd.DataFrame(data)
    return df


def summarize_text_series(series: pd.Series, column_name: str) -> pd.DataFrame:
    text = series.fillna("")
    lengths = text.apply(lambda x: len(x))
    words = text.apply(lambda x: len(re.findall(r"\b\w+\b", x, flags=re.UNICODE)))

    summary = pd.DataFrame(
        {
            "column": column_name,
            "count": text.shape[0],
            "non_empty": (text.str.len() > 0).sum(),
            "min_chars": lengths.min(),
            "max_chars": lengths.max(),
            "mean_chars": round(lengths.mean(), 2),
            "median_chars": round(lengths.median(), 2),
            "min_words": words.min(),
            "max_words": words.max(),
            "mean_words": round(words.mean(), 2),
            "median_words": round(words.median(), 2),
        },
        index=[0],
    )
    return summary


def extract_top_terms(series: pd.Series, top_n: int = 20) -> list[tuple[str, int]]:
    tokens = []
    for text in series.fillna(""):
        tokens.extend(re.findall(r"\b[\wÀ-ỹ]+\b", text.lower(), flags=re.UNICODE))

    stopwords = {
        "của",
        "và",
        "các",
        "có",
        "đã",
        "là",
        "trong",
        "với",
        "cũng",
        "cho",
        "từ",
        "được",
        "đến",
        "những",
        "một",
        "của",
        "ở",
        "sẽ",
        "này",
        "đó",
        "nhiều",
        "theo",
        "còn",
        "về",
        "mà",
        "đi",
        "để",
        "thì",
        "khi",
    }
    filtered = [token for token in tokens if token not in stopwords and len(token) > 2]
    return Counter(filtered).most_common(top_n)


def save_distribution_plot(df: pd.DataFrame, column: str, output_path: Path) -> None:
    plt.figure(figsize=(8, 4))
    sns.countplot(data=df, x=column, order=df[column].value_counts().index)
    plt.xticks(rotation=30, ha="right")
    plt.title(f"Phân bố theo {column}")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_length_boxplot(df: pd.DataFrame, column: str, output_path: Path) -> None:
    text = df[column].fillna("")
    word_counts = text.apply(lambda x: len(re.findall(r"\b\w+\b", x, flags=re.UNICODE)))

    plt.figure(figsize=(8, 4))
    sns.boxplot(y=word_counts)
    plt.title(f"Phân bố số từ trong {column}")
    plt.ylabel("Số từ")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_report(df: pd.DataFrame) -> None:
    print("=" * 70)
    print("EDA cho dữ liệu bài báo")
    print("=" * 70)
    print(f"Số mẫu: {len(df)}")
    print("\nCột dữ liệu:")
    print(df.dtypes.to_string())

    print("\nGiá trị thiếu:")
    print(df.isna().sum().to_string())

    if "label" in df.columns:
        print("\nPhân bố nhãn:")
        print(df["label"].value_counts(dropna=False).to_string())

    if "source_category" in df.columns:
        print("\nPhân bố danh mục nguồn:")
        print(df["source_category"].value_counts(dropna=False).to_string())

    text_columns = [col for col in ["title", "description", "content"] if col in df.columns]
    summary_frames = [summarize_text_series(df[col], col) for col in text_columns]
    summary_df = pd.concat(summary_frames, ignore_index=True)
    print("\nThống kê chiều dài văn bản:")
    print(summary_df.to_string(index=False))

    print("\nTop từ xuất hiện nhiều nhất trong tiêu đề:")
    for term, count in extract_top_terms(df["title"], top_n=15):
        print(f"- {term}: {count}")

    if "label" in df.columns:
        save_distribution_plot(df, "label", OUTPUT_DIR / "label_distribution.png")
    if "source_category" in df.columns:
        save_distribution_plot(df, "source_category", OUTPUT_DIR / "source_category_distribution.png")
    for column in text_columns:
        save_length_boxplot(df, column, OUTPUT_DIR / f"{column}_word_count_boxplot.png")

    summary_df.to_csv(OUTPUT_DIR / "text_summary.csv", index=False)
    df.to_csv(OUTPUT_DIR / "cleaned_for_eda.csv", index=False)

    print(f"\nĐã lưu kết quả vào thư mục: {OUTPUT_DIR}")


def main() -> None:
    sns.set_theme(style="whitegrid")
    df = load_dataset(DATA_PATH)
    generate_report(df)


if __name__ == "__main__":
    main()
