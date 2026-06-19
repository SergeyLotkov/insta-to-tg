import feedparser
import requests
import os
import time

RSS_URL = "https://rss.app/feeds/pciA3C3UBcPVtJaj.xml"
HISTORY_FILE = "history.txt"  # Файл, где будут храниться ссылки

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })
    return response

def load_history():
    """Загружает список уже отправленных ссылок из файла."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        # Читаем строки и убираем пробелы/переносы строк
        return set(line.strip() for line in f if line.strip())

def save_to_history(link):
    """Дописывает новую ссылку в файл истории."""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: Переменные окружения BOT_TOKEN или CHAT_ID не настроены!")
        return

    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("Не удалось получить записи из RSS-ленты или она пуста.")
        return

    # Загружаем историю отправленных постов
    sent_history = load_history()
    sent_count = 0

    # Перебираем посты от старых к новым
    for entry in reversed(feed.entries):
        title = entry.get("title", "Без названия")
        link = entry.get("link", "")

        if not link:
            continue

        # Если ссылка уже есть в истории — пропускаем этот пост
        if link in sent_history:
            continue

        # Если пост новый — отправляем его в Telegram
        message = f"{title}\n{link}"
        send(message)
        print(f"Отправлено: {title}")
        
        # Сохраняем в историю, чтобы больше не отправлять
        save_to_history(link)
        sent_count += 1
        
        time.sleep(1)

    if sent_count == 0:
        print("Новых постов не обнаружено.")
    else:
        print(f"Успешно отправлено новых постов: {sent_count}")

if __name__ == "__main__":
    main()