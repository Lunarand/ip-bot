import os
import re
import logging
from ipaddress import ip_address
from urllib.request import urlopen
import json

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def is_valid_ip(ip_str: str) -> bool:
    try:
        ip_address(ip_str)
        return True
    except ValueError:
        return False

def get_ip_info(ip: str) -> dict:
    url = f'http://ip-api.com/json/{ip}'
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error fetching IP info: {e}")
        return {'status': 'fail', 'message': str(e)}

def format_ip_message(data: dict) -> str:
    if data.get('status') == 'fail':
        return f"❌ Error: {data.get('message', 'Unable to fetch IP information')}"

    parts = []
    parts.append(f"🌐 **IP Address:** `{data.get('query', 'N/A')}`")
    parts.append(f"📍 **Location:** {data.get('city', 'N/A')}, {data.get('regionName', 'N/A')}, {data.get('country', 'N/A')}")
    parts.append(f"🏳️ **Country Code:** {data.get('countryCode', 'N/A')}")
    parts.append(f"🗺️ **Coordinates:** {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}")
    parts.append(f"🌍 **Timezone:** {data.get('timezone', 'N/A')}")
    parts.append(f"🏢 **ISP:** {data.get('isp', 'N/A')}")
    parts.append(f"🏢 **Organization:** {data.get('org', 'N/A')}")
    parts.append(f"🔢 **AS Number:** {data.get('as', 'N/A')}")

    return '\n'.join(parts)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to IP Checker Bot!*\n\n"
        "Send me any IP address and I'll get detailed information about it.\n\n"
        "Example: `8.8.8.8` or `2001:4860:4860::8888`",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send /start to see welcome message\n"
        "2. Send any IPv4 or IPv6 address\n"
        "3. I'll return detailed information about that IP\n\n"
        "Example IPs to try:\n"
        "- `8.8.8.8` (Google DNS)\n"
        "- `1.1.1.1` (Cloudflare)\n"
        "- `142.250.190.46` (Google)",
        parse_mode='Markdown'
    )

async def handle_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    if not is_valid_ip(user_input):
        await update.message.reply_text(
            "⚠️ Invalid IP address. Please enter a valid IPv4 or IPv6 address.\n\n"
            "Example: `8.8.8.8`",
            parse_mode='Markdown'
        )
        return

    await update.message.reply_text("🔍 Fetching IP information...")
    ip_info = get_ip_info(user_input)
    await update.message.reply_text(format_ip_message(ip_info), parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ip))
    app.add_handler(MessageHandler(filters.ALL, error_handler))

    logger.info("Bot starting...")
    app.run_polling(poll_interval=3)

if __name__ == '__main__':
    main()