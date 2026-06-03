import os
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

PROCESSED = set()  # prevent duplicate processing

def log(msg):
    print(msg, flush=True)

def send_message(chat_id, text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id, "text": text
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

def download_file(file_id):
    try:
        r = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}", timeout=10)
        file_path = r.json()["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        content = requests.get(file_url, timeout=30)
        return content.text
    except Exception as e:
        log(f"download_file error: {e}")
        return None

def call_groq(system, user):
    log("Calling Groq...")
    for attempt in range(3):
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
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                log(f"Rate limited — waiting {wait}s")
                time.sleep(wait)
                continue
            data = r.json()
            result = data["choices"][0]["message"]["content"]
            log(f"Groq length: {len(result)}")
            return result
        except Exception as e:
            log(f"Groq error: {e}")
            time.sleep(10)
    return ""

def smart_sample(transcript, max_chars=14000):
    """Sample beginning, middle, and end of transcript for best coverage."""
    total = len(transcript)
    if total <= max_chars:
        return transcript
    third = max_chars // 3
    beginning = transcript[:third]
    mid_start = (total // 2) - (third // 2)
    middle = transcript[mid_start:mid_start + third]
    end = transcript[-third:]
    return f"{beginning}\n\n[...]\n\n{middle}\n\n[...]\n\n{end}"

def generate_script(chat_id, transcript):
    send_typing(chat_id)
    send_message(chat_id, "⚙️ جارٍ تحليل الحلقة وكتابة النص العربي...")

    # Smart sample — beginning, middle, end
    sampled = smart_sample(transcript)
    log(f"Sampled transcript: {len(sampled)} chars from {len(transcript)} total")

    # Single call — extract insights AND write script together
    result = call_groq(
        """أنت كاتب محتوى محترف لقناة آفاق على يوتيوب.

مهمتك:
1. استخرج أفضل 5 أفكار حقيقية من النص المرفق (أرقام، قصص، اقتباسات)
2. اكتب نص يوتيوب عربي كامل مدته 7 دقائق بناءً على هذه الأفكار

قواعد النص:
- عربية فصحى مبسطة — راقية ومفهومة
- جمل قصيرة — لا جملة تتجاوز 20 كلمة
- ممنوع أي كلمة إنجليزية
- ابدأ بجملة صادمة أو إحصائية مدهشة — لا "مرحباً" أو "هل تعلم أن"
- أضف سياقاً خليجياً وعربياً حقيقياً

هيكل النص:
خطاف قوي (15 ثانية) ← مقدمة (30 ثانية) ← 4 نقاط بأفكار حقيقية وأمثلة عربية ← خلاصة ← دعوة للاشتراك

أرسل النص فقط بدون عناوين الأقسام.""",
        f"نص الحلقة:\n{sampled}"
    )

    if not result:
        send_message(chat_id, "❌ حدث خطأ أثناء الكتابة. حاول مرة أخرى بعد دقيقتين.")
        return

    # Generate title separately
    time.sleep(5)
    title = call_groq(
        "اكتب عنواناً يوتيوب عربياً واحداً فقط — جذاب، يحتوي رقماً أو سؤالاً، لا يتجاوز 60 حرفاً. بدون أي نص إضافي.",
        f"النص:\n{result[:500]}"
    )

    header = f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}\n\n"

    # Send as messages
    if len(header) + len(result) > 4000:
        send_message(chat_id, header)
        chunks = [result[i:i+3800] for i in range(0, len(result), 3800)]
        for i, chunk in enumerate(chunks):
            send_message(chat_id, f"📝 النص ({i+1}/{len(chunks)}):\n{chunk}")
    else:
        send_message(chat_id, header + f"📝 النص:\n{result}")

    # Send as downloadable file
    try:
        full_text = f"العنوان:\n{title.strip()}\n\n{result}"
        files = {'document': ('script.txt', full_text.encode('utf-8'), 'text/plain')}
        requests.post(f"{TELEGRAM_API}/sendDocument",
            data={"chat_id": chat_id, "caption": "📄 النص كاملاً للتنزيل"},
            files=files, timeout=30)
        log("File sent")
    except Exception as e:
        log(f"File send error: {e}")

HOW_TO_TEXT = """📋 كيف ترسل نص الحلقة:

1️⃣ اذهب إلى tactiq.io/tools/youtube-transcript
2️⃣ الصق رابط الحلقة
3️⃣ انقر Download — يحفظ ملف .txt
4️⃣ أرسل الملف هنا مباشرة

الروبوت يقرأ الملف ويكتب النص العربي تلقائياً ✅"""

HELP_TEXT = """مرحباً! أنا وكيل آفاق للمحتوى 🎬

أرسل لي ملف .txt لأي حلقة بودكاست وسأكتب لك نص يوتيوب عربي احترافي.

/how — كيف تحصل على الملف
/help — المساعدة"""

def handle_update(update):
    update_id = update.get("update_id")

    # Prevent duplicate processing
    if update_id in PROCESSED:
        log(f"Duplicate update {update_id} — skipping")
        return
    PROCESSED.add(update_id)

    log(f"Update {update_id}: {json.dumps(update)[:150]}")
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")

    if not chat_id:
        return

    text = msg.get("text", "").strip()
    if text:
        log(f"Text: {text[:60]}")
        if text.lower() in ["/start", "/help"]:
            send_message(chat_id, HELP_TEXT)
        elif text.lower() == "/how":
            send_message(chat_id, HOW_TO_TEXT)
        else:
            send_message(chat_id, "أرسل ملف .txt يحتوي على نص الحلقة.\n\nأرسل /how للمساعدة.")
        return

    doc = msg.get("document", {})
    if doc:
        file_id = doc.get("file_id", "")
        file_name = doc.get("file_name", "")
        log(f"Document: {file_name}")

        send_message(chat_id, "📥 جارٍ قراءة الملف...")
        transcript = download_file(file_id)

        if not transcript or len(transcript.strip()) < 200:
            send_message(chat_id, "❌ الملف فارغ أو قصير جداً.")
            return

        log(f"Transcript: {len(transcript)} chars")
        generate_script(chat_id, transcript)
        return

    send_message(chat_id, "أرسل ملف .txt للحصول على النص العربي.\n\nأرسل /how للمساعدة.")

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
