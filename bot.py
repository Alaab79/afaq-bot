import os
import re
import sys
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def log(msg):
    print(msg, flush=True)

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

SCRIPT_SYSTEM = """أنت كاتب محتوى محترف لقناة آفاق على يوتيوب. مهمتك تحويل محتوى بودكاست إنجليزي إلى نص يوتيوب عربي استثنائي.

قواعد إلزامية:
- اكتب بالعربية الفصحى المبسطة — راقية لكن مفهومة لكل العرب
- جمل قصيرة وإيقاع سريع — لا جملة تتجاوز 20 كلمة
- ممنوع أي كلمة إنجليزية — حتى المصطلحات التقنية تُعرَّب
- ممنوع تكرار "على سبيل المثال" — مرة واحدة فقط في كل النص
- لا تبدأ بـ "مرحباً" أو "في هذا الفيديو" أو "هل تعلم أن"
- استخدم الحقائق والأرقام والقصص الحقيقية من المحتوى المقدم
- أضف سياقاً عربياً — اربط كل فكرة بالواقع الخليجي والعربي

هيكل النص:
[خطاف] إحصائية صادمة أو جملة مقلقة — 15 ثانية
[مقدمة] ما ستتعلمه وليه يهمك كعربي — 30 ثانية
[نقطة 1] فكرة حقيقية من المحتوى + رقم أو قصة + تطبيق عربي
[نقطة 2] فكرة حقيقية من المحتوى + رقم أو قصة + تطبيق عربي
[نقطة 3] فكرة حقيقية من المحتوى + رقم أو قصة + تطبيق عربي
[نقطة 4] فكرة حقيقية من المحتوى + رقم أو قصة + تطبيق عربي
[خلاصة] أهم درس في 3 جمل
[دعوة] اشترك في القناة — فيديو جديد كل أسبوع

اكتب النص فقط — بدون عناوين الأقسام."""

TITLE_SYSTEM = """أنت خبير SEO يوتيوب عربي. اكتب عنواناً واحداً فقط بدون أي نص إضافي.
- يثير فضول المشاهد ويجعله ينقر فوراً
- يحتوي على رقم أو سؤال أو وعد واضح
- لا يتجاوز 60 حرفاً
- بالعربية فقط"""

def generate_script(chat_id, transcript):
    send_typing(chat_id)
    send_message(chat_id, "⚙️ جارٍ استخراج أهم الأفكار من الحلقة...")
    insights = call_groq(
        "You are a content analyst. Extract the 6 most surprising, specific, and valuable insights from this podcast transcript. Include exact numbers, statistics, quotes, and specific stories mentioned by the speaker. Be specific — no generic summaries. Return a numbered list.",
        f"Transcript:\n{transcript[:10000]}"
    )
    log(f"Insights: {len(insights)} chars")
    send_message(chat_id, "✅ تم استخراج الأفكار\n⚙️ جارٍ كتابة النص العربي...")
    script = call_groq(
        SCRIPT_SYSTEM,
        f"هذه الأفكار والحقائق الحقيقية المستخرجة من الحلقة:\n{insights}\n\nاكتب نصاً عربياً أصيلاً مدته 7 دقائق يستخدم هذه الحقائق مع إضافة سياق عربي وخليجي حقيقي."
    )
    title = call_groq(
        TITLE_SYSTEM,
        f"الأفكار الرئيسية:\n{insights[:500]}\n\nاكتب عنواناً واحداً فقط."
    )
    header = f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}\n\n"
    if len(header) + len(script) > 4000:
        send_message(chat_id, header)
        chunks = [script[i:i+3800] for i in range(0, len(script), 3800)]
        for i, chunk in enumerate(chunks):
            send_message(chat_id, f"📝 النص ({i+1}/{len(chunks)}):\n{chunk}")
    else:
        send_message(chat_id, header + f"📝 النص:\n{script}")
    log("Script delivered")

HOW_TO_TEXT = """📋 كيف تحصل على نص الحلقة:

1️⃣ اذهب إلى tactiq.io/tools/youtube-transcript
2️⃣ الصق رابط الحلقة
3️⃣ انسخ النص كاملاً
4️⃣ أرسله هنا هكذا:
/script [النص هنا]"""

HELP_TEXT = """مرحباً! أنا وكيل آفاق للمحتوى 🎬

الأوامر:
/script [النص] — حوّل نص الحلقة إلى سكريبت عربي
/how — كيف تحصل على نص الحلقة
/help — المساعدة"""

def handle_update(update):
    log(f"Update: {json.dumps(update)[:150]}")
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip()
    if not chat_id or not text:
        return
    log(f"chat_id: {chat_id}, command: {text[:60]}")
    if text.lower() in ["/start", "/help"]:
        send_message(chat_id, HELP_TEXT)
    elif text.lower() == "/how":
        send_message(chat_id, HOW_TO_TEXT)
    elif text.lower().startswith("/script"):
        transcript = text[7:].strip()
        if len(transcript) < 200:
            send_message(chat_id, "⚠️ النص قصير جداً — أرسل /how للمساعدة.")
        else:
            generate_script(chat_id, transcript)
    else:
        send_message(chat_id, "أرسل /how للمساعدة أو /script [النص] لتوليد السكريبت.")

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
