# 📢 Steam Promo Bot - Functions & Changelog

## 🔄 Version: 2.0 (Updated on 2025-02-11)
### 🔧 Latest Changes:
- **Improved discount filtering:** Fixed an issue where discounts were not being correctly extracted.
- **Best Deals processing fixed:** Now reads directly from `history_promotions.json` and filters correctly.
- **Execution ID now always increments correctly.**
- **Manual stop implemented:** Allows stopping the bot with `CTRL+C`, clears history, and notifies Telegram.
- **Improved logging:** Better error handling for JSON parsing and message sending.

---

## 📜 **Bot Functions**
### 📢 Core Features:
1. **Function to process "Best Deals"** (`process_best_deals()`)  
   📌 Reads the promotions history, filters only games with a discount of **45% or more**, and saves them in `best_deals.json`.

2. **Function to extract promotions** (`extract_promotions()`)  
   📌 Scrapes the Steam promotions page and saves **all** found promotions to `history_promotions.json`.

3. **Function to clear history and best deals** (`clear_history()`)  
   📌 Runs `clear_history.py` to ensure all history and best deals are removed before a new run.

4. **Function to send messages to Telegram** (`send_telegram_message()`)  
   📌 Handles sending messages while **preventing flood errors** (includes retries and delay handling).

5. **Function to stop the bot manually** (`stop_bot()`)  
   📌 Allows stopping execution with **CTRL+C**, sends a shutdown message to Telegram, and clears history.

6. **Function to handle Telegram flood control** (`handle_flood_control()`)  
   📌 Detects if the Telegram API returns **"Too Many Requests"** and waits accordingly before retrying.

7. **Function to read and update execution ID** (`get_execution_id()` & `save_execution_id()`)  
   📌 Ensures **each bot run has a unique Execution ID**, which is displayed in logs and messages.

8. **Main function** (`check_and_send_promotions()`)  
   📌 Executes all steps:
   - Sends **initial search notification** to Telegram.
   - Extracts all promotions.
   - Processes Best Deals.
   - Sends all qualifying deals to Telegram.
   - Sends a **summary message** at the end with the number of deals found.

---

## 📢 **Bot Version Update Notifications**
Every time the bot is updated, it will send a message to Telegram:
