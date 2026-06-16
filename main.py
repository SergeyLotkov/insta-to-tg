import os
import json
import requests
import feedparser

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

RSS_URL = "https://rsshub.app/picuki/profile/handyclass.ru"
LAST_FILE = "last_post.txt"


def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }
    )


feed = feedparser.parse(RSS_URL)

if not feed.entries:
    print("Нет постов")
    exit()

latest = feed.entries[0]
post_id = latest.link

try:
    with open(LAST_FILE, "r") as f:
        last_id = f.read().strip()
except:
    last_id = ""

if post_id != last_id:
    text = f"📸 Новый пост Instagram\n\n{latest.title}\n{latest.link}"
    send_message(text)

    with open(LAST_FILE, "w") as f:
        f.write(post_id)

    print("Отправлено")
else:
    print("Новых постов нет")