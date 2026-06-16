import os
import instaloader

L = instaloader.Instaloader()

L.login(
    os.environ["IG_USERNAME"],
    os.environ["IG_PASSWORD"]
)

profile = instaloader.Profile.from_username(
    L.context,
    "handyclass.ru"
)

post = next(profile.get_posts())

print(post.shortcode)
print(post.caption[:100] if post.caption else "")