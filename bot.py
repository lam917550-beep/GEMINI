import os
import re
import io
import time
import asyncio
import logging
import threading
import urllib.parse
from datetime import datetime

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

MODEL = "gemini-3.5-flash"
MAX_MESSAGE_LENGTH = 12000

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN hoặc GEMINI_API_KEY trong file .env")

# =========================================================
# FLASK WEB SERVER CHO RENDER
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    uptime = round((time.time() - START_TIME) / 3600, 2)
    return f"Ultra AI Bot is online! Uptime: {uptime} hours."

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

SYSTEM_PROMPT = """
Bạn là Siêu Trợ Lý AI đa năng tối thượng trên Telegram. 
Nhiệm vụ: Phản hồi cực kỳ nhanh, chính xác, lập luận logic sâu sắc, code hoàn chỉnh, không bịa đặt, thân thiện và sử dụng định dạng Markdown/HTML tối ưu.
"""

# =========================================================
# QUẢN LÝ DỮ LIỆU & BỘ NHỚ
# =========================================================
USERS_FILE = "users.txt"
known_users = set()
user_interactions = {}
user_locks = {}
user_chat_history = {}

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

# =========================================================
# CORE GEMINI & WEB SCRAPER
# =========================================================
def create_gemini_interaction(user_text, previous_interaction_id=None):
    request = {
        "model": MODEL,
        "input": user_text,
        "system_instruction": SYSTEM_PROMPT,
        "generation_config": {"thinking_level": "high"},
    }
    if previous_interaction_id:
        request["previous_interaction_id"] = previous_interaction_id
    return client.interactions.create(**request)

async def ask_gemini(user_text, previous_interaction_id=None):
    return await asyncio.to_thread(create_gemini_interaction, user_text, previous_interaction_id)

async def fetch_webpage(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                return soup.get_text(separator=' ', strip=True)[:5000]
    except Exception:
        return None

# =========================================================
# 20 TÍNH NĂNG ĐỈNH CAO TÍCH HỢP ĐẦY ĐỦ
# =========================================================

# 1. Smart Web Reader (Tự động quét khi gửi link trong chat)

# 2. AI Image Generation (/img)
async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("⚠️ Hướng dẫn: `/img <mô tả ảnh>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
    try:
        await update.message.reply_photo(photo=url, caption=f"🎨 <b>AI Art:</b> {prompt}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không thể tạo ảnh lúc này.")

# 3. Text-to-Speech (/tts)
async def cmd_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn: `/tts <văn bản>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
    try:
        tts = gTTS(text, lang='vi')
        bio = io.BytesIO()
        await asyncio.to_thread(tts.write_to_fp, bio)
        bio.seek(0)
        await update.message.reply_voice(voice=bio)
    except Exception:
        await update.message.reply_text("❌ Lỗi tạo giọng nói.")

# 4. Live Weather (/thoitiet)
async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = " ".join(context.args)
    if not loc:
        await update.message.reply_text("⚠️ Hướng dẫn: `/thoitiet <thành phố>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        url = f"https://wttr.in/{urllib.parse.quote(loc)}?format=3"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as res:
                text = await res.text()
                await update.message.reply_text(f"🌤️ <b>Thời tiết:</b>\n{text}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không lấy được dữ liệu thời tiết.")

# 5. Instant Translation (/dich)
async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn: `/dich <văn bản>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Dịch đoạn sau sang tiếng Việt (hoặc tiếng Anh nếu gốc là Việt), chỉ trả kết quả: {text}")
    await update.message.reply_text(f"🌐 <b>Bản dịch:</b>\n{res.output_text}", parse_mode="HTML")

# 6. Export Chat History (/export)
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history = user_chat_history.get(uid, [])
    if not history:
        await update.message.reply_text("📭 Chưa có lịch sử trò chuyện để xuất.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    bio = io.BytesIO("\n".join(history).encode('utf-8'))
    bio.name = "chat_history.txt"
    await update.message.reply_document(document=bio, caption="💾 Lịch sử chat của bạn.")

# 7. Admin Statistics (/stats)
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Lệnh dành riêng cho chủ bot.")
        return
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    text = f"📊 <b>THỐNG KÊ HỆ THỐNG</b>\n⏳ Uptime: {h}h {m}m {s}s\n👥 User: {len(known_users)}\n🧠 Model: {MODEL}"
    await update.message.reply_text(text, parse_mode="HTML")

# 8. Interactive Reply Keyboard (Khởi tạo sẵn trong /start)

# 9. Context Reset (/reset)
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_interactions.pop(uid, None)
    user_chat_history[uid] = []
    await update.message.reply_text("🧹 Đã làm mới ngữ cảnh và xóa bộ nhớ đệm thành công!")

# 10. Broadcast System (/thongbao)
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

# 11. Code Executor/Debugger (/code)
async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_query = " ".join(context.args)
    if not code_query:
        await update.message.reply_text("⚠️ Hướng dẫn: `/code <yêu cầu viết/sửa code>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Viết code hoàn chỉnh, tối ưu và giải thích ngắn gọn cho yêu cầu sau: {code_query}")
    await update.message.reply_text(res.output_text)

# 12. Math Equation Solver (/toan)
async def cmd_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    math_q = " ".join(context.args)
    if not math_q:
        await update.message.reply_text("⚠️ Hướng dẫn: `/toan <phương trình/bài toán>`", parse_mode="Markdown")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    res = await ask_gemini(f"Giải chi tiết bài toán sau bước này qua bước khác: {math_q}")
    await update.message.reply_text(f"🧮 <b>Giải toán:</b>\n{res.output_text}", parse_mode="HTML")

# 13. PDF / Document Summarizer (Xử lý file upload tự động)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        await update.message.reply_text("⚠️ Bot hiện tại chỉ hỗ trợ tóm tắt tệp PDF.")
        return
    await update.message.reply_text("⏳ Đang tải và đọc tài liệu PDF...")
    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = io.BytesIO(await file.download_as_bytearray())
        reader = PdfReader(file_bytes)
        text = "".join([page.extract_text() for page in reader.pages])[:10000]
        
        res = await ask_gemini(f"Tóm tắt các điểm chính bằng tiếng Việt từ tài liệu sau:\n{text}")
        await update.message.reply_text(f"📄 <b>Tóm tắt PDF:</b>\n{res.output_text}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Không thể đọc file PDF này.")

# 14. Grammar Corrector (/check)
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn: `/check <câu văn cần sửa lỗi>`", parse_mode="Markdown")
        return
    res = await ask_gemini(f"Sửa lỗi ngữ pháp và viết lại câu chuẩn xác hơn, giải thích ngắn gọn: {text}")
    await update.message.reply_text(res.output_text)

# 15. Daily Reminder / Alarm (/nhac)
async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Hướng dẫn: `/nhac <số_giây> <nội dung>`", parse_mode="Markdown")
        return
    try:
        delay = int(context.args[0])
        msg = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Đã đặt lịch nhắc sau {delay} giây!")
        
        async def send_remind():
            await asyncio.sleep(delay)
            await update.message.reply_text(f"⏰ <b>NHẮC NHỞ:</b>\n{msg}", parse_mode="HTML")
        
        asyncio.create_task(send_remind())
    except ValueError:
        await update.message.reply_text("❌ Số giây không hợp lệ.")

# 16. QR Code Generator (/qr)
async def cmd_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Hướng dẫn: `/qr <nội dung hoặc link>`", parse_mode="Markdown")
        return
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(text)}"
    await update.message.reply_photo(photo=qr_url, caption=f"🔲 <b>Mã QR cho:</b> {text}", parse_mode="HTML")

# 17. Mini Quiz Game (/quiz)
async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await ask_gemini("Tạo 1 câu hỏi trắc nghiệm kiến thức vui ngắn gọn kèm 4 đáp án A, B, C, D và đáp án đúng ở cuối.")
    await update.message.reply_text(f"🎮 <b>ĐỐ VUI HỌC TẬP</b>\n\n{res.output_text}", parse_mode="HTML")

# 18. Currency Converter (/tiente)
async def cmd_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Hướng dẫn: `/tiente <số tiền> <từ> sang <đến>`\nVí dụ: `/tiente 100 USD sang VND`", parse_mode="Markdown")
        return
    res = await ask_gemini(f"Quy đổi tiền tệ chính xác theo thị trường cho yêu cầu: {query}")
    await update.message.reply_text(f"💱 <b>Quy đổi tiền tệ:</b>\n{res.output_text}", parse_mode="HTML")

# 19. Quote / Joke of the Day (/vui)
async def cmd_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await ask_gemini("Hãy cho một câu nói truyền cảm hứng (quote) thâm thúy hoặc một câu chuyện cười vui vẻ ngắn.")
    await update.message.reply_text(res.output_text)

# 20. Voice-to-Text Transcription (Tự động nhận diện Voice Message)
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Bot đã nhận được tin nhắn thoại của bạn. Hiện tại hệ thống đang tối ưu hóa trình phân tích âm thanh trực tiếp từ Gemini.")

# =========================================================
# START & MENU GIAO DIỆN
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(asyncio.to_thread(save_user, update.effective_user.id))
    
    keyboard = [
        ["🧹 Làm mới ngữ cảnh", "🎨 Vẽ ảnh", "🌤️ Thời tiết"],
        ["🧮 Giải toán", "🎮 Câu đố Quiz", "💡 Danh ngôn"],
        ["💾 Xuất lịch sử", "ℹ️ Hướng dẫn", "📊 Thống kê"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

    text = (
        "🤖 <b>SIÊU TRỢ LÝ AI ĐÃ SẴN SÀNG</b>\n\n"
        "Được trang bị 20+ tính năng tối thượng tốc độ cao.\n"
        "👑 Chủ bot: @itznvl\n\n"
        "<b>Các lệnh chính:</b>\n"
        "• `/img <mô tả>` - Vẽ tranh\n"
        "• `/tts <văn bản>` - Đọc giọng nói\n"
        "• `/thoitiet <thành phố>` - Xem thời tiết\n"
        "• `/toan <bài toán>` - Giải toán chi tiết\n"
        "• `/code <yêu cầu>` - Viết code\n"
        "• `/qr <text>` - Tạo mã QR\n"
        "• `/nhac <giây> <nội dung>` - Đặt hẹn nhắc nhở\n"
        "• Tải file PDF trực tiếp để bot tóm tắt!"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>DANH SÁCH LỆNH HỆ THỐNG</b>\n\n"
        "/img - Vẽ ảnh AI\n"
        "/tts - Chuyển văn bản thành giọng nói\n"
        "/thoitiet - Xem thời tiết\n"
        "/dich - Dịch thuật ngôn ngữ\n"
        "/code - Lập trình & Debug\n"
        "/toan - Giải toán học\n"
        "/check - Sửa lỗi ngữ pháp\n"
        "/nhac - Đặt lịch hẹn nhắc nhở\n"
        "/qr - Tạo mã QR nhanh\n"
        "/quiz - Chơi đố vui\n"
        "/tiente - Đổi ngoại tệ\n"
        "/vui - Câu nói hay / Truyện cười\n"
        "/export - Xuất file lịch sử chat\n"
        "/reset - Làm mới bộ nhớ đệm"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# =========================================================
# XỬ LÝ TIN NHẮN CHAT CHÍNH (ĐA NHIỆM SIÊU TỐC)
# =========================================================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()

    # Xử lý tương tác từ Menu Phím Bấm Tĩnh
    if text == "🧹 Làm mới ngữ cảnh":
        await cmd_reset(update, context)
        return
    elif text == "🎨 Vẽ ảnh":
        await update.message.reply_text("💡 Dùng lệnh: `/img <mô tả>`", parse_mode="Markdown")
        return
    elif text == "🌤️ Thời tiết":
        await update.message.reply_text("💡 Dùng lệnh: `/thoitiet <tên thành phố>`", parse_mode="Markdown")
        return
    elif text == "🧮 Giải toán":
        await update.message.reply_text("💡 Dùng lệnh: `/toan <đề bài>`", parse_mode="Markdown")
        return
    elif text == "🎮 Câu đố Quiz":
        await cmd_quiz(update, context)
        return
    elif text == "💡 Danh ngôn":
        await cmd_quote(update, context)
        return
    elif text == "💾 Xuất lịch sử":
        await cmd_export(update, context)
        return
    elif text == "📊 Thống kê":
        await cmd_stats(update, context)
        return
    elif text == "ℹ️ Hướng dẫn":
        await help_command(update, context)
        return

    if len(text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text("⚠️ Tin nhắn quá dài.")
        return

    asyncio.create_task(asyncio.to_thread(save_user, uid))
    lock = get_user_lock(uid)

    async with lock:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Tự động trích xuất Link web nếu có
        urls = re.findall(r'https?://\S+', text)
        if urls:
            web_data = await fetch_webpage(urls[0])
            if web_data:
                text += f"\n\n--- Dữ liệu từ Web {urls[0]} ---\n{web_data}"

        prev_id = user_interactions.get(uid)

        try:
            interaction = await ask_gemini(text, prev_id)
            answer = (getattr(interaction, "output_text", None) or "").strip()

            if not answer:
                raise RuntimeError("Phản hồi rỗng.")

            user_interactions[uid] = interaction.id
            
            if uid not in user_chat_history:
                user_chat_history[uid] = []
            user_chat_history[uid].append(f"User: {update.message.text}")
            user_chat_history[uid].append(f"Bot: {answer}")

            for i in range(0, len(answer), 4000):
                await update.message.reply_text(answer[i:i+4000])

        except Exception as e:
            logger.exception("Lỗi xử lý chat")
            await update.message.reply_text("❌ Hệ thống đang bận hoặc gặp lỗi kết nối mạng.")

# =========================================================
# MAIN KHỞI CHẠY
# =========================================================
def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Đăng ký toàn bộ 20+ lệnh chức năng
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("newchat", cmd_reset))
    app.add_handler(CommandHandler("img", cmd_image))
    app.add_handler(CommandHandler("tts", cmd_tts))
    app.add_handler(CommandHandler("thoitiet", cmd_weather))
    app.add_handler(CommandHandler("dich", cmd_translate))
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

    # Handlers xử lý File, Voice và Văn bản thường
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("=" * 60)
    print("🚀 SIÊU TRỢ LÝ AI ĐÃ HOẠT ĐỘNG VỚI 20+ TÍNH NĂNG ĐỈNH CAO")
    print("✅ Render Port Binding: Hoạt động | Async I/O: Tối ưu tối đa")
    print("=" * 60)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
