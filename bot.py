import os
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
import google.generativeai as genai

# =========================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# =========================================================
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID')

if not TOKEN:
    raise ValueError("⚠️ Chưa cấu hình biến môi trường BOT_TOKEN!")

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=16)

# Cấu hình itznvl AI Core
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-2.0-flash')
else:
    ai_model = None

USER_DATA = {}
SUPPORTED_LANGUAGES = {
    "vi": "🇻🇳 Tiếng Việt", "en": "🇬🇧 English", "id": "🇮🇩 Indonesian", 
    "es": "🇪🇸 Español", "fr": "🇫🇷 Français", "de": "🇩🇪 Deutsch",
    "ru": "🇷🇺 Русский", "pt": "🇵🇹 Português", "it": "🇮🇹 Italiano",
    "zh": "🇨🇳 中文", "ja": "🇯🇵 日本語", "ko": "🇰🇷 한국어",
    "ar": "🇸🇦 العربية", "hi": "🇮🇳 हिन्दी", "th": "🇹🇭 ไทย", "tr": "🇹🇷 Türkçe"
}

LANG_DICT = {
    'vi': {
        'choose_lang': '🌐 Vui lòng chọn ngôn ngữ giao diện itznvl Bot:',
        'lang_selected': '✅ Đã chuyển sang Tiếng Việt.',
        'help_prompt': 'Gõ /help để xem danh sách lệnh.',
        'help_text': (
            "🚀 *ITZNVL BOT - SIÊU BOT TOÀN DIỆN (16 NGÔN NGỮ)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - Bật/tắt chat liên tục\n"
            "/ask <câu hỏi> - Hỏi nhanh itznvl AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <nội dung> - Tạo mã QR\n"
            "/calc <phép tính> - Máy tính\n"
            "/base64 <text> - Mã hóa Base64\n"
            "/password - Tạo mật khẩu mạnh\n"
            "/wiki <từ khóa> - Wikipedia\n"
            "/weather <tỉnh/huyện toàn cầu> - Thời tiết thế giới (cũ & mới)\n"
            "/ping - Độ trễ\n"
            "/id - Xem ID\n\n"
            "📈 *3. FINANCE & FUN*\n"
            "/crypto <coin> - Giá coin\n"
            "/short <link> - Rút gọn link\n"
            "/joke - Chuyện cười\n"
            "/fact - Kiến thức thú vị\n\n"
            "🎮 *4. GAMES & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Tung đồng xu\n"
            "/pin - Ghim tin nhắn\n"
            "/ban - Cấm thành viên\n"
            "/thongbao <nội dung> - Gửi thông báo toàn hệ thống (Admin)\n"
            "/stats - Thống kê"
        ),
        'syntax_err': '⚠️ Sai cú pháp. Dùng đúng định dạng: ',
        'ai_on': '💬 [AI: ON] - Đã kết nối itznvl AI.\n(Gõ /cancel để tắt)',
        'ai_off': '🔇 [AI: OFF] - Đã tắt chat AI.',
        'api_timeout': '⏳ Thời gian chờ API quá hạn!',
        'admin_only': '⚠️ Yêu cầu quyền Quản trị viên nhóm!',
        'no_ai_key': '⚠️ Chưa cấu hình khóa API itznvl AI!'
    },
    'en': {
        'choose_lang': '🌐 Please select itznvl Bot interface language:',
        'lang_selected': '✅ Language set to English.',
        'help_prompt': 'Type /help for command list.',
        'help_text': (
            "🚀 *ITZNVL BOT - ULTIMATE SUPER BOT (16 LANGUAGES)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - Toggle AI chat\n"
            "/ask <query> - Ask itznvl AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <text> - QR Code\n"
            "/calc <expr> - Calculator\n"
            "/base64 <text> - Base64\n"
            "/password - Strong password\n"
            "/wiki <keyword> - Wikipedia\n"
            "/weather <global province/district> - World Weather (Old & New)\n"
            "/ping - Latency\n"
            "/id - Get ID\n\n"
            "📈 *3. FINANCE & FUN*\n"
            "/crypto <coin> - Crypto price\n"
            "/short <link> - Shorten link\n"
            "/joke - Random joke\n"
            "/fact - Fun fact\n\n"
            "🎮 *4. GAMES & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Flip coin\n"
            "/pin - Pin message\n"
            "/ban - Ban member\n"
            "/thongbao <content> - Broadcast to all users (Admin)\n"
            "/stats - Stats"
        ),
        'syntax_err': '⚠️ Invalid syntax. Use: ',
        'ai_on': '💬 [AI: ON] - itznvl AI connected.\n(Type /cancel to off)',
        'ai_off': '🔇 [AI: OFF] - AI chat disabled.',
        'api_timeout': '⏳ API connection timeout!',
        'admin_only': '⚠️ Group Admin permissions required!',
        'no_ai_key': '⚠️ itznvl AI API key not configured!'
    },
    'id': {
        'choose_lang': '🌐 Silakan pilih bahasa antarmuka itznvl Bot:',
        'lang_selected': '✅ Bahasa diatur ke Bahasa Indonesia.',
        'help_prompt': 'Ketik /help untuk melihat perintah.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 BAHASA)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - Alihkan chat AI\n"
            "/ask <pertanyaan> - Tanya itznvl AI\n\n"
            "🛠 *2. UTILITAS*\n"
            "/qr <teks> - Buat QR\n"
            "/calc <ekspresi> - Kalkulator\n"
            "/base64 <teks> - Base64\n"
            "/password - Sandi kuat\n"
            "/wiki <kata kunci> - Wikipedia\n"
            "/weather <provinsi/kabupaten dunia> - Cuaca Global\n"
            "/ping - Latensi\n"
            "/id - Info ID\n\n"
            "📈 *3. KEUANGAN*\n"
            "/crypto <koin> - Harga koin\n"
            "/short <tautan> - Pemendek link\n"
            "/joke - Lelucon\n"
            "/fact - Fakta unik\n\n"
            "🎮 *4. GAME & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Lempar koin\n"
            "/pin - Sematkan pesan\n"
            "/ban - Banned anggota\n"
            "/thongbao <pesan> - Siaran massal (Admin)\n"
            "/stats - Statistik"
        ),
        'syntax_err': '⚠️ Sintaks tidak valid. Gunakan: ',
        'ai_on': '💬 [AI: AKTIF] - Terhubung ke itznvl AI.\n(Ketik /cancel untuk mematikan)',
        'ai_off': '🔇 [AI: NONAKTIF] - Obrolan AI dimatikan.',
        'api_timeout': '⏳ Batas waktu API habis!',
        'admin_only': '⚠️ Memerlukan izin Admin grup!',
        'no_ai_key': '⚠️ Kunci API itznvl AI belum dikonfigurasi!'
    },
    'es': {
        'choose_lang': '🌐 Seleccione el idioma de la interfaz de itznvl Bot:',
        'lang_selected': '✅ Idioma cambiado a Español.',
        'help_prompt': 'Escribe /help para ver comandos.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 IDIOMAS)*\n\n"
            "🤖 *1. IA*\n"
            "/chatwithAI - Alternar chat IA\n"
            "/ask <consulta> - Preguntar a itznvl AI\n\n"
            "🛠 *2. UTILIDADES*\n"
            "/qr <texto> - Código QR\n"
            "/calc <expresión> - Calculadora\n"
            "/base64 <texto> - Base64\n"
            "/password - Contraseña segura\n"
            "/wiki <palabra> - Wikipedia\n"
            "/weather <provincia/distrito mundial> - Clima Global\n"
            "/ping - Latencia\n"
            "/id - Ver ID\n\n"
            "📈 *3. FINANZAS*\n"
            "/crypto <moneda> - Precio cripto\n"
            "/short <enlace> - Acortar enlace\n"
            "/joke - Chiste\n"
            "/fact - Dato curioso\n\n"
            "🎮 *4. JUEGOS Y ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Lanzar moneda\n"
            "/pin - Fijar mensaje\n"
            "/ban - Banear miembro\n"
            "/thongbao <mensaje> - Transmisión (Admin)\n"
            "/stats - Estadísticas"
        ),
        'syntax_err': '⚠️ Sintaxis incorrecta. Use: ',
        'ai_on': '💬 [IA: ACTIVO] - itznvl AI conectado.\n(Escribe /cancel para desactivar)',
        'ai_off': '🔇 [IA: INACTIVO] - Chat de IA desactivado.',
        'api_timeout': '⏳ ¡Tiempo de espera de API agotado!',
        'admin_only': '⚠️ ¡Se requieren permisos de administrador!',
        'no_ai_key': '⚠️ ¡Clave API de itznvl AI no configurada!'
    },
    'fr': {
        'choose_lang': '🌐 Veuillez sélectionner la langue d itznvl Bot :',
        'lang_selected': '✅ Langue définie sur Français.',
        'help_prompt': 'Tapez /help pour les commandes.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 LANGUES)*\n\n"
            "🤖 *1. IA*\n"
            "/chatwithAI - Basculer le chat IA\n"
            "/ask <question> - Demander à itznvl AI\n\n"
            "🛠 *2. UTILITAIRES*\n"
            "/qr <texte> - Code QR\n"
            "/calc <expression> - Calculatrice\n"
            "/base64 <texte> - Base64\n"
            "/password - Mot de passe fort\n"
            "/wiki <mot-clé> - Wikipedia\n"
            "/weather <province/district mondial> - Météo Mondiale\n"
            "/ping - Latence\n"
            "/id - ID utilisateur\n\n"
            "📈 *3. FINANCE*\n"
            "/crypto <monnaie> - Prix crypto\n"
            "/short <lien> - Raccourcir lien\n"
            "/joke - Blague\n"
            "/fact - Fait divers\n\n"
            "🎮 *4. JEUX & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Pile ou face\n"
            "/pin - Épingler message\n"
            "/ban - Bannir membre\n"
            "/thongbao <message> - Diffusion (Admin)\n"
            "/stats - Statistiques"
        ),
        'syntax_err': '⚠️ Syntaxe incorrecte. Utilisez : ',
        'ai_on': '💬 [IA : ACTIVÉE] - itznvl AI connecté.\n(Tapez /cancel pour désactiver)',
        'ai_off': '🔇 [IA : DÉSACTIVÉE] - Chat IA désactivé.',
        'api_timeout': '⏳ Délai d’attente API dépassé !',
        'admin_only': '⚠️ Permissions d’administrateur requises !',
        'no_ai_key': '⚠️ Clé API itznvl AI non configurée !'
    },
    'de': {
        'choose_lang': '🌐 Bitte wählen Sie die Sprache für itznvl Bot:',
        'lang_selected': '✅ Sprache auf Deutsch eingestellt.',
        'help_prompt': 'Geben Sie /help für Befehle ein.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 SPRACHEN)*\n\n"
            "🤖 *1. KI*\n"
            "/chatwithAI - KI-Chat umschalten\n"
            "/ask <frage> - itznvl AI fragen\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <text> - QR-Code\n"
            "/calc <formel> - Rechner\n"
            "/base64 <text> - Base64\n"
            "/password - Sicheres Passwort\n"
            "/wiki <begriff> - Wikipedia\n"
            "/weather <weltweite provinz/stadt> - Weltweites Wetter\n"
            "/ping - Latenz\n"
            "/id - ID anzeigen\n\n"
            "📈 *3. FINANZEN*\n"
            "/crypto <coin> - Krypto-Preis\n"
            "/short <link> - Link kürzen\n"
            "/joke - Witz\n"
            "/fact - Fakten\n\n"
            "🎮 *4. SPIELE & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Münzwurf\n"
            "/pin - Nachricht anheften\n"
            "/ban - Mitglied sperren\n"
            "/thongbao <nachricht> - Rundschreiben (Admin)\n"
            "/stats - Statistiken"
        ),
        'syntax_err': '⚠️ Ungültige Syntax. Verwendung: ',
        'ai_on': '💬 [KI: AN] - itznvl AI verbunden.\n(/cancel zum Ausschalten)',
        'ai_off': '🔇 [KI: AUS] - KI-Chat deaktiviert.',
        'api_timeout': '⏳ API-Zeitüberschreitung!',
        'admin_only': '⚠️ Admin-Rechte erforderlich!',
        'no_ai_key': '⚠️ itznvl AI API-Schlüssel nicht konfiguriert!'
    },
    'ru': {
        'choose_lang': '🌐 Выберите язык интерфейса itznvl Bot:',
        'lang_selected': '✅ Язык изменен на русский.',
        'help_prompt': 'Введите /help для списка команд.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 ЯЗЫКОВ)*\n\n"
            "🤖 *1. ИИ*\n"
            "/chatwithAI - Включить/выключить ИИ\n"
            "/ask <запрос> - Спросить itznvl AI\n\n"
            "🛠 *2. УТИЛИТЫ*\n"
            "/qr <текст> - QR код\n"
            "/calc <пример> - Калькулятор\n"
            "/base64 <текст> - Base64\n"
            "/password - Пароль\n"
            "/wiki <тема> - Википедия\n"
            "/weather <провинция/район мира> - Мировая погода\n"
            "/ping - Пинг\n"
            "/id - ID чата\n\n"
            "📈 *3. ФИНАНСЫ*\n"
            "/crypto <монета> - Курс крипты\n"
            "/short <ссылка> - Сократить ссылку\n"
            "/joke - Шутка\n"
            "/fact - Факт\n\n"
            "🎮 *4. ИГРЫ И АДМИН*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Монетка\n"
            "/pin - Закрепить\n"
            "/ban - Забанить\n"
            "/thongbao <текст> - Рассылка (Админ)\n"
            "/stats - Статистика"
        ),
        'syntax_err': '⚠️ Неверный синтаксис. Используйте: ',
        'ai_on': '💬 [ИИ: ВКЛ] - itznvl AI подключен.\n(Введите /cancel для выключения)',
        'ai_off': '🔇 [ИИ: ВЫКЛ] - Чат отключен.',
        'api_timeout': '⏳ Время ожидания API истекло!',
        'admin_only': '⚠️ Требуются права администратора!',
        'no_ai_key': '⚠️ Ключ API itznvl AI не настроен!'
    },
    'pt': {
        'choose_lang': '🌐 Selecione o idioma do itznvl Bot:',
        'lang_selected': '✅ Idioma definido para Português.',
        'help_prompt': 'Digite /help para comandos.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 IDIOMAS)*\n\n"
            "🤖 *1. IA*\n"
            "/chatwithAI - Alternar chat IA\n"
            "/ask <pergunta> - Perguntar à itznvl AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <texto> - Código QR\n"
            "/calc <conta> - Calculadora\n"
            "/base64 <texto> - Base64\n"
            "/password - Senha forte\n"
            "/wiki <termo> - Wikipedia\n"
            "/weather <província/distrito mundial> - Clima Global\n"
            "/ping - Latência\n"
            "/id - Ver ID\n\n"
            "📈 *3. FINANÇAS*\n"
            "/crypto <moeda> - Preço crypto\n"
            "/short <link> - Encurtar link\n"
            "/joke - Piada\n"
            "/fact - Curiosidade\n\n"
            "🎮 *4. JOGOS & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Cara ou coroa\n"
            "/pin - Fixar mensagem\n"
            "/ban - Banir membro\n"
            "/thongbao <mensagem> - Transmissão (Admin)\n"
            "/stats - Estatísticas"
        ),
        'syntax_err': '⚠️ Sintaxe inválida. Use: ',
        'ai_on': '💬 [IA: LIGADA] - itznvl AI conectado.\n(Digite /cancel para desligar)',
        'ai_off': '🔇 [IA: DESLIGADA] - Chat IA desativado.',
        'api_timeout': '⏳ Tempo limite da API esgotado!',
        'admin_only': '⚠️ Permissões de Administrador necessárias!',
        'no_ai_key': '⚠️ Chave API itznvl AI não configurada!'
    },
    'it': {
        'choose_lang': '🌐 Seleziona la lingua di itznvl Bot:',
        'lang_selected': '✅ Lingua impostata su Italiano.',
        'help_prompt': 'Digita /help per i comandi.',
        'help_text': (
            "🚀 *ITZNVL BOT - SUPER BOT (16 LINGUE)*\n\n"
            "🤖 *1. IA*\n"
            "/chatwithAI - Attiva/disattiva chat IA\n"
            "/ask <domanda> - Chiedi a itznvl AI\n\n"
            "🛠 *2. UTILS*\n"
            "/qr <testo> - Codice QR\n"
            "/calc <formula> - Calcolatrice\n"
            "/base64 <testo> - Base64\n"
            "/password - Password sicura\n"
            "/wiki <termine> - Wikipedia\n"
            "/weather <provincia/distrito mondiale> - Meteo Globale\n"
            "/ping - Latenza\n"
            "/id - ID utente\n\n"
            "📈 *3. FINANZA*\n"
            "/crypto <moneta> - Prezzo crypto\n"
            "/short <link> - Accorcia link\n"
            "/joke - Barzelletta\n"
            "/fact - Curiosità\n\n"
            "🎮 *4. GIOCHI & ADMIN*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Testata o croce\n"
            "/pin - Fissa messaggio\n"
            "/ban - Bannare membro\n"
            "/thongbao <messaggio> - Broadcast (Admin)\n"
            "/stats - Statistiche"
        ),
        'syntax_err': '⚠️ Sintassi non valida. Usa: ',
        'ai_on': '💬 [IA: ATTIVA] - itznvl AI connesso.\n(Digita /cancel per spegnere)',
        'ai_off': '🔇 [IA: DISATTIVA] - Chat IA disattivata.',
        'api_timeout': '⏳ Timeout della richiesta API!',
        'admin_only': '⚠️ Richiesti permessi di Amministratore!',
        'no_ai_key': '⚠️ Chiave API itznvl AI non configurata!'
    },
    'zh': {
        'choose_lang': '🌐 请选择 itznvl Bot 语言：',
        'lang_selected': '✅ 语言已设置为中文。',
        'help_prompt': '输入 /help 查看命令。',
        'help_text': (
            "🚀 *ITZNVL BOT - 超级机器人 (16 语言)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - 切换持续AI聊天\n"
            "/ask <问题> - 问 itznvl AI\n\n"
            "🛠 *2. 工具*\n"
            "/qr <内容> - 二维码\n"
            "/calc <算式> - 计算器\n"
            "/base64 <文本> - Base64\n"
            "/password - 强密码\n"
            "/wiki <关键词> - 维基百科\n"
            "/weather <全球省份/区县> - 全球天气（含旧/新名称）\n"
            "/ping - 延迟\n"
            "/id - 查看ID\n\n"
            "📈 *3. 金融娱乐*\n"
            "/crypto <币种> - 加密货币价格\n"
            "/short <链接> - 短链接\n"
            "/joke - 笑话\n"
            "/fact - 有趣的事实\n\n"
            "🎮 *4. 游戏与管理*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - 掷硬币\n"
            "/pin - 置顶消息\n"
            "/ban - 封禁成员\n"
            "/thongbao <内容> - 全局广播 (Admin)\n"
            "/stats - 统计"
        ),
        'syntax_err': '⚠️ 语法错误。请使用：',
        'ai_on': '💬 [AI：开启] - 已连接 itznvl AI。\n（输入 /cancel 关闭）',
        'ai_off': '🔇 [AI：关闭] - AI聊天已关闭。',
        'api_timeout': '⏳ API请求超时！',
        'admin_only': '⚠️ 需要群组管理员权限！',
        'no_ai_key': '⚠️ 未配置 itznvl AI API密钥！'
    },
    'ja': {
        'choose_lang': '🌐 itznvl Botの言語を選択してください：',
        'lang_selected': '✅ 言語が日本語に設定されました。',
        'help_prompt': '/help でコマンドを表示。',
        'help_text': (
            "🚀 *ITZNVL BOT - スーパーボット (16言語)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - AIチャット切替\n"
            "/ask <質問> - itznvl AIに質問\n\n"
            "🛠 *2. ツール*\n"
            "/qr <テキスト> - QRコード\n"
            "/calc <計算式> - 電卓\n"
            "/base64 <テキスト> - Base64\n"
            "/password - パスワード生成\n"
            "/wiki <キーワード> - Wikipedia\n"
            "/weather <世界中の省/地区> - 世界の天気（旧・新対応）\n"
            "/ping - 遅延確認\n"
            "/id - ID取得\n\n"
            "📈 *3. 金融・エンタメ*\n"
            "/crypto <コイン> - 暗号資産価格\n"
            "/short <リンク> - 短縮リンク\n"
            "/joke - ジョーク\n"
            "/fact - 豆知識\n\n"
            "🎮 *4. ゲーム & 管理*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - コイン投げ\n"
            "/pin - ピン留め\n"
            "/ban - メンバー追放\n"
            "/thongbao <メッセージ> - 一斉送信 (Admin)\n"
            "/stats - 統計"
        ),
        'syntax_err': '⚠️ 構文エラーです。以下を使用してください：',
        'ai_on': '💬 [AI：オン] - itznvl AI接続完了。\n（/cancel でオフ）',
        'ai_off': '🔇 [AI：オフ] - AIチャット停止。',
        'api_timeout': '⏳ API接続がタイムアウトしました！',
        'admin_only': '⚠️ グループ管理者権限が必要です！',
        'no_ai_key': '⚠️ itznvl AI APIキーが設定されていません！'
    },
    'ko': {
        'choose_lang': '🌐 itznvl Bot 언어를 선택하세요:',
        'lang_selected': '✅ 언어가 한국어로 설정되었습니다.',
        'help_prompt': '/help를 입력해 명령어를 확인하세요.',
        'help_text': (
            "🚀 *ITZNVL BOT - 슈퍼봇 (16개 언어)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - AI 채팅 전환\n"
            "/ask <질문> - itznvl AI에게 질문\n\n"
            "🛠 *2. 유틸리티*\n"
            "/qr <내용> - QR 코드 생성\n"
            "/calc <수식> - 계산기\n"
            "/base64 <텍스트> - Base64\n"
            "/password - 안전한 비밀번호\n"
            "/wiki <검색어> - 위키백과\n"
            "/weather <전 세계 도/구역> - 세계 날씨 (구/신 명칭 모두 지원)\n"
            "/ping - 지연 시간\n"
            "/id - ID 확인\n\n"
            "📈 *3. 금융 및 재미*\n"
            "/crypto <코인> - 코인 시세\n"
            "/short <링크> - 링크 단축\n"
            "/joke - 유머\n"
            "/fact - 상식\n\n"
            "🎮 *4. 게임 및 관리자*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - 동전 던지기\n"
            "/pin - 메시지 고정\n"
            "/ban - 멤버 차단\n"
            "/thongbao <메시지> - 전체 공지 (Admin)\n"
            "/stats - 통계"
        ),
        'syntax_err': '⚠️ 구문 오류입니다. 다음을 사용하세요: ',
        'ai_on': '💬 [AI: 켜짐] - itznvl AI 연결됨.\n(/cancel 입력하여 끄기)',
        'ai_off': '🔇 [AI: 꺼짐] - AI 채팅 꺼짐.',
        'api_timeout': '⏳ API 요청 시간이 초과되었습니다!',
        'admin_only': '⚠️ 그룹 관리자 권한이 필요합니다!',
        'no_ai_key': '⚠️ itznvl AI API 키가 설정되지 않았습니다!'
    },
    'ar': {
        'choose_lang': '🌐 الرجاء اختيار لغة واجهة itznvl Bot:',
        'lang_selected': '✅ تم ضبط اللغة على العربية.',
        'help_prompt': 'اكتب /help لعرض الأوامر.',
        'help_text': (
            "🚀 *ITZNVL BOT - الروبوت الخارق (16 لغة)*\n\n"
            "🤖 *1. الذكاء الاصطناعي*\n"
            "/chatwithAI - تبديل وضع الدردشة\n"
            "/ask <سؤال> - اسأل itznvl AI\n\n"
            "🛠 *2. الأدوات*\n"
            "/qr <نص> - رمز الاستجابة السريعة\n"
            "/calc <عملية> - الآلة الحاسبة\n"
            "/base64 <نص> - Base64\n"
            "/password - كلمة مرور قوية\n"
            "/wiki <كلمة> - ويكيبيديا\n"
            "/weather <أي مقاطعة أو منطقة عالمية> - الطقس العالمي (القديم والجديد)\n"
            "/ping - اختبار السرعة\n"
            "/id - المعرف الشخصي\n\n"
            "📈 *3. المالية والترفيه*\n"
            "/crypto <عملة> - أسعار العملات\n"
            "/short <رابط> - تقصير الرابط\n"
            "/joke - نكتة\n"
            "/fact - معلومة مفيدة\n\n"
            "🎮 *4. الألعاب والمشرف*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - رمي العملة\n"
            "/pin - تثبيت رسالة\n"
            "/ban - حظر عضو\n"
            "/thongbao <الرسالة> - إرسال إشعار للجميع (Admin)\n"
            "/stats - الإحصائيات"
        ),
        'syntax_err': '⚠️ صيغة غير صحيحة. استخدم: ',
        'ai_on': '💬 [الذكاء الاصطناعي: مفعل] - تم اتصال itznvl AI.\n(اكتب /cancel للإيقاف)',
        'ai_off': '🔇 [الذكاء الاصطناعي: متوقف] - تم إيقاف الدردشة.',
        'api_timeout': '⏳ انتهت مهلة طلب API!',
        'admin_only': '⚠️ مطلوب صلاحيات المشرف!',
        'no_ai_key': '⚠️ مفتاح API لـ itznvl AI غير مهيأ!'
    },
    'hi': {
        'choose_lang': '🌐 कृपया itznvl Bot की भाषा चुनें:',
        'lang_selected': '✅ भाषा हिंदी पर सेट की गई।',
        'help_prompt': 'कमांड के लिए /help टाइप करें।',
        'help_text': (
            "🚀 *ITZNVL BOT - सुपर बॉट (16 भाषाएँ)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - AI चैट टॉगल करें\n"
            "/ask <सवाल> - itznvl AI سے پوچھें\n\n"
            "🛠 *2. यूटिलिटी*\n"
            "/qr <टेक्स्ट> - QR कोड\n"
            "/calc <गणित> - कैलकुलेटर\n"
            "/base64 <टेक्स्ट> - Base64\n"
            "/password - पासवर्ड\n"
            "/wiki <कीवर्ड> - विकिपيديا\n"
            "/weather <वैश्विक प्रांत/जिला> - विश्व मौसम (पुराना और नया)\n"
            "/ping - पिंग\n"
            "/id - ID देखें\n\n"
            "📈 *3. फाइनेंस*\n"
            "/crypto <कॉइन> - क्रिप्टो मूल्य\n"
            "/short <लिंक> - लिंक छोटा करें\n"
            "/joke - चुटकुला\n"
            "/fact - तथ्य\n\n"
            "🎮 *4. गेम और एडमिन*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - सिक्का उछालें\n"
            "/pin - पिन मैसेज\n"
            "/ban - बैन मेंबर\n"
            "/thongbao <संदेश> - सभी को सूचना दें (Admin)\n"
            "/stats - आंकड़े"
        ),
        'syntax_err': '⚠️ अमान्य सिंटैक्स। उपयोग करें: ',
        'ai_on': '💬 [AI: चालू] - itznvl AI कनेक्टेड।\n(बंद करने के लिए /cancel टाइप करें)',
        'ai_off': '🔇 [AI: बंद] - AI चैट बंद है।',
        'api_timeout': '⏳ API अनुरोध का समय समाप्त!',
        'admin_only': '⚠️ समूह व्यवस्थापक अनुमति आवश्यक!',
        'no_ai_key': '⚠️ itznvl AI एपीआई कुंजी कॉन्फ़िगर नहीं है!'
    },
    'th': {
        'choose_lang': '🌐 กรุณาเลือกภาษา itznvl Bot:',
        'lang_selected': '✅ ตั้งค่าภาษาเป็นภาษาไทยแล้ว',
        'help_prompt': 'พิมพ์ /help เพื่อดูคำสั่ง',
        'help_text': (
            "🚀 *ITZNVL BOT - ซูเปอร์บอท (16 ภาษา)*\n\n"
            "🤖 *1. AI*\n"
            "/chatwithAI - สลับแชท AI\n"
            "/ask <คำถาม> - ถาม itznvl AI\n\n"
            "🛠 *2. เครื่องมือ*\n"
            "/qr <ข้อความ> - QR โค้ด\n"
            "/calc <สมการ> - เครื่องคิดเลข\n"
            "/base64 <ข้อความ> - Base64\n"
            "/password - รหัสผ่าน\n"
            "/wiki <คำค้น> - Wikipedia\n"
            "/weather <จังหวัด/อำเภอทั่วโลก> - สภาพอากาศโลก (ทั้งชื่อเก่าและใหม่)\n"
            "/ping - ความหน่วง\n"
            "/id - ดู ID\n\n"
            "📈 *3. การเงิน*\n"
            "/crypto <เหรียญ> - ราคาเหรียญ\n"
            "/short <ลิงก์> - ย่อลิงก์\n"
            "/joke - มุกตลก\n"
            "/fact - เกร็ดความรู้\n\n"
            "🎮 *4. เกมและผู้ดูแล*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - ทอยเหรียญ\n"
            "/pin - ปักหมุด\n"
            "/ban - แบนสมาชิก\n"
            "/thongbao <ข้อความ> - ส่งประกาศถึงผู้ใช้ทุกคน (Admin)\n"
            "/stats - สถิติ"
        ),
        'syntax_err': '⚠️ รูปแบบไม่ถูกต้อง ใช้: ',
        'ai_on': '💬 [AI: เปิด] - เชื่อมต่อ itznvl AI แล้ว\n(พิมพ์ /cancel เพื่อปิด)',
        'ai_off': '🔇 [AI: ปิด] - ปิดแชท AI แล้ว',
        'api_timeout': '⏳ หมดเวลาการเชื่อมต่อ API!',
        'admin_only': '⚠️ ต้องการสิทธิ์ผู้ดูแลระบบ!',
        'no_ai_key': '⚠️ ยังไม่ได้กำหนดค่าคีย์ itznvl AI!'
    },
    'tr': {
        'choose_lang': '🌐 itznvl Bot dilini seçin:',
        'lang_selected': '✅ Dil Türkçe olarak ayarlandı.',
        'help_prompt': 'Komutlar için /help yazın.',
        'help_text': (
            "🚀 *ITZNVL BOT - SÜPER BOT (16 DİL)*\n\n"
            "🤖 *1. YAPAY ZEKA*\n"
            "/chatwithAI - AI sohbetini aç/kapat\n"
            "/ask <soru> - itznvl AI'ye sor\n\n"
            "🛠 *2. ARAÇLAR*\n"
            "/qr <metin> - QR kod\n"
            "/calc <işlem> - Hesap makinesi\n"
            "/base64 <metin> - Base64\n"
            "/password - Güçlü şifre\n"
            "/wiki <kelime> - Wikipedia\n"
            "/weather <dünya çapında il/ilçe> - Dünya Hava Durumu (Eski ve Yeni)\n"
            "/ping - Gecikme\n"
            "/id - ID göster\n\n"
            "📈 *3. FİNANS*\n"
            "/crypto <coin> - Kripto fiyatı\n"
            "/short <link> - Link kısalt\n"
            "/joke - Fıkra\n"
            "/fact - İlginç bilgi\n\n"
            "🎮 *4. OYUNLAR & YÖNETİCİ*\n"
            "/dice, /dart, /basket, /football, /bowling, /slot\n"
            "/coin - Yazı tura\n"
            "/pin - Mesaj sabitle\n"
            "/ban - Üye engelle\n"
            "/thongbao <mesaj> - Toplu duyuru (Admin)\n"
            "/stats - İstatistikler"
        ),
        'syntax_err': '⚠️ Geçersiz sözdizimi. Şunu kullanın: ',
        'ai_on': '💬 [AI: AÇIK] - itznvl AI bağlandı.\n(Kapatmak için /cancel yazın)',
        'ai_off': '🔇 [AI: KAPALI] - AI sohbeti kapalı.',
        'api_timeout': '⏳ API zaman aşımına uğradı!',
        'admin_only': '⚠️ Grup Yöneticisi izni gerekiyor!',
        'no_ai_key': '⚠️ itznvl AI API anahtarı yapılandırılmadı!'
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

# =========================================================
# SYSTEM COMMANDS
# =========================================================
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
    bot.edit_message_text(f"{get_msg(chat_id, 'lang_selected')}\n\n{get_msg(chat_id, 'help_prompt')}", chat_id, call.message.message_id)

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, get_msg(message.chat.id, 'help_text'), parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    count = USER_DATA.get(message.chat.id, {}).get('stats', 0)
    bot.send_message(message.chat.id, f"📊 Tổng số tương tác / Stats: `{count}`", parse_mode='Markdown')

# =========================================================
# ITZNVL AI MODULE
# =========================================================
@bot.message_handler(commands=['chatwithAI', 'cancel'])
def cmd_ai_toggle(message):
    chat_id = message.chat.id
    is_on = message.text.startswith('/chatwithAI')
    USER_DATA.setdefault(chat_id, {'lang': 'en', 'stats': 0})['ai_mode'] = is_on
    bot.send_message(chat_id, get_msg(chat_id, 'ai_on' if is_on else 'ai_off'))

@bot.message_handler(commands=['ask'])
def cmd_ask(message):
    query = validate_args(message, 2, "/ask <query>")
    if query:
        bot.send_chat_action(message.chat.id, 'typing')
        if not ai_model:
            return bot.reply_to(message, get_msg(message.chat.id, 'no_ai_key'))
        try:
            response = ai_model.generate_content(query)
            bot.reply_to(message, f"🤖 [itznvl AI]:\n{response.text}")
        except Exception as e:
            bot.reply_to(message, f"❌ AI Error: {str(e)}")

# =========================================================
# UTILITIES MODULE
# =========================================================
@bot.message_handler(commands=['qr'])
def cmd_qr(message):
    text = validate_args(message, 2, "/qr <text>")
    if text:
        img = qrcode.make(text)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        bot.send_photo(message.chat.id, bio, caption="✅ QR Code Generated")

@bot.message_handler(commands=['calc'])
def cmd_calc(message):
    expr = validate_args(message, 2, "/calc <expression>")
    if expr:
        try:
            if any(c not in "0123456789+-*/(). " for c in expr): raise ValueError
            res = eval(expr, {"__builtins__": None}, {})
            bot.reply_to(message, f"🧮 `{expr} = {res}`", parse_mode='Markdown')
        except:
            bot.reply_to(message, "❌ Invalid expression.")

@bot.message_handler(commands=['base64'])
def cmd_base64(message):
    text = validate_args(message, 2, "/base64 <text>")
    if text:
        encoded = base64.b64encode(text.encode()).decode()
        bot.reply_to(message, f"🔒 Base64:\n`{encoded}`", parse_mode='Markdown')

@bot.message_handler(commands=['wiki'])
def cmd_wiki(message):
    keyword = validate_args(message, 2, "/wiki <keyword>")
    if keyword:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(keyword)}"
            res = requests.get(url, timeout=3).json()
            if 'extract' in res:
                bot.reply_to(message, f"📚 **{res.get('title')}**\n\n{res.get('extract')}", parse_mode='Markdown')
            else:
                bot.reply_to(message, "❌ Not found.")
        except:
            bot.reply_to(message, "❌ Wikipedia error.")

@bot.message_handler(commands=['weather'])
def cmd_weather(message):
    location = validate_args(message, 2, "/weather <tỉnh/huyện toàn cầu>")
    if location:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            geo_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(location)}&format=json&limit=1&accept-language=vi"
            headers = {'User-Agent': 'itznvl-bot/2.0'}
            geo_res = requests.get(geo_url, headers=headers, timeout=5).json()
            
            query_target = location
            if geo_res:
                query_target = geo_res[0].get('display_name', location)
            
            weather_url = f"https://wttr.in/{urllib.parse.quote(query_target)}?format=3&lang=vi"
            res = requests.get(weather_url, headers=headers, timeout=5)
            
            if res.status_code == 200 and "Unknown location" not in res.text:
                bot.reply_to(message, f"🌤 Thời tiết khu vực (`{location}`):\n`{res.text.strip()}`", parse_mode='Markdown')
            else:
                res_fallback = requests.get(f"https://wttr.in/{urllib.parse.quote(location)}?format=3", headers=headers, timeout=5)
                if res_fallback.status_code == 200 and "Unknown location" not in res_fallback.text:
                    bot.reply_to(message, f"🌤 Thời tiết (`{location}`):\n`{res_fallback.text.strip()}`", parse_mode='Markdown')
                else:
                    bot.reply_to(message, "❌ Không tìm thấy tỉnh, huyện hoặc địa danh này trên thế giới (cả cũ và mới).")
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi dịch vụ thời tiết toàn cầu: {str(e)}")

@bot.message_handler(commands=['ping', 'id', 'password'])
def cmd_quick_utils(message):
    cmd = message.text.split()[0]
    chat_id = message.chat.id
    if cmd == '/ping':
        t1 = time.time()
        m = bot.send_message(chat_id, "⏳")
        bot.edit_message_text(f"🏓 Latency: `{round((time.time() - t1)*1000)}ms`", chat_id, m.message_id, parse_mode='Markdown')
    elif cmd == '/id':
        bot.send_message(chat_id, f"👤 User ID: `{message.from_user.id}`\n💬 Chat ID: `{chat_id}`", parse_mode='Markdown')
    elif cmd == '/password':
        pwd = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=16))
        bot.send_message(chat_id, f"🔑 Password:\n`{pwd}`", parse_mode='Markdown')

# =========================================================
# FINANCE & FUN API MODULE
# =========================================================
@bot.message_handler(commands=['crypto', 'short', 'joke', 'fact'])
def cmd_external_apis(message):
    cmd = message.text.split()[0]
    chat_id = message.chat.id
    try:
        if cmd == '/crypto':
            coin = validate_args(message, 2, "/crypto <coin>")
            if not coin: return
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin.upper()}USDT", timeout=3).json()
            bot.send_message(chat_id, f"📈 **{coin.upper()} / USDT**: `${float(res['price']):,.2f}`", parse_mode='Markdown')
        elif cmd == '/short':
            link = validate_args(message, 2, "/short <link>")
            if not link: return
            res = requests.get(f"https://is.gd/create.php?format=json&url={urllib.parse.quote(link)}", timeout=3).json()
            bot.send_message(chat_id, f"🔗 Short URL:\n{res['shorturl']}")
        elif cmd == '/joke':
            res = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=3).json()
            bot.send_message(chat_id, f"🗣 {res['setup']}\n\n... *{res['punchline']}*", parse_mode='Markdown')
        elif cmd == '/fact':
            res = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=3).json()
            bot.send_message(chat_id, f"💡 **Fun Fact:**\n{res['text']}", parse_mode='Markdown')
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, get_msg(chat_id, 'api_timeout'))
    except:
        bot.send_message(chat_id, "❌ External API error.")

# =========================================================
# GAMES & ADMIN MODULE
# =========================================================
@bot.message_handler(commands=['dice', 'dart', 'basket', 'football', 'bowling', 'slot', 'coin'])
def cmd_games(message):
    cmd = message.text.split()[0]
    if cmd == '/coin':
        res = random.choice(['Heads 🦅', 'Tails 🪙'])
        bot.send_message(message.chat.id, f"🪙 Coin flip: **{res}**", parse_mode='Markdown')
    elif cmd in GAME_EMOJIS_MAP:
        bot.send_dice(message.chat.id, emoji=GAME_EMOJIS_MAP[cmd])

@bot.message_handler(commands=['pin', 'ban'])
def cmd_admin_actions(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "⚠️ Group only!")
    admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        return bot.reply_to(message, get_msg(message.chat.id, 'admin_only'))
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply to a message!")
    try:
        cmd = message.text.split()[0]
        target_id = message.reply_to_message.from_user.id
        if cmd == '/pin':
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Pinned successfully!")
        elif cmd == '/ban':
            bot.ban_chat_member(message.chat.id, target_id)
            bot.reply_to(message, "🔨 User banned.")
    except:
        bot.reply_to(message, "❌ Admin rights missing.")

@bot.message_handler(commands=['thongbao'])
def cmd_thongbao(message):
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return bot.reply_to(message, "⚠️ Bạn không có quyền sử dụng lệnh này!")
    
    text = validate_args(message, 2, "/thongbao <nội dung thông báo>")
    if not text:
        return
    
    success_count = 0
    fail_count = 0
    
    for chat_id in list(USER_DATA.keys()):
        try:
            bot.send_message(chat_id, f"📢 **THÔNG BÁO TỪ ADMIN:**\n\n{text}", parse_mode='Markdown')
            success_count += 1
        except Exception:
            fail_count += 1
            
    bot.reply_to(message, f"✅ Đã gửi thông báo thành công tới `{success_count}` chats.\n❌ Thất bại: `{fail_count}` chats.", parse_mode='Markdown')

# =========================================================
# FALLBACK & AI CHAT HANDLER
# =========================================================
@bot.message_handler(func=lambda message: True)
def handler_fallback(message):
    if not message.text: return
    chat_id = message.chat.id
    USER_DATA.setdefault(chat_id, {'stats': 0})['stats'] += 1
    
    if USER_DATA.get(chat_id, {}).get('ai_mode', False):
        bot.send_chat_action(chat_id, 'typing')
        if not ai_model:
            return bot.reply_to(message, get_msg(chat_id, 'no_ai_key'))
        try:
            response = ai_model.generate_content(message.text)
            bot.reply_to(message, response.text)
        except Exception as e:
            bot.reply_to(message, f"❌ AI Error: {str(e)}")
    elif message.chat.type == 'private':
        bot.send_message(chat_id, get_msg(chat_id, 'help_prompt'))

if __name__ == '__main__':
    print("🚀 itznvl Bot with Broadcast & Global Weather Engine is running...")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
