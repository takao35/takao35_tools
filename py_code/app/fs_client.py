import os
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

JST = timezone(timedelta(hours=9))
JSON_KEY = os.path.join("/home/masuday/projects/takao35","keys","takao35-app-firebase-adminsdk-fbsvc-7a6844dfe5.json")

def db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(JSON_KEY)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def post_news(doc_id: str, *, title: str, type_: str, url: str, pin: int = 2):
    ref = db().collection("news").document(doc_id)
    now = datetime.now(JST)
    data = {
        "title_ja": title,
        "type": type_,               # "weather" / "rail"
        "url": url,                  # クリック先（あなたの情報ページ）
        "pin_rank": pin,             # 0=通常, 2=重要, 3=最上
        "is_published": True,
        "start_at": now,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(data)

if __name__ == "__main__":
    post_news("test001", title="テスト投稿", type_="weather", url="https://example.com", pin=3)
    print("Posted test news item.")
    