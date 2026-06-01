# آفاق Telegram Bot

## Setup in 4 steps

### Step 1 — Create your Telegram bot
1. Open Telegram, search for @BotFather
2. Send /newbot
3. Name it: Afaq Content Agent
4. Username: afaq_content_bot (or anything ending in _bot)
5. Copy the TOKEN it gives you

### Step 2 — Get your Anthropic API key
1. Go to console.anthropic.com
2. Create an API key
3. Copy it

### Step 3 — Deploy to Railway (free)
1. Go to railway.app and sign up
2. Click "New Project" → "Deploy from GitHub"
3. Upload this folder or connect your repo
4. Add environment variables:
   - TELEGRAM_TOKEN = your token from Step 1
   - ANTHROPIC_API_KEY = your key from Step 2
5. Railway gives you a public URL like: https://afaq-bot.up.railway.app

### Step 4 — Register webhook
Open this URL in your browser (replace YOUR_TOKEN and YOUR_URL):
https://api.telegram.org/botYOUR_TOKEN/setWebhook?url=https://YOUR_URL/

That's it. Your bot is live.

## Commands
/run ai       → Arabic script on AI & Technology
/run finance  → Arabic script on Finance & Wealth
/run geo      → Arabic script on Geopolitics
/run mindset  → Arabic script on Mindset & Habits
/run business → Arabic script on Business
/run          → Random pillar
/help         → Show commands

## Customization
Edit PILLAR_DATA in bot.py to add more episodes as you discover them.
