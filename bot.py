import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import qrcode
import random
import string
import time
import io
import urllib.parse
import base64

TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=12)

# =========================================================
# CẤU TRÚC MỞ RỘNG 16 NGÔN NGỮ TOÀN CẦU
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
    "tr": "🇹🇷 Türkçe"
}

LANG_DICT = {
    'vi': {
        'choose_lang': '🌐 Vui lòng chọn ngôn ngữ giao diện:',
        'lang_selected': '✅ Đã chuyển sang Tiếng Việt.',
        'help_prompt': 'Gõ /help để xem danh sách lệnh tĩnh.',
        'help_text': "🚀 *SIÊU BOT (16 NGÔN NGỮ)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILS*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANCE*\n/crypto, /short, /joke\n🎮 *4. GAMES & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Sai cú pháp. Dùng đúng định dạng: ',
        'ai_on': '💬 [AI: ON]\n(Gõ /cancel để tắt)',
        'ai_off': '🔇 [AI: OFF]',
        'api_timeout': '⏳ Thời gian chờ phản hồi API quá hạn!',
        'admin_only': '⚠️ Yêu cầu quyền Quản trị viên (Admin) nhóm!'
    },
    'en': {
        'choose_lang': '🌐 Please select interface language:',
        'lang_selected': '✅ Language set to English.',
        'help_prompt': 'Type /help for static command list.',
        'help_text': "🚀 *SUPER BOT (16 LANGUAGES)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILS*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANCE*\n/crypto, /short, /joke\n🎮 *4. GAMES & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Invalid syntax. Use: ',
        'ai_on': '💬 [AI: ON]\n(Type /cancel to off)',
        'ai_off': '🔇 [AI: OFF]',
        'api_timeout': '⏳ API connection timeout!',
        'admin_only': '⚠️ Group Admin permissions required!'
    },
    'id': {
        'choose_lang': '🌐 Silakan pilih bahasa antarmuka:',
        'lang_selected': '✅ Bahasa diatur ke Bahasa Indonesia.',
        'help_prompt': 'Ketik /help untuk melihat daftar perintah.',
        'help_text': "🚀 *SUPER BOT (16 BAHASA)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILITAS*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. KEUANGAN*\n/crypto, /short, /joke\n🎮 *4. GAME & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Sintaks tidak valid. Gunakan: ',
        'ai_on': '💬 [AI: AKTIF]\n(Ketik /cancel untuk mematikan)',
        'ai_off': '🔇 [AI: NONAKTIF]',
        'api_timeout': '⏳ Batas waktu permintaan API habis!',
        'admin_only': '⚠️ Memerlukan izin Admin grup!'
    },
    'es': {
        'choose_lang': '🌐 Seleccione el idioma de la interfaz:',
        'lang_selected': '✅ Idioma cambiado a Español.',
        'help_prompt': 'Escribe /help para ver la lista de comandos.',
        'help_text': "🚀 *SUPER BOT (16 IDIOMAS)*\n\n🤖 *1. IA*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILIDADES*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANZAS*\n/crypto, /short, /joke\n🎮 *4. JUEGOS Y ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Sintaxis incorrecta. Use: ',
        'ai_on': '💬 [IA: ACTIVO]\n(Escribe /cancel para desactivar)',
        'ai_off': '🔇 [IA: INACTIVO]',
        'api_timeout': '⏳ ¡Tiempo de espera de API agotado!',
        'admin_only': '⚠️ ¡Se requieren permisos de administrador!'
    },
    'fr': {
        'choose_lang': '🌐 Veuillez sélectionner la langue de l’interface :',
        'lang_selected': '✅ Langue définie sur Français.',
        'help_prompt': 'Tapez /help pour voir la liste des commandes.',
        'help_text': "🚀 *SUPER BOT (16 LANGUES)*\n\n🤖 *1. IA*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILITAIRES*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANCE*\n/crypto, /short, /joke\n🎮 *4. JEUX & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Syntaxe incorrecte. Utilisez : ',
        'ai_on': '💬 [IA : ACTIVÉE]\n(Tapez /cancel pour désactiver)',
        'ai_off': '🔇 [IA : DÉSACTIVÉE]',
        'api_timeout': '⏳ Délai d’attente de l’API dépassé !',
        'admin_only': '⚠️ Permissions d’administrateur requises !'
    },
    'de': {
        'choose_lang': '🌐 Bitte wählen Sie die Sprache:',
        'lang_selected': '✅ Sprache auf Deutsch eingestellt.',
        'help_prompt': 'Geben Sie /help ein, um Befehle anzuzeigen.',
        'help_text': "🚀 *SUPER BOT (16 SPRACHEN)*\n\n🤖 *1. KI*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILS*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANZEN*\n/crypto, /short, /joke\n🎮 *4. SPIELE & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Ungültige Syntax. Verwendung: ',
        'ai_on': '💬 [KI: AN]\n(/cancel zum Ausschalten)',
        'ai_off': '🔇 [KI: AUS]',
        'api_timeout': '⏳ API-Zeitüberschreitung!',
        'admin_only': '⚠️ Admin-Rechte erforderlich!'
    },
    'ru': {
        'choose_lang': '🌐 Пожалуйста, выберите язык:',
        'lang_selected': '✅ Язык изменен на русский.',
        'help_prompt': 'Введите /help для просмотра команд.',
        'help_text': "🚀 *SUPER BOT (16 ЯЗЫКОВ)*\n\n🤖 *1. ИИ*\n/chatwithAI, /cancel, /ask\n🛠 *2. УТИЛИТЫ*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. ФИНАНСЫ*\n/crypto, /short, /joke\n🎮 *4. ИГРЫ И АДМИН*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Неверный синтаксис. Используйте: ',
        'ai_on': '💬 [ИИ: ВКЛ]\n(Введите /cancel для выключения)',
        'ai_off': '🔇 [ИИ: ВЫКЛ]',
        'api_timeout': '⏳ Время ожидания API истекло!',
        'admin_only': '⚠️ Требуются права администратора!'
    },
    'pt': {
        'choose_lang': '🌐 Por favor, selecione o idioma:',
        'lang_selected': '✅ Idioma definido para Português.',
        'help_prompt': 'Digite /help para ver os comandos.',
        'help_text': "🚀 *SUPER BOT (16 IDIOMAS)*\n\n🤖 *1. IA*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILIDADES*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANÇAS*\n/crypto, /short, /joke\n🎮 *4. JOGOS & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Sintaxe inválida. Use: ',
        'ai_on': '💬 [IA: LIGADA]\n(Digite /cancel para desligar)',
        'ai_off': '🔇 [IA: DESLIGADA]',
        'api_timeout': '⏳ Tempo limite da API esgotado!',
        'admin_only': '⚠️ Permissões de Administrador necessárias!'
    },
    'it': {
        'choose_lang': '🌐 Seleziona la lingua dell’interfaccia:',
        'lang_selected': '✅ Lingua impostata su Italiano.',
        'help_prompt': 'Digita /help per vedere i comandi.',
        'help_text': "🚀 *SUPER BOT (16 LINGUE)*\n\n🤖 *1. IA*\n/chatwithAI, /cancel, /ask\n🛠 *2. UTILS*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FINANZA*\n/crypto, /short, /joke\n🎮 *4. GIOCHI & ADMIN*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Sintassi non valida. Usa: ',
        'ai_on': '💬 [IA: ATTIVA]\n(Digita /cancel per spegnere)',
        'ai_off': '🔇 [IA: DISATTIVA]',
        'api_timeout': '⏳ Timeout della richiesta API!',
        'admin_only': '⚠️ Richiesti permessi di Amministratore!'
    },
    'zh': {
        'choose_lang': '🌐 请选择界面语言：',
        'lang_selected': '✅ 语言已设置为中文。',
        'help_prompt': '输入 /help 查看静态命令列表。',
        'help_text': "🚀 *超级机器人（16语言）*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. 工具*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. 金融*\n/crypto, /short, /joke\n🎮 *4. 游戏与管理*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ 语法错误。请使用：',
        'ai_on': '💬 [AI：开启]\n（输入 /cancel 关闭）',
        'ai_off': '🔇 [AI：关闭]',
        'api_timeout': '⏳ API 请求超时！',
        'admin_only': '⚠️ 需要群组管理员权限！'
    },
    'ja': {
        'choose_lang': '🌐 インターフェース言語を選択してください：',
        'lang_selected': '✅ 言語が日本語に設定されました。',
        'help_prompt': '/help と入力してコマンドリストを表示します。',
        'help_text': "🚀 *スーパーボット（16言語）*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. ツール*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. 金融*\n/crypto, /short, /joke\n🎮 *4. ゲーム & 管理*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ 構文エラーです。以下を使用してください：',
        'ai_on': '💬 [AI：オン]\n（/cancel でオフ）',
        'ai_off': '🔇 [AI：オフ]',
        'api_timeout': '⏳ API 接続がタイムアウトしました！',
        'admin_only': '⚠️ グループ管理者権限が必要です！'
    },
    'ko': {
        'choose_lang': '🌐 인터페이스 언어를 선택하세요:',
        'lang_selected': '✅ 언어가 한국어로 설정되었습니다.',
        'help_prompt': '/help를 입력하여 명령어 목록을 확인하세요.',
        'help_text': "🚀 *슈퍼봇 (16개 언어)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. 유틸리티*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. 금융*\n/crypto, /short, /joke\n🎮 *4. 게임 및 관리자*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ 구문 오류입니다. 다음을 사용하세요: ',
        'ai_on': '💬 [AI: 켜짐]\n(/cancel을 입력하여 끄기)',
        'ai_off': '🔇 [AI: 꺼짐]',
        'api_timeout': '⏳ API 요청 시간이 초과되었습니다!',
        'admin_only': '⚠️ 그룹 관리자 권한이 필요합니다!'
    },
    'ar': {
        'choose_lang': '🌐 الرجاء اختيار لغة الواجهة:',
        'lang_selected': '✅ تم ضبط اللغة على العربية.',
        'help_prompt': 'اكتب /help لعرض قائمة الأوامر.',
        'help_text': "🚀 *الروبوت الخارق (16 لغة)*\n\n🤖 *1. الذكاء الاصطناعي*\n/chatwithAI, /cancel, /ask\n🛠 *2. الأدوات*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. المالية*\n/crypto, /short, /joke\n🎮 *4. الألعاب والمسؤول*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ صيغة غير صحيحة. استعمل: ',
        'ai_on': '💬 [الذكاء الاصطناعي: مفعل]\n(اكتب /cancel للإيقاف)',
        'ai_off': '🔇 [الذكاء الاصطناعي: متوقف]',
        'api_timeout': '⏳ انتهت مهلة طلب API!',
        'admin_only': '⚠️ مطلوب صلاحيات المشرف!'
    },
    'hi': {
        'choose_lang': '🌐 कृपया इंटरफ़ेस भाषा चुनें:',
        'lang_selected': '✅ भाषा हिंदी पर सेट की गई।',
        'help_prompt': 'आदेश देखने के लिए /help टाइप करें।',
        'help_text': "🚀 *सुपर बॉट (16 भाषाएँ)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. यूटिलिटी*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. फाइनेंस*\n/crypto, /short, /joke\n🎮 *4. गेम और एडमिन*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ अमान्य सिंटैक्स। उपयोग करें: ',
        'ai_on': '💬 [AI: चालू]\n(बंद करने के लिए /cancel टाइप करें)',
        'ai_off': '🔇 [AI: बंद]',
        'api_timeout': '⏳ API अनुरोध का समय समाप्त हो गया!',
        'admin_only': '⚠️ समूह व्यवस्थापक अनुमति आवश्यक है!'
    },
    'th': {
        'choose_lang': '🌐 กรุณาเลือกภาษาของอินเทอร์เฟซ:',
        'lang_selected': '✅ ตั้งค่าภาษาเป็นภาษาไทยแล้ว',
        'help_prompt': 'พิมพ์ /help เพื่อดูรายการคำสั่ง',
        'help_text': "🚀 *ซูเปอร์บอท (16 ภาษา)*\n\n🤖 *1. AI*\n/chatwithAI, /cancel, /ask\n🛠 *2. เครื่องมือ*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. การเงิน*\n/crypto, /short, /joke\n🎮 *4. เกมและผู้ดูแล*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ รูปแบบคำสั่งไม่ถูกต้อง ใช้: ',
        'ai_on': '💬 [AI: เปิด]\n(พิมพ์ /cancel เพื่อปิด)',
        'ai_off': '🔇 [AI: ปิด]',
        'api_timeout': '⏳ หมดเวลาการเชื่อมต่อ API!',
        'admin_only': '⚠️ ต้องการสิทธิ์ผู้ดูแลระบบกลุ่ม!'
    },
    'tr': {
        'choose_lang': '🌐 Lütfen arayüz dilini seçin:',
        'lang_selected': '✅ Dil Türkçe olarak ayarlandı.',
        'help_prompt': 'Komut listesini görmek için /help yazın.',
        'help_text': "🚀 *SÜPER BOT (16 DİL)*\n\n🤖 *1. YAPAY ZEKA*\n/chatwithAI, /cancel, /ask\n🛠 *2. ARAÇLAR*\n/qr, /calc, /base64, /password, /ping, /id\n📈 *3. FİNANS*\n/crypto, /short, /joke\n🎮 *4. OYUNLAR & YÖNETİCİ*\n/dice, /dart, /basket, /coin, /pin, /ban, /stats",
        'syntax_err': '⚠️ Geçersiz sözdizimi. Şunu kullanın: ',
        'ai_on': '💬 [YAPAY ZEKA: AÇIK]\n(Kapatmak için /cancel yazın)',
        'ai_off': '🔇 [YAPAY ZEKA: KAPALI]',
        'api_timeout': '⏳ API istek zaman aşımına uğradı!',
        'admin_only': '⚠️ Grup Yöneticisi izinleri gerekiyor!'
    }
}

GAME_EMOJIS_MAP = {
    '/dice': '🎲', '/dart': '🎯', '/basket': '🏀', 
    '/football': '⚽', '/bowling': '🎳', '/slot': '🎰'
}

def get_msg(chat_id, key):
    lang = USER_DATA.get(chat_id, {}).get('lang', 'en')
    return LANG_DICT.get(lang, LANG_DICT['en']).get(key, LANG_DICT['en'].get(key, key))

def validate_args(message, min_len, syntax):
    args = message.text.split(' ', 1)
    if len(args) < min_len or not args[1].strip():
        bot.send_message(message.chat.id, get_msg(message.chat.id, 'syntax_err') + syntax)
        return None
    return args[1].strip()

@bot.message_handler(commands=['start', 'language'])
def cmd_start(message):
    chat_id = message.chat.id
    USER_DATA.setdefault(chat_id, {'lang': 'en', 'ai_mode': False, 'stats': 0})
    
    markup = InlineKeyboardMarkup()
    buttons = [InlineKeyboardButton(name, callback_data=f"lang_{code}") for code, name in SUPPORTED_LANGUAGES.items()]
    for i in range(0, len(buttons), 2): 
        markup.add(*buttons[i:i+2])
    bot.send_message(chat_id, get_msg(chat_id, 'choose_lang'), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    lang = call.data.split('_')[1]
    USER_DATA.setdefault(chat_id, {'ai_mode': False, 'stats': 0})['lang'] = lang
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        f"{get_msg(chat_id, 'lang_selected')}\n\n{get_msg(chat_id, 'help_prompt')}", 
        chat_id, call.message.message_id
    )

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, get_msg(message.chat.id, 'help_text'), parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    count = USER_DATA.get(message.chat.id, {}).get('stats', 0)
    bot.send_message(message.chat.id, f"📊 Tổng số lệnh/tin nhắn đã xử lý: `{count}`", parse_mode='Markdown')

@bot.message_handler(commands=['chatwithAI', 'cancel'])
def cmd_ai_toggle(message):
    chat_id = message.chat.id
    is_on = message.text.startswith('/chatwithAI')
    USER_DATA.setdefault(chat_id, {'lang': 'en', 'stats': 0})['ai_mode'] = is_on
    bot.send_message(chat_id, get_msg(chat_id, 'ai_on' if is_on else 'ai_off'))

@bot.message_handler(commands=['ask'])
def cmd_ask(message):
    query = validate_args(message, 2, "/ask <câu hỏi>")
    if query:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, f"🤖 [AI]: Đã tiếp nhận câu hỏi: '{query}'")

@bot.message_handler(commands=['qr'])
def cmd_qr(message):
    text = validate_args(message, 2, "/qr <nội dung>")
    if text:
        img = qrcode.make(text)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        bot.send_photo(message.chat.id, bio, caption="✅ QR Code (In-Memory)")

@bot.message_handler(commands=['calc'])
def cmd_calc(message):
    expr = validate_args(message, 2, "/calc <phép tính>")
    if expr:
        try:
            if any(c not in "0123456789+-*/(). " for c in expr): 
                raise ValueError
            res = eval(expr, {"__builtins__": None}, {})
            bot.reply_to(message, f"🧮 `{expr} = {res}`", parse_mode='Markdown')
        except:
            bot.reply_to(message, "❌ Biểu thức toán học không hợp lệ.")

@bot.message_handler(commands=['base64'])
def cmd_base64(message):
    text = validate_args(message, 2, "/base64 <text>")
    if text:
        encoded = base64.b64encode(text.encode()).decode()
        bot.reply_to(message, f"🔒 Base64:\n`{encoded}`", parse_mode='Markdown')

@bot.message_handler(commands=['ping', 'id', 'password'])
def cmd_quick_utils(message):
    cmd = message.text.split()[0]
    chat_id = message.chat.id
    if cmd == '/ping':
        t1 = time.time()
        m = bot.send_message(chat_id, "⏳")
        bot.edit_message_text(f"🏓 Latency: `{round((time.time() - t1)*1000)}ms`", chat_id, m.message_id, parse_mode='Markdown')
    elif cmd == '/id':
        bot.send_message(chat_id, f"👤 User: `{message.from_user.id}` | Chat: `{chat_id}`", parse_mode='Markdown')
    elif cmd == '/password':
        pwd = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=16))
        bot.send_message(chat_id, f"🔑 Mật khẩu: `{pwd}`", parse_mode='Markdown')

@bot.message_handler(commands=['crypto', 'short', 'joke'])
def cmd_external_apis(message):
    cmd = message.text.split()[0]
    chat_id = message.chat.id
    try:
        if cmd == '/crypto':
            coin = validate_args(message, 2, "/crypto <coin> (VD: BTC)")
            if not coin: return
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin.upper()}USDT", timeout=3).json()
            bot.send_message(chat_id, f"📈 **{coin.upper()}**: `${float(res['price']):,.2f}`", parse_mode='Markdown')
        elif cmd == '/short':
            link = validate_args(message, 2, "/short <link>")
            if not link: return
            res = requests.get(f"https://is.gd/create.php?format=json&url={urllib.parse.quote(link)}", timeout=3).json()
            bot.send_message(chat_id, f"🔗 Link: {res['shorturl']}")
        elif cmd == '/joke':
            res = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=3).json()
            bot.send_message(chat_id, f"🗣 {res['setup']}\n\n... {res['punchline']}")
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, get_msg(chat_id, 'api_timeout'))
    except:
        bot.send_message(chat_id, "❌ Lỗi thực thi dữ liệu API.")

@bot.message_handler(commands=['dice', 'dart', 'basket', 'football', 'bowling', 'slot', 'coin'])
def cmd_games(message):
    cmd = message.text.split()[0]
    if cmd == '/coin':
        res = random.choice(['Sấp (Heads) 🦅', 'Ngửa (Tails) 🪙'])
        bot.send_message(message.chat.id, f"🪙 Kết quả: **{res}**", parse_mode='Markdown')
    elif cmd in GAME_EMOJIS_MAP:
        bot.send_dice(message.chat.id, emoji=GAME_EMOJIS_MAP[cmd])

@bot.message_handler(commands=['pin', 'ban'])
def cmd_admin_actions(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "⚠️ Chỉ dùng trong Group!")
    
    admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        return bot.reply_to(message, get_msg(message.chat.id, 'admin_only'))
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Vui lòng Reply tin nhắn cần thao tác!")
    
    try:
        cmd = message.text.split()[0]
        target_id = message.reply_to_message.from_user.id
        if cmd == '/pin':
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Ghim tin nhắn thành công!")
        elif cmd == '/ban':
            bot.ban_chat_member(message.chat.id, target_id)
            bot.reply_to(message, "🔨 Đã cấm người dùng khỏi nhóm.")
    except:
        bot.reply_to(message, "❌ Bot chưa được cấp quyền Admin đầy đủ.")

@bot.message_handler(func=lambda message: True)
def handler_fallback(message):
    if not message.text: return
    chat_id = message.chat.id
    USER_DATA.setdefault(chat_id, {'stats': 0})['stats'] += 1
    
    if USER_DATA.get(chat_id, {}).get('ai_mode', False):
        bot.send_chat_action(chat_id, 'typing')
        bot.reply_to(message, f"🤖 [AI Response]: {message.text}")
    elif message.chat.type == 'private':
        bot.send_message(chat_id, get_msg(chat_id, 'help_prompt'))

if __name__ == '__main__':
    print("🚀 16-Language Static Optimized Bot is running...")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
