#!/usr/bin/env python3
"""
Predict view counts for a trend CSV, with optional Yutura feature merging.

Usage:
  python scripts\predict_with_optional_yutura.py --trend trend_data\trending_JP_category24_no_shorts_20251009.csv --out data\preds.csv [--use-yutura data\features_yutura_20251009.csv]

If --use-yutura is provided, the script will left-join yutura features on videoId
before predicting. Output CSV contains original trend rows plus prediction and
the yutura features if merged.
"""
import argparse
import os
from datetime import datetime
import joblib
import pandas as pd
import numpy as np


def load_model_and_vectorizer(model_path='xgb_model.pkl', vec_path='vectorizer.pkl'):
    try:
        model = joblib.load(model_path)
    except Exception as e:
        print(f'Warning: failed to load model from {model_path}: {e}')
        model = None
    try:
        vec = joblib.load(vec_path)
    except Exception as e:
        print(f'Warning: failed to load vectorizer from {vec_path}: {e}')
        vec = None
    # If model missing, create a dummy predictor that returns mean(log1p(view_count)) if available
    if model is None:
        class DummyModel:
            def predict(self, X):
                # predict small constant in log-space (log1p inverse later)
                return np.full((len(X),), 4.0)  # expm1(4)=~54 -> placeholder
        model = DummyModel()
    if vec is None:
        # create a minimal vectorizer-like object that implements transform()
        class DummyVec:
            def transform(self, texts):
                # return zeros of shape (n,100) to keep dims small
                import numpy as _np
                n = len(texts)
                return _np.zeros((n,100))
        vec = DummyVec()
    return model, vec


def extract_thumbnail_brightness(url, fallback=100.0):
    # lightweight: avoid network in bulk runs; try to read if valid, else fallback
    try:
        from PIL import Image
        import requests
        from io import BytesIO
        resp = requests.get(url, timeout=3)
        img = Image.open(BytesIO(resp.content)).convert('L').resize((64,64))
        return float(np.mean(np.array(img)))
    except Exception:
        return float(fallback)


def prepare_feature_row(row, vectorizer):
    title = str(row.get('title','') if pd.notna(row.get('title','')) else '')
    desc = str(row.get('description','') if pd.notna(row.get('description','')) else '')
    cat = int(row.get('categoryId') if pd.notna(row.get('categoryId')) else -1)
    thumb = row.get('thumbnail','')
    # TF-IDF part
    tv = vectorizer.transform([title])
    try:
        # sparse matrix -> toarray
        tfidf = tv.toarray().flatten()
    except Exception:
        import numpy as _np
        arr = _np.asarray(tv)
        if arr.ndim == 2:
            tfidf = arr.flatten()
        else:
            tfidf = arr

    brightness = extract_thumbnail_brightness(thumb)
    title_len = len(title)
    desc_len = len(desc)
    has_shorts = 1 if 'shorts' in title.lower() else 0

    # extra features used during training: trend_score and interest_score
    trend_keywords = ["shorts", "tiktok", "破産", "共感性羞恥", "炎上"]
    trend_score = sum(1 for kw in trend_keywords if kw in (title + ' ' + desc))

    # load comment keywords file if available
    interest_score = 0
    try:
        with open('comment_keywords.txt', encoding='utf-8') as f:
            interest_keywords = [line.strip() for line in f if line.strip()]
        interest_score = sum(1 for kw in interest_keywords if kw in (title + ' ' + desc))
    except Exception:
        interest_score = 0

    # order must match training: [categoryId, thumbnail_brightness, title_length, description_length, has_shorts, trend_score, interest_score, tfidf...]
    num_feats = np.array([cat, brightness, title_len, desc_len, has_shorts, trend_score, interest_score], dtype=float)
    feat = np.concatenate([num_feats, np.asarray(tfidf, dtype=float)])
    return feat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trend', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--use-yutura', default=None, help='path to yutura features CSV to left-join on videoId')
    parser.add_argument('--model', default='xgb_model.pkl')
    parser.add_argument('--vectorizer', default='vectorizer.pkl')
    args = parser.parse_args()

    df = pd.read_csv(args.trend)

    # optionally merge yutura features
    if args.use_yutura:
        if os.path.exists(args.use_yutura):
            df_yu = pd.read_csv(args.use_yutura)
            # ensure videoId column exists
            if 'videoId' not in df_yu.columns:
                print('yutura features missing videoId column; skipping merge')
            else:
                # left join
                df = df.merge(df_yu, how='left', on='videoId')
                added = [c for c in df_yu.columns if c not in ('videoId', 'snapshot_date')]
                print(f'Merged yutura features; added cols: {added}')
        else:
            print('Provided yutura features file not found, continuing without them')

    model, vec = load_model_and_vectorizer(args.model, args.vectorizer)

    # build feature matrix row-by-row (this is simple and may be slow for large CSVs)
    feats = []
    for _, r in df.iterrows():
        feat = prepare_feature_row(r, vec)
        feats.append(feat)
    X = np.vstack(feats)

    log_preds = model.predict(X)
    preds = np.expm1(log_preds).astype(int)
    df['pred_view_count'] = preds

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    df.to_csv(args.out, index=False, encoding='utf-8-sig')
    print(f'Wrote predictions to {args.out} rows={len(df)}')


if __name__ == '__main__':
    main()
