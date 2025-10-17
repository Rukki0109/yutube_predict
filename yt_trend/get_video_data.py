from googleapiclient.discovery import build
import pandas as pd
from tqdm import tqdm
import time

# ✅ APIキー設定（自分のキーに置き換えてください）
API_KEY = "AIzaSyApavwxqaBLkNyK65iHdgmUf9eX5CsYrmI"
youtube = build("youtube", "v3", developerKey=API_KEY)

# ✅ 対象チャンネルID（ステゴロパンチャーズ）
CHANNEL_ID = "UCusnpkgavQhPV_8e_zEh_jw"

# ✅ 動画ID取得
def get_video_ids(channel_id, max_results=1000):
    video_ids = []
    next_page_token = None
    print("🎬 動画ID取得中...")
    while len(video_ids) < max_results:
        req = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            type='video',
            order="date",
            pageToken=next_page_token
        )
        res = req.execute()
        for item in res["items"]:
            if item["id"]["kind"] == "youtube#video":
                video_ids.append(item["id"]["videoId"])
        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break
        time.sleep(0.1)
    return video_ids[:max_results]

# ✅ 動画詳細取得
def get_video_details(video_ids):
    all_data = []
    print("📦 動画情報取得中...")
    for i in tqdm(range(0, len(video_ids), 50)):
        batch = video_ids[i:i+50]
        res = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch)
        ).execute()
        for item in res["items"]:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            all_data.append({
                "videoId": item["id"],
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "publishedAt": snippet.get("publishedAt"),
                "categoryId": snippet.get("categoryId"),
                "tags": snippet.get("tags", []),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "viewCount": int(stats.get("viewCount", 0)),
                "likeCount": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                "commentCount": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
                "duration": content.get("duration")
            })
        time.sleep(0.1)
    return pd.DataFrame(all_data)

# ✅ 実行
video_ids = get_video_ids(CHANNEL_ID, max_results=1000)
df = get_video_details(video_ids)

# ✅ 保存（必要なら）
df.to_excel("youtube_dataset.xlsx", index=False)
print("✅ 完了！動画数:", len(df))
