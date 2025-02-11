import os
import requests
import asyncio
import logging
import json
import re
import signal
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
DISCOUNT_FILTER = 45  # Only games with discount ≥ 45%
MESSAGE_INTERVAL = 6  # Safe interval between messages (seconds)
STOPPED_MANUALLY = False  # Flag for manual stop

# 📢 STEAM PROMOTION URL
STEAM_PROMO_URL = "https://store.steampowered.com/search/results/?query&specials=1"

# 📢 Bot configuration
request = HTTPXRequest()
bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)

# 📢 Logging configuration
LOG_FILE = "steam_promo_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 📢 Get Execution ID
def get_execution_id():
    if os.path.exists(EXECUTION_ID_FILE):
        try:
            with open(EXECUTION_ID_FILE, "r") as f:
                return int(f.read().strip())  # Lê o ID atual do ficheiro
        except ValueError:
            return 1  # Se o ficheiro estiver corrompido, inicia em 1
    return 1  # Se não existir, inicia em 1

# 📢 Update Execution ID (Agora atualizado no final da execução)
def save_execution_id(exec_id):
    with open(EXECUTION_ID_FILE, "w") as f:
        f.write(str(exec_id))

# 📢 Load history to avoid resending the same promotions
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.warning("⚠️ History file is corrupted. Creating a new one.")
    return {}

# 📢 Function to clear history and best deals
def clear_history():
    open(HISTORY_FILE, 'w').close()
    open(BEST_DEALS_FILE, 'w').close()
    logging.info("🗑️ Promotion history and best deals cleared successfully.")

# 📢 Handle Telegram flood control
async def handle_flood_control(error_message):
    match = re.search(r"Retry in (\d+) seconds", str(error_message))
    if match:
        wait_time = int(match.group(1))
        logging.warning(f"⚠️ Flood control activated! Waiting {wait_time} seconds before retrying...")
        await asyncio.sleep(wait_time)
    else:
        logging.warning("⚠️ No flood wait time specified. Waiting 30 seconds as a precaution...")
        await asyncio.sleep(30)

# 📢 Send messages to Telegram with flood control handling
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

            if "Too Many Requests" in str(e) or "Timed out" in str(e):
                await handle_flood_control(e)
            else:
                break  

    logging.error(f"❌ Failed to send message after {max_attempts} attempts.")
    return False

# 📢 Extract promotions from Steam and preserve history
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
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logging.warning(f"Error processing item: {e}")

    # Merge history to avoid duplicate entries
    history.update(games)

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

    logging.info(f"✅ Promotions saved successfully ({len(games)} new promotions).")
    return games

# 📢 Load previously sent best deals
def load_best_deals():
    if os.path.exists(BEST_DEALS_FILE):
        try:
            with open(BEST_DEALS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.warning("⚠️ Best deals file is corrupted. Creating a new one.")
    return {}

# 📢 Process Best Deals and send only new promotions
async def process_best_deals():
    execution_id = get_execution_id() + 1  # 🔥 Incrementa o ID da execução
    history = load_history()
    previous_best_deals = load_best_deals()

    best_deals = {
        title: data for title, data in history.items()
        if "N/A" not in data["original_price"]
        and int(''.join(filter(str.isdigit, data["discount"]))) >= DISCOUNT_FILTER
    }

    # 🔥 Comparação aprimorada para evitar reenvio de promoções já enviadas
    new_deals = {
        k: v for k, v in best_deals.items()
        if k not in previous_best_deals or previous_best_deals[k]["discount"] != v["discount"]
    }

    if not new_deals:
        logging.info("❌ No new promotions found. No messages will be sent.")
        await send_summary_message(execution_id, 0)  # 🔥 Usa a função para enviar resumo
        return

    with open(BEST_DEALS_FILE, "w", encoding="utf-8") as file:
        json.dump(best_deals, file, indent=4, ensure_ascii=False)

    save_execution_id(execution_id)  # 🔥 Agora salvamos o novo ID no final

    # 📢 Enviar cada nova promoção individualmente
    for title, deal in new_deals.items():
        message = (
            f"🎮 <b>{deal['name']}</b>\n"
            f"💰 Original Price: <s>{deal['original_price']}</s>\n"
            f"🔥 Current Price: {deal['current_price']}\n"
            f"🛍️ Discount: {deal['discount']}\n"
            f"🔗 <a href='{deal['link']}'>View on Steam</a>\n"
        )
        await send_telegram_message(message)
        await asyncio.sleep(MESSAGE_INTERVAL)

    # 📢 Enviar mensagem final com o resumo da execução
    await send_summary_message(execution_id, len(new_deals))



# 📢 Main function
async def check_and_send_promotions():
    execution_id = get_execution_id() + 1  # 🔥 Atualiza o ID da execução no início
    save_execution_id(execution_id)

    logging.info(f"🚀 Running execution ID: {execution_id}")

    extract_promotions()
    await process_best_deals()

if __name__ == "__main__":
    asyncio.run(check_and_send_promotions())
