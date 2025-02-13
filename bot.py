import os
import requests
import asyncio
import logging
import json
import re
import time
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 📢 Load environment variables
load_dotenv()

# 📢 TELEGRAM CONFIGURATION
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 📢 FILTER CONFIGURATION
HISTORY_FILE = "historical_promotions.json"
BEST_DEALS_FILE = "best_deals.json"
EXECUTION_ID_FILE = "execution_id.txt"
DISCOUNT_FILTER = 45  # Apenas jogos com desconto ≥ 45%
MESSAGE_INTERVAL = 6  # Intervalo seguro entre mensagens (segundos)

# 📢 STEAM PROMOTION URL
STEAM_PROMO_URL = "https://store.steampowered.com/search/results/?query&specials=1"

# 📢 BOT CONFIGURATION
request = HTTPXRequest()
bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)

# 📢 LOGGING CONFIGURATION
LOG_FILE = "steam_promo_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 📢 BOT VERSION
BOT_VERSION = "2.1"

# 📢 Notify Telegram about version update
async def send_version_notification():
    message = f"🚀 Steam Promo Bot - Version {BOT_VERSION} is now running!"
    await send_telegram_message(message)

# 📢 Get Execution ID
def get_execution_id():
    if os.path.exists(EXECUTION_ID_FILE):
        try:
            with open(EXECUTION_ID_FILE, "r") as f:
                return int(f.read().strip())  
        except ValueError:
            return 1  
    return 1  

# 📢 Update Execution ID
def save_execution_id(exec_id):
    with open(EXECUTION_ID_FILE, "w") as f:
        f.write(str(exec_id))

# 📢 Load history
def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("⚠️ History file not found or corrupted. Creating a new one.")
        return {}

# 📢 Load previously sent best deals
def load_best_deals():
    try:
        with open(BEST_DEALS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("⚠️ Best deals file not found or corrupted. Creating a new one.")
        return {}

# 📢 Extract promotions from Steam
def extract_promotions():
    history = load_history()

    response = requests.get(STEAM_PROMO_URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        logging.error(f"Error accessing Steam: {response.status_code}")
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    games = {}

    for item in soup.select('.search_result_row'):
        try:
            title = item.select_one('.title').text.strip()
            discount_element = item.select_one('.discount_pct')
            original_price_element = item.select_one('.discount_original_price')
            current_price_element = item.select_one('.discount_final_price')

            discount_text = discount_element.text.strip() if discount_element else "0%"
            original_price = original_price_element.text.strip().replace('€', '').replace(',', '.').replace(' ', '') if original_price_element else "N/A"
            current_price = current_price_element.text.strip().replace('€', '').replace(',', '.').replace(' ', '') if current_price_element else "N/A"

            games[title] = {
                "name": title,
                "discount": discount_text,
                "original_price": f"{original_price}€",
                "current_price": f"{current_price}€",
                "link": item["href"],
                "already_sent": False  
            }
        except Exception as e:
            logging.warning(f"Error processing item: {e}")

    history.update(games)

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

    logging.info(f"✅ Promotions saved successfully ({len(games)} new promotions).")
    return games

# 📢 Send messages to Telegram
async def send_telegram_message(message):
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.HTML
            )
            logging.info(f"✅ Message successfully sent on attempt {attempt}!")
            return True
        except Exception as e:
            logging.error(f"❌ Error sending message (attempt {attempt}): {e}")
            await asyncio.sleep(5)

    logging.error(f"❌ Failed to send message after {max_attempts} attempts.")
    return False

# 📢 Process Best Deals and send only new promotions
async def process_best_deals():
    execution_id = get_execution_id() + 1
    history = load_history()
    previous_best_deals = load_best_deals()

    best_deals = {
        title: data for title, data in history.items()
        if "N/A" not in data["original_price"]
        and int(''.join(filter(str.isdigit, data["discount"]))) >= DISCOUNT_FILTER
    }

    new_deals = {}
    for title, deal in best_deals.items():
        if title not in previous_best_deals:
            new_deals[title] = deal
        elif previous_best_deals[title]["discount"] != deal["discount"]:
            new_deals[title] = deal

    if not new_deals:
        logging.info("❌ No new promotions found. No messages will be sent.")
        return

    for title, deal in new_deals.items():
        message = f"🎮 <b>{deal['name']}</b> - {deal['discount']} 🔗 <a href='{deal['link']}'>View</a>"
        sent = await send_telegram_message(message)
        if sent:
            previous_best_deals[title] = deal
        await asyncio.sleep(MESSAGE_INTERVAL)

    with open(BEST_DEALS_FILE, "w", encoding="utf-8") as file:
        json.dump(previous_best_deals, file, indent=4, ensure_ascii=False)

    save_execution_id(execution_id)

# 📢 Main function
async def check_and_send_promotions():
    await send_version_notification()
    extract_promotions()
    await process_best_deals()

if __name__ == "__main__":
    asyncio.run(check_and_send_promotions())