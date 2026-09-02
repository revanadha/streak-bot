"""
Streak Bot - Bot Telegram untuk mengingatkan & mencatat streak harianmu.

Cara pakai singkat:
1. Install dependency:
   pip install "python-telegram-bot[job-queue]" --break-system-packages

2. Set token bot kamu (dari @BotFather di Telegram) sebagai environment variable:
   export TELEGRAM_BOT_TOKEN="isi_token_kamu"

3. Jalankan:
   python3 streak_bot.py

Command yang tersedia di bot:
- /start         -> daftar & mulai, langsung dapat tombol streak pertama
- /streak        -> cek streak saat ini & streak terpanjang
- /reset         -> reset manual kalau kamu mau mulai ulang
- /jam HH:MM     -> atur jam pengingat harian (contoh: /jam 21:00)

Cara kerja:
- Tiap hari jam yang kamu atur (default 21:00 waktu server), bot kirim pesan
  dengan tombol "🔥 Nyalain Api Hari Ini".
- Klik tombol itu = kamu konfirmasi hari ini kamu berhasil (streak +1).
- Kalau dalam 1 hari penuh kamu gak klik sama sekali, streak otomatis balik ke 0
  saat pengingat berikutnya dikirim (dicek otomatis oleh bot).
- Semua tombol hanya bisa diklik 1x per hari (anti klik berkali-kali buat "ngakalin" angka).

Data disimpan di file JSON lokal (streak_data.json) di folder yang sama,
jadi datamu tetap ada walau bot direstart.
"""

import json
import os
from datetime import datetime, date, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

# Zona waktu yang dipakai untuk semua jadwal reminder.
# Default: Asia/Makassar (WITA, UTC+8). Bisa diganti lewat environment variable
# BOT_TIMEZONE, misalnya "Asia/Jakarta" (WIB) atau "Asia/Jayapura" (WIT).
TIMEZONE = ZoneInfo(os.environ.get("BOT_TIMEZONE", "Asia/Makassar"))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Kalau ada environment variable DATA_DIR (misalnya /data dari Railway Volume),
# simpan data di situ supaya tidak hilang saat redeploy. Kalau tidak ada,
# simpan di folder yang sama dengan script ini (buat dijalankan di laptop sendiri).
DATA_DIR = os.environ.get("DATA_DIR")
if DATA_DIR:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    DATA_FILE = Path(DATA_DIR) / "streak_data.json"
else:
    DATA_FILE = Path(__file__).parent / "streak_data.json"
DEFAULT_REMINDER_HOUR = 21
DEFAULT_REMINDER_MINUTE = 0


# ---------- Penyimpanan data sederhana (JSON) ----------

def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user(data: dict, user_id: str) -> dict:
    if user_id not in data:
        data[user_id] = {
            "streak": 0,
            "longest_streak": 0,
            "last_confirmed_date": None,  # format YYYY-MM-DD
            "reminder_hour": DEFAULT_REMINDER_HOUR,
            "reminder_minute": DEFAULT_REMINDER_MINUTE,
        }
    return data[user_id]


# ---------- Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user(data, user_id)
    save_data(data)

    await update.message.reply_text(
        "Halo! Bot ini bakal bantu kamu ngitung streak harian kamu.\n\n"
        "Setiap hari kamu bakal dapat pengingat dengan tombol 🔥. "
        "Klik tombolnya kalau hari itu kamu berhasil.\n\n"
        "Command lain:\n"
        "/streak - cek progres kamu\n"
        "/reset - reset streak kalau mau mulai ulang\n"
        "/jam HH:MM - atur jam pengingat harian\n\n"
        "Yuk mulai sekarang, klik tombol di bawah ini:"
    )
    await send_streak_button(update.effective_chat.id, context)

    # jadwalkan reminder harian buat user ini
    schedule_daily_reminder(context.application, user_id, user["reminder_hour"], user["reminder_minute"])


async def send_streak_button(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔥 Nyalain Api Hari Ini", callback_data="confirm_streak")]]
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="Sudah waktunya cek in harian kamu. Klik kalau hari ini kamu berhasil menjaga streak-mu 👇",
        reply_markup=keyboard,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()

    data = load_data()
    user = get_user(data, user_id)

    today_str = date.today().isoformat()

    if user["last_confirmed_date"] == today_str:
        await query.edit_message_text(
            f"Kamu sudah konfirmasi hari ini ✅\nStreak kamu sekarang: {user['streak']} hari 🔥"
        )
        return

    user["streak"] += 1
    user["longest_streak"] = max(user["longest_streak"], user["streak"])
    user["last_confirmed_date"] = today_str
    save_data(data)

    await query.edit_message_text(
        f"Mantap! Streak kamu sekarang: {user['streak']} hari 🔥\n"
        f"Streak terpanjang: {user['longest_streak']} hari 🏆\n\n"
        "Terus jaga konsistensinya, sampai ketemu besok!"
    )


async def streak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user(data, user_id)
    save_data(data)

    await update.message.reply_text(
        f"Streak kamu saat ini: {user['streak']} hari 🔥\n"
        f"Streak terpanjang: {user['longest_streak']} hari 🏆"
    )


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user(data, user_id)
    user["streak"] = 0
    user["last_confirmed_date"] = None
    save_data(data)

    await update.message.reply_text(
        "Oke, streak sudah direset ke 0. Gapapa, yang penting mulai lagi hari ini 💪"
    )


async def set_reminder_time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Format: /jam HH:MM (contoh: /jam 21:00)")
        return

    try:
        hour, minute = map(int, context.args[0].split(":"))
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        await update.message.reply_text("Format jam salah. Contoh yang benar: /jam 21:00")
        return

    data = load_data()
    user = get_user(data, user_id)
    user["reminder_hour"] = hour
    user["reminder_minute"] = minute
    save_data(data)

    schedule_daily_reminder(context.application, user_id, hour, minute)

    await update.message.reply_text(f"Oke, pengingat harian diatur jam {hour:02d}:{minute:02d}.")


# ---------- Penjadwalan reminder harian per user ----------

async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    chat_id = context.job.chat_id

    data = load_data()
    user = get_user(data, user_id)

    # Kalau kemarin gak dikonfirmasi, streak putus -> reset ke 0
    today_str = date.today().isoformat()
    if user["last_confirmed_date"] and user["last_confirmed_date"] != today_str:
        last = datetime.fromisoformat(user["last_confirmed_date"]).date()
        days_gap = (date.today() - last).days
        if days_gap > 1:
            user["streak"] = 0
    save_data(data)

    await send_streak_button(chat_id, context)


def schedule_daily_reminder(application: Application, user_id: str, hour: int, minute: int):
    job_name = f"reminder_{user_id}"
    # hapus job lama kalau ada, biar gak dobel saat jam diganti
    current_jobs = application.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    application.job_queue.run_daily(
        daily_reminder_job,
        time=dtime(hour=hour, minute=minute, tzinfo=TIMEZONE),
        chat_id=int(user_id),
        name=job_name,
        data={"user_id": user_id},
    )


def restore_all_reminders(application: Application):
    """Dipanggil sekali saat bot start, biar user yang udah pernah /start tetap dapat reminder."""
    data = load_data()
    for user_id, user in data.items():
        schedule_daily_reminder(
            application, user_id, user.get("reminder_hour", DEFAULT_REMINDER_HOUR),
            user.get("reminder_minute", DEFAULT_REMINDER_MINUTE),
        )


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN belum di-set. Jalankan:\n"
            "export TELEGRAM_BOT_TOKEN='token_kamu_dari_BotFather'"
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("streak", streak_cmd))
    application.add_handler(CommandHandler("reset", reset_cmd))
    application.add_handler(CommandHandler("jam", set_reminder_time_cmd))
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^confirm_streak$"))

    restore_all_reminders(application)

    print("Bot jalan... tekan Ctrl+C untuk berhenti.")
    application.run_polling()


if __name__ == "__main__":
    main()
