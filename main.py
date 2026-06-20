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
    """Отправляет фото или видео БЕЗ подписи, а затем отправляет ВЕСЬ текст поста вторым сообщением."""
    method = "sendVideo" if is_video else "sendPhoto"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    
    # 1. Отправляем только медиафайл (без текста)
    payload = {
        "chat_id": CHAT_ID
    }
    payload["video" if is_video else "photo"] = media_url

    response = requests.post(url, data=payload)
    
    # 2. Если медиа успешно ушло и у нас есть текст, отправляем его целиком вторым сообщением
    if response.json().get("ok") and caption:
        text_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        text_payload = {
            "chat_id": CHAT_ID,
            "text": caption[:4096]  # Ограничение Telegram на одно текстовое сообщение
        }
        requests.post(text_url, data=text_payload)

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

        # Получаем текст из description (там обычно полный текст), если пусто — берем summary или title
        raw_text = entry.get("description") or entry.get("summary") or entry.get("title", "")
        
        # Если в тексте есть HTML-теги от RSS.app, вырезаем их
        if "<" in raw_text and ">" in raw_text:
            raw_text = re.sub(r'<[^>]+>', '', raw_text)

        # Чистим текст от хэштегов
        caption_text = clean_text(raw_text)

        # Ищем медиафайл в RSS (картинку или видео)
        media_url = None
        is_video = False

        # Способ 1: Ищем в media_content
        if "media_content" in entry:
            media_items = entry["media_content"]
            if media_items and len(media_items) > 0:
                media_url = media_items[0].get("url")
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

        # Если медиафайл найден, отправляем
        if media_url:
            print(f"Отправляем медиа ({'Видео' if is_video else 'Фото'}): {media_url}")
            res = send_media(caption_text, media_url, is_video=is_video)
            
            # Если Telegram вернул ошибку медиа (например, ссылка устарела или формат не тот)
            if not res.json().get("ok"):
                print(f"Ошибка отправки медиа, пробуем отправить просто текстом: {res.text}")
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": CHAT_ID, "text": f"{caption_text}\n\nСмотреть в Insta: {link}"})
        else:
            # Если в посте вообще не было медиа, отправляем только текст
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": caption_text})

        save_to_history(link)
        sent_count += 1
        time.sleep(3)  # Пауза между постами, чтобы Telegram не заблокировал за спам

    print(f"Успешно обработано новых постов: {sent_count}")

if __name__ == "__main__":
    main()