import os
import re
import io
import time
import asyncio
import logging
import threading
import random
import string
import urllib.parse

from dotenv import load_dotenv
from google import genai
from flask import Flask
import aiohttp
from bs4 import BeautifulSoup
from gtts import gTTS
from pypdf import PdfReader

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

# =========================================================
# CONFIG & GLOBALS
# =========================================================
START_TIME = time.time()
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID") 

if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        ADMIN_ID = None

MODEL = "gemini-2.5-flash"
MAX_MESSAGE_LENGTH = 4000

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN hoặc GEMINI_API_KEY trong file .env")

# =========================================================
# FLASK WEB SERVER CHO RENDER
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    uptime = round((time.time() - START_TIME) / 3600, 2)
    return f"Ultra AI Bot is running! Uptime: {uptime} hours."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    import logging as flask_logging
    flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)
    app.run(host="0.0.0.0", port=port)

# =========================================================
# LOGGING & AI CLIENT
# =========================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "Bạn là Siêu Trợ Lý AI đa năng trên Telegram. "
    "Nhiệm vụ: Phản hồi cực kỳ nhanh, chính xác, lập luận logic sâu sắc, "
    "cung cấp code hoàn chỉnh khi được yêu cầu, thân thiện."
)

# =========================================================
# QUẢN LÝ DỮ LIỆU TRONG RAM
# =========================================================
USERS_FILE = "users.txt"
known_users = set()
user_locks = {}
user_chat_history = {}
user_languages = {}

def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for line in f:
                if line.strip().isdigit():
                    known_users.add(int(line.strip()))

def _save_user_sync(user_id):
    if user_id not in known_users:
        known_users.add(user_id)
        try:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")
        except Exception as e:
            logger.error(f"Lỗi lưu user: {e}")

async def save_user_async(user_id):
    await asyncio.to_thread(_save_user_sync, user_id)

load_users()

# =========================================================
# TỪ ĐIỂN VĂN BẢN HỆ THỐNG
# =========================================================
TEXTS = {
    "vi": {
        "welcome": "🤖 <b>CHÀO MỪNG ĐẾN VỚI SIÊU TRỢ LÝ AI</b>\n\nBạn đã chọn ngôn ngữ: <b>Tiếng Việt 🇻🇳</b>\nHệ thống tích hợp hơn 25+ tính năng thông minh.\n\n👑 <b>Chủ bot:</b> @itznvl\n\nGõ /help để xem danh sách lệnh hoặc sử dụng menu bên dưới.",
        "lang_changed": "✅ Đã chuyển ngôn ngữ thành công sang <b>Tiếng Việt 🇻🇳</b>!",
        "choose_lang": "🌍 <b>Vui lòng chọn ngôn ngữ của bạn / Please select your language:</b>",
        "help": (
            "📖 <b>DANH SÁCH LỆNH HỆ THỐNG</b>\n\n"
            "👑 <b>Chủ bot:</b> @itznvl\n\n"
            "• `/language` - Đổi ngôn ngữ (Việt / Anh)\n"
            "• `/myid` - Xem ID Telegram của bạn\n"
            "• `/img [mô tả]` - Vẽ ảnh AI chất lượng cao\n"
            "• `/tts [văn bản]` - Chuyển văn bản thành giọng nói\n"
            "• `/thoitiet [thành phố]` - Xem thời tiết thời gian thực\n"
            "• `/dich [văn bản]` - Dịch thuật đa ngôn ngữ siêu tốc\n"
            "• `/code [yêu cầu]` - Lập trình & Debug mã nguồn\n"
            "• `/toan [bài toán]` - Giải toán chi tiết từng bước\n"
            "• `/crypto [coin]` - Tra cứu giá tiền mã hóa (BTC, ETH...)\n"
            "• `/password [độ dài]` - Tạo mật khẩu siêu bảo mật\n"
            "• `/ascii [chữ]` - Biến văn bản thành nghệ thuật chữ ASCII\n"
            "• `/check [câu]` - Sửa lỗi ngữ pháp\n"
            "• `/nhac [giây] [nội dung]` - Đặt lịch hẹn nhắc nhở\n"
            "• `/qr [text]` - Tạo mã QR nhanh\n"
            "• `/quiz` - Chơi đố vui kiến thức\n"
            "• `/tiente [số] [từ] sang [đến]` - Đổi ngoại tệ\n"
            "• `/vui` - Câu nói hay / Truyện cười thư giãn\n"
            "• `/export` - Xuất file lịch sử chat (.txt)\n"
            "• `/reset` - Làm mới bộ nhớ đệm ngữ cảnh\n\n"
            "💡 <b>Mẹo:</b> <i>Bạn có thể gửi một tệp PDF trực tiếp vào khung chat để bot đọc và tóm tắt!</i>"
        ),
        "menu": {
            "reset": "🧹 Xóa trí nhớ",
            "img": "🎨 Vẽ ảnh",
            "weather": "🌤️ Thời tiết",
            "math": "🧮 Giải toán",
            "quiz": "🎮 Đố vui",
            "quote": "💡 Danh ngôn",
            "export": "💾 Xuất lịch sử",
            "help": "ℹ️ Hướng dẫn",
            "lang": "🌍 Đổi ngôn ngữ"
        }
    },
    "en": {
        "welcome": "🤖 <b>WELCOME TO ULTRA AI ASSISTANT</b>\n\nYou have selected: <b>English 🇬🇧</b>\nEquipped with 25+ advanced smart features.\n\n👑 <b>Bot Owner:</b> @itznvl\n\nType /help to see all commands or use the menu below.",
        "lang_changed": "✅ Successfully changed language to <b>English 🇬🇧</b>!",
        "choose_lang": "🌍 <b>Please select your language / Vui lòng chọn ngôn ngữ:</b>",
        "help": (
            "📖 <b>SYSTEM COMMANDS LIST</b>\n\n"
            "👑 <b>Bot Owner:</b> @itznvl\n\n"
            "• `/language` - Change language (English / Vietnamese)\n"
            "• `/myid` - Check your Telegram ID\n"
            "• `/img [prompt]` - Generate high-quality AI art\n"
            "• `/tts [text]` - Convert text to natural voice message\n"
            "• `/thoitiet [city]` - Real-time weather forecast\n"
            "• `/dich [text]` - Instant multi-language translation\n"
            "• `/code [request]` - Write & debug programming code\n"
            "• `/toan [math problem]` - Step-by-step math solver\n"
            "• `/crypto [coin]` - Check cryptocurrency prices (BTC, ETH...)\n"
            "• `/password [length]` - Generate secure random passwords\n"
            "• `/ascii [text]` - Turn text into cool ASCII text art\n"
            "• `/check [sentence]` - Fix grammar errors\n"
            "• `/nhac [seconds] [msg]` - Set a quick timer reminder\n"
            "• `/qr [text]` - Generate instant QR code\n"
            "• `/quiz` - Play fun trivia quiz games\n"
            "• `/tiente [amount] [from] to [to]` - Currency converter\n"
            "• `/vui` - Daily quotes & jokes\n"
            "• `/export` - Export chat history to .txt file\n"
            "• `/reset` - Reset conversation context memory\n\n"
            "💡 <b>Tip:</b> <i>You can upload a PDF file directly to the chat, and the bot will automatically read and summarize it!</i>"
        ),
        "menu": {
            "reset": "🧹 Reset Context",
            "img": "🎨 AI Image",
            "weather": "🌤️ Weather",
            "math": "🧮 Math Solver",
            "quiz": "🎮 Trivia Quiz",
            "quote": "💡 Daily Quote",
            "export": "💾 Export History",
            "help": "ℹ️ Help Guide",
            "lang": "🌍 Change Language"
        }
    }
}

def get_user_lang(uid):
    return user_languages.get(uid, "vi")

def get_markup(uid):
    lang = get_user_lang(uid)
    m = TEXTS[lang]["menu"]
    keyboard = [
        [m["reset"], m["img"], m["weather"]],
        [m["math"], m["quiz"], m["quote"]],
        [m["export"], m["help"], m["lang"]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# =========================================================
# CORE GEMINI & SCRAPER
# =========================================================
async def ask_gemini(prompt_text):
    def _call():
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt_text,
            config={"system_instruction": SYSTEM_PROMPT}
        )
        return response.text
    return await asyncio.to_thread(_call)

async def fetch_webpage(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                return soup.get_text(separator=' ', strip=True)[:4000]
    except Exception:
        return None

# =========================================================
# LỆNH HỆ THỐNG TĨNH
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    asyncio.create_task(save_user_async(uid)) 
    
    if uid not in user_languages:
        keyboard = [
            [
                InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            TEXTS["vi"]["choose_lang"],
            parse_mode="HTML",
            reply_markup=markup
        )
        return

    lang = get_user_lang(uid)
    markup = get_markup(uid)
    await update.message.reply_text(TEXTS[lang]["welcome"], parse_mode="HTML", reply_markup=markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    await update.message.reply_text(TEXTS[lang]["help"], parse_mode="HTML")

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌍 <b>Chọn ngôn ngữ / Choose your language:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data == "lang_vi":
        user_languages[uid] = "vi"
    elif query.data == "lang_en":
        user_languages[uid] = "en"
        
    lang = get_user_lang(uid)
    markup = get_markup(uid)
    
    await query.message.edit_text(TEXTS[lang]["lang_changed"], parse_mode="HTML")
    await query.message.reply_text(TEXTS[lang]["welcome"], parse_mode="HTML", reply_markup=markup)

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_chat_history[uid] = []
    lang = get_user_lang(uid)
    msg = "🧹 Đã xóa sạch trí nhớ, bắt đầu cuộc trò chuyện mới!" if lang == "vi" else "🧹 Context successfully reset!"
    await update.message.reply_text(msg)

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    msg = f"🆔 <b>ID Telegram của bạn là:</b> <code>{uid}</code>" if lang == "vi" else f"🆔 <b>Your Telegram ID is:</b> <code>{uid}</code>"
    await update.message.reply_text(msg, parse_mode="HTML")

# =========================================================
# TÍNH NĂNG AI / API (AN TOÀN KHÔNG DÙNG HTML PARSER)
# =========================================================
async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /img [mô tả]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
    try:
        await update.message.reply_photo(photo=url, caption=f"🎨 AI Art: {prompt}")
    except Exception:
        await update.message.reply_text("❌ Lỗi tải ảnh. / Cannot generate image.")

async def cmd_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /tts [văn bản]")
        return
    uid = update.effective_user.id
    lang_code = 'en' if get_user_lang(uid) == 'en' else 'vi'
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
    try:
        tts = gTTS(text, lang=lang_code)
        bio = io.BytesIO()
        await asyncio.to_thread(tts.write_to_fp, bio)
        bio.seek(0)
        await update.message.reply_voice(voice=bio)
    except Exception:
        await update.message.reply_text("❌ Lỗi tạo giọng nói.")

async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = " ".join(context.args)
    if not loc:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /thoitiet [thành phố]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        url = f"https://wttr.in/{urllib.parse.quote(loc)}?format=3"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as res:
                text = await res.text()
                await update.message.reply_text(f"🌤️ Thời tiết / Weather:\n{text}")
    except Exception:
        await update.message.reply_text("❌ Lỗi API Thời tiết.")

async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /dich [văn bản]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    uid = update.effective_user.id
    target = "English" if get_user_lang(uid) == "en" else "tiếng Việt"
    res = await ask_gemini(f"Dịch đoạn sau sang {target}, chỉ trả kết quả, không giải thích: {text}")
    await update.message.reply_text(f"🌐 Bản dịch / Translation:\n{res}")

async def cmd_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = " ".join(context.args).lower() or "bitcoin"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Cung cấp thông tin giá hiện tại và xu hướng ngắn gọn của đồng tiền mã hóa '{coin}'.")
    await update.message.reply_text(f"🪙 Crypto Info:\n{res}")

async def cmd_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 12
    if context.args and context.args[0].isdigit():
        length = int(context.args[0])
        length = max(6, min(length, 64))
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    await update.message.reply_text(f"🔑 Mật khẩu bảo mật:\n`{pwd}`", parse_mode="Markdown")

async def cmd_ascii(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /ascii [chữ]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Tạo nghệ thuật chữ ASCII art đẹp và ngắn gọn cho từ khóa: {text}")
    await update.message.reply_text(f"```text\n{res}\n```", parse_mode="Markdown")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history = user_chat_history.get(uid, [])
    if not history:
        await update.message.reply_text("📭 Chưa có lịch sử trò chuyện.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    bio = io.BytesIO("\n".join(history).encode('utf-8'))
    bio.name = "chat_history.txt"
    await update.message.reply_document(document=bio, caption="💾 Lịch sử chat của bạn.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Lệnh dành riêng cho Admin.")
        return
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    text = f"📊 THỐNG KÊ HỆ THỐNG\n⏳ Uptime: {h}h {m}m {s}s\n👥 User: {len(known_users)}\n🧠 Model: {MODEL}"
    await update.message.reply_text(text)

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền.")
        return
    parts = update.message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("⚠️ Hướng dẫn: /thongbao [nội dung]")
        return
    msg = await update.message.reply_text(f"🚀 Đang gửi thông báo đến {len(known_users)} người...")
    success, fail = 0, 0
    for uid in list(known_users):
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 Thông báo từ Admin:\n\n{parts[1].strip()}")
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    await msg.edit_text(f"✅ Hoàn tất! Thành công: {success} | Thất bại: {fail}")

async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_query = " ".join(context.args)
    if not code_query:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /code [yêu cầu]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Viết code hoàn chỉnh, tối ưu và giải thích ngắn gọn cho: {code_query}")
    await update.message.reply_text(res)

async def cmd_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    math_q = " ".join(context.args)
    if not math_q:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /toan [bài toán]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Giải chi tiết bài toán sau: {math_q}")
    await update.message.reply_text(f"🧮 Giải toán / Math Solver:\n{res}")

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /check [câu]")
        return
    res = await ask_gemini(f"Sửa lỗi ngữ pháp và viết lại câu chuẩn xác hơn: {text}")
    await update.message.reply_text(res)

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /nhac [giây] [nội dung]")
        return
    try:
        delay = int(context.args[0])
        msg = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Đã đặt lịch nhắc sau {delay} giây!")
        
        async def send_remind():
            await asyncio.sleep(delay)
            await update.message.reply_text(f"⏰ NHẮC NHỞ:\n{msg}")
        
        asyncio.create_task(send_remind())
    except ValueError:
        await update.message.reply_text("❌ Số giây không hợp lệ.")

async def cmd_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /qr [text]")
        return
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(text)}"
    await update.message.reply_photo(photo=qr_url, caption=f"🔲 Mã QR: {text}")

async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini("Tạo 1 câu hỏi trắc nghiệm kiến thức vui ngắn gọn kèm 4 đáp án A, B, C, D và đáp án đúng ở cuối.")
    await update.message.reply_text(f"🎮 ĐỐ VUI / TRIVIA QUIZ\n\n{res}")

async def cmd_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: /tiente [số] [từ] sang [đến]")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Quy đổi tiền tệ chính xác cho: {query}")
    await update.message.reply_text(f"💱 Quy đổi tiền tệ:\n{res}")

async def cmd_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini("Cho một câu nói truyền cảm hứng hoặc truyện cười ngắn gọn thư giãn.")
    await update.message.reply_text(f"💡 Danh ngôn / Truyện cười:\n{res}")

# =========================================================
# XỬ LÝ ĐỌC FILE PDF & VOICE
# =========================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        await update.message.reply_text("⚠️ Bot chỉ hỗ trợ file PDF.")
        return
    msg = await update.message.reply_text("⏳ Đang tải và đọc tài liệu PDF...")
    
    async def process_pdf():
        try:
            file = await context.bot.get_file(doc.file_id)
            file_bytes = io.BytesIO(await file.download_as_bytearray())
            reader = PdfReader(file_bytes)
            text = "".join([page.extract_text() for page in reader.pages])[:8000]
            res = await ask_gemini(f"Tóm tắt các điểm chính từ tài liệu sau:\n{text}")
            await msg.edit_text(f"📄 Tóm tắt PDF:\n{res}")
        except Exception:
            await msg.edit_text("❌ Lỗi đọc file PDF.")
            
    asyncio.create_task(process_pdf()) 

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Bot đã nhận được tin nhắn thoại.")

# =========================================================
# XỬ LÝ CHAT CHÍNH VÀ MENU
# =========================================================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()
    lang = get_user_lang(uid)
    m = TEXTS[lang]["menu"]
    
    if text == m["reset"]:
        await cmd_reset(update, context); return
    elif text == m["img"]:
        await update.message.reply_text("💡 Gõ: /img [nội dung ảnh]"); return
    elif text == m["weather"]:
        await update.message.reply_text("💡 Gõ: /thoitiet [tên thành phố]"); return
    elif text == m["math"]:
        await update.message.reply_text("💡 Gõ: /toan [đề bài toán]"); return
    elif text == m["quiz"]:
        await cmd_quiz(update, context); return
    elif text == m["quote"]:
        await cmd_quote(update, context); return
    elif text == m["export"]:
        await cmd_export(update, context); return
    elif text == m["help"]:
        await help_command(update, context); return
    elif text == m["lang"]:
        await cmd_language(update, context); return

    if len(text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text("⚠️ Tin nhắn quá dài.")
        return

    asyncio.create_task(save_user_async(uid))
    lock = get_user_lock(uid)

    async with lock:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        urls = re.findall(r'https?://\S+', text)
        if urls:
            web_data = await fetch_webpage(urls[0])
            if web_data:
                text += f"\n\n--- Dữ liệu Web {urls[0]} ---\n{web_data}"

        try:
            history_context = "\n".join(user_chat_history.get(uid, [])[-4:])
            full_prompt = f"Lịch sử:\n{history_context}\n\nNgười dùng nói: {text}" if history_context else text
            
            answer = await ask_gemini(full_prompt)
            if not answer: raise RuntimeError("Rỗng")

            if uid not in user_chat_history:
                user_chat_history[uid] = []
                
            user_chat_history[uid].append(f"User: {update.message.text}")
            user_chat_history[uid].append(f"Bot: {answer}")
            
            if len(user_chat_history[uid]) > 30:
                user_chat_history[uid] = user_chat_history[uid][-30:]

            for i in range(0, len(answer), 4000):
                await update.message.reply_text(answer[i:i+4000])

        except Exception as e:
            logger.exception("Lỗi API Chat thực tế:")
            await update.message.reply_text(f"❌ Lỗi xử lý: {str(e)[:100]}")

# =========================================================
# MAIN KHỞI CHẠY
# =========================================================
def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("newchat", cmd_reset))
    app.add_handler(CommandHandler("img", cmd_image))
    app.add_handler(CommandHandler("tts", cmd_tts))
    app.add_handler(CommandHandler("thoitiet", cmd_weather))
    app.add_handler(CommandHandler("dich", cmd_translate))
    app.add_handler(CommandHandler("crypto", cmd_crypto))
    app.add_handler(CommandHandler("password", cmd_password))
    app.add_handler(CommandHandler("ascii", cmd_ascii))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("thongbao", cmd_thongbao))
    app.add_handler(CommandHandler("code", cmd_code))
    app.add_handler(CommandHandler("toan", cmd_math))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("nhac", cmd_reminder))
    app.add_handler(CommandHandler("qr", cmd_qr))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("tiente", cmd_currency))
    app.add_handler(CommandHandler("vui", cmd_quote))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("=" * 60)
    print("🚀 SIÊU TRỢ LÝ AI ĐÃ KHỞI ĐỘNG HOÀN HẢO KHÔNG LỖI!")
    print("=" * 60)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
