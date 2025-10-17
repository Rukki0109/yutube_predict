# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

def train_rf(X_train, y_train, n_estimators=100, max_depth=10, random_state=42, n_jobs=-1):
    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=random_state, n_jobs=n_jobs)
    model.fit(X_train, y_train)
    return model

def evaluate_rmse(model, X_test, y_test):
    log_pred = model.predict(X_test)
    y_pred  = np.expm1(log_pred).astype(int)
    rmse_log = mean_squared_error(np.log1p(y_test), log_pred) ** 0.5
    rmse_raw = mean_squared_error(y_test, y_pred) ** 0.5
    return rmse_log, rmse_raw, y_pred

def feature_importance_df(model, columns, top=30):
    imp = pd.Series(model.feature_importances_, index=columns)
    return imp.sort_values(ascending=False).head(top)
