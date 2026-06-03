import os
import json
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
PROCESSED      = set()

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
        return requests.get(file_url, timeout=30).text
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

def smart_sample(transcript, max_chars=12000):
    total = len(transcript)
    if total <= max_chars:
        return transcript
    third = max_chars // 3
    mid_start = (total // 2) - (third // 2)
    return (transcript[:third] + "\n\n[...]\n\n" +
            transcript[mid_start:mid_start+third] + "\n\n[...]\n\n" +
            transcript[-third:])

def process_transcript(chat_id, transcript):
    """Runs in background thread — Telegram never times out."""
    log(f"Background processing started for chat {chat_id}")
    try:
        sampled = smart_sample(transcript)
        log(f"Sampled: {len(sampled)} chars from {len(transcript)}")

        send_typing(chat_id)

        script = call_groq(
            """أنت كاتب محتوى محترف لقناة آفاق على يوتيوب.

مهمتك: اكتب نص يوتيوب عربي كامل مدته 7 دقائق بناءً على محتوى البودكاست المرفق.

قواعد إلزامية:
- استخدم الحقائق والأرقام والقصص الحقيقية من النص المرفق
- عربية فصحى مبسطة — جمل قصيرة لا تتجاوز 20 كلمة
- ممنوع أي كلمة إنجليزية
- ابدأ بجملة صادمة أو إحصائية — لا "مرحباً" أو "هل تعلم أن"
- أضف سياقاً خليجياً وعربياً حقيقياً لكل فكرة

الهيكل:
خطاف قوي ← مقدمة ← 4 نقاط بأفكار حقيقية وأمثلة عربية ← خلاصة ← دعوة للاشتراك

اكتب النص فقط بدون عناوين الأقسام.""",
            f"نص الحلقة:\n{sampled}"
        )

        if not script:
            send_message(chat_id, "❌ حدث خطأ. حاول مرة أخرى بعد دقيقتين.")
            return

        time.sleep(5)

        title = call_groq(
            "اكتب عنواناً يوتيوب عربياً واحداً فقط — جذاب، يحتوي رقماً أو سؤالاً، لا يتجاوز 60 حرفاً. بدون أي نص إضافي.",
            f"النص:\n{script[:400]}"
        )

        header = f"✅ النص جاهز!\n\n📺 العنوان:\n{title.strip()}\n\n"

        if len(header) + len(script) > 4000:
            send_message(chat_id, header)
            for i, chunk in enumerate([script[j:j+3800] for j in range(0, len(script), 3800)]):
                send_message(chat_id, f"📝 النص ({i+1}):\n{chunk}")
        else:
            send_message(chat_id, header + f"📝 النص:\n{script}")

        # Send as file
        try:
            full_text = f"العنوان:\n{title.strip()}\n\n{script}"
            files = {'document': ('script.txt', full_text.encode('utf-8'), 'text/plain')}
            requests.post(f"{TELEGRAM_API}/sendDocument",
                data={"chat_id": chat_id, "caption": "📄 النص كاملاً للتنزيل"},
                files=files, timeout=30)
            log("File sent successfully")
        except Exception as e:
            log(f"File error: {e}")

    except Exception as e:
        log(f"Background processing error: {e}")
        send_message(chat_id, "❌ حدث خطأ غير متوقع. حاول مرة أخرى.")

HOW_TO_TEXT = """📋 كيف ترسل نص الحلقة:

1️⃣ اذهب إلى tactiq.io/tools/youtube-transcript
2️⃣ الصق رابط الحلقة
3️⃣ انقر Download — يحفظ ملف .txt
4️⃣ أرسل الملف هنا مباشرة ✅"""

HELP_TEXT = """مرحباً! أنا وكيل آفاق للمحتوى 🎬

أرسل لي ملف .txt لأي حلقة بودكاست وسأكتب لك نص يوتيوب عربي في دقيقتين.

/how — كيف تحصل على الملف
/help — المساعدة"""

def handle_update(update):
    update_id = update.get("update_id")
    if update_id in PROCESSED:
        log(f"Duplicate {update_id} — skipping")
        return
    PROCESSED.add(update_id)

    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return

    text = msg.get("text", "").strip()
    if text:
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

        # Respond to Telegram immediately
        send_message(chat_id, "📥 استلمت الملف — جارٍ الكتابة...\n\n⏱ سيصلك النص خلال دقيقتين.")

        # Download file
        transcript = download_file(file_id)
        if not transcript or len(transcript.strip()) < 200:
            send_message(chat_id, "❌ الملف فارغ أو قصير جداً.")
            return

        log(f"Transcript: {len(transcript)} chars — starting background thread")

        # Process in background — Telegram won't retry
        t = threading.Thread(target=process_transcript, args=(chat_id, transcript))
        t.daemon = True
        t.start()
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
        # Respond to Telegram IMMEDIATELY
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        # Process in separate thread
        try:
            update = json.loads(body)
            threading.Thread(target=handle_update, args=(update,), daemon=True).start()
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
