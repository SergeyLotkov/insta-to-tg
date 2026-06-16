import os
import requests
import instaloader

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

L = instaloader.Instaloader()

profile = instaloader.Profile.from_username(
    L.context,
    "handyclass.ru"
)

post = next(profile.get_posts())

text = f"""📸 Новый пост Instagram

{post.caption[:500] if post.caption else ''}

https://www.instagram.com/p/{post.shortcode}/
"""

r = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": text
    }
)

print("Telegram:", r.status_code)
print("Post:", post.shortcode)