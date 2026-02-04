# telegram_alert.py
import requests

BOT_TOKEN = "8593528287:AAH8yWiEbSVyjzXf1pGTpHdCjD48vp-NLNU"
CHAT_ID = "5252788911"


def send_alert(title, data=None):

    message = f"{title}: {data}\n"
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": False
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Telegram Error:", e)
