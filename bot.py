import os
import io
import time
import base64
import random
import string
import threading
import urllib.parse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import qrcode
import telebot
import google.generativeai as genai
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

if not TOKEN:
    raise ValueError("Chưa cấu hình biến môi trường BOT_TOKEN!")

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=16
)

app = Flask(__name__)

# =========================================================
# AI
# =========================================================

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel("gemini-2.0-flash")
else:
    ai_model = None


# =========================================================
# DATA
# =========================================================

USER_DATA = {}

SUPPORTED_LANGUAGES = {
    "vi": "🇻🇳 Tiếng Việt",
    "en": "🇬🇧 English",
    "id": "🇮🇩 Indonesian",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "ru": "🇷🇺 Русский",
    "pt": "🇵🇹 Português",
    "it": "🇮🇹 Italiano",
    "zh": "🇨🇳 中文",
    "ja": "🇯🇵 日本語",
    "ko": "🇰🇷 한국어",
    "ar": "🇸🇦 العربية",
    "hi": "🇮🇳 हिन्दी",
    "th": "🇹🇭 ไทย",
    "tr": "🇹🇷 Türkçe",
}


# =========================================================
# LANGUAGE
# =========================================================

LANG_DICT = {
    "vi": {
        "choose_lang": "🌐 Vui lòng chọn ngôn ngữ giao diện itznvl Bot:",
        "lang_selected": "✅ Đã chuyển sang Tiếng Việt.",
        "help_prompt": "Gõ /help để xem danh sách lệnh.",
        "help_text": (
            "🚀 *ITZNVL BOT - SIÊU BOT TOÀN DIỆN*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - Bật/tắt chat liên tục\n"
            "/ask <câu hỏi> - Hỏi nhanh AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <nội dung> - Tạo mã QR\n"
            "/calc <phép tính> - Máy tính\n"
            "/base64 <text> - Mã hóa Base64\n"
            "/password - Tạo mật khẩu mạnh\n"
            "/wiki <từ khóa> - Wikipedia\n"
            "/weather <địa danh> - Thời tiết\n"
            "/clock <HH:MM> <quốc gia> - Đặt báo thức\n"
            "/ping - Độ trễ\n"
            "/id - Xem ID\n\n"
            "📈 *3. FINANCE*\n"
            "/crypto <coin> - Giá coin\n"
            "/short <link> - Rút gọn link\n\n"
            "🎉 *4. FUN*\n"
            "/joke - Chuyện cười\n"
            "/fact - Kiến thức thú vị\n\n"
            "🎮 *5. GAMES*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Tung đồng xu\n\n"
            "🛡 *6. ADMIN & SYSTEM*\n"
            "/pin - Ghim tin nhắn\n"
            "/ban - Cấm thành viên\n"
            "/thongbao <nội dung> - Gửi thông báo\n"
            "/stats - Thống kê\n"
            "/language - Đổi ngôn ngữ"
        ),
        "syntax_err": "⚠️ Sai cú pháp. Dùng đúng định dạng: ",
        "ai_on": "💬 [AI: ON] - Đã kết nối itznvl AI.\n(Gõ /cancel để tắt)",
        "ai_off": "🔇 [AI: OFF] - Đã tắt chat AI.",
        "api_timeout": "⏳ Thời gian chờ API quá hạn!",
        "admin_only": "⚠️ Yêu cầu quyền Quản trị viên nhóm!",
        "no_ai_key": "⚠️ Chưa cấu hình khóa API itznvl AI!",
        "clock_usage": (
            "⏰ Cách dùng: /clock + thời gian + quốc gia\n"
            "Ví dụ: /clock 07:30 Vietnam"
        ),
        "clock_invalid_time": "❌ Thời gian không hợp lệ. Hãy dùng HH:MM, ví dụ 07:30.",
        "clock_invalid_country": "❌ Không nhận diện được quốc gia hoặc múi giờ.",
        "clock_set": "✅ Đã đặt báo thức!",
        "clock_alarm": "⏰ *BÁO THỨC!*\n\n🔔 Đã đến giờ {time}\n🌍 Quốc gia: {country}\n🕐 Múi giờ: {timezone}",
    },

    "en": {
        "choose_lang": "🌐 Please select itznvl Bot interface language:",
        "lang_selected": "✅ Language set to English.",
        "help_prompt": "Type /help to see the command list.",
        "help_text": (
            "🚀 *ITZNVL BOT - ULTIMATE SUPER BOT*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - Toggle AI chat\n"
            "/ask <query> - Ask AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <text> - QR Code\n"
            "/calc <expression> - Calculator\n"
            "/base64 <text> - Base64\n"
            "/password - Strong password\n"
            "/wiki <keyword> - Wikipedia\n"
            "/weather <location> - Weather\n"
            "/clock <HH:MM> <country> - Set an alarm\n"
            "/ping - Latency\n"
            "/id - Get ID\n\n"
            "📈 *3. FINANCE*\n"
            "/crypto <coin> - Crypto price\n"
            "/short <link> - Shorten URL\n\n"
            "🎉 *4. FUN*\n"
            "/joke - Random joke\n"
            "/fact - Fun fact\n\n"
            "🎮 *5. GAMES*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Flip coin\n\n"
            "🛡 *6. ADMIN & SYSTEM*\n"
            "/pin - Pin message\n"
            "/ban - Ban member\n"
            "/thongbao <content> - Broadcast\n"
            "/stats - Stats\n"
            "/language - Change language"
        ),
        "syntax_err": "⚠️ Invalid syntax. Use: ",
        "ai_on": "💬 [AI: ON] - itznvl AI connected.\n(Type /cancel to turn off)",
        "ai_off": "🔇 [AI: OFF] - AI chat disabled.",
        "api_timeout": "⏳ API connection timeout!",
        "admin_only": "⚠️ Group Admin permissions required!",
        "no_ai_key": "⚠️ itznvl AI API key not configured!",
        "clock_usage": (
            "⏰ Usage: /clock + time + country\n"
            "Example: /clock 07:30 Vietnam"
        ),
        "clock_invalid_time": "❌ Invalid time. Use HH:MM, for example 07:30.",
        "clock_invalid_country": "❌ Country or timezone not recognized.",
        "clock_set": "✅ Alarm set!",
        "clock_alarm": "⏰ *ALARM!*\n\n🔔 It is now {time}\n🌍 Country: {country}\n🕐 Timezone: {timezone}",
    },

    "id": {
        "choose_lang": "🌐 Silakan pilih bahasa antarmuka bot:",
        "lang_selected": "✅ Bahasa diubah ke Indonesia.",
        "help_prompt": "Ketik /help untuk melihat daftar perintah.",
        "help_text": "Gunakan /help untuk melihat semua perintah.\n/clock <HH:MM> <negara> - Atur alarm\n/language - Ganti bahasa",
        "syntax_err": "⚠️ Sintaks salah. Gunakan: ",
        "ai_on": "💬 [AI: ON] - AI terhubung.",
        "ai_off": "🔇 [AI: OFF] - AI dimatikan.",
        "api_timeout": "⏳ Waktu tunggu API habis!",
        "admin_only": "⚠️ Memerlukan hak admin grup!",
        "no_ai_key": "⚠️ API key AI belum dikonfigurasi!",
        "clock_usage": "⏰ Penggunaan: /clock + waktu + negara\nContoh: /clock 07:30 Indonesia",
        "clock_invalid_time": "❌ Waktu tidak valid. Gunakan HH:MM.",
        "clock_invalid_country": "❌ Negara atau zona waktu tidak dikenali.",
        "clock_set": "✅ Alarm berhasil diatur!",
        "clock_alarm": "⏰ *ALARM!*\n\n🔔 Waktu {time}\n🌍 Negara: {country}\n🕐 Zona waktu: {timezone}",
    },

    "es": {
        "choose_lang": "🌐 Selecciona el idioma del bot:",
        "lang_selected": "✅ Idioma cambiado a Español.",
        "help_prompt": "Escribe /help para ver los comandos.",
        "help_text": "/clock <HH:MM> <país> - Crear una alarma\n/language - Cambiar idioma",
        "syntax_err": "⚠️ Sintaxis incorrecta. Usa: ",
        "ai_on": "💬 [AI: ON] - IA conectada.",
        "ai_off": "🔇 [AI: OFF] - IA desactivada.",
        "api_timeout": "⏳ Tiempo de espera de API agotado.",
        "admin_only": "⚠️ Se requieren permisos de administrador.",
        "no_ai_key": "⚠️ Falta la clave de API.",
        "clock_usage": "⏰ Uso: /clock + hora + país\nEjemplo: /clock 07:30 Spain",
        "clock_invalid_time": "❌ Hora no válida. Usa HH:MM.",
        "clock_invalid_country": "❌ País o zona horaria no reconocidos.",
        "clock_set": "✅ Alarma configurada.",
        "clock_alarm": "⏰ *¡ALARMA!*\n\n🔔 Hora: {time}\n🌍 País: {country}\n🕐 Zona horaria: {timezone}",
    },

    "fr": {
        "choose_lang": "🌐 Choisissez la langue du bot:",
        "lang_selected": "✅ Langue définie sur Français.",
        "help_prompt": "Tapez /help pour voir les commandes.",
        "help_text": "/clock <HH:MM> <pays> - Créer une alarme\n/language - Changer la langue",
        "syntax_err": "⚠️ Syntaxe incorrecte. Utilisez: ",
        "ai_on": "💬 [AI: ON] - IA connectée.",
        "ai_off": "🔇 [AI: OFF] - IA désactivée.",
        "api_timeout": "⏳ Délai API dépassé.",
        "admin_only": "⚠️ Droits administrateur requis.",
        "no_ai_key": "⚠️ Clé API manquante.",
        "clock_usage": "⏰ Utilisation: /clock + heure + pays\nExemple: /clock 07:30 France",
        "clock_invalid_time": "❌ Heure invalide. Utilisez HH:MM.",
        "clock_invalid_country": "❌ Pays ou fuseau horaire inconnu.",
        "clock_set": "✅ Alarme configurée.",
        "clock_alarm": "⏰ *ALARME !*\n\n🔔 Heure: {time}\n🌍 Pays: {country}\n🕐 Fuseau: {timezone}",
    },

    "de": {
        "choose_lang": "🌐 Bitte Sprache auswählen:",
        "lang_selected": "✅ Sprache auf Deutsch gesetzt.",
        "help_prompt": "Gib /help ein, um die Befehle zu sehen.",
        "help_text": "/clock <HH:MM> <Land> - Wecker setzen\n/language - Sprache ändern",
        "syntax_err": "⚠️ Ungültige Syntax. Verwende: ",
        "ai_on": "💬 [AI: ON] - KI verbunden.",
        "ai_off": "🔇 [AI: OFF] - KI deaktiviert.",
        "api_timeout": "⏳ API-Zeitüberschreitung.",
        "admin_only": "⚠️ Gruppen-Adminrechte erforderlich.",
        "no_ai_key": "⚠️ AI-API-Key fehlt.",
        "clock_usage": "⏰ Verwendung: /clock + Zeit + Land\nBeispiel: /clock 07:30 Germany",
        "clock_invalid_time": "❌ Ungültige Zeit. HH:MM verwenden.",
        "clock_invalid_country": "❌ Land oder Zeitzone nicht erkannt.",
        "clock_set": "✅ Wecker gesetzt.",
        "clock_alarm": "⏰ *WECKER!*\n\n🔔 Zeit: {time}\n🌍 Land: {country}\n🕐 Zeitzone: {timezone}",
    },

    "ru": {
        "choose_lang": "🌐 Выберите язык:",
        "lang_selected": "✅ Язык изменён на русский.",
        "help_prompt": "Введите /help для списка команд.",
        "help_text": "/clock <HH:MM> <страна> - Установить будильник\n/language - Изменить язык",
        "syntax_err": "⚠️ Неверный синтаксис. Используйте: ",
        "ai_on": "💬 [AI: ON] - ИИ подключён.",
        "ai_off": "🔇 [AI: OFF] - ИИ отключён.",
        "api_timeout": "⏳ Тайм-аут API.",
        "admin_only": "⚠️ Нужны права администратора.",
        "no_ai_key": "⚠️ API ключ ИИ не настроен.",
        "clock_usage": "⏰ Использование: /clock + время + страна\nПример: /clock 07:30 Russia",
        "clock_invalid_time": "❌ Неверное время. Используйте HH:MM.",
        "clock_invalid_country": "❌ Страна или часовой пояс не распознаны.",
        "clock_set": "✅ Будильник установлен.",
        "clock_alarm": "⏰ *БУДИЛЬНИК!*\n\n🔔 Время: {time}\n🌍 Страна: {country}\n🕐 Часовой пояс: {timezone}",
    },

    "pt": {
        "choose_lang": "🌐 Escolha o idioma:",
        "lang_selected": "✅ Idioma alterado para Português.",
        "help_prompt": "Digite /help para ver os comandos.",
        "help_text": "/clock <HH:MM> <país> - Definir alarme\n/language - Alterar idioma",
        "syntax_err": "⚠️ Sintaxe inválida. Use: ",
        "ai_on": "💬 [AI: ON] - IA conectada.",
        "ai_off": "🔇 [AI: OFF] - IA desligada.",
        "api_timeout": "⏳ Tempo limite da API.",
        "admin_only": "⚠️ Permissão de administrador necessária.",
        "no_ai_key": "⚠️ Chave de API ausente.",
        "clock_usage": "⏰ Uso: /clock + hora + país\nExemplo: /clock 07:30 Portugal",
        "clock_invalid_time": "❌ Hora inválida. Use HH:MM.",
        "clock_invalid_country": "❌ País ou fuso horário não reconhecido.",
        "clock_set": "✅ Alarme definido.",
        "clock_alarm": "⏰ *ALARME!*\n\n🔔 Hora: {time}\n🌍 País: {country}\n🕐 Fuso: {timezone}",
    },

    "it": {
        "choose_lang": "🌐 Scegli la lingua:",
        "lang_selected": "✅ Lingua impostata su Italiano.",
        "help_prompt": "Digita /help per vedere i comandi.",
        "help_text": "/clock <HH:MM> <paese> - Imposta una sveglia\n/language - Cambia lingua",
        "syntax_err": "⚠️ Sintassi non valida. Usa: ",
        "ai_on": "💬 [AI: ON] - IA connessa.",
        "ai_off": "🔇 [AI: OFF] - IA disattivata.",
        "api_timeout": "⏳ Timeout API.",
        "admin_only": "⚠️ Servono i permessi di amministratore.",
        "no_ai_key": "⚠️ Chiave API mancante.",
        "clock_usage": "⏰ Uso: /clock + ora + paese\nEsempio: /clock 07:30 Italy",
        "clock_invalid_time": "❌ Ora non valida. Usa HH:MM.",
        "clock_invalid_country": "❌ Paese o fuso orario non riconosciuto.",
        "clock_set": "✅ Sveglia impostata.",
        "clock_alarm": "⏰ *SVEGLIA!*\n\n🔔 Ora: {time}\n🌍 Paese: {country}\n🕐 Fuso: {timezone}",
    },

    "zh": {
        "choose_lang": "🌐 请选择语言:",
        "lang_selected": "✅ 已切换到中文。",
        "help_prompt": "输入 /help 查看命令。",
        "help_text": "/clock <HH:MM> <国家> - 设置闹钟\n/language - 更换语言",
        "syntax_err": "⚠️ 格式错误。使用: ",
        "ai_on": "💬 [AI: ON] - AI 已连接。",
        "ai_off": "🔇 [AI: OFF] - AI 已关闭。",
        "api_timeout": "⏳ API 请求超时。",
        "admin_only": "⚠️ 需要管理员权限。",
        "no_ai_key": "⚠️ 未配置 AI API 密钥。",
        "clock_usage": "⏰ 用法：/clock + 时间 + 国家\n示例：/clock 07:30 China",
        "clock_invalid_time": "❌ 时间无效。请使用 HH:MM。",
        "clock_invalid_country": "❌ 无法识别国家或时区。",
        "clock_set": "✅ 闹钟已设置。",
        "clock_alarm": "⏰ *闹钟！*\n\n🔔 时间：{time}\n🌍 国家：{country}\n🕐 时区：{timezone}",
    },

    "ja": {
        "choose_lang": "🌐 言語を選択してください:",
        "lang_selected": "✅ 日本語に変更しました。",
        "help_prompt": "/help でコマンド一覧を表示します。",
        "help_text": "/clock <HH:MM> <国> - アラーム設定\n/language - 言語変更",
        "syntax_err": "⚠️ 構文が正しくありません: ",
        "ai_on": "💬 [AI: ON] - AI 接続済み。",
        "ai_off": "🔇 [AI: OFF] - AI 無効。",
        "api_timeout": "⏳ API タイムアウト。",
        "admin_only": "⚠️ 管理者権限が必要です。",
        "no_ai_key": "⚠️ AI API キーが設定されていません。",
        "clock_usage": "⏰ 使い方: /clock + 時刻 + 国\n例: /clock 07:30 Japan",
        "clock_invalid_time": "❌ 時刻が無効です。HH:MM を使用してください。",
        "clock_invalid_country": "❌ 国またはタイムゾーンを認識できません。",
        "clock_set": "✅ アラームを設定しました。",
        "clock_alarm": "⏰ *アラーム！*\n\n🔔 時刻: {time}\n🌍 国: {country}\n🕐 タイムゾーン: {timezone}",
    },

    "ko": {
        "choose_lang": "🌐 언어를 선택하세요:",
        "lang_selected": "✅ 한국어로 변경되었습니다.",
        "help_prompt": "/help 를 입력해 명령어를 확인하세요.",
        "help_text": "/clock <HH:MM> <국가> - 알람 설정\n/language - 언어 변경",
        "syntax_err": "⚠️ 잘못된 문법입니다: ",
        "ai_on": "💬 [AI: ON] - AI 연결됨.",
        "ai_off": "🔇 [AI: OFF] - AI 비활성화.",
        "api_timeout": "⏳ API 시간 초과.",
        "admin_only": "⚠️ 관리자 권한이 필요합니다.",
        "no_ai_key": "⚠️ AI API 키가 없습니다.",
        "clock_usage": "⏰ 사용법: /clock + 시간 + 국가\n예: /clock 07:30 South Korea",
        "clock_invalid_time": "❌ 잘못된 시간입니다. HH:MM 형식을 사용하세요.",
        "clock_invalid_country": "❌ 국가 또는 시간대를 인식할 수 없습니다.",
        "clock_set": "✅ 알람이 설정되었습니다.",
        "clock_alarm": "⏰ *알람!*\n\n🔔 시간: {time}\n🌍 국가: {country}\n🕐 시간대: {timezone}",
    },

    "ar": {
        "choose_lang": "🌐 اختر اللغة:",
        "lang_selected": "✅ تم تغيير اللغة إلى العربية.",
        "help_prompt": "اكتب /help لعرض الأوامر.",
        "help_text": "/clock <HH:MM> <الدولة> - ضبط منبه\n/language - تغيير اللغة",
        "syntax_err": "⚠️ صيغة غير صحيحة. استخدم: ",
        "ai_on": "💬 [AI: ON] - تم الاتصال بالذكاء الاصطناعي.",
        "ai_off": "🔇 [AI: OFF] - تم إيقاف الذكاء الاصطناعي.",
        "api_timeout": "⏳ انتهت مهلة API.",
        "admin_only": "⚠️ تحتاج إلى صلاحيات مشرف.",
        "no_ai_key": "⚠️ مفتاح API غير مضبوط.",
        "clock_usage": "⏰ الاستخدام: /clock + الوقت + الدولة\nمثال: /clock 07:30 Saudi Arabia",
        "clock_invalid_time": "❌ الوقت غير صالح. استخدم HH:MM.",
        "clock_invalid_country": "❌ لم يتم التعرف على الدولة أو المنطقة الزمنية.",
        "clock_set": "✅ تم ضبط المنبه.",
        "clock_alarm": "⏰ *منبه!*\n\n🔔 الوقت: {time}\n🌍 الدولة: {country}\n🕐 المنطقة الزمنية: {timezone}",
    },

    "hi": {
        "choose_lang": "🌐 भाषा चुनें:",
        "lang_selected": "✅ भाषा हिन्दी पर सेट की गई।",
        "help_prompt": "/help से कमांड देखें।",
        "help_text": "/clock <HH:MM> <देश> - अलार्म सेट करें\n/language - भाषा बदलें",
        "syntax_err": "⚠️ गलत प्रारूप। उपयोग करें: ",
        "ai_on": "💬 [AI: ON] - AI जुड़ा हुआ है।",
        "ai_off": "🔇 [AI: OFF] - AI बंद है।",
        "api_timeout": "⏳ API टाइमआउट।",
        "admin_only": "⚠️ एडमिन अनुमति आवश्यक है।",
        "no_ai_key": "⚠️ AI API key उपलब्ध नहीं है।",
        "clock_usage": "⏰ उपयोग: /clock + समय + देश\nउदाहरण: /clock 07:30 India",
        "clock_invalid_time": "❌ समय गलत है। HH:MM उपयोग करें।",
        "clock_invalid_country": "❌ देश या टाइम ज़ोन नहीं मिला।",
        "clock_set": "✅ अलार्म सेट हो गया।",
        "clock_alarm": "⏰ *अलार्म!*\n\n🔔 समय: {time}\n🌍 देश: {country}\n🕐 टाइम ज़ोन: {timezone}",
    },

    "th": {
        "choose_lang": "🌐 กรุณาเลือกภาษา:",
        "lang_selected": "✅ เปลี่ยนเป็นภาษาไทยแล้ว",
        "help_prompt": "พิมพ์ /help เพื่อดูคำสั่ง",
        "help_text": "/clock <HH:MM> <ประเทศ> - ตั้งปลุก\n/language - เปลี่ยนภาษา",
        "syntax_err": "⚠️ รูปแบบไม่ถูกต้อง ใช้: ",
        "ai_on": "💬 [AI: ON] - เชื่อมต่อ AI แล้ว",
        "ai_off": "🔇 [AI: OFF] - ปิด AI แล้ว",
        "api_timeout": "⏳ API หมดเวลา",
        "admin_only": "⚠️ ต้องมีสิทธิ์ผู้ดูแล",
        "no_ai_key": "⚠️ ยังไม่ได้ตั้งค่า AI API key",
        "clock_usage": "⏰ วิธีใช้: /clock + เวลา + ประเทศ\nตัวอย่าง: /clock 07:30 Thailand",
        "clock_invalid_time": "❌ เวลาไม่ถูกต้อง ใช้รูปแบบ HH:MM",
        "clock_invalid_country": "❌ ไม่รู้จักประเทศหรือเขตเวลา",
        "clock_set": "✅ ตั้งปลุกแล้ว",
        "clock_alarm": "⏰ *เวลาปลุก!*\n\n🔔 เวลา: {time}\n🌍 ประเทศ: {country}\n🕐 เขตเวลา: {timezone}",
    },

    "tr": {
        "choose_lang": "🌐 Dil seçin:",
        "lang_selected": "✅ Dil Türkçe olarak ayarlandı.",
        "help_prompt": "Komutları görmek için /help yazın.",
        "help_text": "/clock <HH:MM> <ülke> - Alarm kur\n/language - Dili değiştir",
        "syntax_err": "⚠️ Geçersiz sözdizimi. Kullanım: ",
        "ai_on": "💬 [AI: ON] - AI bağlandı.",
        "ai_off": "🔇 [AI: OFF] - AI kapatıldı.",
        "api_timeout": "⏳ API zaman aşımı.",
        "admin_only": "⚠️ Yönetici izni gerekiyor.",
        "no_ai_key": "⚠️ AI API anahtarı yapılandırılmadı.",
        "clock_usage": "⏰ Kullanım: /clock + saat + ülke\nÖrnek: /clock 07:30 Turkey",
        "clock_invalid_time": "❌ Geçersiz saat. HH:MM kullanın.",
        "clock_invalid_country": "❌ Ülke veya saat dilimi tanınmadı.",
        "clock_set": "✅ Alarm kuruldu.",
        "clock_alarm": "⏰ *ALARM!*\n\n🔔 Saat: {time}\n🌍 Ülke: {country}\n🕐 Saat dilimi: {timezone}",
    },
}


def get_user(chat_id):
    return USER_DATA.setdefault(
        chat_id,
        {
            "lang": "en",
            "ai_mode": False,
            "stats": 0,
        }
    )


def get_msg(chat_id, key):
    lang = get_user(chat_id).get("lang", "en")
    return LANG_DICT.get(lang, LANG_DICT["en"]).get(
        key,
        LANG_DICT["en"].get(key, key)
    )


def validate_args(message, syntax):
    text = (message.text or "").split(maxsplit=1)

    if len(text) < 2 or not text[1].strip():
        bot.send_message(
            message.chat.id,
            get_msg(message.chat.id, "syntax_err") + syntax
        )
        return None

    return text[1].strip()


# =========================================================
# GAME EMOJIS
# =========================================================

GAME_EMOJIS_MAP = {
    "/dice": "🎲",
    "/dart": "🎯",
    "/basket": "🏀",
    "/football": "⚽",
    "/bowling": "🎳",
    "/slot": "🎰",
}


# =========================================================
# CLOCK / ALARM
# =========================================================

COUNTRY_TIMEZONES = {
    "vietnam": "Asia/Ho_Chi_Minh",
    "viet nam": "Asia/Ho_Chi_Minh",
    "việt nam": "Asia/Ho_Chi_Minh",
    "vn": "Asia/Ho_Chi_Minh",

    "thailand": "Asia/Bangkok",
    "thái lan": "Asia/Bangkok",

    "indonesia": "Asia/Jakarta",
    "singapore": "Asia/Singapore",
    "malaysia": "Asia/Kuala_Lumpur",
    "philippines": "Asia/Manila",
    "philippine": "Asia/Manila",

    "japan": "Asia/Tokyo",
    "nhật bản": "Asia/Tokyo",
    "jp": "Asia/Tokyo",

    "south korea": "Asia/Seoul",
    "korea": "Asia/Seoul",
    "hàn quốc": "Asia/Seoul",

    "china": "Asia/Shanghai",
    "trung quốc": "Asia/Shanghai",
    "cn": "Asia/Shanghai",

    "india": "Asia/Kolkata",
    "ấn độ": "Asia/Kolkata",

    "uae": "Asia/Dubai",
    "united arab emirates": "Asia/Dubai",

    "united kingdom": "Europe/London",
    "uk": "Europe/London",
    "england": "Europe/London",
    "anh": "Europe/London",

    "france": "Europe/Paris",
    "pháp": "Europe/Paris",

    "germany": "Europe/Berlin",
    "đức": "Europe/Berlin",

    "italy": "Europe/Rome",
    "ý": "Europe/Rome",

    "spain": "Europe/Madrid",
    "tây ban nha": "Europe/Madrid",

    "portugal": "Europe/Lisbon",
    "bồ đào nha": "Europe/Lisbon",

    "russia": "Europe/Moscow",
    "nga": "Europe/Moscow",

    "turkey": "Europe/Istanbul",
    "thổ nhĩ kỳ": "Europe/Istanbul",

    "united states": "America/New_York",
    "usa": "America/New_York",
    "us": "America/New_York",
    "america": "America/New_York",

    "canada": "America/Toronto",
    "mexico": "America/Mexico_City",

    "brazil": "America/Sao_Paulo",
    "argentina": "America/Argentina/Buenos_Aires",

    "australia": "Australia/Sydney",
    "new zealand": "Pacific/Auckland",

    "south africa": "Africa/Johannesburg",
    "egypt": "Africa/Cairo",
    "saudi arabia": "Asia/Riyadh",
}

CLOCK_ALARMS = {}
CLOCK_LOCK = threading.Lock()
CLOCK_NEXT_ID = 1


def normalize_country(country):
    return " ".join(country.strip().lower().split())


def get_timezone(country):
    value = country.strip()
    key = normalize_country(value)

    # Hỗ trợ nhập trực tiếp IANA timezone:
    # Asia/Ho_Chi_Minh
    if "/" in value:
        try:
            return ZoneInfo(value)
        except ZoneInfoNotFoundError:
            return None

    timezone_name = COUNTRY_TIMEZONES.get(key)

    if not timezone_name:
        return None

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None


def parse_clock_time(value):
    value = value.strip().lower()

    # 07:30
    if ":" in value:
        parts = value.split(":", 1)

    # 07.30
    elif "." in value:
        parts = value.split(".", 1)

    # 07h30
    elif "h" in value:
        parts = value.split("h", 1)

    else:
        return None

    if len(parts) != 2:
        return None

    try:
        hour = int(parts[0])
        minute = int(parts[1] or 0)
    except ValueError:
        return None

    if not 0 <= hour <= 23:
        return None

    if not 0 <= minute <= 59:
        return None

    return hour, minute


def create_alarm(chat_id, hour, minute, timezone_obj, country):
    global CLOCK_NEXT_ID

    now_local = datetime.now(timezone_obj)

    target = now_local.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    # Nếu giờ đã qua thì đặt sang ngày mai
    if target <= now_local:
        target += timedelta(days=1)

    with CLOCK_LOCK:
        alarm_id = CLOCK_NEXT_ID

        CLOCK_ALARMS[alarm_id] = {
            "chat_id": chat_id,
            "target": target,
            "country": country,
            "timezone": str(timezone_obj),
        }

        CLOCK_NEXT_ID += 1

    return alarm_id, target


def clock_worker():
    while True:
        now_utc = datetime.now(timezone.utc)
        due = []

        with CLOCK_LOCK:
            for alarm_id, alarm in list(CLOCK_ALARMS.items()):
                target_utc = alarm["target"].astimezone(timezone.utc)

                if now_utc >= target_utc:
                    due.append((alarm_id, alarm))
                    del CLOCK_ALARMS[alarm_id]

        for alarm_id, alarm in due:
            target = alarm["target"]

            try:
                chat_id = alarm["chat_id"]
                text = get_msg(chat_id, "clock_alarm").format(
                    time=target.strftime("%H:%M"),
                    country=alarm["country"],
                    timezone=alarm["timezone"],
                )

                bot.send_message(
                    chat_id,
                    text,
                    parse_mode="Markdown"
                )

                print(
                    f"[CLOCK] Alarm {alarm_id} sent "
                    f"to chat {chat_id}"
                )

            except Exception as e:
                print(
                    f"[CLOCK] Alarm {alarm_id} failed: {e}"
                )

        time.sleep(1)


clock_thread = threading.Thread(
    target=clock_worker,
    daemon=True,
    name="clock-worker"
)
clock_thread.start()


# =========================================================
# START / LANGUAGE
# =========================================================

@bot.message_handler(commands=["start", "language"])
def cmd_start(message):
    chat_id = message.chat.id
    get_user(chat_id)

    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton(
            name,
            callback_data=f"lang_{code}"
        )
        for code, name in SUPPORTED_LANGUAGES.items()
    ]

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i + 2])

    bot.send_message(
        chat_id,
        get_msg(chat_id, "choose_lang"),
        reply_markup=markup
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("lang_")
)
def callback_lang(call):
    chat_id = call.message.chat.id
    lang = call.data.split("_", 1)[1]

    if lang not in SUPPORTED_LANGUAGES:
        bot.answer_callback_query(call.id)
        return

    get_user(chat_id)["lang"] = lang

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        (
            f"{get_msg(chat_id, 'lang_selected')}\n\n"
            f"{get_msg(chat_id, 'help_prompt')}"
        ),
        chat_id,
        call.message.message_id
    )


# =========================================================
# HELP / STATS
# =========================================================

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        get_msg(message.chat.id, "help_text"),
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    data = get_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"📊 Tổng số tương tác: `{data.get('stats', 0)}`",
        parse_mode="Markdown"
    )


# =========================================================
# AI
# =========================================================

@bot.message_handler(commands=["chatwithAI", "cancel"])
def cmd_ai_toggle(message):
    chat_id = message.chat.id
    data = get_user(chat_id)

    is_on = (message.text or "").lower().startswith("/chatwithai")

    data["ai_mode"] = is_on

    bot.send_message(
        chat_id,
        get_msg(chat_id, "ai_on" if is_on else "ai_off")
    )


@bot.message_handler(commands=["ask"])
def cmd_ask(message):
    query = validate_args(
        message,
        "/ask <query>"
    )

    if not query:
        return

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    if not ai_model:
        bot.reply_to(
            message,
            get_msg(message.chat.id, "no_ai_key")
        )
        return

    try:
        response = ai_model.generate_content(query)

        bot.reply_to(
            message,
            f"🤖 [itznvl AI]:\n{response.text}"
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ AI Error: {e}"
        )


# =========================================================
# CLOCK COMMAND
# =========================================================

@bot.message_handler(commands=["clock"])
def cmd_clock(message):
    chat_id = message.chat.id
    text = message.text or ""

    parts = text.split(maxsplit=2)

    # Chỉ gõ /clock
    if len(parts) < 3:
        bot.reply_to(
            message,
            get_msg(chat_id, "clock_usage")
        )
        return

    time_text = parts[1].strip()
    country = parts[2].strip()

    parsed = parse_clock_time(time_text)

    if parsed is None:
        bot.reply_to(
            message,
            get_msg(chat_id, "clock_invalid_time")
        )
        return

    timezone_obj = get_timezone(country)

    if timezone_obj is None:
        bot.reply_to(
            message,
            get_msg(chat_id, "clock_invalid_country")
        )
        return

    hour, minute = parsed

    alarm_id, target = create_alarm(
        chat_id,
        hour,
        minute,
        timezone_obj,
        country
    )

    now_local = datetime.now(timezone_obj)

    day_text = (
        "hôm nay"
        if target.date() == now_local.date()
        else "ngày mai"
    )

    # Dùng English-safe message để tránh lỗi Markdown ở quốc gia
    bot.send_message(
        chat_id,
        (
            f"⏰ <b>{get_msg(chat_id, 'clock_set')}</b>\n\n"
            f"🔔 Thời gian: "
            f"<code>{target.strftime('%H:%M')}</code>\n"
            f"📅 {day_text}: "
            f"<code>{target.strftime('%d/%m/%Y')}</code>\n"
            f"🌍 Quốc gia: "
            f"<code>{country}</code>\n"
            f"🕐 Múi giờ: "
            f"<code>{timezone_obj}</code>\n"
            f"🆔 Alarm ID: "
            f"<code>{alarm_id}</code>"
        ),
        parse_mode="HTML"
    )


# =========================================================
# QR
# =========================================================

@bot.message_handler(commands=["qr"])
def cmd_qr(message):
    text = validate_args(
        message,
        "/qr <text>"
    )

    if not text:
        return

    try:
        image = qrcode.make(text)

        bio = io.BytesIO()
        image.save(bio, format="PNG")
        bio.seek(0)

        bot.send_photo(
            message.chat.id,
            bio,
            caption="✅ QR Code Generated"
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ QR error: {e}"
        )


# =========================================================
# CALCULATOR
# =========================================================

@bot.message_handler(commands=["calc"])
def cmd_calc(message):
    expr = validate_args(
        message,
        "/calc <expression>"
    )

    if not expr:
        return

    allowed = set(
        "0123456789+-*/(). %"
    )

    if any(c not in allowed for c in expr):
        bot.reply_to(
            message,
            "❌ Invalid expression."
        )
        return

    try:
        result = eval(
            expr,
            {
                "__builtins__": None
            },
            {}
        )

        bot.reply_to(
            message,
            f"🧮 `{expr} = {result}`",
            parse_mode="Markdown"
        )

    except Exception:
        bot.reply_to(
            message,
            "❌ Invalid expression."
        )


# =========================================================
# BASE64
# =========================================================

@bot.message_handler(commands=["base64"])
def cmd_base64(message):
    text = validate_args(
        message,
        "/base64 <text>"
    )

    if not text:
        return

    encoded = base64.b64encode(
        text.encode("utf-8")
    ).decode("utf-8")

    bot.reply_to(
        message,
        f"🔒 Base64:\n`{encoded}`",
        parse_mode="Markdown"
    )


# =========================================================
# WIKIPEDIA
# =========================================================

@bot.message_handler(commands=["wiki"])
def cmd_wiki(message):
    keyword = validate_args(
        message,
        "/wiki <keyword>"
    )

    if not keyword:
        return

    try:
        url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(keyword)
        )

        response = requests.get(
            url,
            timeout=5,
            headers={
                "User-Agent": "itznvl-bot/3.0"
            }
        )

        data = response.json()

        if data.get("extract"):
            title = data.get(
                "title",
                keyword
            )

            bot.reply_to(
                message,
                (
                    f"📚 *{title}*\n\n"
                    f"{data['extract']}"
                ),
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(
                message,
                "❌ Not found."
            )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Wikipedia error: {e}"
        )


# =========================================================
# WEATHER
# =========================================================

@bot.message_handler(commands=["weather"])
def cmd_weather(message):
    location = validate_args(
        message,
        "/weather <location>"
    )

    if not location:
        return

    try:
        bot.send_chat_action(
            message.chat.id,
            "typing"
        )

        headers = {
            "User-Agent": "itznvl-bot/3.0"
        }

        geo_url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={urllib.parse.quote(location)}"
            "&format=json"
            "&limit=1"
            "&accept-language=vi"
        )

        geo_response = requests.get(
            geo_url,
            headers=headers,
            timeout=5
        )

        geo_data = geo_response.json()

        target = location

        if geo_data:
            target = geo_data[0].get(
                "display_name",
                location
            )

        weather_url = (
            "https://wttr.in/"
            + urllib.parse.quote(target)
            + "?format=3&lang=vi"
        )

        weather_response = requests.get(
            weather_url,
            headers=headers,
            timeout=7
        )

        if (
            weather_response.status_code == 200
            and "Unknown location"
            not in weather_response.text
        ):
            bot.reply_to(
                message,
                (
                    f"🌤 Thời tiết `{location}`:\n"
                    f"`{weather_response.text.strip()}`"
                ),
                parse_mode="Markdown"
            )
            return

        fallback_url = (
            "https://wttr.in/"
            + urllib.parse.quote(location)
            + "?format=3"
        )

        fallback = requests.get(
            fallback_url,
            headers=headers,
            timeout=7
        )

        if (
            fallback.status_code == 200
            and "Unknown location"
            not in fallback.text
        ):
            bot.reply_to(
                message,
                (
                    f"🌤 Thời tiết `{location}`:\n"
                    f"`{fallback.text.strip()}`"
                ),
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(
                message,
                "❌ Không tìm thấy địa danh này."
            )

    except requests.exceptions.Timeout:
        bot.reply_to(
            message,
            get_msg(message.chat.id, "api_timeout")
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Lỗi dịch vụ thời tiết: {e}"
        )


# =========================================================
# QUICK UTILS
# =========================================================

@bot.message_handler(
    commands=["ping", "id", "password"]
)
def cmd_quick_utils(message):
    command = (
        message.text or ""
    ).split()[0].lower()

    chat_id = message.chat.id

    if command == "/ping":
        started = time.perf_counter()

        msg = bot.send_message(
            chat_id,
            "⏳"
        )

        latency = round(
            (time.perf_counter() - started) * 1000
        )

        bot.edit_message_text(
            f"🏓 Latency: `{latency}ms`",
            chat_id,
            msg.message_id,
            parse_mode="Markdown"
        )

    elif command == "/id":
        bot.send_message(
            chat_id,
            (
                f"👤 User ID: "
                f"`{message.from_user.id}`\n"
                f"💬 Chat ID: `{chat_id}`"
            ),
            parse_mode="Markdown"
        )

    elif command == "/password":
        chars = (
            string.ascii_letters
            + string.digits
            + "!@#$%^&*"
        )

        password = "".join(
            random.choices(
                chars,
                k=16
            )
        )

        bot.send_message(
            chat_id,
            (
                "🔑 Password:\n"
                f"`{password}`"
            ),
            parse_mode="Markdown"
        )


# =========================================================
# FINANCE / FUN
# =========================================================

@bot.message_handler(
    commands=["crypto", "short", "joke", "fact"]
)
def cmd_external_apis(message):
    command = (
        message.text or ""
    ).split()[0].lower()

    chat_id = message.chat.id

    try:
        if command == "/crypto":
            coin = validate_args(
                message,
                "/crypto <coin>"
            )

            if not coin:
                return

            symbol = coin.strip().upper() + "USDT"

            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={
                    "symbol": symbol
                },
                timeout=5
            )

            data = response.json()

            if "price" not in data:
                raise ValueError(
                    "Coin không tồn tại hoặc Binance không hỗ trợ."
                )

            price = float(
                data["price"]
            )

            bot.send_message(
                chat_id,
                (
                    f"📈 *{coin.upper()} / USDT*\n"
                    f"`{price:,.8f}`"
                ),
                parse_mode="Markdown"
            )

        elif command == "/short":
            link = validate_args(
                message,
                "/short <link>"
            )

            if not link:
                return

            response = requests.get(
                "https://is.gd/create.php",
                params={
                    "format": "json",
                    "url": link
                },
                timeout=5
            )

            data = response.json()

            if "shorturl" not in data:
                raise ValueError(
                    data.get(
                        "errormessage",
                        "Không thể rút gọn link."
                    )
                )

            bot.send_message(
                chat_id,
                f"🔗 Short URL:\n{data['shorturl']}"
            )

        elif command == "/joke":
            response = requests.get(
                "https://official-joke-api.appspot.com/random_joke",
                timeout=5
            )

            data = response.json()

            bot.send_message(
                chat_id,
                (
                    f"🗣 {data['setup']}\n\n"
                    f"😂 *{data['punchline']}*"
                ),
                parse_mode="Markdown"
            )

        elif command == "/fact":
            response = requests.get(
                "https://uselessfacts.jsph.pl/api/v2/facts/random",
                params={
                    "language": "en"
                },
                timeout=5
            )

            data = response.json()

            bot.send_message(
                chat_id,
                (
                    "💡 *Fun Fact:*\n"
                    f"{data.get('text', 'No fact found.')}"
                ),
                parse_mode="Markdown"
            )

    except requests.exceptions.Timeout:
        bot.send_message(
            chat_id,
            get_msg(chat_id, "api_timeout")
        )

    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ External API error: {e}"
        )


# =========================================================
# GAMES
# =========================================================

@bot.message_handler(
    commands=[
        "dice",
        "dart",
        "basket",
        "football",
        "bowling",
        "slot",
        "coin",
    ]
)
def cmd_games(message):
    command = (
        message.text or ""
    ).split()[0].lower()

    if command == "/coin":
        result = random.choice(
            [
                "Heads 🦅",
                "Tails 🪙",
            ]
        )

        bot.send_message(
            message.chat.id,
            f"🪙 Coin flip: *{result}*",
            parse_mode="Markdown"
        )

    elif command in GAME_EMOJIS_MAP:
        bot.send_dice(
            message.chat.id,
            emoji=GAME_EMOJIS_MAP[command]
        )


# =========================================================
# ADMIN
# =========================================================

@bot.message_handler(
    commands=["pin", "ban"]
)
def cmd_admin_actions(message):
    if message.chat.type not in [
        "group",
        "supergroup",
    ]:
        bot.reply_to(
            message,
            "⚠️ Group only!"
        )
        return

    try:
        admins = bot.get_chat_administrators(
            message.chat.id
        )

        admin_ids = {
            admin.user.id
            for admin in admins
        }

        if message.from_user.id not in admin_ids:
            bot.reply_to(
                message,
                get_msg(
                    message.chat.id,
                    "admin_only"
                )
            )
            return

        if not message.reply_to_message:
            bot.reply_to(
                message,
                "⚠️ Reply to a message!"
            )
            return

        command = (
            message.text or ""
        ).split()[0].lower()

        target_id = (
            message.reply_to_message
            .from_user
            .id
        )

        if command == "/pin":
            bot.pin_chat_message(
                message.chat.id,
                message.reply_to_message.message_id
            )

            bot.reply_to(
                message,
                "📌 Pinned successfully!"
            )

        elif command == "/ban":
            bot.ban_chat_member(
                message.chat.id,
                target_id
            )

            bot.reply_to(
                message,
                "🔨 User banned."
            )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Admin action failed: {e}"
        )


# =========================================================
# BROADCAST
# =========================================================

@bot.message_handler(
    commands=["thongbao"]
)
def cmd_thongbao(message):
    if (
        ADMIN_ID
        and str(message.from_user.id)
        != str(ADMIN_ID)
    ):
        bot.reply_to(
            message,
            "⚠️ Bạn không có quyền sử dụng lệnh này!"
        )
        return

    text = validate_args(
        message,
        "/thongbao <nội dung>"
    )

    if not text:
        return

    success = 0
    failed = 0

    for chat_id in list(USER_DATA.keys()):
        try:
            bot.send_message(
                chat_id,
                (
                    "📢 *THÔNG BÁO TỪ ADMIN:*\n\n"
                    f"{text}"
                ),
                parse_mode="Markdown"
            )
            success += 1

        except Exception as e:
            failed += 1
            print(
                f"[BROADCAST] {chat_id}: {e}"
            )

    bot.reply_to(
        message,
        (
            f"✅ Thành công: `{success}`\n"
            f"❌ Thất bại: `{failed}`"
        ),
        parse_mode="Markdown"
    )


# =========================================================
# FALLBACK + AI CHAT
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def handler_fallback(message):
    if not message.text:
        return

    chat_id = message.chat.id
    data = get_user(chat_id)

    data["stats"] += 1

    if data.get("ai_mode", False):
        bot.send_chat_action(
            chat_id,
            "typing"
        )

        if not ai_model:
            bot.reply_to(
                message,
                get_msg(
                    chat_id,
                    "no_ai_key"
                )
            )
            return

        try:
            response = ai_model.generate_content(
                message.text
            )

            bot.reply_to(
                message,
                response.text
            )

        except Exception as e:
            bot.reply_to(
                message,
                f"❌ AI Error: {e}"
            )

    elif message.chat.type == "private":
        bot.send_message(
            chat_id,
            get_msg(
                chat_id,
                "help_prompt"
            )
        )


# =========================================================
# FLASK WEBHOOK
# =========================================================

@app.route(
    f"/{TOKEN}",
    methods=["POST"]
)
def webhook():
    if request.headers.get(
        "content-type",
        ""
    ).startswith("application/json"):

        try:
            json_string = (
                request.get_data()
                .decode("utf-8")
            )

            update = (
                telebot.types.Update
                .de_json(json_string)
            )

            bot.process_new_updates(
                [update]
            )

            return "", 200

        except Exception as e:
            print(
                f"[WEBHOOK] Error: {e}"
            )
            return "Bad Request", 400

    return "Forbidden", 403


@app.route("/", methods=["GET"])
def index():
    return (
        "itznvl Bot Web Service is running successfully!",
        200
    )


# =========================================================
# WEBHOOK SETUP
# =========================================================

def setup_webhook():
    if not RENDER_EXTERNAL_URL:
        print(
            "⚠️ RENDER_EXTERNAL_URL chưa được cấu hình."
        )
        print(
            "Bot sẽ không tự set webhook."
        )
        return

    webhook_url = (
        f"{RENDER_EXTERNAL_URL}/{TOKEN}"
    )

    try:
        bot.remove_webhook()

        time.sleep(0.5)

        result = bot.set_webhook(
            url=webhook_url
        )

        print(
            f"🔗 Webhook: {webhook_url}"
        )
        print(
            f"✅ Webhook configured: {result}"
        )

    except Exception as e:
        print(
            f"❌ Webhook setup failed: {e}"
        )


# Gunicorn import bot:app sẽ chạy phần này.
setup_webhook()


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    print(
        f"🚀 Starting Flask on port {port}..."
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
```
