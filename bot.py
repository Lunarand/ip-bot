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

INDIA_OPERATORS = {
    'Reliance Jio': ['639', '638', '637', '636', '635', '634', '633', '632', '631', '630', '629', '628', '627', '626', '625', '624', '623', '622', '621', '620', '619', '618', '617', '616', '615', '614', '613', '612', '611', '609', '608', '607', '606', '605', '604', '603', '602', '601'],
    'Airtel': ['999', '998', '997', '996', '995', '994', '993', '992', '991', '990', '989', '988', '987', '986', '985', '984', '983', '982', '981', '980', '979', '978', '977', '976', '975', '974', '973', '972', '971', '970', '969', '968', '967', '966', '965', '964', '963', '962', '961', '960', '959', '958', '957', '956', '955', '954', '953', '952', '951', '950'],
    'Vi (Vodafone Idea)': ['9998', '9997', '9996', '9995', '9994', '9993', '9992', '9991', '9990', '9989', '9988', '9987', '9986', '9985', '9984', '9983', '9982', '9981', '9980'],
    'BSNL': ['944', '943', '942', '941', '940', '939', '938', '937', '936', '935', '934', '933', '932', '931', '930', '829', '828', '827', '826', '825', '824', '823', '822', '821', '820', '819', '818', '817', '816', '815', '814', '813', '812', '811', '810'],
    'MTNL': ['996', '995', '994', '993', '992', '991', '990'],
}

def get_indian_operator(phone: str) -> dict:
    phone = re.sub(r'[^0-9]', '', phone)
    if not phone.startswith('91') or len(phone) < 12:
        return None
    
    number_without_91 = phone[2:5]
    
    for operator, prefixes in INDIA_OPERATORS.items():
        if number_without_91[:3] in prefixes or number_without_91[:4] in prefixes:
            return {'operator': operator, 'source': 'Indian STD Codes'}
    
    return {'operator': 'Unknown', 'source': 'Indian STD Codes'}

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
    if data and data.get('ip'):
        return {
            'source': 'ipapi.co',
            'ip': data.get('ip'),
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
    if data and data.get('success') != False and data.get('ip'):
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

def get_all_ip_info(ip: str) -> list:
    results = []
    funcs = [get_ipapi_com, get_ipapi_co, get_ipwhois_io]
    for func in funcs:
        try:
            result = func(ip)
            if result and len(result) > 1:
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
    if data.get('lat') and data.get('lon'):
        parts.append(f"🗺️ **Coordinates:** {data.get('lat')}, {data.get('lon')}")
    if data.get('timezone'):
        parts.append(f"🌍 **Timezone:** {data.get('timezone', 'N/A')}")
    parts.append(f"🏢 **ISP:** {data.get('isp', 'N/A')}")
    if data.get('org'):
        parts.append(f"🏢 **Org:** {data.get('org', 'N/A')}")
    if data.get('asn'):
        parts.append(f"🔢 **ASN:** {data.get('asn', 'N/A')}")
    return '\n'.join(parts)

def format_ip_message(results: list) -> str:
    if not results:
        return "❌ Could not fetch IP information."

    msg = "📊 *IP Lookup Results (Multiple Sources)*\n\n"
    
    for i, data in enumerate(results, 1):
        msg += f"{'━'*30}\n"
        msg += f"Source {i}: {data.get('source')}\n"
        msg += f"{'━'*30}\n"
        msg += format_source_result(data) + "\n\n"
    
    return msg

def get_calltracer_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    if not clean.startswith('+'):
        clean = '+' + clean
    
    data = fetch_url(f'https://calltracer.io/api/lookup/{clean}')
    if data and data.get('number'):
        return {
            'source': 'calltracer.io',
            'number': data.get('number'),
            'international': data.get('international'),
            'national': data.get('national'),
            'country_code': data.get('country_code'),
            'country': data.get('country'),
            'number_type': data.get('number_type'),
            'carrier': data.get('carrier'),
            'location': data.get('location'),
            'is_valid': data.get('is_valid'),
            'spam_total': data.get('reports', {}).get('total'),
            'spam_score': data.get('reports', {}).get('spam_score'),
        }
    return None

def get_phonenumber_api_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    data = fetch_url(f'http://phone-number-api.com/json/?number={clean}')
    if data and data.get('status') == 'success':
        return {
            'source': 'phone-number-api.com',
            'number_type': data.get('numberType'),
            'valid': data.get('numberValid'),
            'country_code': data.get('numberCountryCode'),
            'area_code': data.get('numberAreaCode'),
            'format_e164': data.get('formatE164'),
            'format_national': data.get('formatNational'),
            'country': data.get('country'),
            'country_name': data.get('countryName'),
            'region_name': data.get('regionName'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'timezone': data.get('timezone'),
            'currency': data.get('currency'),
        }
    return None

def get_libphonenumber_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    data = fetch_url(f'https://libphonenumberapi.com/api/phone-numbers/{clean}')
    if data and data.get('is_valid') is not None:
        return {
            'source': 'libphonenumberapi.com',
            'valid': data.get('is_valid'),
            'type': data.get('type'),
            'carrier': data.get('carrier'),
            'geo_name': data.get('geo_name'),
            'country': data.get('country'),
            'e164': data.get('formats', {}).get('e164'),
            'international': data.get('formats', {}).get('international'),
        }
    return None

def get_simowner_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    if len(clean) == 12:
        clean = clean[2:]
    
    try:
        url = f'https://simownerapp.com/api/phone/{clean}'
        data = fetch_url(url)
        if data and data.get('name'):
            return {
                'source': 'simownerapp.com',
                'name': data.get('name'),
                'operator': data.get('operator'),
                'circle': data.get('circle'),
                'state': data.get('state'),
                'type': data.get('type'),
            }
    except:
        pass
    
    html = fetch_text(f'https://simownerapp.com/reverse-phone-lookup?number={clean}')
    if html:
        name_match = re.search(r'(?:Owner|Name|Caller)[:\s]*([A-Z][a-zA-Z\s]{2,30})', html, re.IGNORECASE)
        if name_match:
            return {
                'source': 'simownerapp.com',
                'name': name_match.group(1).strip(),
                'note': 'Name found via search'
            }
    return None

def get_phonenumbertracker_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    if len(clean) == 12:
        clean = clean[2:]
    
    html = fetch_text(f'https://www.phonenumbertracker.com/phone-number/{clean}')
    if html:
        name_match = re.search(r'Owner[:\s]*([A-Z][a-zA-Z\s]{2,30})', html, re.IGNORECASE)
        operator_match = re.search(r'Service Provider[:\s]*([A-Za-z\s]+)', html, re.IGNORECASE)
        location_match = re.search(r'Location[:\s]*([A-Za-z\s,\-]+)', html, re.IGNORECASE)
        
        if name_match or operator_match or location_match:
            result = {'source': 'phonenumbertracker.com'}
            if name_match:
                result['name'] = name_match.group(1).strip()
            if operator_match:
                result['operator'] = operator_match.group(1).strip()
            if location_match:
                result['location'] = location_match.group(1).strip()
            return result
    return None

def get_indiantrace_info(phone: str) -> dict:
    clean = re.sub(r'[^0-9]', '', phone)
    if len(clean) == 12:
        clean = clean[2:]
    
    html = fetch_text(f'https://www.indiantrace.com/trace-mobile-number/{clean}')
    if html:
        name_match = re.search(r'(?:Name|Owner)[:\s]*([A-Za-z\s]{3,40})', html, re.IGNORECASE)
        operator_match = re.search(r'(?:Operator|Network)[:\s]*([A-Za-z\s]+)', html, re.IGNORECASE)
        location_match = re.search(r'(?:Location|Circle)[:\s]*([A-Za-z\s]+)', html, re.IGNORECASE)
        
        if name_match or operator_match:
            result = {'source': 'indiantrace.com'}
            if name_match:
                result['name'] = name_match.group(1).strip()
            if operator_match:
                result['operator'] = operator_match.group(1).strip()
            if location_match:
                result['circle'] = location_match.group(1).strip()
            return result
    return None

def get_all_phone_info(phone: str) -> list:
    results = []
    cleaned = clean_phone(phone)
    
    funcs = [get_calltracer_info, get_phonenumber_api_info, get_libphonenumber_info]
    for func in funcs:
        try:
            result = func(cleaned)
            if result and len(result) > 1:
                results.append(result)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
    
    if cleaned.startswith('91') and len(cleaned) >= 12:
        try:
            sim_result = get_simowner_info(cleaned)
            if sim_result:
                results.append(sim_result)
        except Exception as e:
            logger.error(f"Error in simowner: {e}")
        
        try:
            trace_result = get_indiantrace_info(cleaned)
            if trace_result:
                results.append(trace_result)
        except Exception as e:
            logger.error(f"Error in indiantrace: {e}")
        
        operator_info = get_indian_operator(cleaned)
        if operator_info:
            results.append(operator_info)
    
    if not results:
        basic_info = {
            'source': 'Basic Parser',
            'number': cleaned,
            'note': 'No results found. Try again later.'
        }
        results.append(basic_info)
    
    return results

def format_phone_result(data: dict) -> str:
    parts = [f"📡 *Source: {data.get('source')}*"]
    
    if data.get('note'):
        parts.append(f"📝 {data.get('note')}")
    
    if data.get('is_valid') is not None:
        parts.append(f"✅ **Valid:** {'Yes' if data.get('is_valid') else 'No'}")
    if data.get('valid') is not None:
        parts.append(f"✅ **Valid:** {'Yes' if data.get('valid') else 'No'}")
    
    if data.get('name'):
        parts.append(f"👤 **Name:** {data.get('name')}")
    
    parts.append(f"📱 **Number:** `{data.get('number') or data.get('e164') or data.get('international') or data.get('phone') or 'N/A'}`")
    
    country = data.get('country') or data.get('country_name')
    if country:
        parts.append(f"🇮🇳 **Country:** {country}")
    if data.get('country_code'):
        parts.append(f"🏳️ **Code:** +{data.get('country_code')}")
    
    if data.get('circle') or data.get('state') or data.get('region_name'):
        parts.append(f"📍 **Circle:** {data.get('circle') or data.get('state') or data.get('region_name')}")
    if data.get('city') or data.get('location') or data.get('geo_name'):
        parts.append(f"🏙️ **City:** {data.get('city') or data.get('location') or data.get('geo_name')}")
    
    if data.get('operator') or data.get('carrier'):
        parts.append(f"🏢 **Operator:** {data.get('operator') or data.get('carrier', 'N/A')}")
    
    if data.get('number_type') or data.get('type'):
        parts.append(f"📱 **Type:** {data.get('number_type') or data.get('type', 'N/A')}")
    
    if data.get('spam_total') is not None:
        parts.append(f"⚠️ **Reports:** {data.get('spam_total', 'N/A')}")
    if data.get('spam_score') is not None:
        parts.append(f"📊 **Spam:** {data.get('spam_score', 'N/A')}")
    
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
    
    name_found = any(d.get('name') for d in results)
    if not name_found:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📝 *Note:* Name lookup is limited. For full details, use Truecaller app directly."
    
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
        "• Phone number (e.g. `+919876543210`)\n\n"
        "I'll try to get name, operator & location for Indian numbers!",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send /start to see welcome message\n"
        "2. Send IP address or phone number\n"
        "3. I'll return available information\n\n"
        "For Indian numbers (+91), tries to get:\n"
        "• Name (if available in public databases)\n"
        "• Operator (Jio/Airtel/Vi/BSNL)\n"
        "• Circle/Location",
        parse_mode='Markdown'
    )

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    input_type = detect_input_type(user_input)
    
    if input_type == 'unknown':
        await update.message.reply_text(
            "⚠️ Invalid input. Please send:\n"
            "• Valid IP address (e.g. `8.8.8.8`)\n"
            "• Valid phone number (e.g. `+919876543210`)",
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