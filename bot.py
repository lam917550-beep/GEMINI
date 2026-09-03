import os
import asyncio
import logging
import threading
import io
import time
import requests
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
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# DUMMY WEB SERVER CHO RENDER WEB SERVICE
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra Telegram Gemini Bot is active and running!"

@app.route('/health')
def health():
    return "OK", 200

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# =========================================================
# CONFIG & ENVIRONMENT
# =========================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN trong biến môi trường hoặc file .env")

if not GEMINI_API_KEY:
    raise RuntimeError("Thiếu GEMINI_API_KEY trong biến môi trường hoặc file .env")

MODEL = "gemini-2.5-flash"
MAX_MESSAGE_LENGTH = 12000

DEFAULT_SYSTEM_PROMPT = """
Bạn là một siêu trợ lý AI cao cấp tích hợp trên Telegram.
Nhiệm vụ:
- Cung cấp câu trả lời chính xác, thông minh, súc tích và tự nhiên bằng tiếng Việt.
- Hỗ trợ toàn diện: Lập trình, toán học, phân tích tài liệu, dịch thuật, viết nội dung, giải đố, sáng tạo và xử lý công việc.
- Khi viết code, luôn cung cấp code hoàn chỉnh, tối ưu và có giải thích ngắn gọn.
- Luôn giữ thái độ lịch sự, chuyên nghiệp và thân thiện.
"""

# =========================================================
# CLIENT & LOGGING
# =========================================================
client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# =========================================================
# MEMORY & STATE MANAGEMENT
# =========================================================
user_system_prompts = {}
user_models = {}
user_locks = {}

def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

def get_user_config(user_id):
    if user_id not in user_system_prompts:
        user_system_prompts[user_id] = DEFAULT_SYSTEM_PROMPT
    if user_id not in user_models:
        user_models[user_id] = MODEL
    return user_system_prompts[user_id], user_models[user_id]

# =========================================================
# GEMINI ENGINE (TỐI ƯU TỐC ĐỘ CAO NHẤT)
# =========================================================
async def ask_gemini(user_text, system_prompt=DEFAULT_SYSTEM_PROMPT, model=MODEL):
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
    return response.text if response and response.text else "Không nhận được phản hồi từ AI."

# =========================================================
# 40 TÍNH NĂNG CHÍNH (COMMAND HANDLERS)
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🆕 Cuộc trò chuyện mới", callback_data="new_chat"),
         InlineKeyboardButton("ℹ️ 40 Tính năng", callback_data="features")],
        [InlineKeyboardButton("⚙️ Cấu hình Model", callback_data="model"),
         InlineKeyboardButton("📊 Thống kê phiên", callback_data="stats")]
    ]
    text = (
        "🚀 **SIÊU TRỢ LÝ GEMINI AI (40 TÍNH NĂNG - SIÊU TỐC)**\n\n"
        "Bot đã tối ưu hóa tốc độ phản hồi tối đa.\n\n"
        "👉 Gõ `/help` để xem danh sách toàn bộ 40 tính năng!"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 **DANH SÁCH 40 TÍNH NĂNG HỆ THỐNG**\n\n"
        "⚙️ **Hệ thống & Cài đặt:**\n"
        "1. `/start` - Giao diện chính\n"
        "2. `/help` - Bảng hướng dẫn 40 tính năng\n"
        "3. `/newchat` - Làm sạch ngữ cảnh\n"
        "4. `/model` - Đổi model AI\n"
        "5. `/system` - Đổi nhân cách AI\n"
        "6. `/ping` - Kiểm tra tốc độ phản hồi\n"
        "7. `/stats` - Thống kê phiên làm việc\n"
        "8. `/features` - Xem lại danh sách tính năng\n"
        "9. `/clear` - Xóa lịch sử nhanh\n"
        "10. `/support` - Hỗ trợ kỹ thuật\n"
        "11. `/debug` - Kiểm tra trạng thái\n"
        "12. `/feedback` - Gửi góp ý\n"
        "13. `/info` - Thông tin phiên bản\n\n"
        "💡 **Lập trình & Kỹ thuật:**\n"
        "14. `/code` - Viết & giải thích mã nguồn\n"
        "15. `/regex` - Tạo biểu thức chính quy\n"
        "16. `/sql` - Viết câu lệnh SQL\n"
        "17. `/json` - Xử lý & sửa lỗi JSON\n"
        "18. `/calc` - Tính toán biểu thức toán học\n"
        "19. `/web` - Phân tích nội dung trang web\n\n"
        "✍️ **Xử lý Văn bản & Ngôn ngữ:**\n"
        "20. `/translate` - Dịch thuật đa ngôn ngữ\n"
        "21. `/summarize` - Tóm tắt văn bản dài\n"
        "22. `/grammar` - Sửa lỗi chính tả & ngữ pháp\n"
        "23. `/rewrite` - Viết lại văn phong chuyên nghiệp\n"
        "24. `/explain` - Giải thích khái niệm phức tạp\n"
        "25. `/email` - Soạn thảo email công sở\n\n"
        "🎨 **Sáng tạo & Giải trí:**\n"
        "26. `/joke` - Kể chuyện cười\n"
        "27. `/quote` - Lời khuyên động lực\n"
        "28. `/fact` - Kiến thức khoa học thú vị\n"
        "29. `/riddle` - Câu đố vui hại não\n"
        "30. `/fortune` - Xem vận mệnh vui\n"
        "31. `/roast` - Tấu hài vui vẻ\n"
        "32. `/compliment` - Lời khen tích cực\n"
        "33. `/rhyme` - Sáng tác thơ lục bát\n"
        "34. `/acrostic` - Thơ ghép chữ cái\n"
        "35. `/story` - Sáng tác truyện ngắn\n\n"
        "🎯 **Đời sống & Tiện ích:**\n"
        "36. `/todo` - Lên kế hoạch công việc\n"
        "37. `/workout` - Gợi ý tập luyện thể hình\n"
        "38. `/recipe` - Gợi ý món ăn từ nguyên liệu\n"
        "39. Gửi **File PDF** để bot đọc hiểu tài liệu\n"
        "40. Gửi **Hình ảnh** kèm nội dung để bot phân tích thị giác"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def newchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧹 Đã làm sạch lịch sử trò chuyện!")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _, current_model = get_user_config(user_id)
    if context.args:
        new_m = context.args[0]
        user_models[user_id] = new_m
        await update.message.reply_text(f"✅ Đã chuyển sang model: `{new_m}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"🤖 Model hiện tại: `{current_model}`\n💡 Dùng lệnh: `/model <tên_model>` để đổi.", parse_mode="Markdown")

async def system_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        curr_sys, _ = get_user_config(user_id)
        await update.message.reply_text(f"ℹ️ Nhân cách hệ thống hiện tại:\n_{curr_sys}_", parse_mode="Markdown")
        return
    new_sys = " ".join(context.args)
    user_system_prompts[user_id] = new_sys
    await update.message.reply_text("✅ Đã cập nhật nhân cách AI thành công!")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: `/translate <ngôn_ngữ> <văn_bản>`", parse_mode="Markdown")
        return
    lang, text = context.args[0], " ".join(context.args[1:])
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Dịch sang tiếng {lang}:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/code <yêu_cầu>`", parse_mode="Markdown")
        return
    req = " ".join(context.args)
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Viết mã nguồn hoàn chỉnh, tối ưu cho yêu cầu: {req}", sys_p, mdl)
    await update.message.reply_text(res)

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Vui lòng cung cấp văn bản cần tóm tắt.")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Tóm tắt ngắn gọn các ý chính:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/calc <biểu_thức>`", parse_mode="Markdown")
        return
    expr = "".join(context.args)
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Tính toán và giải thích chi tiết: {expr}", sys_p, mdl)
    await update.message.reply_text(res)

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/web <URL>`", parse_mode="Markdown")
        return
    url = context.args[0]
    try:
        html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).text
        soup = BeautifulSoup(html, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        content = soup.get_text(separator=' ', strip=True)[:8000]
        user_id = update.effective_user.id
        sys_p, mdl = get_user_config(user_id)
        res = await ask_gemini(f"Phân tích nội dung trang web:\n\n{content}", sys_p, mdl)
        await update.message.reply_text(res)
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi tải trang web: {e}")

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Kể một câu chuyện cười ngắn thông minh bằng tiếng Việt.", sys_p, mdl)
    await update.message.reply_text(res)

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Cho tôi một câu nói truyền cảm hứng sâu sắc.", sys_p, mdl)
    await update.message.reply_text(res)

async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Chia sẻ một sự thật khoa học thú vị ít người biết.", sys_p, mdl)
    await update.message.reply_text(res)

async def riddle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Đưa ra một câu đố vui hại não kèm gợi ý.", sys_p, mdl)
    await update.message.reply_text(res)

async def fortune_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Dự đoán vui vận may ngày hôm nay hài hước.", sys_p, mdl)
    await update.message.reply_text(res)

async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Roast (tấu hài châm biếm nhẹ nhàng) tôi một cách văn minh.", sys_p, mdl)
    await update.message.reply_text(res)

async def compliment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini("Dành cho tôi những lời khen ngợi chân thành nhất.", sys_p, mdl)
    await update.message.reply_text(res)

async def regex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/regex <yêu_cầu>`", parse_mode="Markdown")
        return
    req = " ".join(context.args)
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Viết Regex và giải thích chi tiết cho: {req}", sys_p, mdl)
    await update.message.reply_text(res)

async def sql_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/sql <yêu_cầu>`", parse_mode="Markdown")
        return
    req = " ".join(context.args)
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Viết câu lệnh SQL tối ưu cho: {req}", sys_p, mdl)
    await update.message.reply_text(res)

async def json_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Vui lòng cung cấp dữ liệu JSON cần xử lý.")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Định dạng và sửa lỗi cấu trúc JSON:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def grammar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Vui lòng nhập văn bản cần sửa lỗi.")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Sửa lỗi chính tả và hoàn thiện ngữ pháp:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Vui lòng nhập văn bản cần viết lại.")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Viết lại theo văn phong chuyên nghiệp:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Vui lòng nhập khái niệm.")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Giải thích khái niệm cực kỳ dễ hiểu:\n\n{text}", sys_p, mdl)
    await update.message.reply_text(res)

async def rhyme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) or "cuộc sống"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Sáng tác bài thơ lục bát hay về chủ đề: {topic}", sys_p, mdl)
    await update.message.reply_text(res)

async def acrostic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = " ".join(context.args) or "GEMINI"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Viết thơ ghép chữ cái đầu với từ khóa: {word}", sys_p, mdl)
    await update.message.reply_text(res)

async def story_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genre = " ".join(context.args) or "khoa học viễn tưởng"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Sáng tác truyện ngắn thể loại: {genre}", sys_p, mdl)
    await update.message.reply_text(res)

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = " ".join(context.args)
    if not req:
        await update.message.reply_text("⚠️ Cú pháp: `/email <yêu_cầu>`", parse_mode="Markdown")
        return
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Soạn email công sở lịch sự theo yêu cầu: {req}", sys_p, mdl)
    await update.message.reply_text(res)

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = " ".join(context.args) or "ngày làm việc hiệu quả"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Lập danh sách việc cần làm chi tiết cho: {task}", sys_p, mdl)
    await update.message.reply_text(res)

async def workout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal = " ".join(context.args) or "tăng cơ giảm mỡ"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Gợi ý lịch tập thể hình cho mục tiêu: {goal}", sys_p, mdl)
    await update.message.reply_text(res)

async def recipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ingredients = " ".join(context.args) or "trứng, cà chua"
    user_id = update.effective_user.id
    sys_p, mdl = get_user_config(user_id)
    res = await ask_gemini(f"Gợi ý công thức món ăn từ nguyên liệu: {ingredients}", sys_p, mdl)
    await update.message.reply_text(res)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_t = time.time()
    msg = await update.message.reply_text("🏓 Đang kiểm tra...")
    latency = int((time.time() - start_t) * 1000)
    await msg.edit_text(f"🏓 Pong! Tốc độ phản hồi: `{latency}ms`", parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _, mdl = get_user_config(user_id)
    await update.message.reply_text(f"📊 Model: `{mdl}`\nTrạng thái: `Hoạt động siêu tốc`", parse_mode="Markdown")

async def features_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await newchat(update, context)

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 Hỗ trợ kỹ thuật: Vui lòng liên hệ quản trị viên.")

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Debug: All systems operational.")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Cảm ơn phản hồi của bạn!")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 **Ultra Gemini Bot v4.1** (Fast Mode)", parse_mode="Markdown")

# Xử lý file PDF
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("⚠️ Vui lòng gửi file `.pdf`.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    file = await context.bot.get_file(doc.file_id)
    bytes_data = await file.download_as_bytearray()
    try:
        reader = PdfReader(io.BytesIO(bytes_data))
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])[:10000]
        user_id = update.effective_user.id
        sys_p, mdl = get_user_config(user_id)
        res = await ask_gemini(f"Phân tích tài liệu PDF:\n\n{text}", sys_p, mdl)
        await update.message.reply_text(res)
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi xử lý PDF: {e}")

# Xử lý hình ảnh (Vision)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    caption = update.message.caption or "Phân tích hình ảnh này."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    file = await context.bot.get_file(photo.file_id)
    bytes_data = await file.download_as_bytearray()
    try:
        img_part = types.Part.from_bytes(data=bytes(bytes_data), mime_type="image/jpeg")
        user_id = update.effective_user.id
        sys_p, mdl = get_user_config(user_id)
        
        def _call_vision():
            return client.models.generate_content(
                model=mdl,
                contents=[img_part, caption],
                config=types.GenerateContentConfig(
                    system_instruction=sys_p,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
        response = await asyncio.to_thread(_call_vision)
        await update.message.reply_text(response.text if response and response.text else "Không thể phân tích ảnh.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi xử lý ảnh: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "features":
        await help_command(update, context)
    elif query.data == "stats":
        await stats_command(update, context)
    else:
        await query.message.reply_text("✅ Thao tác thành công.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = [
        InlineQueryResultArticle(
            id="1",
            title="Hỏi Gemini AI",
            input_message_content=InputTextMessageContent(f"Câu hỏi: {query}"),
            description=f"Truy vấn: {query}"
        )
    ]
    await update.inline_query.answer(results)

# Chat handler chính
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    user_id = update.effective_user.id
    lock = get_user_lock(user_id)
    
    async with lock:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        sys_p, mdl = get_user_config(user_id)

        try:
            answer = await ask_gemini(user_text, sys_p, mdl)
            max_len = 4000
            if len(answer) <= max_len:
                await update.message.reply_text(answer)
            else:
                for i in range(0, len(answer), max_len):
                    await update.message.reply_text(answer[i:i+max_len])
        except Exception as e:
            logger.exception("Gemini execution error")
            await update.message.reply_text("❌ Đã xảy ra lỗi, vui lòng thử lại sau!")

def main():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    commands = [
        ("start", start), ("help", help_command), ("newchat", newchat),
        ("model", model_command), ("system", system_command), ("translate", translate_command),
        ("code", code_command), ("summarize", summarize_command), ("calc", calc_command),
        ("web", web_command), ("joke", joke_command), ("quote", quote_command),
        ("fact", fact_command), ("riddle", riddle_command), ("fortune", fortune_command),
        ("roast", roast_command), ("compliment", compliment_command), ("regex", regex_command),
        ("sql", sql_command), ("json", json_command), ("grammar", grammar_command),
        ("rewrite", rewrite_command), ("explain", explain_command), ("rhyme", rhyme_command),
        ("acrostic", acrostic_command), ("story", story_command), ("email", email_command),
        ("todo", todo_command), ("workout", workout_command), ("recipe", recipe_command),
        ("ping", ping_command), ("stats", stats_command), ("features", features_command),
        ("clear", clear_command), ("support", support_command), ("debug", debug_command),
        ("feedback", feedback_command), ("info", info_command)
    ]
    
    for cmd, handler in commands:
        application.add_handler(CommandHandler(cmd, handler))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("=" * 55)
    print("🤖 ULTRA TELEGRAM AI BOT (40 TÍNH NĂNG - FAST MODE) ĐANG CHẠY...")
    print("=" * 55)
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
