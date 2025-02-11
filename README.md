# 🎮 Steam Promo Bot

This bot web scrapes Steam promotions and sends the best deals to a Telegram group. https://t.me/steampromos

## 📢 Features

- 🔍 **Automatic Search:** Automatically collects all Steam promotions.
- 🎯 **Discount Filter:** Only games with **45% or more** discount are considered as "Best Deals".
- 💾 **Promotion History:** Saves promotions locally to avoid duplicate submissions.
- 📢 **Send to Telegram:** Posts the best promotions directly to a Telegram group.
- 🚀 **Asynchronous Execution:** Uses `asyncio` for better performance when sending messages.
- 🛑 **Manual Stop:** Allows you to stop the bot and notifies the group about the interruption. - 🗑️ **Clear History:** Asks before each execution if the promotion history should be cleared.

## 🛠️ Technologies Used

- Python 🐍
- BeautifulSoup 🌐 (Web Scraping)
- Telegram Bot API 📲
- JSON 📄 (local storage)
- Asyncio ⚡ (asynchronous execution)

## 🚀 How to Use

1. **Clone the repository:**

```bash
git clone https://github.com/your-user/steam-promo-bot.git
cd steam-promo-bot
```

2. **Create a virtual environment and install the dependencies:**

```bash
python3 -m venv venv
source venv/bin/activate # For Linux/macOS
venv\\Scripts\\activate # For Windows

pip install -r requirements.txt
```

3. **Create a `.env` file with your Steam credentials Telegram:**

```ini
TELEGRAM_BOT_TOKEN=your-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

4. **Run the bot:**

```bash
python bot.py
```

## 🔄 Update History

### 🆕 Version 2.0 (02/11/2025)
- ✅ Ask before deleting the history before execution.
- ✅ Improvement in the extraction and filtering of discounts.
- ✅ Execution ID now always increments correctly.
- ✅ Implemented `CTRL+C` to stop the bot and send notification to Telegram.
- ✅ Improvements in logging and message control to avoid blocking by flood.

## 📝 License

This project is distributed under the MIT license. Feel free to modify and contribute! 🎉

---

Created by **Ricardo Guimarães** 🚀
