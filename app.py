"""
Flask app untuk menjalankan bot dalam mode WEBHOOK.

File ini dipakai khusus saat deploy ke PythonAnywhere (atau hosting web app
gratis lain yang tidak bisa menjalankan proses run_polling() terus-menerus).

Cara kerja singkat:
- Telegram akan mengirim POST request ke URL:
    https://<username>.pythonanywhere.com/webhook/<BOT_TOKEN>
  setiap kali ada pesan/klik tombol baru dari user.
- Flask app ini menerima POST tersebut, mengubahnya jadi objek Update milik
  python-telegram-bot, lalu memprosesnya memakai handler yang sama persis
  dengan mode polling (lihat bot_core.py).

Token dipakai sebagai bagian dari URL supaya orang lain tidak bisa mengirim
update palsu ke bot kamu (semacam "secret path").
"""

import os
import asyncio
import logging

from flask import Flask, request

from telegram import Update
from bot_core import build_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "MASUKKAN_TOKEN_BOT_DI_SINI")

flask_app = Flask(__name__)

# Satu event loop yang dipakai berulang untuk memproses setiap update.
# PythonAnywhere (free tier) menjalankan app di satu proses/thread WSGI,
# sehingga pola ini aman dipakai untuk penggunaan personal/kelas kecil.
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

telegram_app = build_application(BOT_TOKEN)
_loop.run_until_complete(telegram_app.initialize())


@flask_app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    _loop.run_until_complete(telegram_app.process_update(update))
    return "ok"


@flask_app.route("/", methods=["GET"])
def index():
    # Halaman sederhana untuk cek app hidup (opsional, boleh dibuka di browser).
    return "Bot tugas kuliah aktif via webhook."


if __name__ == "__main__":
    # Hanya untuk uji coba lokal (bukan untuk produksi).
    flask_app.run(port=5000)
