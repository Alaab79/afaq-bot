import os
import json
import random
import requests
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

PILLAR_DATA = {
    "ai": {
        "label": "AI & Technology",
        "episodes": [
            {"source": "Lex Fridman", "episode": "Sam Altman — OpenAI, GPT-5, AGI and the Future", "views": "8M+",
             "ideas": "AGI is closer than people think · AI will create abundance but also displacement · OpenAI safety vs speed tension · What jobs survive AI · The importance of AI alignment"},
            {"source": "Lex Fridman", "episode": "Sundar Pichai — Google, AI, and the Future", "views": "8M+",
             "ideas": "AI is the most profound tech shift in history · Gemini vs GPT competition · AI changing how we search · Responsibility of AI companies · Impact on all industries"},
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

HELP_TEXT = """مرحباً! أنا وكيل آفاق لإنتاج المحتوى.

الأوامر المتاحة:
/run ai
/run finance
/run geo
/run mindset
/run business
/run — نص عشوائي
/help — المساعدة"""

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
        log(f"send_message status: {r.status_code}")
    except Exception as e:
        log(f"send_message error: {e}")

def send_typing(chat_id):
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction", json={
            "chat_id": chat_id,
            "action": "typing"
        }, timeout=5)
    except Exception as e:
        log(f"send_typing error: {e}")

def call_claude(system, user):
    log("Calling Groq API...")
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_KEY}"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 4000,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        },
        timeout=60
    )
    log(f"Groq API status: {r.status_code}")
    data = r.json()
    try:
        result = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        log(f"Groq parse error: {data}")
        result = ""
    log(f"Groq response length: {len(result)}")
    return result

def run_agent(chat_id, pillar_key):
    log(f"run_agent called with pillar: {pillar_key}")

    if pillar_key == "random" or pillar_key not in PILLAR_DATA:
        pillar_key = random.choice(list(PILLAR_DATA.keys()))

    pillar = PILLAR_DATA[pillar_key]
    ep = random.choice(pillar["episodes"])

    send_typing(chat_id)
    send_message(chat_id, f"جارٍ توليد النص...\n\nالمحور: {pillar['label']}\nالمصدر: {ep['source']}")

    try:
        script = call_claude(
            """أنت كاتب محتوى محترف لقناة آفاق على يوتيوب. مهمتك كتابة نصوص عربية استثنائية تجعل المشاهد يتوقف عن التمرير.

قواعد الكتابة:
- اكتب بالعربية الفصحى المبسطة — واضحة كالحديث اليومي لكن راقية كالإعلام المحترف
- تجنب الجمل الطويلة — جملة قصيرة. توقف. ثم جملة أخرى. هذا الإيقاع يشد المستمع
- لا تبدأ بـ "في هذا الفيديو" أو "مرحباً بكم" — ابدأ بصدمة أو سؤال أو إحصائية مدهشة
- أضف أمثلة حقيقية من السعودية والإمارات والأردن ومصر
- اربط الأفكار بالواقع العربي — غلاء المعيشة، سوق العمل، رؤية 2030، جيل Z العربي
- كل نقطة يجب أن تحتوي على: الفكرة + دليل أو مثال + تطبيق عملي للمشاهب العربي

هيكل النص الإلزامي:
[خطاف] — جملتان مدهشتان تجعل المشاهد يتوقف (15 ثانية)
[مقدمة] — ما ستتعلمه وليه مهم لك أنت كعربي تحديداً (30 ثانية)
[نقطة 1] — الفكرة + مثال عربي + تطبيق عملي
[نقطة 2] — الفكرة + مثال عربي + تطبيق عملي
[نقطة 3] — الفكرة + مثال عربي + تطبيق عملي
[نقطة 4] — الفكرة + مثال عربي + تطبيق عملي
[خلاصة] — 3 جمل تلخص أهم درس
[دعوة] — اشترك في القناة، فيديو جديد كل أسبوع

اكتب النص فقط بدون تعليقات أو عناوين الأقسام.""",
            f"المحور: {pillar['label']}\nالمصدر: {ep['source']} — {ep['episode']}\nالأفكار الأساسية: {ep['ideas']}\n\nاكتب نصاً عربياً أصيلاً مدته 7 دقائق. لا تترجم — أعد صياغة الأفكار بأسلوبك مع إضافة سياق عربي حقيقي وأمثلة من منطقتنا."
        )

        title = call_claude(
            """أنت خبير SEO يوتيوب عربي. اكتب عنواناً يوتيوب واحداً فقط بدون أي نص إضافي.
قواعد العنوان الجيد:
- يثير فضول المشاهب ويجعله يريد النقر فوراً
- يحتوي على رقم أو سؤال أو وعد واضح
- لا يتجاوز 60 حرفاً
- بالعربية الفصحى المبسطة
مثال جيد: كيف تحفظ ٢٠٪ من راتبك حتى لو كان محدوداً
مثال سيء: فيديو عن المال والادخار""",
            f"المحور: {pillar['label']}\nالأفكار: {ep['ideas']}\n\nاكتب عنواناً واحداً فقط."
        )

        msg = f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}\n\n📝 النص:\n{script[:3500]}"
        send_message(chat_id, msg)
        log("Script sent successfully")

    except Exception as e:
        log(f"run_agent error: {e}")
        send_message(chat_id, f"حدث خطأ: {str(e)}")

def handle_update(update):
    log(f"handle_update: {json.dumps(update)[:200]}")
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip().lower()

    log(f"chat_id: {chat_id}, text: {text}")

    if not chat_id or not text:
        log("No chat_id or text — skipping")
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
    def do_GET(self):
        log(f"GET request from {self.client_address}")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Afaq bot is running.")

    def do_POST(self):
        log(f"POST request from {self.client_address}, path: {self.path}")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        log(f"POST body length: {length}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            update = json.loads(body)
            handle_update(update)
        except Exception as e:
            log(f"POST handler error: {e}")

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    log(f"Starting آفاق bot on port {port}")
    log(f"TELEGRAM_TOKEN set: {bool(TELEGRAM_TOKEN)}")
    log(f"GROQ_KEY set: {bool(GROQ_KEY)}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
