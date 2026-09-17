"""
Skrip bantuan untuk mendaftarkan atau menghapus webhook Telegram.

Jalankan SEKALI SAJA setelah web app kamu aktif di PythonAnywhere:

    python set_webhook.py set https://username.pythonanywhere.com

Untuk menghapus webhook (misalnya mau kembali ke mode polling):

    python set_webhook.py delete
"""

import os
import sys
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "MASUKKAN_TOKEN_BOT_DI_SINI")


def set_webhook(base_url: str):
    base_url = base_url.rstrip("/")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    webhook_url = f"{base_url}/webhook/{BOT_TOKEN}"
    resp = requests.post(url, data={"url": webhook_url})
    print(resp.json())


def delete_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    resp = requests.post(url)
    print(resp.json())


def get_webhook_info():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    resp = requests.get(url)
    print(resp.json())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pemakaian:")
        print("  python set_webhook.py set https://username.pythonanywhere.com")
        print("  python set_webhook.py delete")
        print("  python set_webhook.py info")
        sys.exit(1)

    action = sys.argv[1]
    if action == "set":
        if len(sys.argv) < 3:
            print("Sertakan base URL, contoh:")
            print("  python set_webhook.py set https://username.pythonanywhere.com")
            sys.exit(1)
        set_webhook(sys.argv[2])
    elif action == "delete":
        delete_webhook()
    elif action == "info":
        get_webhook_info()
    else:
        print(f"Aksi tidak dikenal: {action}")
