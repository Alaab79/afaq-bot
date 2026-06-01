import os
import json
import random
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "YOUR_KEY_HERE")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

PILLAR_DATA = {
    "ai": {
        "label": "AI & Technology",
        "episodes": [
            {"source": "Lex Fridman", "episode": "Sam Altman — OpenAI, GPT-5, AGI and the Future", "views": "8M+",
             "ideas": "AGI is closer than people think · AI will create abundance but also displacement · OpenAI safety vs speed tension · What jobs survive AI · The importance of AI alignment"},
            {"source": "Lex Fridman", "episode": "Sundar Pichai — Google, AI, and the Future", "views": "8M+",
             "ideas": "AI is the most profound tech shift in history · Gemini vs GPT competition · AI changing how we search · Responsibility of AI companies · Impact on all industries"},
            {"source": "Lex Fridman", "episode": "Yuval Noah Harari — AI, Power and Humanity", "views": "5M+",
             "ideas": "AI can hack human psychology at scale · Who controls the algorithm controls society · Democracy threatened by AI propaganda · Humans need new stories for the AI age"},
        ]
    },
    "finance": {
        "label": "Finance & Wealth",
        "episodes": [
            {"source": "Diary of a CEO", "episode": "Nischa Shah — The Truth About Money", "views": "5M+",
             "ideas": "Pay yourself first · 65-20-15 money framework · Compound interest is the most powerful force · Why saving in a bank makes you poorer · Difference between assets and liabilities"},
            {"source": "Diary of a CEO", "episode": "Ramit Sethi — Common Financial Mistakes", "views": "6M+",
             "ideas": "Buying a house is not always a good investment · Money psychology matters more than math · Lifestyle inflation is the silent wealth killer · Automate finances · Rich people focus on big wins"},
        ]
    },
    "geo": {
        "label": "Geopolitics",
        "episodes": [
            {"source": "Peter Zeihan", "episode": "China's Fall and the End of Globalization", "views": "4M+",
             "ideas": "China demographics mean it gets old before rich · US reshoring manufacturing · Global supply chains ending · Energy independence as strategic weapon · Middle East must diversify faster"},
            {"source": "All-In Podcast", "episode": "The New World Order — AI and Energy Shifts", "views": "3M+",
             "ideas": "AI is the new oil · Gulf states making right bets on AI · Petrodollar system eroding · Vision 2030 most ambitious national transformation ever · Gulf has narrow window to diversify"},
        ]
    },
    "mindset": {
        "label": "Mindset & Habits",
        "episodes": [
            {"source": "Diary of a CEO", "episode": "James Clear — Atomic Habits", "views": "7M+",
             "ideas": "You don't rise to goals you fall to systems · 1% better daily = 37x in a year · Identity is foundation of habits · Make habits obvious attractive easy satisfying · Environment design beats willpower"},
        ]
    },
    "business": {
        "label": "Business & Entrepreneurship",
        "episodes": [
            {"source": "My First Million", "episode": "Business Ideas That Made Millions", "views": "4M+",
             "ideas": "Best businesses solve one specific problem · Distribution more important than product · Boring businesses make more money · Starting costs almost nothing with AI tools · First idea will fail — iterate fast"},
        ]
    },
}

HELP_TEXT = """
🌐 *آفاق Content Agent*

مرحباً! أنا وكيلك الذكي لإنتاج محتوى قناة آفاق.

*الأوامر المتاحة:*
/run ai — نص عن الذكاء الاصطناعي
/run finance — نص عن المال والاستثمار
/run geo — نص عن الجيوسياسة
/run mindset — نص عن العقلية والعادات
/run business — نص عن الأعمال
/run — نص عشوائي من أي محور
/help — عرض هذه المساعدة

*مثال:* أرسل `/run finance` واحصل على نص كامل جاهز للتسجيل في ElevenLabs خلال دقيقتين.
"""

def send_message(chat_id, text, parse_mode="Markdown"):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    })

def send_typing(chat_id):
    requests.post(f"{TELEGRAM_API}/sendChatAction", json={
        "chat_id": chat_id,
        "action": "typing"
    })

def call_claude(system, user):
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json",
                 "x-api-key": ANTHROPIC_KEY,
                 "anthropic-version": "2023-06-01"},
        json={"model": "claude-sonnet-4-20250514",
              "max_tokens": 1000,
              "system": system,
              "messages": [{"role": "user", "content": user}]})
    data = r.json()
    return "".join(b["text"] for b in data.get("content", []) if b["type"] == "text")

def run_agent(chat_id, pillar_key):
    if pillar_key == "random" or pillar_key not in PILLAR_DATA:
        pillar_key = random.choice(list(PILLAR_DATA.keys()))

    pillar = PILLAR_DATA[pillar_key]
    ep = random.choice(pillar["episodes"])

    send_typing(chat_id)
    send_message(chat_id, f"⚙️ *تشغيل الوكيل...*\n\nالمحور: {pillar['label']}\nالمصدر: {ep['source']} — {ep['episode']} ({ep['views']} مشاهدة)\n\n_جارٍ توليد النص العربي..._")

    script = call_claude(
        "أنت كاتب محتوى لقناة آفاق على يوتيوب. تكتب بالعربية الفصحى المبسطة. ابدأ بخطاف قوي (15 ثانية)، ثم مقدمة، ثم 4-5 نقاط مع سياق خليجي وعربي، ثم دعوة للاشتراك. اكتب النص فقط بدون تعليقات.",
        f"المحور: {pillar['label']}\nالحلقة: {ep['episode']} ({ep['source']})\nالأفكار الأساسية: {ep['ideas']}\n\nاكتب نصاً عربياً أصيلاً بمدة 6-8 دقائق مع إضافة أمثلة خليجية وعربية محددة."
    )

    title = call_claude(
        "أنت خبير SEO يوتيوب عربي. أعط عنواناً يوتيوب عربياً جذاباً فقط (بدون أي نص آخر، 60 حرفاً كحد أقصى).",
        f"المحور: {pillar['label']}\nالنص: {script[:300]}"
    )

    output = f"""
✅ *النص جاهز!*

📺 *العنوان المقترح:*
{title.strip()}

📝 *النص الكامل:*
{script[:3000]}{"..." if len(script) > 3000 else ""}

🎙 *ElevenLabs:* صوت عربي هادئ، سرعة أبطأ من الافتراضي قليلاً
🎬 *CapCut:* فعّل الترجمة العربية التلقائية
📌 *المصدر:* {ep['source']} — {ep['episode']}
    """

    send_message(chat_id, output.strip())

def handle_update(update):
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip().lower()

    if not chat_id or not text:
        return

    if text in ["/start", "/help"]:
        send_message(chat_id, HELP_TEXT)
    elif text == "/run":
        run_agent(chat_id, "random")
    elif text.startswith("/run "):
        pillar = text.split(" ", 1)[1].strip()
        run_agent(chat_id, pillar)
    else:
        send_message(chat_id, "أرسل /help لرؤية الأوامر المتاحة.")

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        try:
            update = json.loads(body)
            handle_update(update)
        except Exception as e:
            print(f"Error: {e}")

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting آفاق bot on port {port}...")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
