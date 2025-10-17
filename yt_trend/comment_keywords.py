from googleapiclient.discovery import build
from janome.tokenizer import Tokenizer
from collections import Counter
import time

# 🔧 APIキーとチャンネルID（ステゴロパンチャーズ）
API_KEY = "AIzaSyApavwxqaBLkNyK65iHdgmUf9eX5CsYrmI"  # ← 必ずご自身のAPIキーに置き換えてください
CHANNEL_ID = "UCusnpkgavQhPV_8e_zEh_jw"

# YouTube API 初期化
youtube = build("youtube", "v3", developerKey=API_KEY)

# ✅ 最新の動画IDを取得
def get_latest_video_id(channel_id):
    res = youtube.search().list(
        part="id",
        channelId=channel_id,
        order="date",
        maxResults=1,
        type="video"
    ).execute()
    return res["items"][0]["id"]["videoId"]

# ✅ コメントを収集
def get_comments(video_id, max_results=100):
    comments = []
    next_page_token = None
    while len(comments) < max_results:
        res = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100,
            pageToken=next_page_token
        ).execute()
        for item in res["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)
        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break
        time.sleep(0.1)
    return comments[:max_results]

# ✅ キーワードを抽出
def extract_keywords(comments, top_n=30):
    tokenizer = Tokenizer()
    all_text = " ".join(comments)
    tokens = [token.surface for token in tokenizer.tokenize(all_text)
              if len(token.surface) > 1]  # 1文字語を除外
    counter = Counter(tokens)
    return [word for word, _ in counter.most_common(top_n)]

# ✅ 実行フロー
def main():
    print("🎬 最新動画を取得中...")
    latest_video_id = get_latest_video_id(CHANNEL_ID)
    print(f"📺 最新動画ID: {latest_video_id}")

    print("💬 コメントを収集中...")
    comments = get_comments(latest_video_id, max_results=100)
    print(f"💾 コメント数: {len(comments)}")

    print("🔍 キーワードを抽出中...")
    keywords = extract_keywords(comments, top_n=30)

    print("📝 comment_keywords.txt に保存中...")
    with open("comment_keywords.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(keywords))

    print("✅ 完了！コメントキーワードを保存しました。")

if __name__ == "__main__":
    main()
