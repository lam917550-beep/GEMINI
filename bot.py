```python
import os
import io
import time
import ast
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
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN chưa được cấu hình.")

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=16
)

app = Flask(__name__)


# =========================================================
# GEMINI AI
# =========================================================

gemini_client = None

if GEMINI_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_KEY
        )
        print("✅ Gemini AI initialized.")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}")
        gemini_client = None


# =========================================================
# USER DATA
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
# LANGUAGE DATA
# =========================================================

LANG = {
    "vi": {
        "choose": "🌐 Vui lòng chọn ngôn ngữ giao diện:",
        "selected": "✅ Đã chuyển sang Tiếng Việt.",
        "help_prompt": "Gõ /help để xem danh sách lệnh.",
        "syntax": "⚠️ Sai cú pháp. Dùng: ",
        "ai_on": "💬 [AI: ON] - Đã bật AI.\nGõ /cancel để tắt.",
        "ai_off": "🔇 [AI: OFF] - Đã tắt AI.",
        "no_ai": "⚠️ Chưa cấu hình GEMINI_API_KEY.",
        "timeout": "⏳ API timeout.",
        "admin": "⚠️ Bạn cần quyền quản trị viên.",
        "clock_usage": (
            "⏰ Cách dùng:\n"
            "/clock <HH:MM> <quốc gia>\n\n"
            "Ví dụ:\n"
            "/clock 07:30 Vietnam"
        ),
        "clock_time": "❌ Thời gian không hợp lệ. Dùng HH:MM, ví dụ 07:30.",
        "clock_country": "❌ Không nhận diện được quốc gia hoặc múi giờ.",
        "clock_set": "✅ Đã đặt báo thức!",
        "clock_alarm": (
            "⏰ *BÁO THỨC!*\n\n"
            "🔔 Giờ: `{time}`\n"
            "🌍 Quốc gia: `{country}`\n"
            "🕐 Múi giờ: `{timezone}`"
        ),
        "group_only": "⚠️ Lệnh này chỉ dùng trong nhóm.",
        "reply_required": "⚠️ Hãy reply tin nhắn cần thực hiện lệnh.",
        "invalid_expression": "❌ Phép tính không hợp lệ.",
        "not_found": "❌ Không tìm thấy.",
    },

    "en": {
        "choose": "🌐 Please select the interface language:",
        "selected": "✅ Language changed to English.",
        "help_prompt": "Type /help to see the commands.",
        "syntax": "⚠️ Invalid syntax. Use: ",
        "ai_on": "💬 [AI: ON] - AI enabled.\nType /cancel to turn it off.",
        "ai_off": "🔇 [AI: OFF] - AI disabled.",
        "no_ai": "⚠️ GEMINI_API_KEY is not configured.",
        "timeout": "⏳ API timeout.",
        "admin": "⚠️ Administrator permissions required.",
        "clock_usage": (
            "⏰ Usage:\n"
            "/clock <HH:MM> <country>\n\n"
            "Example:\n"
            "/clock 07:30 Vietnam"
        ),
        "clock_time": "❌ Invalid time. Use HH:MM, for example 07:30.",
        "clock_country": "❌ Country or timezone not recognized.",
        "clock_set": "✅ Alarm set!",
        "clock_alarm": (
            "⏰ *ALARM!*\n\n"
            "🔔 Time: `{time}`\n"
            "🌍 Country: `{country}`\n"
            "🕐 Timezone: `{timezone}`"
        ),
        "group_only": "⚠️ This command only works in groups.",
        "reply_required": "⚠️ Reply to the target message first.",
        "invalid_expression": "❌ Invalid expression.",
        "not_found": "❌ Not found.",
    },

    "id": {
        "choose": "🌐 Silakan pilih bahasa:",
        "selected": "✅ Bahasa diubah ke Indonesia.",
        "help_prompt": "Ketik /help untuk melihat perintah.",
        "syntax": "⚠️ Sintaks salah. Gunakan: ",
        "ai_on": "💬 [AI: ON] - AI aktif.",
        "ai_off": "🔇 [AI: OFF] - AI dimatikan.",
        "no_ai": "⚠️ GEMINI_API_KEY belum diatur.",
        "timeout": "⏳ API timeout.",
        "admin": "⚠️ Memerlukan hak admin.",
        "clock_usage": "/clock <HH:MM> <negara>\nContoh: /clock 07:30 Indonesia",
        "clock_time": "❌ Waktu tidak valid. Gunakan HH:MM.",
        "clock_country": "❌ Negara atau zona waktu tidak dikenal.",
        "clock_set": "✅ Alarm berhasil diatur!",
        "clock_alarm": "⏰ *ALARM!*\n\n🔔 Waktu: `{time}`\n🌍 Negara: `{country}`\n🕐 Zona waktu: `{timezone}`",
        "group_only": "⚠️ Hanya dapat digunakan di grup.",
        "reply_required": "⚠️ Balas pesan target terlebih dahulu.",
        "invalid_expression": "❌ Ekspresi tidak valid.",
        "not_found": "❌ Tidak ditemukan.",
    },

    "es": {
        "choose": "🌐 Selecciona el idioma:",
        "selected": "✅ Idioma cambiado a Español.",
        "help_prompt": "Escribe /help para ver los comandos.",
        "syntax": "⚠️ Sintaxis incorrecta. Usa: ",
        "ai_on": "💬 [AI: ON] - IA activada.",
        "ai_off": "🔇 [AI: OFF] - IA desactivada.",
        "no_ai": "⚠️ Falta GEMINI_API_KEY.",
        "timeout": "⏳ Tiempo de espera agotado.",
        "admin": "⚠️ Se requieren permisos de administrador.",
        "clock_usage": "/clock <HH:MM> <país>\nEjemplo: /clock 07:30 Spain",
        "clock_time": "❌ Hora no válida. Usa HH:MM.",
        "clock_country": "❌ País o zona horaria no reconocidos.",
        "clock_set": "✅ Alarma configurada.",
        "clock_alarm": "⏰ *¡ALARMA!*\n\n🔔 Hora: `{time}`\n🌍 País: `{country}`\n🕐 Zona: `{timezone}`",
        "group_only": "⚠️ Solo funciona en grupos.",
        "reply_required": "⚠️ Responde al mensaje objetivo.",
        "invalid_expression": "❌ Expresión no válida.",
        "not_found": "❌ No encontrado.",
    },

    "fr": {
        "choose": "🌐 Choisissez la langue:",
        "selected": "✅ Langue changée en français.",
        "help_prompt": "Tapez /help pour voir les commandes.",
        "syntax": "⚠️ Syntaxe invalide. Utilisez: ",
        "ai_on": "💬 [AI: ON] - IA activée.",
        "ai_off": "🔇 [AI: OFF] - IA désactivée.",
        "no_ai": "⚠️ GEMINI_API_KEY manquante.",
        "timeout": "⏳ Délai API dépassé.",
        "admin": "⚠️ Droits administrateur requis.",
        "clock_usage": "/clock <HH:MM> <pays>\nExemple: /clock 07:30 France",
        "clock_time": "❌ Heure invalide. Utilisez HH:MM.",
        "clock_country": "❌ Pays ou fuseau non reconnu.",
        "clock_set": "✅ Alarme configurée.",
        "clock_alarm": "⏰ *ALARME !*\n\n🔔 Heure: `{time}`\n🌍 Pays: `{country}`\n🕐 Fuseau: `{timezone}`",
        "group_only": "⚠️ Fonctionne uniquement dans les groupes.",
        "reply_required": "⚠️ Répondez au message cible.",
        "invalid_expression": "❌ Expression invalide.",
        "not_found": "❌ Introuvable.",
    },

    "de": {
        "choose": "🌐 Sprache auswählen:",
        "selected": "✅ Sprache auf Deutsch geändert.",
        "help_prompt": "Gib /help ein.",
        "syntax": "⚠️ Ungültige Syntax. Verwende: ",
        "ai_on": "💬 [AI: ON] - KI aktiviert.",
        "ai_off": "🔇 [AI: OFF] - KI deaktiviert.",
        "no_ai": "⚠️ GEMINI_API_KEY fehlt.",
        "timeout": "⏳ API-Zeitüberschreitung.",
        "admin": "⚠️ Administratorrechte erforderlich.",
        "clock_usage": "/clock <HH:MM> <Land>\nBeispiel: /clock 07:30 Germany",
        "clock_time": "❌ Ungültige Zeit. Verwende HH:MM.",
        "clock_country": "❌ Land oder Zeitzone nicht erkannt.",
        "clock_set": "✅ Wecker eingestellt.",
        "clock_alarm": "⏰ *WECKER!*\n\n🔔 Zeit: `{time}`\n🌍 Land: `{country}`\n🕐 Zeitzone: `{timezone}`",
        "group_only": "⚠️ Nur in Gruppen verfügbar.",
        "reply_required": "⚠️ Auf die Zielnachricht antworten.",
        "invalid_expression": "❌ Ungültiger Ausdruck.",
        "not_found": "❌ Nicht gefunden.",
    },

    "ru": {
        "choose": "🌐 Выберите язык:",
        "selected": "✅ Язык изменён на русский.",
        "help_prompt": "Введите /help.",
        "syntax": "⚠️ Неверный синтаксис. Используйте: ",
        "ai_on": "💬 [AI: ON] - ИИ включён.",
        "ai_off": "🔇 [AI: OFF] - ИИ выключен.",
        "no_ai": "⚠️ GEMINI_API_KEY не настроен.",
        "timeout": "⏳ Тайм-аут API.",
        "admin": "⚠️ Требуются права администратора.",
        "clock_usage": "/clock <HH:MM> <страна>\nПример: /clock 07:30 Russia",
        "clock_time": "❌ Неверное время. Используйте HH:MM.",
        "clock_country": "❌ Страна или часовой пояс не распознаны.",
        "clock_set": "✅ Будильник установлен.",
        "clock_alarm": "⏰ *БУДИЛЬНИК!*\n\n🔔 Время: `{time}`\n🌍 Страна: `{country}`\n🕐 Часовой пояс: `{timezone}`",
        "group_only": "⚠️ Только в группах.",
        "reply_required": "⚠️ Ответьте на сообщение.",
        "invalid_expression": "❌ Неверное выражение.",
        "not_found": "❌ Не найдено.",
    },

    "pt": {
        "choose": "🌐 Escolha o idioma:",
        "selected": "✅ Idioma alterado para Português.",
        "help_prompt": "Digite /help.",
        "syntax": "⚠️ Sintaxe inválida. Use: ",
        "ai_on": "💬 [AI: ON] - IA ativada.",
        "ai_off": "🔇 [AI: OFF] - IA desativada.",
        "no_ai": "⚠️ GEMINI_API_KEY ausente.",
        "timeout": "⏳ Timeout da API.",
        "admin": "⚠️ Permissão de administrador necessária.",
        "clock_usage": "/clock <HH:MM> <país>\nExemplo: /clock 07:30 Portugal",
        "clock_time": "❌ Hora inválida. Use HH:MM.",
        "clock_country": "❌ País ou fuso não reconhecido.",
        "clock_set": "✅ Alarme definido.",
        "clock_alarm": "⏰ *ALARME!*\n\n🔔 Hora: `{time}`\n🌍 País: `{country}`\n🕐 Fuso: `{timezone}`",
        "group_only": "⚠️ Apenas em grupos.",
        "reply_required": "⚠️ Responda à mensagem.",
        "invalid_expression": "❌ Expressão inválida.",
        "not_found": "❌ Não encontrado.",
    },

    "it": {
        "choose": "🌐 Scegli la lingua:",
        "selected": "✅ Lingua impostata su Italiano.",
        "help_prompt": "Digita /help.",
        "syntax": "⚠️ Sintassi non valida. Usa: ",
        "ai_on": "💬 [AI: ON] - IA attivata.",
        "ai_off": "🔇 [AI: OFF] - IA disattivata.",
        "no_ai": "⚠️ GEMINI_API_KEY mancante.",
        "timeout": "⏳ Timeout API.",
        "admin": "⚠️ Servono permessi amministratore.",
        "clock_usage": "/clock <HH:MM> <paese>\nEsempio: /clock 07:30 Italy",
        "clock_time": "❌ Ora non valida. Usa HH:MM.",
        "clock_country": "❌ Paese o fuso non riconosciuto.",
        "clock_set": "✅ Sveglia impostata.",
        "clock_alarm": "⏰ *SVEGLIA!*\n\n🔔 Ora: `{time}`\n🌍 Paese: `{country}`\n🕐 Fuso: `{timezone}`",
        "group_only": "⚠️ Solo nei gruppi.",
        "reply_required": "⚠️ Rispondi al messaggio.",
        "invalid_expression": "❌ Espressione non valida.",
        "not_found": "❌ Non trovato.",
    },

    "zh": {
        "choose": "🌐 请选择语言:",
        "selected": "✅ 已切换到中文。",
        "help_prompt": "输入 /help。",
        "syntax": "⚠️ 格式错误。使用: ",
        "ai_on": "💬 [AI: ON] - AI 已开启。",
        "ai_off": "🔇 [AI: OFF] - AI 已关闭。",
        "no_ai": "⚠️ 未配置 GEMINI_API_KEY。",
        "timeout": "⏳ API 超时。",
        "admin": "⚠️ 需要管理员权限。",
        "clock_usage": "/clock <HH:MM> <国家>\n例如: /clock 07:30 China",
        "clock_time": "❌ 时间无效。使用 HH:MM。",
        "clock_country": "❌ 无法识别国家或时区。",
        "clock_set": "✅ 闹钟已设置。",
        "clock_alarm": "⏰ *闹钟！*\n\n🔔 时间: `{time}`\n🌍 国家: `{country}`\n🕐 时区: `{timezone}`",
        "group_only": "⚠️ 只能在群组中使用。",
        "reply_required": "⚠️ 请先回复目标消息。",
        "invalid_expression": "❌ 表达式无效。",
        "not_found": "❌ 未找到。",
    },

    "ja": {
        "choose": "🌐 言語を選択してください:",
        "selected": "✅ 日本語に変更しました。",
        "help_prompt": "/help を入力してください。",
        "syntax": "⚠️ 構文エラー。使用方法: ",
        "ai_on": "💬 [AI: ON] - AI を有効にしました。",
        "ai_off": "🔇 [AI: OFF] - AI を無効にしました。",
        "no_ai": "⚠️ GEMINI_API_KEY が設定されていません。",
        "timeout": "⏳ API タイムアウト。",
        "admin": "⚠️ 管理者権限が必要です。",
        "clock_usage": "/clock <HH:MM> <国>\n例: /clock 07:30 Japan",
        "clock_time": "❌ 時刻が無効です。HH:MM を使用してください。",
        "clock_country": "❌ 国またはタイムゾーンを認識できません。",
        "clock_set": "✅ アラームを設定しました。",
        "clock_alarm": "⏰ *アラーム！*\n\n🔔 時刻: `{time}`\n🌍 国: `{country}`\n🕐 タイムゾーン: `{timezone}`",
        "group_only": "⚠️ グループのみ。",
        "reply_required": "⚠️ 対象メッセージに返信してください。",
        "invalid_expression": "❌ 無効な式です。",
        "not_found": "❌ 見つかりません。",
    },

    "ko": {
        "choose": "🌐 언어를 선택하세요:",
        "selected": "✅ 한국어로 변경되었습니다.",
        "help_prompt": "/help 를 입력하세요.",
        "syntax": "⚠️ 잘못된 문법입니다. 사용: ",
        "ai_on": "💬 [AI: ON] - AI 활성화.",
        "ai_off": "🔇 [AI: OFF] - AI 비활성화.",
        "no_ai": "⚠️ GEMINI_API_KEY가 없습니다.",
        "timeout": "⏳ API 시간 초과.",
        "admin": "⚠️ 관리자 권한이 필요합니다.",
        "clock_usage": "/clock <HH:MM> <국가>\n예: /clock 07:30 South Korea",
        "clock_time": "❌ 잘못된 시간입니다. HH:MM을 사용하세요.",
        "clock_country": "❌ 국가 또는 시간대를 인식할 수 없습니다.",
        "clock_set": "✅ 알람이 설정되었습니다.",
        "clock_alarm": "⏰ *알람!*\n\n🔔 시간: `{time}`\n🌍 국가: `{country}`\n🕐 시간대: `{timezone}`",
        "group_only": "⚠️ 그룹에서만 사용 가능합니다.",
        "reply_required": "⚠️ 대상 메시지에 답장하세요.",
        "invalid_expression": "❌ 잘못된 식입니다.",
        "not_found": "❌ 찾을 수 없습니다.",
    },

    "ar": {
        "choose": "🌐 اختر اللغة:",
        "selected": "✅ تم تغيير اللغة إلى العربية.",
        "help_prompt": "اكتب /help.",
        "syntax": "⚠️ صيغة غير صحيحة. استخدم: ",
        "ai_on": "💬 [AI: ON] - تم تشغيل الذكاء الاصطناعي.",
        "ai_off": "🔇 [AI: OFF] - تم إيقاف الذكاء الاصطناعي.",
        "no_ai": "⚠️ لم يتم إعداد GEMINI_API_KEY.",
        "timeout": "⏳ انتهت مهلة API.",
        "admin": "⚠️ تحتاج صلاحيات المسؤول.",
        "clock_usage": "/clock <HH:MM> <الدولة>\nمثال: /clock 07:30 Saudi Arabia",
        "clock_time": "❌ وقت غير صالح. استخدم HH:MM.",
        "clock_country": "❌ لم يتم التعرف على الدولة أو المنطقة الزمنية.",
        "clock_set": "✅ تم ضبط المنبه.",
        "clock_alarm": "⏰ *منبه!*\n\n🔔 الوقت: `{time}`\n🌍 الدولة: `{country}`\n🕐 المنطقة: `{timezone}`",
        "group_only": "⚠️ للمجموعات فقط.",
        "reply_required": "⚠️ قم بالرد على الرسالة المستهدفة.",
        "invalid_expression": "❌ تعبير غير صالح.",
        "not_found": "❌ لم يتم العثور عليه.",
    },

    "hi": {
        "choose": "🌐 भाषा चुनें:",
        "selected": "✅ भाषा हिन्दी कर दी गई।",
        "help_prompt": "/help लिखें।",
        "syntax": "⚠️ गलत प्रारूप। उपयोग: ",
        "ai_on": "💬 [AI: ON] - AI चालू है।",
        "ai_off": "🔇 [AI: OFF] - AI बंद है।",
        "no_ai": "⚠️ GEMINI_API_KEY सेट नहीं है।",
        "timeout": "⏳ API timeout।",
        "admin": "⚠️ एडमिन अनुमति आवश्यक है।",
        "clock_usage": "/clock <HH:MM> <देश>\nउदाहरण: /clock 07:30 India",
        "clock_time": "❌ समय गलत है। HH:MM उपयोग करें।",
        "clock_country": "❌ देश या टाइम ज़ोन नहीं मिला।",
        "clock_set": "✅ अलार्म सेट हो गया।",
        "clock_alarm": "⏰ *अलार्म!*\n\n🔔 समय: `{time}`\n🌍 देश: `{country}`\n🕐 टाइम ज़ोन: `{timezone}`",
        "group_only": "⚠️ केवल समूह में।",
        "reply_required": "⚠️ लक्ष्य संदेश का जवाब दें।",
        "invalid_expression": "❌ अमान्य अभिव्यक्ति।",
        "not_found": "❌ नहीं मिला।",
    },

    "th": {
        "choose": "🌐 กรุณาเลือกภาษา:",
        "selected": "✅ เปลี่ยนเป็นภาษาไทยแล้ว",
        "help_prompt": "พิมพ์ /help",
        "syntax": "⚠️ รูปแบบไม่ถูกต้อง ใช้: ",
        "ai_on": "💬 [AI: ON] - เปิด AI แล้ว",
        "ai_off": "🔇 [AI: OFF] - ปิด AI แล้ว",
        "no_ai": "⚠️ ยังไม่ได้ตั้งค่า GEMINI_API_KEY",
        "timeout": "⏳ API หมดเวลา",
        "admin": "⚠️ ต้องมีสิทธิ์ผู้ดูแล",
        "clock_usage": "/clock <HH:MM> <ประเทศ>\nตัวอย่าง: /clock 07:30 Thailand",
        "clock_time": "❌ เวลาไม่ถูกต้อง ใช้ HH:MM",
        "clock_country": "❌ ไม่รู้จักประเทศหรือเขตเวลา",
        "clock_set": "✅ ตั้งปลุกแล้ว",
        "clock_alarm": "⏰ *เวลาปลุก!*\n\n🔔 เวลา: `{time}`\n🌍 ประเทศ: `{country}`\n🕐 เขตเวลา: `{timezone}`",
        "group_only": "⚠️ ใช้ได้เฉพาะในกลุ่ม",
        "reply_required": "⚠️ โปรดตอบกลับข้อความเป้าหมาย",
        "invalid_expression": "❌ นิพจน์ไม่ถูกต้อง",
        "not_found": "❌ ไม่พบ",
    },

    "tr": {
        "choose": "🌐 Dil seçin:",
        "selected": "✅ Dil Türkçe olarak ayarlandı.",
        "help_prompt": "/help yazın.",
        "syntax": "⚠️ Geçersiz sözdizimi. Kullanım: ",
        "ai_on": "💬 [AI: ON] - AI açıldı.",
        "ai_off": "🔇 [AI: OFF] - AI kapatıldı.",
        "no_ai": "⚠️ GEMINI_API_KEY ayarlanmadı.",
        "timeout": "⏳ API zaman aşımı.",
        "admin": "⚠️ Yönetici izni gerekiyor.",
        "clock_usage": "/clock <HH:MM> <ülke>\nÖrnek: /clock 07:30 Turkey",
        "clock_time": "❌ Geçersiz saat. HH:MM kullanın.",
        "clock_country": "❌ Ülke veya saat dilimi tanınmadı.",
        "clock_set": "✅ Alarm kuruldu.",
        "clock_alarm": "⏰ *ALARM!*\n\n🔔 Saat: `{time}`\n🌍 Ülke: `{country}`\n🕐 Saat dilimi: `{timezone}`",
        "group_only": "⚠️ Yalnızca gruplarda.",
        "reply_required": "⚠️ Hedef mesaja yanıt verin.",
        "invalid_expression": "❌ Geçersiz ifade.",
        "not_found": "❌ Bulunamadı.",
    },
}


def user_data(chat_id):
    return USER_DATA.setdefault(
        chat_id,
        {
            "lang": "en",
            "ai_mode": False,
            "stats": 0
        }
    )


def get_lang(chat_id):
    return user_data(chat_id).get("lang", "en")


def msg(chat_id, key):
    lang = get_lang(chat_id)
    return LANG.get(
        lang,
        LANG["en"]
    ).get(
        key,
        LANG["en"].get(key, key)
    )


# =========================================================
# HELP TEXT
# =========================================================

HELP_TEXT = {
    "vi": (
        "🚀 *ITZNVL BOT*\n\n"
        "🤖 *AI*\n"
        "/chatwithAI - Bật/tắt AI liên tục\n"
        "/ask <câu hỏi> - Hỏi AI\n\n"
        "🛠 *UTILS*\n"
        "/qr <text> - Tạo QR\n"
        "/calc <phép tính> - Máy tính\n"
        "/base64 <text> - Base64\n"
        "/password - Mật khẩu mạnh\n"
        "/wiki <từ khóa> - Wikipedia\n"
        "/weather <địa danh> - Thời tiết\n"
        "/clock <HH:MM> <quốc gia> - Báo thức\n"
        "/ping - Kiểm tra độ trễ\n"
        "/id - Xem ID\n\n"
        "📈 *FINANCE*\n"
        "/crypto <coin> - Giá crypto\n"
        "/short <link> - Rút gọn link\n\n"
        "🎉 *FUN*\n"
        "/joke - Joke\n"
        "/fact - Fun fact\n\n"
        "🎮 *GAMES*\n"
        "/dice /dart /basket /football /bowling /slot\n"
        "/coin - Tung đồng xu\n\n"
        "🛡 *ADMIN*\n"
        "/pin - Ghim tin nhắn\n"
        "/ban - Ban user\n"
        "/thongbao <nội dung> - Broadcast\n"
        "/stats - Thống kê\n\n"
        "🌐 /language - Đổi ngôn ngữ"
    ),

    "en": (
        "🚀 *ITZNVL BOT*\n\n"
        "🤖 *AI*\n"
        "/chatwithAI - Toggle AI chat\n"
        "/ask <query> - Ask AI\n\n"
        "🛠 *UTILS*\n"
        "/qr <text> - QR Code\n"
        "/calc <expression> - Calculator\n"
        "/base64 <text> - Base64\n"
        "/password - Strong password\n"
        "/wiki <keyword> - Wikipedia\n"
        "/weather <location> - Weather\n"
        "/clock <HH:MM> <country> - Alarm\n"
        "/ping - Latency\n"
        "/id - IDs\n\n"
        "📈 *FINANCE*\n"
        "/crypto <coin> - Crypto price\n"
        "/short <link> - Short URL\n\n"
        "🎉 *FUN*\n"
        "/joke - Joke\n"
        "/fact - Fun fact\n\n"
        "🎮 *GAMES*\n"
        "/dice /dart /basket /football /bowling /slot\n"
        "/coin - Coin flip\n\n"
        "🛡 *ADMIN*\n"
        "/pin - Pin\n"
        "/ban - Ban\n"
        "/thongbao <text> - Broadcast\n"
        "/stats - Statistics\n\n"
        "🌐 /language - Change language"
    ),
}


def help_text(chat_id):
    lang = get_lang(chat_id)
    return HELP_TEXT.get(
        lang,
        HELP_TEXT["en"]
    )


# =========================================================
# CLOCK
# =========================================================

COUNTRY_TIMEZONES = {
    "vietnam": "Asia/Ho_Chi_Minh",
    "viet nam": "Asia/Ho_Chi_Minh",
    "việt nam": "Asia/Ho_Chi_Minh",
    "vn": "Asia/Ho_Chi_Minh",

    "thailand": "Asia/Bangkok",
    "thái lan": "Asia/Bangkok",
    "thai": "Asia/Bangkok",

    "indonesia": "Asia/Jakarta",
    "indonesian": "Asia/Jakarta",

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

    "saudi arabia": "Asia/Riyadh",

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
}


CLOCK_ALARMS = {}
CLOCK_LOCK = threading.Lock()
CLOCK_ID = 1


def normalize_country(value):
    return " ".join(
        value.strip().lower().split()
    )


def resolve_timezone(country):
    original = country.strip()

    # Cho phép dùng trực tiếp IANA timezone:
    # Asia/Ho_Chi_Minh
    if "/" in original:
        try:
            return ZoneInfo(original)
        except ZoneInfoNotFoundError:
            return None

    name = COUNTRY_TIMEZONES.get(
        normalize_country(original)
    )

    if not name:
        return None

    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return None


def parse_time(value):
    value = value.strip().lower()

    for separator in (":", ".", "h"):
        if separator in value:
            left, right = value.split(
                separator,
                1
            )

            if not right:
                right = "0"

            try:
                hour = int(left)
                minute = int(right)
            except ValueError:
                return None

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute

            return None

    return None


def add_alarm(
    chat_id,
    hour,
    minute,
    tz,
    country
):
    global CLOCK_ID

    now_local = datetime.now(tz)

    target = now_local.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    if target <= now_local:
        target += timedelta(days=1)

    with CLOCK_LOCK:
        alarm_id = CLOCK_ID

        CLOCK_ALARMS[alarm_id] = {
            "chat_id": chat_id,
            "target": target,
            "country": country,
            "timezone": str(tz),
        }

        CLOCK_ID += 1

    return alarm_id, target


def clock_worker():
    while True:
        current = datetime.now(
            timezone.utc
        )

        due = []

        with CLOCK_LOCK:
            for alarm_id, alarm in list(
                CLOCK_ALARMS.items()
            ):
                target_utc = (
                    alarm["target"]
                    .astimezone(timezone.utc)
                )

                if current >= target_utc:
                    due.append(
                        (alarm_id, alarm)
                    )

                    del CLOCK_ALARMS[
                        alarm_id
                    ]

        for alarm_id, alarm in due:
            try:
                chat_id = alarm["chat_id"]
                target = alarm["target"]

                text = msg(
                    chat_id,
                    "clock_alarm"
                ).format(
                    time=target.strftime(
                        "%H:%M"
                    ),
                    country=alarm["country"],
                    timezone=alarm["timezone"]
                )

                bot.send_message(
                    chat_id,
                    text,
                    parse_mode="Markdown"
                )

                print(
                    f"✅ Clock alarm {alarm_id} sent "
                    f"to {chat_id}"
                )

            except Exception as e:
                print(
                    f"❌ Clock alarm {alarm_id} error: {e}"
                )

        time.sleep(1)


clock_thread = threading.Thread(
    target=clock_worker,
    daemon=True,
    name="clock-worker"
)

clock_thread.start()


# =========================================================
# SAFE CALCULATOR
# =========================================================

_ALLOWED_AST = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Constant,
)


def safe_calculate(expression):
    tree = ast.parse(
        expression,
        mode="eval"
    )

    for node in ast.walk(tree):
        if not isinstance(
            node,
            _ALLOWED_AST
        ):
            raise ValueError

        if (
            isinstance(node, ast.Constant)
            and not isinstance(
                node.value,
                (int, float)
            )
        ):
            raise ValueError

    return eval(
        compile(
            tree,
            "<calc>",
            "eval"
        ),
        {
            "__builtins__": {}
        },
        {}
    )


# =========================================================
# START / LANGUAGE
# =========================================================

@bot.message_handler(
    commands=["start", "language"]
)
def cmd_start(message):
    chat_id = message.chat.id

    user_data(chat_id)

    keyboard = InlineKeyboardMarkup()

    buttons = [
        InlineKeyboardButton(
            name,
            callback_data=f"lang_{code}"
        )
        for code, name
        in SUPPORTED_LANGUAGES.items()
    ]

    for index in range(
        0,
        len(buttons),
        2
    ):
        keyboard.add(
            *buttons[index:index + 2]
        )

    bot.send_message(
        chat_id,
        msg(chat_id, "choose"),
        reply_markup=keyboard
    )


@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("lang_")
)
def callback_language(call):
    chat_id = call.message.chat.id

    language = call.data.split(
        "_",
        1
    )[1]

    if language not in SUPPORTED_LANGUAGES:
        bot.answer_callback_query(
            call.id
        )
        return

    user_data(chat_id)["lang"] = language

    bot.answer_callback_query(
        call.id
    )

    bot.edit_message_text(
        (
            msg(
                chat_id,
                "selected"
            )
            + "\n\n"
            + msg(
                chat_id,
                "help_prompt"
            )
        ),
        chat_id,
        call.message.message_id
    )


# =========================================================
# HELP
# =========================================================

@bot.message_handler(
    commands=["help"]
)
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        help_text(message.chat.id),
        parse_mode="Markdown"
    )


# =========================================================
# STATS
# =========================================================

@bot.message_handler(
    commands=["stats"]
)
def cmd_stats(message):
    data = user_data(
        message.chat.id
    )

    bot.send_message(
        message.chat.id,
        (
            "📊 Stats\n"
            f"Interactions: `{data['stats']}`"
        ),
        parse_mode="Markdown"
    )


# =========================================================
# AI
# =========================================================

@bot.message_handler(
    commands=["chatwithAI", "cancel"]
)
def cmd_ai_toggle(message):
    chat_id = message.chat.id
    data = user_data(chat_id)

    command = (
        message.text or ""
    ).split()[0].lower()

    enabled = (
        command == "/chatwithai"
    )

    data["ai_mode"] = enabled

    bot.send_message(
        chat_id,
        msg(
            chat_id,
            "ai_on" if enabled else "ai_off"
        )
    )


def ask_ai(prompt):
    if not gemini_client:
        raise RuntimeError(
            "AI_NOT_CONFIGURED"
        )

    response = (
        gemini_client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt
        )
    )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:
        return "⚠️ AI không trả về nội dung."

    return text


@bot.message_handler(
    commands=["ask"]
)
def cmd_ask(message):
    text = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(text) < 2:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/ask <query>"
        )
        return

    query = text[1].strip()

    if not query:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/ask <query>"
        )
        return

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    try:
        answer = ask_ai(query)

        bot.reply_to(
            message,
            f"🤖 *itznvl AI:*\n{answer}",
            parse_mode="Markdown"
        )

    except RuntimeError as e:
        if str(e) == "AI_NOT_CONFIGURED":
            bot.reply_to(
                message,
                msg(
                    message.chat.id,
                    "no_ai"
                )
            )
        else:
            bot.reply_to(
                message,
                f"❌ AI Error: {e}"
            )

    except Exception as e:
        print(f"[AI] {e}")

        bot.reply_to(
            message,
            f"❌ AI Error: {e}"
        )


# =========================================================
# CLOCK COMMAND
# =========================================================

@bot.message_handler(
    commands=["clock"]
)
def cmd_clock(message):
    chat_id = message.chat.id

    parts = (
        message.text or ""
    ).split(
        maxsplit=2
    )

    if len(parts) < 3:
        bot.reply_to(
            message,
            msg(
                chat_id,
                "clock_usage"
            )
        )
        return

    time_text = parts[1].strip()
    country = parts[2].strip()

    parsed = parse_time(
        time_text
    )

    if parsed is None:
        bot.reply_to(
            message,
            msg(
                chat_id,
                "clock_time"
            )
        )
        return

    tz = resolve_timezone(
        country
    )

    if tz is None:
        bot.reply_to(
            message,
            msg(
                chat_id,
                "clock_country"
            )
        )
        return

    hour, minute = parsed

    alarm_id, target = add_alarm(
        chat_id,
        hour,
        minute,
        tz,
        country
    )

    local_now = datetime.now(tz)

    day = (
        "today"
        if target.date()
        == local_now.date()
        else "tomorrow"
    )

    bot.send_message(
        chat_id,
        (
            f"⏰ <b>{msg(chat_id, 'clock_set')}</b>\n\n"
            f"🔔 Time: <code>{target:%H:%M}</code>\n"
            f"📅 <code>{target:%d/%m/%Y}</code> "
            f"({day})\n"
            f"🌍 Country: <code>{country}</code>\n"
            f"🕐 Timezone: <code>{tz}</code>\n"
            f"🆔 Alarm ID: <code>{alarm_id}</code>"
        ),
        parse_mode="HTML"
    )


# =========================================================
# QR
# =========================================================

@bot.message_handler(
    commands=["qr"]
)
def cmd_qr(message):
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/qr <text>"
        )
        return

    text = parts[1].strip()

    try:
        image = qrcode.make(text)

        output = io.BytesIO()
        image.save(
            output,
            format="PNG"
        )
        output.seek(0)

        bot.send_photo(
            message.chat.id,
            output,
            caption="✅ QR Code Generated"
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ QR Error: {e}"
        )


# =========================================================
# CALCULATOR
# =========================================================

@bot.message_handler(
    commands=["calc"]
)
def cmd_calc(message):
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/calc <expression>"
        )
        return

    expression = parts[1].strip()

    if len(expression) > 200:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "invalid_expression"
            )
        )
        return

    try:
        result = safe_calculate(
            expression
        )

        bot.reply_to(
            message,
            f"🧮 `{expression} = {result}`",
            parse_mode="Markdown"
        )

    except Exception:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "invalid_expression"
            )
        )


# =========================================================
# BASE64
# =========================================================

@bot.message_handler(
    commands=["base64"]
)
def cmd_base64(message):
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/base64 <text>"
        )
        return

    encoded = base64.b64encode(
        parts[1].encode(
            "utf-8"
        )
    ).decode(
        "utf-8"
    )

    bot.reply_to(
        message,
        f"🔒 Base64:\n`{encoded}`",
        parse_mode="Markdown"
    )


# =========================================================
# WIKIPEDIA
# =========================================================

@bot.message_handler(
    commands=["wiki"]
)
def cmd_wiki(message):
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/wiki <keyword>"
        )
        return

    keyword = parts[1].strip()

    try:
        url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(
                keyword
            )
        )

        response = requests.get(
            url,
            headers={
                "User-Agent":
                "itznvl-bot/4.0"
            },
            timeout=7
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP {response.status_code}"
            )

        data = response.json()

        extract = data.get(
            "extract"
        )

        if not extract:
            bot.reply_to(
                message,
                msg(
                    message.chat.id,
                    "not_found"
                )
            )
            return

        title = data.get(
            "title",
            keyword
        )

        bot.reply_to(
            message,
            f"📚 *{title}*\n\n{extract}",
            parse_mode="Markdown"
        )

    except Exception as e:
        print(
            f"[WIKI] {e}"
        )

        bot.reply_to(
            message,
            f"❌ Wikipedia Error: {e}"
        )


# =========================================================
# WEATHER
# =========================================================

@bot.message_handler(
    commands=["weather"]
)
def cmd_weather(message):
    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "syntax"
            ) + "/weather <location>"
        )
        return

    location = parts[1].strip()

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    headers = {
        "User-Agent":
        "itznvl-bot/4.0"
    }

    try:
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "limit": 1,
                "accept-language": "vi"
            },
            headers=headers,
            timeout=7
        ).json()

        target = location

        if geo:
            target = geo[0].get(
                "display_name",
                location
            )

        weather = requests.get(
            "https://wttr.in/"
            + urllib.parse.quote(
                target
            ),
            params={
                "format": "3",
                "lang": "vi"
            },
            headers=headers,
            timeout=10
        )

        text = weather.text.strip()

        if (
            weather.status_code != 200
            or not text
            or "Unknown location"
            in text
        ):
            raise RuntimeError(
                "Location not found"
            )

        bot.reply_to(
            message,
            (
                f"🌤 `{location}`\n"
                f"`{text}`"
            ),
            parse_mode="Markdown"
        )

    except requests.exceptions.Timeout:
        bot.reply_to(
            message,
            msg(
                message.chat.id,
                "timeout"
            )
        )

    except Exception as e:
        print(
            f"[WEATHER] {e}"
        )

        bot.reply_to(
            message,
            f"❌ Weather Error: {e}"
        )


# =========================================================
# QUICK COMMANDS
# =========================================================

@bot.message_handler(
    commands=[
        "ping",
        "id",
        "password"
    ]
)
def cmd_quick(message):
    command = (
        message.text or ""
    ).split()[0].lower()

    chat_id = message.chat.id

    if command == "/ping":
        start = time.perf_counter()

        sent = bot.send_message(
            chat_id,
            "⏳"
        )

        ms = round(
            (time.perf_counter() - start)
            * 1000
        )

        bot.edit_message_text(
            f"🏓 Latency: `{ms}ms`",
            chat_id,
            sent.message_id,
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

    else:
        characters = (
            string.ascii_letters
            + string.digits
            + "!@#$%^&*"
        )

        password = "".join(
            random.choices(
                characters,
                k=20
            )
        )

        bot.send_message(
            chat_id,
            (
                "🔐 Password:\n"
                f"`{password}`"
            ),
            parse_mode="Markdown"
        )


# =========================================================
# CRYPTO / SHORT / JOKE / FACT
# =========================================================

@bot.message_handler(
    commands=[
        "crypto",
        "short",
        "joke",
        "fact"
    ]
)
def cmd_external(message):
    command = (
        message.text or ""
    ).split()[0].lower()

    chat_id = message.chat.id

    try:
        if command == "/crypto":
            parts = (
                message.text or ""
            ).split(
                maxsplit=1
            )

            if len(parts) < 2:
                bot.reply_to(
                    message,
                    msg(chat_id, "syntax")
                    + "/crypto <coin>"
                )
                return

            coin = (
                parts[1]
                .strip()
                .upper()
            )

            symbol = coin + "USDT"

            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={
                    "symbol": symbol
                },
                timeout=7
            )

            data = response.json()

            if "price" not in data:
                raise RuntimeError(
                    "Coin not found."
                )

            price = float(
                data["price"]
            )

            bot.send_message(
                chat_id,
                (
                    f"📈 *{coin}/USDT*\n"
                    f"`{price:,.8f}`"
                ),
                parse_mode="Markdown"
            )

        elif command == "/short":
            parts = (
                message.text or ""
            ).split(
                maxsplit=1
            )

            if len(parts) < 2:
                bot.reply_to(
                    message,
                    msg(chat_id, "syntax")
                    + "/short <link>"
                )
                return

            link = parts[1].strip()

            response = requests.get(
                "https://is.gd/create.php",
                params={
                    "format": "json",
                    "url": link
                },
                timeout=7
            )

            data = response.json()

            short_url = data.get(
                "shorturl"
            )

            if not short_url:
                raise RuntimeError(
                    data.get(
                        "errormessage",
                        "Unable to shorten URL."
                    )
                )

            bot.send_message(
                chat_id,
                f"🔗 Short URL:\n{short_url}"
            )

        elif command == "/joke":
            response = requests.get(
                "https://official-joke-api.appspot.com/random_joke",
                timeout=7
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
                timeout=7
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
            msg(
                chat_id,
                "timeout"
            )
        )

    except Exception as e:
        print(
            f"[EXTERNAL] {e}"
        )

        bot.send_message(
            chat_id,
            f"❌ API Error: {e}"
        )


# =========================================================
# GAMES
# =========================================================

GAME_EMOJIS = {
    "/dice": "🎲",
    "/dart": "🎯",
    "/basket": "🏀",
    "/football": "⚽",
    "/bowling": "🎳",
    "/slot": "🎰",
}


@bot.message_handler(
    commands=[
        "dice",
        "dart",
        "basket",
        "football",
        "bowling",
        "slot",
        "coin"
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
                "Tails 🪙"
            ]
        )

        bot.send_message(
            message.chat.id,
            f"🪙 *{result}*",
            parse_mode="Markdown"
        )
        return

    emoji = GAME_EMOJIS.get(
        command
    )

    if emoji:
        bot.send_dice(
            message.chat.id,
            emoji=emoji
        )


# =========================================================
# ADMIN
# =========================================================

@bot.message_handler(
    commands=[
        "pin",
        "ban"
    ]
)
def cmd_admin(message):
    chat_id = message.chat.id

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        bot.reply_to(
            message,
            msg(
                chat_id,
                "group_only"
            )
        )
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            msg(
                chat_id,
                "reply_required"
            )
        )
        return

    try:
        admins = bot.get_chat_administrators(
            chat_id
        )

        admin_ids = {
            admin.user.id
            for admin in admins
        }

        if message.from_user.id not in admin_ids:
            bot.reply_to(
                message,
                msg(
                    chat_id,
                    "admin"
                )
            )
            return

        command = (
            message.text or ""
        ).split()[0].lower()

        target = (
            message.reply_to_message
            .from_user
            .id
        )

        if command == "/pin":
            bot.pin_chat_message(
                chat_id,
                message.reply_to_message.message_id
            )

            bot.reply_to(
                message,
                "📌 Pinned successfully!"
            )

        elif command == "/ban":
            bot.ban_chat_member(
                chat_id,
                target
            )

            bot.reply_to(
                message,
                "🔨 User banned."
            )

    except Exception as e:
        print(
            f"[ADMIN] {e}"
        )

        bot.reply_to(
            message,
            f"❌ Admin error: {e}"
        )


# =========================================================
# BROADCAST
# =========================================================

@bot.message_handler(
    commands=["thongbao"]
)
def cmd_broadcast(message):
    chat_id = message.chat.id

    if (
        ADMIN_ID
        and str(
            message.from_user.id
        )
        != str(ADMIN_ID)
    ):
        bot.reply_to(
            message,
            "⚠️ Bạn không có quyền sử dụng lệnh này!"
        )
        return

    parts = (
        message.text or ""
    ).split(
        maxsplit=1
    )

    if len(parts) < 2:
        bot.reply_to(
            message,
            msg(chat_id, "syntax")
            + "/thongbao <nội dung>"
        )
        return

    text = parts[1].strip()

    success = 0
    failed = 0

    for target_chat in list(
        USER_DATA.keys()
    ):
        try:
            bot.send_message(
                target_chat,
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
                f"[BROADCAST] "
                f"{target_chat}: {e}"
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
# FALLBACK / CONTINUOUS AI
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def fallback(message):
    if not message.text:
        return

    chat_id = message.chat.id
    data = user_data(chat_id)

    data["stats"] += 1

    if not data.get(
        "ai_mode",
        False
    ):
        if message.chat.type == "private":
            bot.send_message(
                chat_id,
                msg(
                    chat_id,
                    "help_prompt"
                )
            )
        return

    bot.send_chat_action(
        chat_id,
        "typing"
    )

    try:
        answer = ask_ai(
            message.text
        )

        bot.reply_to(
            message,
            answer
        )

    except RuntimeError as e:
        if str(e) == "AI_NOT_CONFIGURED":
            bot.reply_to(
                message,
                msg(
                    chat_id,
                    "no_ai"
                )
            )
        else:
            bot.reply_to(
                message,
                f"❌ AI Error: {e}"
            )

    except Exception as e:
        print(
            f"[AI CHAT] {e}"
        )

        bot.reply_to(
            message,
            f"❌ AI Error: {e}"
        )


# =========================================================
# WEBHOOK
# =========================================================

WEBHOOK_PATH = f"/telegram/{TOKEN}"


@app.route(
    WEBHOOK_PATH,
    methods=["POST"]
)
def telegram_webhook():
    content_type = request.headers.get(
        "content-type",
        ""
    )

    if not content_type.startswith(
        "application/json"
    ):
        return "Forbidden", 403

    try:
        body = request.get_data(
            as_text=True
        )

        update = (
            telebot.types.Update
            .de_json(body)
        )

        bot.process_new_updates(
            [update]
        )

        return "", 200

    except Exception as e:
        print(
            f"[WEBHOOK] {e}"
        )

        return "Bad Request", 400


@app.get("/")
def health():
    return (
        "itznvl Bot Web Service is running successfully!",
        200
    )


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }, 200


# =========================================================
# WEBHOOK SETUP
# =========================================================

def configure_webhook():
    if not RENDER_EXTERNAL_URL:
        print(
            "⚠️ RENDER_EXTERNAL_URL chưa được cấu hình."
        )
        print(
            "⚠️ Webhook chưa được tự động thiết lập."
        )
        return

    webhook_url = (
        f"{RENDER_EXTERNAL_URL}"
        f"{WEBHOOK_PATH}"
    )

    try:
        bot.remove_webhook()

        time.sleep(
            1
        )

        result = bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )

        print(
            f"🌐 Service URL: "
            f"{RENDER_EXTERNAL_URL}"
        )

        print(
            f"🔗 Webhook URL: "
            f"{webhook_url}"
        )

        print(
            f"✅ Webhook configured: "
            f"{result}"
        )

    except Exception as e:
        print(
            f"❌ Webhook setup failed: {e}"
        )


# =========================================================
# STARTUP
# =========================================================

configure_webhook()


if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    print(
        f"🚀 Starting Flask on "
        f"0.0.0.0:{port}"
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
```
