import os
import json
import time
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

def call_groq(system, user, retries=3):
    log("Calling Groq...")
    for attempt in range(retries):
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
                wait = 15 * (attempt + 1)
                log(f"Rate limited — waiting {wait}s before retry {attempt+1}/{retries}")
                time.sleep(wait)
                continue
            data = r.json()
            result = data["choices"][0]["message"]["content"]
            log(f"Groq response length: {len(result)}")
            return result
        except Exception as e:
            log(f"Groq error: {e}")
            if attempt < retries - 1:
                time.sleep(10)
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

def extract_insights_from_full_transcript(transcript):
    """Split transcript into chunks and extract insights from each, then merge best ones."""
    chunk_size = 8000
    chunks = [transcript[i:i+chunk_size] for i in range(0, min(len(transcript), 48000), chunk_size)]
    log(f"Processing {len(chunks)} chunks from transcript")

    all_insights = []
    for i, chunk in enumerate(chunks):
        log(f"Processing chunk {i+1}/{len(chunks)}")
        result = call_groq(
            "You are a content analyst. Extract the 3 most surprising, specific, and valuable insights from this podcast transcript chunk. Include exact numbers, statistics, quotes, and specific stories. Be specific — no generic summaries. Return a numbered list.",
            f"Transcript chunk {i+1}:\n{chunk}"
        )
        if result:
            all_insights.append(result)
        time.sleep(3)  # avoid rate limiting between chunks

    # Merge and pick best 6 from all chunks
    combined = "\n\n".join(all_insights)
    best_insights = call_groq(
        "You are a content analyst. From the following insights extracted from different parts of a podcast, select and refine the 6 most surprising, specific, and valuable ones. Include exact numbers, statistics, and stories. Return a clean numbered list of exactly 6 insights.",
        f"All extracted insights:\n{combined[:12000]}"
    )
    return best_insights

def generate_script(chat_id, transcript):
    send_typing(chat_id)
    send_message(chat_id, "⚙️ جارٍ مسح الحلقة كاملة واستخراج أفضل الأفكار...")

    insights = extract_insights_from_full_transcript(transcript)
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

    # Also send as a text file for easy copying
    try:
        full_text = f"العنوان:\n{title.strip()}\n\n{script}"
        files = {'document': ('script.txt', full_text.encode('utf-8'), 'text/plain')}
        requests.post(f"{TELEGRAM_API}/sendDocument",
            data={"chat_id": chat_id, "caption": "📄 النص كاملاً — اضغط لتنزيله"},
            files=files, timeout=30)
        log("File sent")
    except Exception as e:
        log(f"File send error: {e}")

HOW_TO_TEXT = """📋 كيف ترسل نص الحلقة:

1️⃣ اذهب إلى tactiq.io/tools/youtube-transcript
2️⃣ الصق رابط الحلقة
3️⃣ انقر Copy أو Download
4️⃣ احفظ النص كملف .txt
5️⃣ أرسل الملف مباشرة هنا في المحادثة

الروبوت سيقرأ الملف ويكتب لك النص العربي تلقائياً ✅"""

HELP_TEXT = """مرحباً! أنا وكيل آفاق للمحتوى 🎬

أرسل لي ملف .txt يحتوي على نص أي حلقة بودكاست وسأحوّله إلى نص يوتيوب عربي احترافي.

الأوامر:
/how — كيف ترسل نص الحلقة
/help — المساعدة

المصادر الموصى بها:
• Lex Fridman Podcast
• Diary of a CEO  
• Peter Zeihan
• All-In Podcast
• My First Million"""

def handle_update(update):
    log(f"Update: {json.dumps(update)[:200]}")
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")

    if not chat_id:
        return

    # Handle text commands
    text = msg.get("text", "").strip()
    if text:
        log(f"Text: {text[:60]}")
        if text.lower() in ["/start", "/help"]:
            send_message(chat_id, HELP_TEXT)
        elif text.lower() == "/how":
            send_message(chat_id, HOW_TO_TEXT)
        else:
            send_message(chat_id, "أرسل لي ملف .txt يحتوي على نص الحلقة.\n\nأرسل /how لمعرفة كيفية الحصول على النص.")
        return

    # Handle document upload
    doc = msg.get("document", {})
    if doc:
        file_name = doc.get("file_name", "")
        file_id = doc.get("file_id", "")
        mime_type = doc.get("mime_type", "")
        log(f"Document received: {file_name} ({mime_type})")

        if not file_id:
            send_message(chat_id, "❌ لم أتمكن من قراءة الملف.")
            return

        send_message(chat_id, "📥 جارٍ قراءة الملف...")
        transcript = download_file(file_id)

        if not transcript or len(transcript.strip()) < 200:
            send_message(chat_id, "❌ الملف فارغ أو قصير جداً.\n\nتأكد أن الملف يحتوي على نص الحلقة كاملاً.")
            return

        log(f"Transcript loaded: {len(transcript)} chars")
        generate_script(chat_id, transcript)
        return

    send_message(chat_id, "أرسل لي ملف .txt يحتوي على نص الحلقة.\n\nأرسل /how للمساعدة.")

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
