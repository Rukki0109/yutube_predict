import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from janome.tokenizer import Tokenizer
from isodate import parse_duration

# 📥 データ読み込み
df = pd.read_excel("youtube_dataset.xlsx")

# 🧠 Shorts判定（durationから60秒以下をShortsとする）
df["duration_seconds"] = df["duration"].apply(lambda x: parse_duration(x).total_seconds())
df["is_shorts"] = df["duration_seconds"] <= 60

# 🎯 通常動画（Shortsでない）だけ抽出
df = df[df["is_shorts"] == False].copy()

# 🔧 欠損補完と型変換
df["title"] = df["title"].fillna("")
df["description"] = df["description"].fillna("")
df["categoryId"] = pd.to_numeric(df["categoryId"], errors="coerce").fillna(-1).astype(int)
df["viewCount"] = pd.to_numeric(df["viewCount"], errors="coerce").fillna(0)
df["publishedAt"] = pd.to_datetime(df["publishedAt"], errors="coerce")

# 🕒 投稿タイミング特徴量
df["weekday"] = df["publishedAt"].dt.weekday
df["hour"] = df["publishedAt"].dt.hour
df["is_weekend"] = df["weekday"].apply(lambda x: 1 if x >= 5 else 0)
df["day"] = df["publishedAt"].dt.day
df["is_month_start"] = df["day"] <= 3
df["is_month_end"] = df["day"] >= 28
df.drop(columns=["day"], inplace=True)

# 🔤 JanomeでTF-IDF（100次元）
tokenizer = Tokenizer()
def tokenize_japanese(text):
    return [token.base_form for token in tokenizer.tokenize(text)
            if token.part_of_speech.split(',')[0] in ['名詞', '動詞', '形容詞']]

vectorizer = TfidfVectorizer(tokenizer=tokenize_japanese, token_pattern=None, max_features=100)
tfidf_matrix = vectorizer.fit_transform(df["title"])
tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=[f"tfidf_{w}" for w in vectorizer.get_feature_names_out()])

# 🎯 目的変数（logスケール）
y = np.log1p(df["viewCount"])

# 📊 特徴量定義
X_base = pd.concat([df[["categoryId"]].reset_index(drop=True), tfidf_df.reset_index(drop=True)], axis=1)
timing_cols = ["weekday", "hour", "is_weekend", "is_month_start", "is_month_end"]
X_ext = pd.concat([df[["categoryId"] + timing_cols].reset_index(drop=True), tfidf_df.reset_index(drop=True)], axis=1)

# 🚀 学習・評価関数
def evaluate_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    return rmse

# 📈 モデル精度比較
rmse_base = evaluate_model(X_base, y)
rmse_ext = evaluate_model(X_ext, y)

# 📝 結果出力
print(f"📉 通常動画のみでのモデル精度比較（RMSE, logスケール）")
print(f"- TF-IDF + categoryId モデル：{rmse_base:.4f}")
print(f"- + 投稿タイミング拡張モデル：{rmse_ext:.4f}")
