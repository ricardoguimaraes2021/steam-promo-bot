import json
import os
import logging

# 📢 File names
HISTORY_FILE = "history_promotions.json"
BEST_DEALS_FILE = "best_deals.json"
EXECUTION_ID_FILE = "execution_id.txt"

# 📢 Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("steam_promo_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def clear_history():
    """ Removes all stored promotions and recreates empty JSON files. """
    cleared_files = []

    for file in [HISTORY_FILE, BEST_DEALS_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
                logging.info(f"🗑️ Cleared {file} successfully.")
                cleared_files.append(file)
            except Exception as e:
                logging.error(f"❌ Error clearing {file}: {e}")
                print(f"❌ Error clearing {file}: {e}")
        else:
            logging.warning(f"⚠️ {file} not found. Creating an empty file.")
            with open(file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4, ensure_ascii=False)

    # Reset execution ID to 1
    try:
        with open(EXECUTION_ID_FILE, "w", encoding="utf-8") as f:
            f.write("1")
        logging.info("🔄 Execution ID reset to 1.")
    except Exception as e:
        logging.error(f"❌ Error resetting execution ID: {e}")
        print(f"❌ Error resetting execution ID: {e}")

    if cleared_files:
        print(f"✅ Successfully cleared: {', '.join(cleared_files)}")
    else:
        print("✅ No existing history found. Empty files created.")

if __name__ == "__main__":
    clear_history()
