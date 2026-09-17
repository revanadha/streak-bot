import logging
import sqlite3
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tugas.db")

MATKUL_LIST = [
    "Metode Penelitian",
    "Etika dan Profesi",
    "Pemrograman Mobile",
    "Pra Skripsi",
    "Pemrograman Fungsional",
    "Pengantar Game",
    "Piranti Cerdas",
    "Pemrograman Web",
]

SELECT_MATKUL, INPUT_JUDUL = range(2)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            matkul TEXT NOT NULL,
            judul TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'belum',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def matkul_keyboard(prefix: str, include_all: bool = False):
    buttons = []
    row = []
    for i, m in enumerate(MATKUL_LIST):
        row.append(InlineKeyboardButton(m, callback_data=f"{prefix}|{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if include_all:
        buttons.append([InlineKeyboardButton("📋 Semua Matkul", callback_data=f"{prefix}|all")])
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# /start & /help
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Halo! Saya bot pencatat tugas kuliah.\n\n"
        "Perintah yang tersedia:\n"
        "/tambah - tambah tugas baru\n"
        "/list - lihat daftar tugas (bisa per matkul atau semua)\n"
        "/stats - ringkasan jumlah tugas selesai/belum per matkul\n"
        "/batal - batalkan proses yang sedang berjalan\n"
    )
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ---------------------------------------------------------------------------
# /tambah (ConversationHandler): pilih matkul -> ketik judul tugas
# ---------------------------------------------------------------------------

async def tambah_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pilih mata kuliah untuk tugas ini:",
        reply_markup=matkul_keyboard("addmatkul"),
    )
    return SELECT_MATKUL


async def tambah_pilih_matkul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("|")[1])
    matkul = MATKUL_LIST[idx]
    context.user_data["matkul"] = matkul
    await query.edit_message_text(f"Matkul: {matkul}\n\nKetik judul/deskripsi tugasnya:")
    return INPUT_JUDUL


async def tambah_input_judul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    judul = update.message.text.strip()
    matkul = context.user_data.get("matkul")
    user_id = update.effective_user.id

    conn = get_conn()
    conn.execute(
        "INSERT INTO tasks (user_id, matkul, judul, status, created_at) VALUES (?, ?, ?, 'belum', ?)",
        (user_id, matkul, judul, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Tugas ditambahkan!\nMatkul: {matkul}\nTugas: {judul}\nStatus: ⬜ Belum dikerjakan"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /list: pilih matkul (atau semua) -> tampilkan daftar tugas + tombol aksi
# ---------------------------------------------------------------------------

async def list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pilih matkul yang ingin dilihat tugasnya:",
        reply_markup=matkul_keyboard("listmatkul", include_all=True),
    )


def build_task_list_text_and_keyboard(user_id: int, matkul_filter):
    conn = get_conn()
    if matkul_filter is None:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? ORDER BY matkul, status, id",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND matkul=? ORDER BY status, id",
            (user_id, matkul_filter),
        ).fetchall()
    conn.close()

    if not rows:
        text = (
            "Belum ada tugas tercatat."
            if matkul_filter is None
            else f"Belum ada tugas untuk {matkul_filter}."
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="backlist")]]
        return text, InlineKeyboardMarkup(keyboard)

    lines = []
    buttons = []
    current_matkul = None
    for r in rows:
        if matkul_filter is None and r["matkul"] != current_matkul:
            current_matkul = r["matkul"]
            lines.append(f"\n📚 {current_matkul}")
        emoji = "✅" if r["status"] == "selesai" else "⬜"
        lines.append(f"{emoji} #{r['id']} - {r['judul']}")
        toggle_label = "Tandai Belum" if r["status"] == "selesai" else "Tandai Selesai"
        buttons.append(
            [
                InlineKeyboardButton(f"{toggle_label} (#{r['id']})", callback_data=f"toggle|{r['id']}"),
                InlineKeyboardButton(f"🗑 Hapus #{r['id']}", callback_data=f"delete|{r['id']}"),
            ]
        )
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="backlist")])
    text = "\n".join(lines).strip()
    return text, InlineKeyboardMarkup(buttons)


async def list_pilih_matkul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")[1]
    matkul_filter = None if data == "all" else MATKUL_LIST[int(data)]
    context.user_data["last_list_filter"] = matkul_filter
    text, keyboard = build_task_list_text_and_keyboard(update.effective_user.id, matkul_filter)
    await query.edit_message_text(text, reply_markup=keyboard)


async def back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Pilih matkul yang ingin dilihat tugasnya:",
        reply_markup=matkul_keyboard("listmatkul", include_all=True),
    )


async def toggle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("|")[1])
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, update.effective_user.id)
    ).fetchone()
    if row:
        new_status = "belum" if row["status"] == "selesai" else "selesai"
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
        conn.commit()
    conn.close()

    matkul_filter = context.user_data.get("last_list_filter")
    text, keyboard = build_task_list_text_and_keyboard(update.effective_user.id, matkul_filter)
    await query.edit_message_text(text, reply_markup=keyboard)


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("|")[1])
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, update.effective_user.id))
    conn.commit()
    conn.close()

    matkul_filter = context.user_data.get("last_list_filter")
    text, keyboard = build_task_list_text_and_keyboard(update.effective_user.id, matkul_filter)
    await query.edit_message_text(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_conn()
    lines = ["📊 Ringkasan Tugas:\n"]
    total_selesai = 0
    total_belum = 0
    for m in MATKUL_LIST:
        selesai = conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE user_id=? AND matkul=? AND status='selesai'",
            (user_id, m),
        ).fetchone()["c"]
        belum = conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE user_id=? AND matkul=? AND status='belum'",
            (user_id, m),
        ).fetchone()["c"]
        total_selesai += selesai
        total_belum += belum
        lines.append(f"{m}: ✅ {selesai} | ⬜ {belum}")
    conn.close()
    total = total_selesai + total_belum
    lines.append(f"\nTotal: ✅ {total_selesai} selesai, ⬜ {total_belum} belum dari {total} tugas.")
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Pembuatan Application (dipakai baik oleh mode polling maupun webhook)
# ---------------------------------------------------------------------------

def build_application(token: str) -> Application:
    """Membuat objek Application dengan semua handler terpasang.

    Tidak memanggil run_polling() di sini supaya fungsi ini bisa dipakai ulang
    baik oleh skrip polling (bot.py) maupun oleh Flask app untuk webhook
    (app.py, dipakai di PythonAnywhere).
    """
    init_db()
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("tambah", tambah_start)],
        states={
            SELECT_MATKUL: [CallbackQueryHandler(tambah_pilih_matkul, pattern=r"^addmatkul\|")],
            INPUT_JUDUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_input_judul)],
        },
        fallbacks=[CommandHandler("batal", batal)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(list_pilih_matkul, pattern=r"^listmatkul\|"))
    app.add_handler(CallbackQueryHandler(back_to_list, pattern=r"^backlist$"))
    app.add_handler(CallbackQueryHandler(toggle_task, pattern=r"^toggle\|"))
    app.add_handler(CallbackQueryHandler(delete_task, pattern=r"^delete\|"))

    return app
