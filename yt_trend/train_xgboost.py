from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pandas as pd
import numpy as np
import joblib

# 特徴量と目的変数の読み込み
X = pd.read_pickle("X.pkl")
y = pd.read_pickle("y.pkl")

# 学習データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# XGBoost モデル構築
model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# 評価
y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"✅ XGBoost学習完了！RMSE（logスケール）: {rmse:.4f}")

# 特徴重要度上位10
importances = model.feature_importances_
top_features = pd.Series(importances, index=X.columns).sort_values(ascending=False).head(10)
print("\n📊 重要な特徴量TOP10：")
print(top_features)

# 保存
joblib.dump(model, "xgb_model.pkl")
