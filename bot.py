import os
import re
import sys
import json
import random
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from youtube_transcript_api import YouTubeTranscriptApi

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def log(msg):
    print(msg, flush=True)

# ─── TELEGRAM ────────────────────────────────────────────────────────────────

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=15)
        log(f"send_message: {r.status_code}")
    except Exception as e:
        log(f"send_message error: {e}")

def send_typing(chat_id):
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction", json={
            "chat_id": chat_id, "action": "typing"
        }, timeout=5)
    except: pass

# ─── GROQ ────────────────────────────────────────────────────────────────────

def call_groq(system, user):
    log("Calling Groq...")
    try:
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
            timeout=90
        )
        log(f"Groq status: {r.status_code}")
        data = r.json()
        result = data["choices"][0]["message"]["content"]
        log(f"Groq response length: {len(result)}")
        return result
    except Exception as e:
        log(f"Groq error: {e}")
        return ""

# ─── YOUTUBE TRANSCRIPT ──────────────────────────────────────────────────────

def extract_video_id(url):
    patterns = [
        r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def get_transcript(video_id):
    log(f"Fetching transcript for: {video_id}")
    try:
        # Try English first, then any language
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Join all text and limit to first 12000 chars (enough for a 60 min episode)
        full_text = " ".join([t['text'] for t in transcript])
        log(f"Transcript length: {len(full_text)} chars")
        return full_text[:12000]
    except Exception as e:
        log(f"Transcript error: {e}")
        return None

# ─── SCRIPT GENERATION ───────────────────────────────────────────────────────

SCRIPT_SYSTEM = """أنت كاتب محتوى محترف لقناة آفاق على يوتيوب. مهمتك تحويل محتوى بودكاست إنجليزي إلى نص يوتيوب عربي استثنائي.

قواعد إلزامية:
- اكتب بالعربية الفصحى المبسطة — راقية لكن مفهومة لكل العرب
- جمل قصيرة وإيقاع سريع — لا جملة تتجاوز 20 كلمة
- ممنوع أي كلمة إنجليزية — حتى المصطلحات التقنية تُعرَّب
- ممنوع تكرار "على سبيل المثال" — استخدمها مرة واحدة فقط
- لا تبدأ بـ "مرحباً" أو "في هذا الفيديو" أو "هل تعلم أن"
- استخدم الحقائق والأرقام والقصص الحقيقية من المحتوى المقدم
- أضف سياقاً عربياً حقيقياً — اربط كل فكرة بالواقع الخليجي والعربي

هيكل النص الإلزامي:
[خطاف] إحصائية صادمة أو جملة تقلق المشاهد — 15 ثانية فقط
[مقدمة] ما ستتعلمه وليه يهمك أنت كعربي — 30 ثانية
[نقطة 1] فكرة من المحتوى + رقم أو قصة حقيقية + تطبيق في الوطن العربي
[نقطة 2] فكرة من المحتوى + رقم أو قصة حقيقية + تطبيق في الوطن العربي
[نقطة 3] فكرة من المحتوى + رقم أو قصة حقيقية + تطبيق في الوطن العربي
[نقطة 4] فكرة من المحتوى + رقم أو قصة حقيقية + تطبيق في الوطن العربي
[خلاصة] أهم درس في 3 جمل
[دعوة] اشترك في القناة — فيديو جديد كل أسبوع

اكتب النص فقط — بدون عناوين الأقسام بين قوسين."""

TITLE_SYSTEM = """أنت خبير SEO يوتيوب عربي. اكتب عنواناً واحداً فقط بدون أي نص إضافي.
قواعد:
- يثير فضول المشاهد ويجعله ينقر فوراً
- يحتوي على رقم أو سؤال أو وعد واضح
- لا يتجاوز 60 حرفاً
- بالعربية فقط
مثال جيد: كيف تحفظ ٢٠٪ من راتبك حتى لو كان محدوداً
مثال سيء: فيديو عن المال والادخار"""

def generate_from_transcript(chat_id, video_id, url):
    send_typing(chat_id)
    send_message(chat_id, "⚙️ جارٍ استخراج محتوى الحلقة...")

    transcript = get_transcript(video_id)
    if not transcript:
        send_message(chat_id, "❌ لم أتمكن من استخراج النص من هذا الفيديو.\n\nتأكد أن:\n• الرابط صحيح\n• الفيديو عام وليس خاصاً\n• الفيديو يحتوي على ترجمة تلقائية")
        return

    send_message(chat_id, "✅ تم استخراج المحتوى\n⚙️ جارٍ كتابة النص العربي...")

    # Extract key insights first
    insights = call_groq(
        "You are a content analyst. Extract the 6 most surprising, specific, and valuable insights from this podcast transcript. Include exact numbers, statistics, and specific stories mentioned. Return a numbered list in English.",
        f"Transcript excerpt:\n{transcript}"
    )
    log(f"Insights extracted: {len(insights)} chars")

    # Generate Arabic script from real insights
    script = call_groq(
        SCRIPT_SYSTEM,
        f"هذه الأفكار والحقائق الحقيقية المستخرجة من الحلقة:\n{insights}\n\nاكتب نصاً عربياً أصيلاً مدته 7 دقائق يستخدم هذه الحقائق الحقيقية مع إضافة سياق عربي وخليجي."
    )

    # Generate title
    title = call_groq(TITLE_SYSTEM, f"الأفكار الرئيسية: {insights[:500]}\n\nاكتب عنواناً واحداً فقط.")

    msg = f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}\n\n📝 النص:\n{script}"
    
    # Split if too long for Telegram
    if len(msg) > 4000:
        send_message(chat_id, f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}")
        # Send script in chunks
        chunks = [script[i:i+3500] for i in range(0, len(script), 3500)]
        for i, chunk in enumerate(chunks):
            send_message(chat_id, f"📝 النص ({i+1}/{len(chunks)}):\n{chunk}")
    else:
        send_message(chat_id, msg)

    log("Script delivered successfully")

# ─── HELP TEXT ───────────────────────────────────────────────────────────────

HELP_TEXT = """مرحباً! أنا وكيل آفاق للمحتوى 🎬

أرسل لي رابط يوتيوب لأي بودكاست وسأحوّله إلى نص عربي احترافي جاهز للتسجيل.

طريقة الاستخدام:
أرسل رابط الحلقة مباشرة:
https://youtube.com/watch?v=xxxxx

أو استخدم الأوامر:
/help — عرض هذه المساعدة

المصادر الموصى بها:
• Lex Fridman Podcast
• Diary of a CEO
• Peter Zeihan
• All-In Podcast
• My First Million"""

# ─── UPDATE HANDLER ──────────────────────────────────────────────────────────

def handle_update(update):
    log(f"Update received: {json.dumps(update)[:150]}")
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip()

    if not chat_id or not text:
        return

    log(f"chat_id: {chat_id}, text: {text[:80]}")

    if text.lower() in ["/start", "/help"]:
        send_message(chat_id, HELP_TEXT)
        return

    # Check if it's a YouTube URL
    if "youtube.com" in text or "youtu.be" in text:
        video_id = extract_video_id(text)
        if video_id:
            generate_from_transcript(chat_id, video_id, text)
        else:
            send_message(chat_id, "❌ لم أتعرف على رابط يوتيوب صحيح. أرسل الرابط كاملاً.")
        return

    send_message(chat_id, "أرسل رابط يوتيوب لحلقة بودكاست وسأحوّلها إلى نص عربي.\n\nمثال:\nhttps://youtube.com/watch?v=xxxxx\n\nأو أرسل /help للمساعدة.")

# ─── SERVER ──────────────────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Afaq bot is running.")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            update = json.loads(body)
            handle_update(update)
        except Exception as e:
            log(f"POST error: {e}")

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    log(f"Starting Afaq bot on port {port}")
    log(f"TELEGRAM_TOKEN set: {bool(TELEGRAM_TOKEN)}")
    log(f"GROQ_KEY set: {bool(GROQ_KEY)}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
