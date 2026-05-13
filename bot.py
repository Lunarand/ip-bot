import os
import re
import logging
import signal
import sys
from ipaddress import ip_address
from urllib.request import urlopen, Request
from urllib.error import URLError
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

def is_valid_phone(phone_str: str) -> bool:
    phone = re.sub(r'[\s\-\+\(\)]', '', phone_str)
    return bool(re.match(r'^\+?[1-9]\d{7,14}$', phone))

def clean_phone(phone_str: str) -> str:
    return re.sub(r'[\s\-\(\)]', '', phone_str)

def fetch_url(url: str, headers: dict = None) -> dict:
    try:
        req = Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def fetch_text(url: str) -> str:
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            return response.read().decode()
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def get_ipapi_com(ip: str) -> dict:
    data = fetch_url(f'http://ip-api.com/json/{ip}')
    if data and data.get('status') == 'success':
        return {
            'source': 'ip-api.com',
            'ip': data.get('query'),
            'country': data.get('country'),
            'country_code': data.get('countryCode'),
            'region': data.get('regionName'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'timezone': data.get('timezone'),
            'isp': data.get('isp'),
            'org': data.get('org'),
            'as': data.get('as'),
        }
    return None

def get_ipapi_co(ip: str) -> dict:
    data = fetch_url(f'https://ipapi.co/{ip}/json/')
    if data:
        return {
            'source': 'ipapi.co',
            'ip': data.get('ip'),
            'version': data.get('ip_version'),
            'country': data.get('country_name'),
            'country_code': data.get('country_code'),
            'region': data.get('region'),
            'city': data.get('city'),
            'postal': data.get('postal'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'timezone': data.get('timezone'),
            'isp': data.get('org'),
            'org': data.get('network'),
            'asn': data.get('asn'),
            'languages': data.get('languages'),
            'currency': data.get('currency'),
        }
    return None

def get_ipwhois_io(ip: str) -> dict:
    data = fetch_url(f'https://ipwhois.io/json/{ip}')
    if data and not data.get('success') == False:
        return {
            'source': 'ipwhois.io',
            'ip': data.get('ip'),
            'country': data.get('country'),
            'country_code': data.get('country_code'),
            'region': data.get('region'),
            'city': data.get('city'),
            'postal': data.get('postal'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'timezone': data.get('timezone'),
            'isp': data.get('isp'),
            'org': data.get('org'),
            'asn': data.get('asn'),
        }
    return None

def get_ipapi_lat(ip: str) -> dict:
    data = fetch_url(f'https://ipapi.lat/{ip}/json/')
    if data and not data.get('error'):
        return {
            'source': 'ipapi.lat',
            'ip': data.get('ip'),
            'country': data.get('country'),
            'country_code': data.get('country_code'),
            'region': data.get('region_name'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'timezone': data.get('timezone'),
            'isp': data.get('isp'),
            'org': data.get('org'),
            'asn': data.get('asn'),
        }
    return None

def get_geolocation_io(ip: str) -> dict:
    data = fetch_url(f'https://api.geolocation.io/?ip={ip}')
    if data and not data.get('error'):
        return {
            'source': 'geolocation.io',
            'ip': data.get('ip'),
            'country': data.get('country'),
            'country_code': data.get('country_code'),
            'region': data.get('region'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'timezone': data.get('timezone'),
            'isp': data.get('isp'),
            'org': data.get('organization'),
            'asn': data.get('asn'),
        }
    return None

def get_all_ip_info(ip: str) -> list:
    results = []
    funcs = [get_ipapi_com, get_ipapi_co, get_ipwhois_io, get_ipapi_lat, get_geolocation_io]
    for func in funcs:
        try:
            result = func(ip)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
    return results

def format_source_result(data: dict) -> str:
    parts = [f"📡 *Source: {data.get('source')}*"]
    parts.append(f"🌐 **IP:** `{data.get('ip', 'N/A')}`")
    parts.append(f"🏳️ **Country:** {data.get('country', 'N/A')} ({data.get('country_code', 'N/A')})")
    parts.append(f"📍 **Region:** {data.get('region', 'N/A')}")
    parts.append(f"🏙️ **City:** {data.get('city', 'N/A')}")
    if data.get('postal') or data.get('zip'):
        parts.append(f"📮 **Zip:** {data.get('postal') or data.get('zip', 'N/A')}")
    parts.append(f"🗺️ **Coordinates:** {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}")
    parts.append(f"🌍 **Timezone:** {data.get('timezone', 'N/A')}")
    parts.append(f"🏢 **ISP:** {data.get('isp', 'N/A')}")
    parts.append(f"🏢 **Org:** {data.get('org', 'N/A')}")
    if data.get('asn'):
        parts.append(f"🔢 **ASN:** {data.get('asn', 'N/A')}")
    if data.get('as'):
        parts.append(f"🔢 **AS:** {data.get('as', 'N/A')}")
    
    if data.get('languages'):
        parts.append(f"🗣️ **Languages:** {data.get('languages', 'N/A')}")
    if data.get('currency'):
        parts.append(f"💰 **Currency:** {data.get('currency', 'N/A')}")
    
    return '\n'.join(parts)

def format_ip_message(results: list) -> str:
    if not results:
        return "❌ Could not fetch IP information from any source."

    msg = "📊 *IP Lookup Results (Multiple Sources)*\n\n"
    
    for i, data in enumerate(results, 1):
        msg += f"{'━'*30}\n"
        msg += f"Source {i}: {data.get('source')}\n"
        msg += f"{'━'*30}\n"
        msg += format_source_result(data) + "\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📝 *Note:* Phone numbers & emails are NOT directly associated with IP addresses."
    
    return msg

def get_calltracer_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    if not clean.startswith('+'):
        clean = '+' + clean
    
    data = fetch_url(f'https://calltracer.io/api/lookup/{clean}')
    if data:
        return {
            'source': 'calltracer.io',
            'number': data.get('number'),
            'international': data.get('international'),
            'national': data.get('national'),
            'country_code': data.get('country_code'),
            'country_iso': data.get('country_iso'),
            'country': data.get('country'),
            'number_type': data.get('number_type'),
            'carrier': data.get('carrier'),
            'location': data.get('location'),
            'timezones': data.get('timezones'),
            'is_valid': data.get('is_valid'),
            'spam_total': data.get('reports', {}).get('total'),
            'spam_score': data.get('reports', {}).get('spam_score'),
            'spam_last_reported': data.get('reports', {}).get('last_reported_at'),
        }
    return None

def get_phonenumber_api_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    data = fetch_url(f'http://phone-number-api.com/json/?number={clean}')
    if data and data.get('status') == 'success':
        return {
            'source': 'phone-number-api.com',
            'query': data.get('query'),
            'number_type': data.get('numberType'),
            'valid': data.get('numberValid'),
            'valid_for_region': data.get('numberValidForRegion'),
            'disposable': data.get('isDisposible'),
            'country_code': data.get('numberCountryCode'),
            'area_code': data.get('numberAreaCode'),
            'format_e164': data.get('formatE164'),
            'format_national': data.get('formatNational'),
            'format_international': data.get('formatInternational'),
            'continent': data.get('continent'),
            'continent_code': data.get('continentCode'),
            'country': data.get('country'),
            'country_name': data.get('countryName'),
            'region': data.get('region'),
            'region_name': data.get('regionName'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'timezone': data.get('timezone'),
            'offset': data.get('offset'),
            'languages': data.get('languageLikely'),
            'currency': data.get('currency'),
        }
    return None

def get_libphonenumber_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    data = fetch_url(f'https://libphonenumberapi.com/api/phone-numbers/{clean}')
    if data:
        return {
            'source': 'libphonenumberapi.com',
            'valid': data.get('is_valid'),
            'possible': data.get('is_possible'),
            'type': data.get('type'),
            'carrier': data.get('carrier'),
            'geo_name': data.get('geo_name'),
            'timezone': data.get('timezone'),
            'country': data.get('country'),
            'e164': data.get('formats', {}).get('e164'),
            'international': data.get('formats', {}).get('international'),
            'national': data.get('formats', {}).get('national'),
        }
    return None

def get_all_phone_info(phone: str) -> list:
    results = []
    cleaned = clean_phone(phone)
    
    funcs = [get_calltracer_info, get_phonenumber_api_info, get_libphonenumber_info]
    for func in funcs:
        try:
            result = func(cleaned)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
    
    if not results:
        basic_info = {
            'source': 'Basic Parser',
            'number': cleaned,
            'country_prefix': cleaned[:3] if cleaned.startswith('+') else None,
            'note': 'No API results. Only basic parsing available.'
        }
        results.append(basic_info)
    
    return results

def format_phone_result(data: dict) -> str:
    parts = [f"📡 *Source: {data.get('source')}*"]
    
    if data.get('note'):
        parts.append(f"📝 {data.get('note')}")
        return '\n'.join(parts)
    
    if data.get('is_valid') is not None:
        parts.append(f"✅ **Valid:** {'Yes' if data.get('is_valid') else 'No'}")
    if data.get('valid') is not None:
        parts.append(f"✅ **Valid:** {'Yes' if data.get('valid') else 'No'}")
    if data.get('number'):
        parts.append(f"📱 **Number:** `{data.get('number')}`")
    if data.get('international'):
        parts.append(f"🌍 **Intl Format:** {data.get('international')}")
    if data.get('national'):
        parts.append(f"📝 **National:** {data.get('national')}")
    if data.get('format_e164'):
        parts.append(f"📋 **E164:** {data.get('format_e164')}")
    if data.get('format_international'):
        parts.append(f"🌍 **Intl Format:** {data.get('format_international')}")
    if data.get('format_national'):
        parts.append(f"📝 **National:** {data.get('format_national')}")
    
    country_name = data.get('country') or data.get('country_name')
    if country_name:
        parts.append(f"🏳️ **Country:** {country_name}")
    if data.get('country_iso') or data.get('country_code'):
        parts.append(f"🏳️ **Country Code:** {data.get('country_iso') or data.get('country_code')}")
    
    if data.get('location') or data.get('city') or data.get('region_name'):
        parts.append(f"📍 **Location:** {data.get('location') or data.get('city') or data.get('region_name')}")
    
    if data.get('region') or data.get('region_name'):
        parts.append(f"📍 **Region:** {data.get('region') or data.get('region_name', 'N/A')}")
    
    if data.get('city'):
        parts.append(f"🏙️ **City:** {data.get('city', 'N/A')}")
    
    if data.get('zip'):
        parts.append(f"📮 **Zip:** {data.get('zip', 'N/A')}")
    
    if data.get('lat') and data.get('lon'):
        parts.append(f"🗺️ **Coordinates:** {data.get('lat')}, {data.get('lon')}")
    
    if data.get('timezone'):
        parts.append(f"🌍 **Timezone:** {data.get('timezone', 'N/A')}")
    
    if data.get('carrier'):
        parts.append(f"🏢 **Carrier:** {data.get('carrier', 'N/A')}")
    
    if data.get('number_type') or data.get('type'):
        parts.append(f"📱 **Line Type:** {data.get('number_type') or data.get('type', 'N/A')}")
    
    if data.get('spam_total') is not None:
        parts.append(f"⚠️ **Spam Reports:** {data.get('spam_total', 'N/A')}")
    if data.get('spam_score') is not None:
        parts.append(f"📊 **Spam Score:** {data.get('spam_score', 'N/A')}")
    
    if data.get('disposable') is not None:
        parts.append(f"🗑️ **Disposable:** {'Yes' if data.get('disposable') else 'No'}")
    
    if data.get('languages'):
        parts.append(f"🗣️ **Languages:** {', '.join(data.get('languages', []))}")
    if data.get('currency'):
        parts.append(f"💰 **Currency:** {data.get('currency', 'N/A')}")
    
    parts.append(f"📞 **Phone:** Not available (privacy protected)")
    parts.append(f"📧 **Email:** Not available (privacy protected)")
    parts.append(f"📍 **Address:** Not available (privacy protected)")
    
    return '\n'.join(parts)

def format_phone_message(results: list) -> str:
    if not results:
        return "❌ Could not fetch phone information."

    msg = "📱 *Phone Number Lookup Results*\n\n"
    
    for i, data in enumerate(results, 1):
        msg += f"{'━'*30}\n"
        msg += f"Source {i}: {data.get('source')}\n"
        msg += f"{'━'*30}\n"
        msg += format_phone_result(data) + "\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📝 *Note:* Phone numbers & emails are protected by privacy. Actual contact details are NOT available via APIs."
    
    return msg

def detect_input_type(user_input: str) -> str:
    user_input = user_input.strip()
    
    if is_valid_ip(user_input):
        return 'ip'
    
    if is_valid_phone(user_input):
        return 'phone'
    
    return 'unknown'

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to IP & Phone Checker Bot!*\n\n"
        "Send me:\n"
        "• IP address (e.g. `8.8.8.8`)\n"
        "• Phone number (e.g. `+14155552671`)\n\n"
        "I'll fetch details from multiple sources.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send /start to see welcome message\n"
        "2. Send IP address or phone number\n"
        "3. I'll return information from multiple sources\n\n"
        "Examples:\n"
        "IP: `8.8.8.8`, `1.1.1.1`\n"
        "Phone: `+14155552671`, `+442071838750`",
        parse_mode='Markdown'
    )

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    input_type = detect_input_type(user_input)
    
    if input_type == 'unknown':
        await update.message.reply_text(
            "⚠️ Invalid input. Please send:\n"
            "• Valid IP address (e.g. `8.8.8.8`)\n"
            "• Valid phone number (e.g. `+1234567890`)",
            parse_mode='Markdown'
        )
        return
    
    if input_type == 'ip':
        await update.message.reply_text("🔍 Fetching IP information...")
        results = get_all_ip_info(user_input)
        await update.message.reply_text(format_ip_message(results), parse_mode='Markdown')
    
    elif input_type == 'phone':
        await update.message.reply_text("🔍 Fetching phone information...")
        results = get_all_phone_info(user_input)
        await update.message.reply_text(format_phone_message(results), parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def signal_handler(signum, frame):
    logger.info("Received shutdown signal, stopping bot...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(MessageHandler(filters.ALL, error_handler))

    logger.info("Bot starting...")
    app.run_polling(poll_interval=3)

if __name__ == '__main__':
    main()