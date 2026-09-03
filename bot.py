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
# FLASK WEB SERVER CHO RENDER (GIỮ ALIVE)
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    uptime = round((time.time() - START_TIME) / 3600, 2)
    return f"Ultra AI Bot with Multi-language is online! Uptime: {uptime} hours."

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
    "Bạn là Siêu Trợ Lý AI đa năng tối thượng trên Telegram. "
    "Nhiệm vụ: Phản hồi cực kỳ nhanh, chính xác, lập luận logic sâu sắc, "
    "cung cấp code hoàn chỉnh khi được yêu cầu, thân thiện, và định dạng Markdown rõ ràng."
)

# =========================================================
# QUẢN LÝ DỮ LIỆU, NGÔN NGỮ & BỘ NHỚ
# =========================================================
USERS_FILE = "users.txt"
known_users = set()
user_locks = {}
user_chat_history = {}
user_languages = {}  # Lưu ngôn ngữ của user: 'vi' hoặc 'en'

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

def save_user(user_id):
    if user_id not in known_users:
        known_users.add(user_id)
        try:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")
        except Exception as e:
            logger.error(f"Lỗi lưu user: {e}")

load_users()

# Từ điển đa ngôn ngữ (Tiếng Việt & English)
TEXTS = {
    "vi": {
        "welcome": "🤖 <b>CHÀO MỪNG ĐẾN VỚI SIÊU TRỢ LÝ AI</b>\n\nBạn đã chọn ngôn ngữ: <b>Tiếng Việt 🇻🇳</b>\nHệ thống tích hợp hơn 25+ tính năng thông minh tối thượng.\nGõ /help để xem danh sách lệnh hoặc sử dụng menu bên dưới.",
        "lang_changed": "✅ Đã chuyển ngôn ngữ thành công sang <b>Tiếng Việt 🇻🇳</b>!",
        "choose_lang": "🌍 <b>Vui lòng chọn ngôn ngữ của bạn / Please select your language:</b>",
        "help": (
            "📖 <b>DANH SÁCH LỆNH HỆ THỐNG (TIẾNG VIỆT)</b>\n\n"
            "• `/language` - Đổi ngôn ngữ (Việt / Anh)\n"
            "• `/img <mô tả>` - Vẽ ảnh AI chất lượng cao\n"
            "• `/tts <văn bản>` - Chuyển văn bản thành giọng nói\n"
            "• `/thoitiet <thành phố>` - Xem thời tiết thời gian thực\n"
            "• `/dich <văn bản>` - Dịch thuật đa ngôn ngữ\n"
            "• `/code <yêu cầu>` - Lập trình & Debug mã nguồn\n"
            "• `/toan <bài toán>` - Giải toán chi tiết từng bước\n"
            "• `/crypto <coin>` - Tra cứu giá tiền mã hóa (BTC, ETH...)\n"
            "• `/password [độ dài]` - Tạo mật khẩu siêu bảo mật ngẫu nhiên\n"
            "• `/ascii <chữ>` - Biến văn bản thành nghệ thuật chữ ASCII\n"
            "• `/check <câu>` - Sửa lỗi ngữ pháp\n"
            "• `/nhac <giây> <nội dung>` - Đặt lịch hẹn nhắc nhở\n"
            "• `/qr <text>` - Tạo mã QR nhanh\n"
            "• `/quiz` - Chơi đố vui kiến thức\n"
            "• `/tiente <số> <từ> sang <đến>` - Đổi ngoại tệ\n"
            "• `/vui` - Câu nói hay / Truyện cười thư giãn\n"
            "• `/export` - Xuất file lịch sử chat (.txt)\n"
            "• `/reset` - Làm mới bộ nhớ đệm ngữ cảnh\n"
            "• Tải tệp PDF trực tiếp vào khung chat để bot tóm tắt!"
        ),
        "menu_reset": "🧹 Làm mới ngữ cảnh",
        "menu_img": "🎨 Vẽ ảnh",
        "menu_weather": "🌤️ Thời tiết",
        "menu_math": "🧮 Giải toán",
        "menu_quiz": "🎮 Câu đố Quiz",
        "menu_quote": "💡 Danh ngôn",
        "menu_export": "💾 Xuất lịch sử",
        "menu_help": "ℹ️ Hướng dẫn",
        "menu_lang": "🌍 Đổi ngôn ngữ"
    },
    "en": {
        "welcome": "🤖 <b>WELCOME TO ULTRA AI ASSISTANT</b>\n\nYou have selected: <b>English 🇬🇧</b>\nEquipped with 25+ advanced smart features.\nType /help to see all commands or use the menu below.",
        "lang_changed": "✅ Successfully changed language to <b>English 🇬🇧</b>!",
        "choose_lang": "🌍 <b>Please select your language / Vui lòng chọn ngôn ngữ:</b>",
        "help": (
            "📖 <b>SYSTEM COMMANDS LIST (ENGLISH)</b>\n\n"
            "• `/language` - Change language (English / Vietnamese)\n"
            "• `/img <prompt>` - Generate high-quality AI art\n"
            "• `/tts <text>` - Convert text to natural voice message\n"
            "• `/thoitiet <city>` - Real-time weather forecast\n"
            "• `/dich <text>` - Instant multi-language translation\n"
            "• `/code <request>` - Write & debug programming code\n"
            "• `/toan <math problem>` - Step-by-step math solver\n"
            "• `/crypto <coin>` - Check cryptocurrency prices (BTC, ETH...)\n"
            "• `/password [length]` - Generate secure random passwords\n"
            "• `/ascii <text>` - Turn text into cool ASCII text art\n"
            "• `/check <sentence>` - Fix grammar errors\n"
            "• `/nhac <seconds> <msg>` - Set a quick timer reminder\n"
            "• `/qr <text>` - Generate instant QR code\n"
            "• `/quiz` - Play fun trivia quiz games\n"
            "• `/tiente <amount> <from> to <to>` - Currency converter\n"
            "• `/vui` - Daily quotes & jokes\n"
            "• `/export` - Export chat history to .txt file\n"
            "• `/reset` - Reset conversation context memory\n"
            "• Upload a PDF file directly to chat for AI summarization!"
        ),
        "menu_reset": "🧹 Reset Context",
        "menu_img": "🎨 AI Image",
        "menu_weather": "🌤️ Weather",
        "menu_math": "🧮 Math Solver",
        "menu_quiz": "🎮 Trivia Quiz",
        "menu_quote": "💡 Daily Quote",
        "menu_export": "💾 Export History",
        "menu_help": "ℹ️ Help Guide",
        "menu_lang": "🌍 Change Language"
    }
}

def get_user_lang(uid):
    return user_languages.get(uid, "vi")

def get_markup(uid):
    lang = get_user_lang(uid)
    t = TEXTS[lang]
    keyboard = [
        [t["menu_reset"], t["menu_img"], t["menu_weather"]],
        [t["menu_math"], t["menu_quiz"], t["menu_quote"]],
        [t["menu_export"], t["menu_help"], t["menu_lang"]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# =========================================================
# CORE GEMINI & WEB SCRAPER
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
# TÍNH NĂNG NÂNG CAO (25+ TÍNH NĂNG)
# =========================================================

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

async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/img <prompt>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
    try:
        await update.message.reply_photo(photo=url, caption=f"🎨 <b>AI Art:</b> {prompt}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không thể tạo ảnh lúc này. / Cannot generate image.")

async def cmd_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/tts <text>`", parse_mode="Markdown")
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
        await update.message.reply_text("❌ Lỗi tạo giọng nói. / Voice generation error.")

async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = " ".join(context.args)
    if not loc:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/thoitiet <city>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        url = f"https://wttr.in/{urllib.parse.quote(loc)}?format=3"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as res:
                text = await res.text()
                await update.message.reply_text(f"🌤️ <b>Weather / Thời tiết:</b>\n{text}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không lấy được dữ liệu thời tiết. / Weather unavailable.")

async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/dich <text>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    uid = update.effective_user.id
    target = "English" if get_user_lang(uid) == "en" else "tiếng Việt"
    res = await ask_gemini(f"Dịch đoạn sau sang {target}, chỉ trả kết quả: {text}")
    await update.message.reply_text(f"🌐 <b>Translation / Bản dịch:</b>\n{res}", parse_mode="HTML")

async def cmd_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = " ".join(context.args).lower() or "bitcoin"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Cung cấp thông tin giá hiện tại và xu hướng ngắn gọn của đồng tiền mã hóa '{coin}' theo thị trường mới nhất.")
    await update.message.reply_text(f"🪙 <b>Crypto Info:</b>\n{res}", parse_mode="HTML")

async def cmd_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 12
    if context.args and context.args[0].isdigit():
        length = int(context.args[0])
        length = max(6, min(length, 64))
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    await update.message.reply_text(f"🔑 <b>Mật khẩu bảo mật / Secure Password:</b>\n`{pwd}`", parse_mode="Markdown")

async def cmd_ascii(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/ascii <text>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Tạo nghệ thuật chữ ASCII art đẹp và ngắn gọn cho từ khóa sau: {text}")
    await update.message.reply_text(f"```\n{res}\n```", parse_mode="Markdown")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history = user_chat_history.get(uid, [])
    if not history:
        await update.message.reply_text("📭 Chưa có lịch sử trò chuyện để xuất. / No chat history.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    bio = io.BytesIO("\n".join(history).encode('utf-8'))
    bio.name = "chat_history.txt"
    await update.message.reply_document(document=bio, caption="💾 Lịch sử chat của bạn / Chat History.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Lệnh dành riêng cho Admin.")
        return
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    text = f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n⏳ Uptime: {h}h {m}m {s}s\n👥 User: {len(known_users)}\n🧠 Model: {MODEL}"
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_chat_history[uid] = []
    lang = get_user_lang(uid)
    msg = "🧹 Đã làm mới ngữ cảnh thành công!" if lang == "vi" else "🧹 Context successfully reset!"
    await update.message.reply_text(msg)

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền.")
        return
    parts = update.message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("⚠️ Hướng dẫn: `/thongbao <nội dung>`", parse_mode="Markdown")
        return
    msg = await update.message.reply_text(f"🚀 Đang gửi thông báo đến {len(known_users)} người...")
    success, fail = 0, 0
    for uid in list(known_users):
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>Thông báo từ Admin:</b>\n\n{parts[1].strip()}", parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    await msg.edit_text(f"✅ Hoàn tất! Thành công: {success} | Thất bại: {fail}")

async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_query = " ".join(context.args)
    if not code_query:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/code <request>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Viết code hoàn chỉnh, tối ưu và giải thích ngắn gọn cho yêu cầu sau: {code_query}")
    await update.message.reply_text(res)

async def cmd_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    math_q = " ".join(context.args)
    if not math_q:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/toan <problem>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Giải chi tiết bài toán sau bước này qua bước khác: {math_q}")
    await update.message.reply_text(f"🧮 <b>Giải toán / Math Solver:</b>\n{res}", parse_mode="HTML")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        await update.message.reply_text("⚠️ Bot chỉ hỗ trợ tóm tắt tệp PDF. / PDF only.")
        return
    await update.message.reply_text("⏳ Đang tải và đọc tài liệu PDF... / Reading PDF...")
    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = io.BytesIO(await file.download_as_bytearray())
        reader = PdfReader(file_bytes)
        text = "".join([page.extract_text() for page in reader.pages])[:8000]
        
        res = await ask_gemini(f"Tóm tắt các điểm chính bằng tiếng Việt/Anh từ tài liệu sau:\n{text}")
        await update.message.reply_text(f"📄 <b>Tóm tắt PDF / PDF Summary:</b>\n{res}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không thể đọc file PDF này. / Error reading PDF.")

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/check <sentence>`", parse_mode="Markdown")
        return
    res = await ask_gemini(f"Sửa lỗi ngữ pháp và viết lại câu chuẩn xác hơn, giải thích ngắn gọn: {text}")
    await update.message.reply_text(res)

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/nhac <seconds> <message>`", parse_mode="Markdown")
        return
    try:
        delay = int(context.args[0])
        msg = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Đã đặt lịch nhắc sau {delay} giây! / Reminder set!")
        
        async def send_remind():
            await asyncio.sleep(delay)
            await update.message.reply_text(f"⏰ <b>NHẮC NHỞ / REMINDER:</b>\n{msg}", parse_mode="HTML")
        
        asyncio.create_task(send_remind())
    except ValueError:
        await update.message.reply_text("❌ Số giây không hợp lệ. / Invalid seconds.")

async def cmd_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/qr <text>`", parse_mode="Markdown")
        return
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(text)}"
    await update.message.reply_photo(photo=qr_url, caption=f"🔲 <b>Mã QR:</b> {text}", parse_mode="HTML")

async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await ask_gemini("Tạo 1 câu hỏi trắc nghiệm kiến thức vui ngắn gọn kèm 4 đáp án A, B, C, D và đáp án đúng ở cuối.")
    await update.message.reply_text(f"🎮 <b>ĐỐ VUI / TRIVIA QUIZ</b>\n\n{res}", parse_mode="HTML")

async def cmd_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Hướng dẫn / Usage: `/tiente 100 USD sang VND`", parse_mode="Markdown")
        return
    res = await ask_gemini(f"Quy đổi tiền tệ chính xác theo thị trường cho yêu cầu: {query}")
    await update.message.reply_text(f"💱 <b>Quy đổi tiền tệ / Currency:</b>\n{res}", parse_mode="HTML")

async def cmd_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await ask_gemini("Hãy cho một câu nói truyền cảm hứng (quote) thâm thúy hoặc một câu chuyện cười vui vẻ ngắn.")
    await update.message.reply_text(res)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Bot đã nhận được tin nhắn thoại của bạn. / Voice message received.")

# =========================================================
# LỆNH /start VÀ /help ĐA NGÔN NGỮ
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    asyncio.create_task(asyncio.to_thread(save_user, uid))
    
    # Nếu user chưa chọn ngôn ngữ, hiển thị bảng chọn ngôn ngữ trước
    if uid not in user_languages:
        keyboard = [
            [
                InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌍 <b>Vui lòng chọn ngôn ngữ của bạn / Please select your language:</b>",
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

# =========================================================
# XỬ LÝ TIN NHẮN CHAT CHÍNH
# =========================================================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()
    lang = get_user_lang(uid)
    t = TEXTS[lang]

    # Xử lý phím bấm nhanh từ Menu tương ứng với ngôn ngữ của user
    if text in [TEXTS["vi"]["menu_reset"], TEXTS["en"]["menu_reset"]]:
        await cmd_reset(update, context)
        return
    elif text in [TEXTS["vi"]["menu_img"], TEXTS["en"]["menu_img"]]:
        await update.message.reply_text("💡 Dùng lệnh / Use command: `/img <prompt>`", parse_mode="Markdown")
        return
    elif text in [TEXTS["vi"]["menu_weather"], TEXTS["en"]["menu_weather"]]:
        await update.message.reply_text("💡 Dùng lệnh / Use command: `/thoitiet <city>`", parse_mode="Markdown")
        return
    elif text in [TEXTS["vi"]["menu_math"], TEXTS["en"]["menu_math"]]:
        await update.message.reply_text("💡 Dùng lệnh / Use command: `/toan <problem>`", parse_mode="Markdown")
        return
    elif text in [TEXTS["vi"]["menu_quiz"], TEXTS["en"]["menu_quiz"]]:
        await cmd_quiz(update, context)
        return
    elif text in [TEXTS["vi"]["menu_quote"], TEXTS["en"]["menu_quote"]]:
        await cmd_quote(update, context)
        return
    elif text in [TEXTS["vi"]["menu_export"], TEXTS["en"]["menu_export"]]:
        await cmd_export(update, context)
        return
    elif text in [TEXTS["vi"]["menu_help"], TEXTS["en"]["menu_help"]]:
        await help_command(update, context)
        return
    elif text in [TEXTS["vi"]["menu_lang"], TEXTS["en"]["menu_lang"]]:
        await cmd_language(update, context)
        return

    if len(text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text("⚠️ Tin nhắn quá dài. / Message too long.")
        return

    asyncio.create_task(asyncio.to_thread(save_user, uid))
    lock = get_user_lock(uid)

    async with lock:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Trích xuất URL nếu người dùng gửi link web
        urls = re.findall(r'https?://\S+', text)
        if urls:
            web_data = await fetch_webpage(urls[0])
            if web_data:
                text += f"\n\n--- Dữ liệu từ Web {urls[0]} ---\n{web_data}"

        try:
            answer = await ask_gemini(text)
            if not answer:
                raise RuntimeError("Phản hồi rỗng.")

            if uid not in user_chat_history:
                user_chat_history[uid] = []
            user_chat_history[uid].append(f"User: {update.message.text}")
            user_chat_history[uid].append(f"Bot: {answer}")

            for i in range(0, len(answer), 4000):
                await update.message.reply_text(answer[i:i+4000])

        except Exception as e:
            logger.exception("Lỗi xử lý chat")
            await update.message.reply_text("❌ Hệ thống đang bận hoặc gặp lỗi kết nối mạng. / System busy.")

# =========================================================
# MAIN KHỞI CHẠY
# =========================================================
def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Đăng ký các Handler lệnh & Callback
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", cmd_language))
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

    # Xử lý File, Voice và Văn bản
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("=" * 60)
    print("🚀 SIÊU TRỢ LÝ AI ĐÃ HOẠT ĐỘNG VỚI ĐA NGÔN NGỮ (VI/EN) & 25+ TÍNH NĂNG")
    print("=" * 60)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
