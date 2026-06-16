import os
import requests
import feedparser

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

RSS_URL = "https://rsshub.app/picuki/profile/handyclass.ru"

feed = feedparser.parse(RSS_URL)

if not feed.entries:
    print("Нет постов")
    exit()

post = feed.entries[0]

text = f"📸 Новый пост Instagram\n\n{post.title}\n{post.link}"

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": text
    }
)

print("Отправлено")