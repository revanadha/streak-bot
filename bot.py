import os
import logging

from bot_core import build_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ambil token dari environment variable BOT_TOKEN, atau isi langsung di sini.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "MASUKKAN_TOKEN_BOT_DI_SINI")


def main():
    app = build_application(BOT_TOKEN)
    logger.info("Bot berjalan (mode polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
