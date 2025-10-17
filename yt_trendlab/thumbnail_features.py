# -*- coding: utf-8 -*-

import numpy as np
import cv2
from PIL import Image
import pandas as pd
import requests
from io import BytesIO
import mediapipe as mp
from tqdm import tqdm


# tqdm/notebook優先のバー選択
try:
    from tqdm.notebook import tqdm as tqdm_nb
    _TQDM = tqdm_nb
except Exception:
    _TQDM = tqdm

def _progress_logger(i, total, last_pct, step_pct=5):
    pct = int((i / total) * 100)
    if pct >= last_pct + step_pct:
        print(f"[yt_trendlab] サムネ進捗: {pct}% ({i}/{total})")
        return pct
    return last_pct

def ensure_thumbnail_features(df, verbose=True, step_pct=5):
    """
    既にTHUMBNAIL_COLSが揃っていればスキップ。
    足りない場合は全行を計算し、進捗バーと%ログを出力する。
    """
    if set(THUMBNAIL_COLS).issubset(df.columns):
        if verbose: print("[yt_trendlab] サムネ特徴: 既存列あり → 抽出スキップ")
        return df
    if "thumbnail" not in df.columns:
        raise ValueError("⚠️ 'thumbnail' 列がありません")

    urls = df["thumbnail"].tolist()
    total = len(urls)
    if verbose: print(f"[yt_trendlab] サムネ抽出開始: {total} 件")

    feats = []
    bar = _TQDM(total=total, desc="🖼️ サムネ抽出", unit="img")
    last_pct = -step_pct
    for i, url in enumerate(urls, start=1):
        feats.append(extract_all_thumbnail_features_mediapipe(url))
        bar.update(1)
        if verbose:
            last_pct = _progress_logger(i, total, last_pct, step_pct=step_pct)
    bar.close()

    feats_df = pd.DataFrame(feats, columns=THUMBNAIL_COLS)
    return pd.concat([df.reset_index(drop=True), feats_df], axis=1)

THUMBNAIL_COLS = [
    "brightness","face_count","telop_ratio",
    "r_mean","g_mean","b_mean","h_mean","s_mean","v_mean"
] + [f"color_ratio_{i}" for i in range(5)]

def extract_all_thumbnail_features_mediapipe(url: str):
    try:
        resp = requests.get(url, timeout=10)
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        arr = np.array(img)
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        brightness = hsv[:,:,2].mean()
        r_mean, g_mean, b_mean = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
        h_mean, s_mean, v_mean = hsv[:,:,0].mean(), hsv[:,:,1].mean(), hsv[:,:,2].mean()
        pixels = arr.reshape(-1,3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, _ = cv2.kmeans(pixels, 5, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        counts = np.bincount(labels.flatten(), minlength=5)
        color_ratios = (counts / counts.sum()).tolist()
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        telop_ratio = float((thresh==255).sum()) / float(thresh.size)
        with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
            res = fd.process(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
            face_count = len(res.detections) if res.detections else 0
        return [brightness, face_count, telop_ratio,
                r_mean, g_mean, b_mean, h_mean, s_mean, v_mean] + color_ratios
    except Exception:
        return [0]*len(THUMBNAIL_COLS)
