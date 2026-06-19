import feedparser
import requests
import os

RSS_URL = ""https://rss.app/feeds/pciA3C3UBcPVtJaj.xml""

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

def main():
    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries[:5]:
        title = entry.get("title", "")
        link = entry.get("link", "")

        send(f"{title}\n{link}")

if __name__ == "__main__":
    main()