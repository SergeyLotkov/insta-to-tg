import feedparser
import requests
import os
import time
import re

RSS_URL = "https://rss.app/feeds/pciA3C3UBcPVtJaj.xml"
HISTORY_FILE = "history.txt"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def clean_text(text):
    """Удаляет хэштеги (#tags) и лишние ссылки из текста поста."""
    if not text:
        return ""
    # Удаляем хэштеги (слово, начинающееся с #)
    text = re.sub(r'#\w+', '', text)
    # Удаляем лишние пробелы, которые могли остаться
    text = re.sub(r' +', ' ', text)
    return text.strip()

def send_media(caption, media_url, is_video=False):
    """Отправляет фото или видео в Telegram с подписью."""
    # Выбираем правильный метод API в зависимости от типа медиа
    method = "sendVideo" if is_video else "sendPhoto"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    
    # Telegram принимает прямую ссылку на медиафайл, скачивать его на диск не нужно
    payload = {
        "chat_id": CHAT_ID,
        "caption": caption[:1024]  # Ограничение Telegram на длину подписи к медиа
    }
    payload["video" if is_video else "photo"] = media_url

    response = requests.post(url, data=payload)
    return response

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_to_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: Переменные окружения BOT_TOKEN или CHAT_ID не настроены!")
        return

    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("Не удалось получить записи из RSS-ленты.")
        return

    sent_history = load_history()
    sent_count = 0

    for entry in reversed(feed.entries):
        link = entry.get("link", "")
        if not link or link in sent_history:
            continue

        # Чистим текст: убираем хэштеги
        title = entry.get("title", "")
        caption_text = clean_text(title)

        # Ищем медиафайл в RSS (картинку или видео)
        media_url = None
        is_video = False

        # Способ 1: Ищем в media_content (стандарт для видео/фото в RSS.app)
        if "media_content" in entry:
            media_items = entry["media_content"]
            if media_items and len(media_items) > 0:
                media_url = media_items[0].get("url")
                # Проверяем, видео это или картинка
                medium_type = media_items[0].get("medium", "")
                if medium_type == "video" or (media_url and ".mp4" in media_url):
                    is_video = True

        # Способ 2: Запасной (enclosures)
        if not media_url and "enclosures" in entry:
            enclosures = entry["enclosures"]
            if enclosures and len(enclosures) > 0:
                media_url = enclosures[0].get("href")
                if enclosures[0].get("type", "").startswith("video") or (media_url and ".mp4" in media_url):
                    is_video = True

        # Если медиафайл найден, отправляем красивым постом
        if media_url:
            print(f"Отправляем медиа ({'Видео' if is_video else 'Фото'}): {media_url}")
            res = send_media(caption_text, media_url, is_video=is_video)
            
            # Если Telegram вернул ошибку (например, видео слишком большое для ссылки)
            if not res.json().get("ok"):
                print(f"Ошибка отправки медиа, пробуем отправить просто текстом: {res.text}")
                # Запасной вариант: отправляем просто очищенный текст, если медиа не пролезло
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": CHAT_ID, "text": f"{caption_text}\n\nСмотреть в Insta: {link}"})
        else:
            # Если в посте вообще не было медиа (редко для инсты), отправляем только текст
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": caption_text})

        save_to_history(link)
        sent_count += 1
        time.sleep(2)  # Чуть увеличили паузу, так как медиа обрабатывается дольше

    print(f"Успешно обработано новых постов: {sent_count}")

if __name__ == "__main__":
    main()