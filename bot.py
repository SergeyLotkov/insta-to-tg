#!/usr/bin/env python3
"""
RSS -> Telegram репостер.

Читает RSS-фид (rss.app), находит новые посты (по guid),
отправляет текст + картинку в Telegram-канал, запоминает
отправленные посты в posted.json, чтобы не дублировать.
"""

import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request

# ---------- Конфиг ----------

RSS_URL = os.environ.get("RSS_URL", "https://rss.app/feeds/pciA3C3UBcPVtJaj.xml")
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = Path(__file__).parent / "posted.json"

# Если True (первый запуск) — просто запоминаем все текущие посты
# как "уже отправленные", ничего не постим. Управляется наличием
# state-файла: если его нет, считаем это первым запуском.
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ---------- Утилиты ----------

def http_get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (rss-to-tg-bot)"})
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def http_post_json(url: str, payload: dict) -> dict:
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"posted_guids": [], "initialized": False}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- Парсинг RSS ----------

def strip_html(raw_html: str) -> str:
    """Убирает html-теги, декодирует энтити, нормализует пробелы/переводы строк."""
    # Заменим закрывающие div/p на перевод строки, чтобы не слипался текст
    text = re.sub(r"<\s*/\s*(div|p|br)\s*/?\s*>", "\n", raw_html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # Убираем лишние пустые строки
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln != ""]
    return "\n".join(lines)


def remove_hashtags(text: str) -> str:
    """Удаляет хештеги (#слово, с юникод-буквами) и подчищает пробелы после."""
    text = re.sub(r"#[\w\u0400-\u04FF]+", "", text)
    # Убираем строки, которые после удаления хештегов стали пустыми/из пробелов
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln != ""]
    text = "\n".join(lines)
    # Сжимаем повторные пробелы
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def parse_feed(xml_bytes: bytes) -> list[dict]:
    ns = {"media": "http://search.yahoo.com/mrss/"}
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    items = []
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        guid = guid_el.text.strip() if guid_el is not None and guid_el.text else None
        if not guid:
            # fallback на link, если guid почему-то отсутствует
            link_el = item.find("link")
            guid = link_el.text.strip() if link_el is not None and link_el.text else None
        if not guid:
            continue

        link_el = item.find("link")
        link = link_el.text.strip() if link_el is not None and link_el.text else ""

        pubdate_el = item.find("pubDate")
        pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

        desc_el = item.find("description")
        description_html = desc_el.text or "" if desc_el is not None else ""
        text = strip_html(description_html)
        text = remove_hashtags(text)

        image_url = None
        media_el = item.find("media:content", ns)
        if media_el is not None:
            image_url = media_el.get("url")
        if not image_url:
            # fallback: вытащить src первой <img> из description
            m = re.search(r'<img[^>]+src="([^"]+)"', description_html)
            if m:
                image_url = m.group(1)

        items.append(
            {
                "guid": guid,
                "link": link,
                "pubdate": pubdate,
                "text": text,
                "image_url": image_url,
            }
        )
    return items


# ---------- Telegram ----------

TELEGRAM_CAPTION_LIMIT = 1024


def send_photo(chat_id: str, photo_url: str, caption: str) -> None:
    caption = caption[:TELEGRAM_CAPTION_LIMIT]
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
    }
    result = http_post_json(f"{TELEGRAM_API}/sendPhoto", payload)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram sendPhoto failed: {result}")


def send_message(chat_id: str, text: str) -> None:
    payload = {"chat_id": chat_id, "text": text}
    result = http_post_json(f"{TELEGRAM_API}/sendMessage", payload)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {result}")


# ---------- Основная логика ----------

def main() -> None:
    print(f"Fetching feed: {RSS_URL}")
    xml_bytes = http_get(RSS_URL)
    items = parse_feed(xml_bytes)
    print(f"Found {len(items)} items in feed")

    state = load_state()
    posted_guids = set(state.get("posted_guids", []))

    # Первый запуск: ничего не публикуем, просто фиксируем текущие посты
    # как уже отправленные, чтобы не заспамить канал старым архивом.
    if not state.get("initialized"):
        print("First run detected: marking all current items as posted, no sending.")
        for it in items:
            posted_guids.add(it["guid"])
        state["posted_guids"] = list(posted_guids)
        state["initialized"] = True
        save_state(state)
        print(f"Initialized with {len(posted_guids)} guids. Done.")
        return

    # RSS обычно отдаёт новые посты первыми, нам нужно публиковать
    # от старых к новым, чтобы порядок в канале совпадал с Instagram
    new_items = [it for it in items if it["guid"] not in posted_guids]
    new_items.reverse()

    if not new_items:
        print("No new items.")
        return

    print(f"Found {len(new_items)} new item(s). Posting...")

    for it in new_items:
        guid = it["guid"]
        text = it["text"] or ""
        image_url = it["image_url"]

        try:
            if image_url:
                send_photo(CHAT_ID, image_url, text)
            else:
                # На случай если у поста вообще нет картинки
                send_message(CHAT_ID, text)
            print(f"Posted guid={guid}")
        except Exception as e:
            print(f"ERROR posting guid={guid}: {e}", file=sys.stderr)
            # Не добавляем guid в posted, чтобы попробовать снова в следующий раз
            continue

        posted_guids.add(guid)
        state["posted_guids"] = list(posted_guids)
        save_state(state)

        # небольшая пауза между сообщениями, чтобы не упереться в rate limit
        time.sleep(2)

    print("Done.")


if __name__ == "__main__":
    main()
