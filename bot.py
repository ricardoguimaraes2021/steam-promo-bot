import os
import requests
import asyncio
import logging
import json
import re
import signal
import subprocess
import time
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 📢 Carregar variáveis do ambiente
load_dotenv()

# 📢 CONFIGURAÇÃO DO TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 📢 CONFIGURAÇÕES DO FILTRO
HISTORY_FILE = "historical_promotions.json"
BEST_DEALS_FILE = "best_deals.json"
EXECUTION_ID_FILE = "execution_id.txt"
DISCOUNT_FILTER = 45  # Apenas jogos com desconto ≥ 45%
MESSAGE_INTERVAL = 6  # Intervalo seguro entre mensagens (segundos)
STOPPED_MANUALLY = False  # Flag para parar manualmente

# 📢 URL das promoções na Steam
STEAM_PROMO_URL = "https://store.steampowered.com/search/results/?query&specials=1"

# 📢 Configuração do bot
request = HTTPXRequest()
bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)

# 📢 Configuração dos logs
LOG_FILE = "steam_promo_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 📢 Função para obter Execution ID
def get_execution_id():
    if os.path.exists(EXECUTION_ID_FILE):
        with open(EXECUTION_ID_FILE, "r") as f:
            return int(f.read().strip()) + 1
    return 1

# 📢 Função para atualizar Execution ID
def save_execution_id(exec_id):
    with open(EXECUTION_ID_FILE, "w") as f:
        f.write(str(exec_id))

EXECUTION_ID = get_execution_id()
save_execution_id(EXECUTION_ID)

# 📢 Perguntar antes de limpar histórico
def ask_clear_history():
    choice = input("🛑 Do you want to clear the promotions history before running the bot? (y/n) ").strip().lower()
    return choice == "y"

# 📢 Função para limpar histórico e best deals
def clear_history():
    try:
        open(HISTORY_FILE, 'w').close()
        open(BEST_DEALS_FILE, 'w').close()
        logging.info("🗑️ Promotion history and best deals cleared successfully.")
    except Exception as e:
        logging.error(f"❌ Error clearing history: {e}")

# 📢 Captura do tempo de espera do erro 429 (Telegram Flood Control)
async def handle_flood_control(error_message):
    match = re.search(r"Retry in (\d+) seconds", str(error_message))
    if match:
        wait_time = int(match.group(1))
        logging.warning(f"⚠️ Flood control activated! Waiting {wait_time} seconds before retrying...")
        await asyncio.sleep(wait_time)
    else:
        logging.warning("⚠️ No flood wait time specified. Waiting 30 seconds as a precaution...")
        await asyncio.sleep(30)

# 📢 Envio de mensagens para o Telegram com controle de flood
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

# 📢 Função para parar o bot manualmente
def stop_bot(signum, frame):
    """Stops the bot manually, sends a message, clears Best Deals, and runs the history cleaner."""
    global STOPPED_MANUALLY
    STOPPED_MANUALLY = True
    logging.warning("🚨 Bot execution manually stopped! Clearing history and best deals...")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_telegram_message(
        f"🚨 <b>Bot Execution Stopped!</b>\n"
        f"📌 Bot Execution ID: {EXECUTION_ID}\n"
        f"🗑️ All Best Deals and Promotion History have been deleted automatically.\n"
        f"🕒 Stopped at: {datetime.now().strftime('%d/%m/%Y - %H:%M')}"
    ))

    clear_history()
    logging.info("✅ Bot stopped, history cleared, and best deals deleted.")
    exit(0)

# 📢 Vincular SIGINT (CTRL+C) à função de parada
signal.signal(signal.SIGINT, stop_bot)

# 📢 Captura de promoções da Steam
def extract_promotions():
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

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(games, file, indent=4, ensure_ascii=False)

    logging.info(f"✅ Promotions saved successfully ({len(games)} promotions).")
    return games

# 📢 Processamento das melhores promoções
async def process_best_deals():
    if not os.path.exists(HISTORY_FILE):
        logging.warning("⚠️ History file not found. No promotions processed.")
        return {}

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        promotions = json.load(file)

    best_deals = {
        title: data for title, data in promotions.items()
        if "N/A" not in data["original_price"]
        and int(''.join(filter(str.isdigit, data["discount"]))) >= DISCOUNT_FILTER
    }

    with open(BEST_DEALS_FILE, "w", encoding="utf-8") as file:
        json.dump(best_deals, file, indent=4, ensure_ascii=False)

    logging.info(f"✅ Best Deals saved successfully ({len(best_deals)} promotions).")

    for title, deal in best_deals.items():
        message = (
            f"🎮 <b>{deal['name']}</b>\n"
            f"💰 Preço Original: <s>{deal['original_price']}</s>\n"
            f"🔥 Preço Atual: {deal['current_price']}\n"
            f"🛍️ Desconto: {deal['discount']}\n"
            f"🔗 <a href='{deal['link']}'>Ver na Steam</a>\n"
        )
        await send_telegram_message(message)
        await asyncio.sleep(MESSAGE_INTERVAL)

# 📢 Função principal
async def check_and_send_promotions():
    if ask_clear_history():
        clear_history()
        await send_telegram_message("🗑️ Promotions history has been cleared. The bot will start fresh.")

    extract_promotions()
    await process_best_deals()

if __name__ == "__main__":
    asyncio.run(check_and_send_promotions())
