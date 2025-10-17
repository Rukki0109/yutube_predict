from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import numpy as np

# ✅ 学習データの分割（8:2）
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ✅ モデル構築＆学習
model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,       # 木の深さ（調整可能）
    random_state=42,
    n_jobs=-1           # 並列実行で高速化
)
model.fit(X_train, y_train)

# ✅ 予測
y_pred = model.predict(X_test)

# ✅ 評価（RMSE）
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"✅ 再学習完了！RMSE（logスケール）: {rmse:.4f}")

# ✅ 重要な特徴量を確認（上位10）
importances = model.feature_importances_
top_features = pd.Series(importances, index=X.columns).sort_values(ascending=False).head(10)
print("\n📊 重要な特徴量TOP10：")
print(top_features)
