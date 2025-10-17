# ✅ feature_extraction.py（完全版：307次元対応）
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from PIL import Image
import requests
from io import BytesIO
from tqdm import tqdm
import joblib

# 📥 データ読み込み
df = pd.read_excel("youtube_dataset.xlsx")

# 🔤 タイトルTF-IDF（300次元）
vectorizer = TfidfVectorizer(max_features=300)
tfidf_matrix = vectorizer.fit_transform(df["title"].fillna(""))
tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=[f"tfidf_{t}" for t in vectorizer.get_feature_names_out()])
tfidf_df.index = df.index

# 📊 カテゴリ変換
df["categoryId"] = pd.to_numeric(df["categoryId"], errors='coerce').fillna(-1).astype(int)

# 🎨 サムネイル明度
print("🎨 サムネイル明度抽出中...")
def extract_thumbnail_brightness(url):
    try:
        img = Image.open(BytesIO(requests.get(url, timeout=5).content)).convert("L").resize((64, 64))
        return np.mean(np.array(img))
    except:
        return np.nan

df["thumbnail_brightness"] = [extract_thumbnail_brightness(url) for url in tqdm(df["thumbnail"].fillna(""))]
df["thumbnail_brightness"] = df["thumbnail_brightness"].fillna(df["thumbnail_brightness"].mean())

# ✨ 拡張特徴量
df["title_length"] = df["title"].fillna("").str.len()
df["description_length"] = df["description"].fillna("").str.len()
df["has_shorts"] = df["title"].str.contains("shorts", case=False, na=False).astype(int)

# 🧠 トレンド・コメントワードスコア
df["trend_score"] = df.apply(lambda row: sum(kw in str(row["title"]) + str(row["description"]) for kw in ["shorts", "tiktok", "破産", "共感性羞恥", "炎上"]), axis=1)
with open("comment_keywords.txt", encoding="utf-8") as f:
    interest_keywords = [line.strip() for line in f.readlines()]
df["interest_score"] = df.apply(lambda row: sum(kw in str(row["title"]) + str(row["description"]) for kw in interest_keywords), axis=1)

# ✅ 特徴量セット
feature_df = pd.concat([
    df[["categoryId", "thumbnail_brightness", "title_length", "description_length", "has_shorts", "trend_score", "interest_score"]],
    tfidf_df
], axis=1)

# 🔢 目的変数
df["log_view"] = np.log1p(df["viewCount"])
X = feature_df
y = df["log_view"]

# 💾 保存
X.to_pickle("X.pkl")
y.to_pickle("y.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

print("✅ 特徴量設計 完了！（307次元）")
