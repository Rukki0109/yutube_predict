import numpy as np
from PIL import Image
import requests
from io import BytesIO
import joblib
import pandas as pd

# 🔧 モデル・ベクトライザ読込
model = joblib.load("xgb_model.pkl")  # または rf_model.pkl に差し替え可
vectorizer = joblib.load("vectorizer.pkl")
fallback_brightness = 100.0  # 明度欠損時の平均代替値

# 🎨 サムネイル明度取得
def extract_thumbnail_brightness(url):
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content)).convert("L").resize((64, 64))
        return np.mean(np.array(img))
    except:
        return fallback_brightness

# 🔮 推論関数（拡張特徴量対応）
def predict_view_count(title: str, description: str, categoryId: int, thumbnail_url: str) -> int:
    # TF-IDF（300次元）
    tfidf_vec = vectorizer.transform([title]).toarray().flatten()

    # その他の特徴量
    genre = [categoryId]
    brightness = extract_thumbnail_brightness(thumbnail_url)
    title_len = len(title)
    description_len = len(description)
    has_shorts = int("shorts" in title.lower())

    # 特徴量統合（カテゴリ, 明度, 長さ3種, TF-IDF）
    feature_vec = np.concatenate([
        genre,
        [brightness, title_len, description_len, has_shorts],
        tfidf_vec
    ])

    # logスケールで予測 → exp変換
    log_pred = model.predict([feature_vec])[0]
    view_pred = int(np.expm1(log_pred))  # log1pの逆変換

    return view_pred
