# -*- coding: utf-8 -*-
"""
Yutura-augmented training pipeline.

This is a variant of `pipeline.run_all` that removes the trending CSV-based
features and instead left-joins Yutura-extracted features (CSV) onto the
dataset before vectorization / training. Use this to retrain a model that
explicitly includes Yutura signals.

Function:
  run_all_with_yutura(xlsx_path, yutura_csv, ...)

Returns same contract as original pipeline.run_all: model, df_result, metrics, imp_top
"""

from time import perf_counter
import pandas as pd
import numpy as np
from isodate import parse_duration
from .thumbnail_features import ensure_thumbnail_features, THUMBNAIL_COLS
from .text_features import build_vectorizer
from .modeling import train_rf, evaluate_rmse, feature_importance_df


def run_all_with_yutura(xlsx_path: str,
                        yutura_csv: str,
                        cutoff="2025-07-01",
                        tfidf_max_features=300,
                        verbose: bool = True,
                        progress_step_pct: int = 5,
                        yutura_cols=None):
    """Train/evaluate model including Yutura features.

    Args:
      xlsx_path: path to dataset excel (same as original pipeline)
      yutura_csv: path to yutura features CSV (must contain `videoId` column)
      cutoff: cutoff timestamp string for train/test split
      tfidf_max_features: TF-IDF max features
      yutura_cols: list of column names from yutura CSV to include; if None,
                   a sensible default list will be used when present.

    Returns: model, df_result, metrics, imp_top
    """
    t0 = perf_counter()
    def log(msg):
        if verbose:
            print(f"[yt_trendlab.yutura] {msg}")

    log("Loading dataset...")
    df = pd.read_excel(xlsx_path)
    df["title"] = df["title"].fillna("")
    df["categoryId"] = pd.to_numeric(df["categoryId"], errors="coerce").fillna(-1).astype(int)
    df["viewCount"] = pd.to_numeric(df["viewCount"], errors="coerce").fillna(0)
    df["publishedAt"] = pd.to_datetime(df["publishedAt"], utc=True)
    df["duration_seconds"] = df["duration"].apply(lambda x: parse_duration(x).total_seconds() if pd.notnull(x) else 0)
    df = df[df["duration_seconds"] > 60].copy()
    log(f"Loaded rows: {len(df)} (after Shorts filter)")

    # thumbnail features
    log("Ensuring thumbnail features...")
    df = ensure_thumbnail_features(df, verbose=verbose, step_pct=progress_step_pct)

    # time features
    log("Building time features...")
    df["weekday"] = df["publishedAt"].dt.weekday
    df["hour"] = df["publishedAt"].dt.hour
    df["is_weekend"] = df["weekday"].isin([5,6]).astype(int)
    df["is_month_start"] = df["publishedAt"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["publishedAt"].dt.is_month_end.astype(int)

    # Merge Yutura features (replaces trend features)
    log("Merging Yutura features...")
    if not yutura_csv:
        raise ValueError("yutura_csv must be provided for this pipeline variant")
    ydf = pd.read_csv(yutura_csv)
    if 'videoId' not in ydf.columns:
        log("Warning: yutura CSV does not contain 'videoId' column; attempting to merge on title instead")
        df = df.merge(ydf, how='left', left_on='title', right_on='title')
    else:
        df = df.merge(ydf, how='left', on='videoId')

    # choose default yutura columns if not provided
    if yutura_cols is None:
        # common columns produced by yutura pipeline; may vary by export
        ycols = [
            'mention_count_3d','mention_any_3d','max_jaccard_3d','channel_mentioned_3d','days_since_last_mention_3d',
            'mention_count_7d','mention_any_7d','max_jaccard_7d','channel_mentioned_7d','days_since_last_mention_7d'
        ]
    else:
        ycols = list(yutura_cols)

    # keep only the intersection of requested columns and dataframe columns
    ycols = [c for c in ycols if c in df.columns]
    log(f"Yutura columns to include: {ycols}")

    # fill missing yutura values
    for c in ycols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # TF-IDF
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

    # assemble features: base + thumbnail + tfidf + yutura
    log("Assembling feature matrices (including Yutura)...")
    base_cols = ["categoryId","weekday","hour","is_weekend","is_month_start","is_month_end"]
    X_train = pd.concat([df_train[base_cols], df_train[[c for c in THUMBNAIL_COLS]], tfidf_df_tr], axis=1)
    X_test  = pd.concat([df_test[base_cols],  df_test[[c for c in THUMBNAIL_COLS]],  tfidf_df_te], axis=1)

    if ycols:
        X_train = pd.concat([X_train, df_train[ycols]], axis=1).reset_index(drop=True)
        X_test  = pd.concat([X_test,  df_test[ycols]],  axis=1).reset_index(drop=True)
    else:
        X_train = X_train.reset_index(drop=True)
        X_test  = X_test.reset_index(drop=True)

    y_train = np.log1p(df_train["viewCount"])
    y_test  = df_test["viewCount"]

    # train & eval
    log("Training RandomForest & evaluating...")
    model = train_rf(X_train, y_train)
    rmse_log, rmse_raw, y_pred = evaluate_rmse(model, X_test, y_test)
    imp_top = feature_importance_df(model, X_train.columns, top=30)
    log(f"Done. RMSE(log)={rmse_log:.4f}, RMSE(raw)={rmse_raw:.1f}")

    # result table
    df_result = df_test[["title","publishedAt","viewCount"]].copy()
    df_result["predicted_viewCount"] = y_pred
    df_result["abs_error"] = (df_result["predicted_viewCount"] - df_result["viewCount"]).abs()
    df_result = df_result.sort_values("publishedAt", ascending=False).reset_index(drop=True)

    metrics = {"rmse_log": rmse_log, "rmse_raw": rmse_raw}
    log(f"Total time: {perf_counter()-t0:.1f}s")
    return model, df_result, metrics, imp_top
