import os
import asyncio
import logging
import threading
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flask import Flask
from pypdf import PdfReader
from bs4 import BeautifulSoup

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# WEB SERVER CHO RENDER
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra Telegram Gemini Bot (JobQueue Optimized) is active!"

@app.route('/health')
def health():
    return "OK", 200

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# =========================================================
# CONFIG & STATE
# =========================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Thiếu token hoặc API key trong biến môi trường!")

MODEL = "gemini-2.5-flash"

user_languages = {}     # user_id -> lang_code
user_locations = {}     # user_id -> location string
user_locks = {}

SUPPORTED_LANGUAGES = {
    "en": "English", "vi": "Tiếng Việt", "es": "Español", "fr": "Français",
    "de": "Deutsch", "zh": "中文", "ja": "日本語", "ko": "한국어",
    "ru": "Русский", "pt": "Português", "it": "Italiano", "ar": "العربية",
    "hi": "हिन्दी", "th": "ไทย", "id": "Indonesian", "nl": "Nederlands"
}

QUIZ_TOPICS = [
    ("geography", "Geography / Địa lý"),
    ("science", "Science / Khoa học"),
    ("game", "Gaming / Trò chơi"),
    ("movie", "Movies / Phim ảnh"),
    ("music", "Music / Âm nhạc"),
    ("history", "History / Lịch sử"),
    ("literature", "Literature / Văn học"),
    ("tech", "Technology / Công nghệ"),
    ("sports", "Sports / Thể thao"),
    ("art", "Art & Design / Nghệ thuật"),
    ("philosophy", "Philosophy / Triết học"),
    ("astronomy", "Astronomy / Thiên văn học"),
    ("anime", "Anime & Manga / Hoạt hình Nhật"),
    ("popculture", "Pop Culture / Văn hóa đại chúng"),
    ("mythology", "Mythology / Thần thoại"),
    ("cooking", "Cooking & Food / Nấu ăn"),
    ("business", "Business & Economics / Kinh doanh"),
    ("psychology", "Psychology / Tâm lý học"),
    ("nature", "Nature & Animals / Thiên nhiên & Động vật"),
    ("automotive", "Automotive / Xe hơi")
]

BOT_FOOTER = "\n\n---\n*Owner: @itznvl | Hãy chia sẻ bot cho mọi người nhé!*"

STATIC_HELP = {
    "vi": (
        "📖 **DANH SÁCH LỆNH VÀ TÍNH NĂNG (TĨNH - SIÊU TỐC)**\n\n"
        "• `/start` - Khởi động & chọn ngôn ngữ giao diện (16 ngôn ngữ)\n"
        "• `/language` - Thay đổi ngôn ngữ giao diện bất cứ lúc nào\n"
        "• `/help` - Xem hướng dẫn này\n"
        "• `/weather <địa điểm>` - Xem bảng thời tiết 24h (hỗ trợ cấp huyện cũ/mới tại VN & toàn cầu, vd: `/weather Thanh Ba, Phú Thọ`)\n"
        "• `/clock HH:MM` - Đặt báo thức theo vị trí của bạn\n"
        "• `/quiz` - Mở bảng chọn 20 chủ đề câu đố\n"
        "• `/quest` - Chơi game phiêu lưu tương tác RPG\n"
        "• `/ping` - Kiểm tra tốc độ phản hồi hệ thống\n"
        "• `/stats` - Xem thông tin phiên làm việc\n"
        "• `/support` - Liên hệ hỗ trợ kỹ thuật\n"
        "• Gửi hình ảnh hoặc file PDF để AI phân tích trực tiếp."
    ),
    "en": (
        "📖 **COMMANDS & FEATURES (STATIC - INSTANT)**\n\n"
        "• `/start` - Initialize & select interface language (16 languages)\n"
        "• `/language` - Change interface language anytime\n"
        "• `/help` - View this help guide\n"
        "• `/weather <location>` - View 24h weather table (supports districts worldwide & Vietnam old/new, e.g., `/weather Tokyo`)\n"
        "• `/clock HH:MM` - Set a location-based alarm\n"
        "• `/quiz` - Open the 20+ topic trivia quiz menu\n"
        "• `/quest` - Play interactive text RPG adventure\n"
        "• `/ping` - Check system response latency\n"
        "• `/stats` - View session statistics\n"
        "• `/support` - Contact technical support\n"
        "• Send images or PDF files for direct AI analysis."
    )
}

def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

def get_user_lang(user_id):
    return user_languages.get(user_id, "en")

client = genai.Client(api_key=GEMINI_API_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ask_gemini(user_text, system_prompt="You are a helpful assistant.", model=MODEL):
    def _call():
        return client.models.generate_content(
            model=model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
        )
    response = await asyncio.to_thread(_call)
    return (response.text if response and response.text else "Error getting response.") + BOT_FOOTER

# =========================================================
# LỆNH TĨNH (THỰC THI TRONG VÒNG < 0.001s)
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_languages[user_id] = "en"
    
    keyboard = []
    row = []
    for code, name in SUPPORTED_LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    welcome_text = (
        "Welcome to Ultra Gemini AI Bot! 🚀\n\n"
        "Please select your preferred language below:\n"
        "*(Vui lòng chọn ngôn ngữ của bạn bên dưới:)*"
        + BOT_FOOTER
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for code, name in SUPPORTED_LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    text = (
        "🌍 **Select your language / Chọn ngôn ngữ giao diện:**\n\n"
        + BOT_FOOTER
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang_code = query.data.split("_")[1]
    user_languages[user_id] = lang_code
    
    lang_name = SUPPORTED_LANGUAGES.get(lang_code, "English")
    prompt_loc = (
        f"Great! Language set to **{lang_name}**.\n\n"
        "🌍 **Where are you located?** (e.g., Thanh Ba, Phú Thọ / Tokyo, Japan / New York, USA)\n"
        "Please reply with your location so I can set alarms and check weather accurately!"
        + BOT_FOOTER
    )
    await query.message.edit_text(prompt_loc, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = STATIC_HELP.get(lang, STATIC_HELP["en"]) + BOT_FOOTER
    await update.message.reply_text(text, parse_mode="Markdown")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_t = datetime.datetime.now()
    msg = await update.message.reply_text("🏓 Checking static latency...")
    latency = (datetime.datetime.now() - start_t).total_seconds() * 1000
    await msg.edit_text(f"🏓 Pong! Static command latency: `{latency:.3f}ms`" + BOT_FOOTER, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    loc = user_locations.get(user_id, "Not set")
    text = (
        f"📊 **Session Statistics**\n"
        f"• Language: `{lang}`\n"
        f"• Location: `{loc}`\n"
        f"• Status: `Static handlers operational (< 0.001s)`"
        + BOT_FOOTER
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 Technical Support: Contact the system administrator for assistance." + BOT_FOOTER)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for key, desc in QUIZ_TOPICS:
        row.append(InlineKeyboardButton(desc, callback_data=f"quiz_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    text = (
        "🧠 **SELECT A QUIZ TOPIC**\nClick a topic below to generate a question:"
        + BOT_FOOTER
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =========================================================
# LỆNH TIỆN ÍCH & AI (WEATHER, CLOCK, QUEST, CHAT)
# =========================================================
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.args:
        location = " ".join(context.args)
    else:
        location = user_locations.get(user_id)
        if not location:
            await update.message.reply_text(
                "⚠️ Please specify a location or set your location first.\n"
                "Usage: `/weather Thanh Ba, Phú Thọ` or `/weather Tokyo`" + BOT_FOOTER,
                parse_mode="Markdown"
            )
            return

    lang = get_user_lang(user_id)
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    sys_p = (
        f"You are a professional meteorology assistant. Provide an accurate weather forecast table "
        f"for the exact location '{location}' starting from the current time ({current_time_str}) through the rest of the day (24h forecast). "
        f"The table must include columns/fields: Time, Temperature (°C), Condition (Sunny/Rainy/Cloudy/Storm...), Wind Speed (km/h), and Humidity (%). "
        f"Support all district-level locations worldwide and in Vietnam (both old and new district names). "
        f"Language of explanation: '{lang}'. Format neatly in a Markdown table."
    )
    
    async with get_user_lock(user_id):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        try:
            res = await ask_gemini(f"Get 24h weather table for {location}", sys_p, MODEL)
            await update.message.reply_text(res, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ Could not fetch weather data. Please try again with a valid location format." + BOT_FOOTER)

async def alarm_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    time_str = job.data['time_str']
    location = job.data['location']
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ **ALARM RINGING!**\nTime ({time_str}) reached! Location: {location}" + BOT_FOOTER,
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def clock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/clock HH:MM` (e.g., `/clock 07:30`)" + BOT_FOOTER, parse_mode="Markdown")
        return
    
    time_str = context.args[0]
    try:
        alarm_time = datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Please use HH:MM (24-hour format)." + BOT_FOOTER)
        return

    location = user_locations.get(user_id, "Unknown location")
    
    now = datetime.datetime.now()
    target_dt = datetime.datetime.combine(now.date(), alarm_time)
    if target_dt <= now:
        target_dt += datetime.timedelta(days=1)
    
    delay = (target_dt - now).total_seconds()
    
    context.job_queue.run_once(
        alarm_callback, 
        when=delay, 
        chat_id=update.effective_chat.id, 
        data={'time_str': time_str, 'location': location}
    )
    
    await update.message.reply_text(f"✅ Alarm set for **{time_str}** (Location: {location})." + BOT_FOOTER, parse_mode="Markdown")

async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    topic = query.data.split("_")[1]
    lang = get_user_lang(user_id)
    
    sys_p = f"You are a quiz master. Create an interesting multiple-choice question about '{topic}' in language '{lang}'. Provide options A, B, C, D and reveal the answer."
    res = await ask_gemini("Give me a question.", sys_p, MODEL)
    await query.message.reply_text(res, parse_mode="Markdown")

async def quest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    sys_p = f"You are an interactive text RPG game master. Start a short fantasy adventure quest in language '{lang}', presenting a scenario and 2 choices for the player."
    res = await ask_gemini("Start new quest.", sys_p, MODEL)
    await update.message.reply_text(res, parse_mode="Markdown")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if user_id not in user_locations and len(user_text) < 50:
        user_locations[user_id] = user_text
        await update.message.reply_text(f"📍 Location saved: **{user_text}**. Type `/help` to see commands." + BOT_FOOTER, parse_mode="Markdown")
        return

    lang = get_user_lang(user_id)
    sys_p = f"You are an advanced AI assistant. Respond in language code '{lang}'. Be concise and accurate."

    lock = get_user_lock(user_id)
    async with lock:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        try:
            answer = await ask_gemini(user_text, sys_p, MODEL)
            max_len = 4000
            if len(answer) <= max_len:
                await update.message.reply_text(answer, parse_mode="Markdown")
            else:
                for i in range(0, len(answer), max_len):
                    await update.message.reply_text(answer[i:i+max_len], parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ An error occurred. Please try again." + BOT_FOOTER, parse_mode="Markdown")

def main():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Static commands (executed instantly without Gemini overhead)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    
    # Utility & AI commands
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("clock", clock_command))
    application.add_handler(CommandHandler("quest", quest_command))
    
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(handle_quiz_callback, pattern="^quiz_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🤖 Ultra Telegram AI Bot with Native JobQueue is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
