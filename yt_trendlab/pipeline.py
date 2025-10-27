# -*- coding: utf-8 -*-

from time import perf_counter
import pandas as pd
import numpy as np
from isodate import parse_duration
from .thumbnail_features import ensure_thumbnail_features, THUMBNAIL_COLS
from .text_features import build_vectorizer
from .modeling import train_rf, evaluate_rmse, feature_importance_df



def run_all(xlsx_path: str, cutoff="2025-07-01", tfidf_max_features=300, verbose: bool = True, progress_step_pct: int = 5):
    t0 = perf_counter()
    def log(msg):
        if verbose:
            print(f"[yt_trendlab] {msg}")

    # 1) load & basic clean
    log("Loading dataset...")
    df = pd.read_excel(xlsx_path)
    df["title"] = df["title"].fillna("")
    df["categoryId"] = pd.to_numeric(df["categoryId"], errors="coerce").fillna(-1).astype(int)
    df["viewCount"] = pd.to_numeric(df["viewCount"], errors="coerce").fillna(0)
    df["publishedAt"] = pd.to_datetime(df["publishedAt"], utc=True)
    df["duration_seconds"] = df["duration"].apply(lambda x: parse_duration(x).total_seconds() if pd.notnull(x) else 0)
    df = df[df["duration_seconds"] > 60].copy()
    log(f"Loaded rows: {len(df)} (after Shorts filter)")
    # 2) thumbnail
    log("Ensuring thumbnail features...")
    df = ensure_thumbnail_features(df, verbose=verbose, step_pct=progress_step_pct)

    # 3) time
    log("Building time features...")
    df["weekday"] = df["publishedAt"].dt.weekday
    df["hour"] = df["publishedAt"].dt.hour
    df["is_weekend"] = df["weekday"].isin([5,6]).astype(int)
    df["is_month_start"] = df["publishedAt"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["publishedAt"].dt.is_month_end.astype(int)

    # 4) trending features: removed for single-script parity (we don't add external trend features here)
    log("Skipping external trend feature enrichment (using local features only)")

    # 5) TF-IDF
    log("Vectorizing titles (TF-IDF)...")
    vectorizer = build_vectorizer(max_features=tfidf_max_features)
    cutoff_ts = pd.to_datetime(cutoff, utc=True)
    df_train = df[df["publishedAt"] < cutoff_ts].copy()
    df_test  = df[df["publishedAt"] >= cutoff_ts].copy()

    tfidf_train = vectorizer.fit_transform(df_train["title"])
    tfidf_test  = vectorizer.transform(df_test["title"])
    tfidf_cols  = [f"tfidf_{w}" for w in vectorizer.get_feature_names_out()]
    tfidf_df_tr = pd.DataFrame(tfidf_train.toarray(), columns=tfidf_cols, index=df_train.index)
    tfidf_df_te = pd.DataFrame(tfidf_test.toarray(),  columns=tfidf_cols, index=df_test.index)

    # 6) assemble features
    log("Assembling feature matrices...")
    # restore days_since_posted and use the same base columns as the standalone script
    df["days_since_posted"] = (pd.Timestamp.now(tz="UTC") - df["publishedAt"]).dt.days
    # recompute train/test slices (to ensure days_since_posted present in both)
    df_train = df[df["publishedAt"] < cutoff_ts].copy()
    df_test  = df[df["publishedAt"] >= cutoff_ts].copy()

    base_cols = ["categoryId","weekday","hour","is_weekend","is_month_start","is_month_end","days_since_posted"]
    X_train = pd.concat([df_train[base_cols].reset_index(drop=True), df_train[[c for c in THUMBNAIL_COLS]].reset_index(drop=True), tfidf_df_tr.reset_index(drop=True)], axis=1)
    X_test  = pd.concat([df_test[base_cols].reset_index(drop=True),  df_test[[c for c in THUMBNAIL_COLS]].reset_index(drop=True),  tfidf_df_te.reset_index(drop=True)], axis=1)

    y_train = np.log1p(df_train["viewCount"])
    y_test  = df_test["viewCount"]

    # 7) train & eval
    log("Training RandomForest & evaluating...")
    model = train_rf(X_train, y_train)
    rmse_log, rmse_raw, y_pred = evaluate_rmse(model, X_test, y_test)
    imp_top = feature_importance_df(model, X_train.columns, top=30)
    log(f"Done. RMSE(log)={rmse_log:.4f}, RMSE(raw)={rmse_raw:.1f}")

    # 8) result table
    df_result = df_test[["title","publishedAt","viewCount"]].copy()
    df_result["predicted_viewCount"] = y_pred
    df_result["abs_error"] = (df_result["predicted_viewCount"] - df_result["viewCount"]).abs()
    df_result = df_result.sort_values("publishedAt", ascending=False).reset_index(drop=True)

    metrics = {"rmse_log": rmse_log, "rmse_raw": rmse_raw}
    log(f"Total time: {perf_counter()-t0:.1f}s")
    return model, df_result, metrics, imp_top
