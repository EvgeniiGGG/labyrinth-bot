import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = '8426468943:AAEZnrVo1BsHAW-OfFvC7wcsT0bDYXFXwJE'  # Ваш токен
CREDS_FILE = 'bot_credentials.json'
SHEET_NAME = 'Лабиринт Без Стен - Сценарий'
# =====================

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка доступа к Google API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ТАБЛИЦЕЙ ===

def find_row_by_message_id(message_id):
    # Получаем все значения из столбца A (ID)
    all_ids = sheet.col_values(1)
    # Ищем номер строки, где находится наш ID
    try:
        row_number = all_ids.index(message_id) + 1
        return row_number
    except ValueError:
        return None

def get_message_data(message_id):
    row_num = find_row_by_message_id(message_id)
    if not row_num:
        return None

    # Получаем всю строку данных
    row_data = sheet.row_values(row_num)

    # Добавляем пустые строки, чтобы избежать ошибок индекса
    while len(row_data) < 10:
        row_data.append('')

    message_data = {
        'text': row_data[1],
        'option_a': row_data[2],
        'next_a': row_data[3],
        'option_b': row_data[4],
        'next_b': row_data[5],
        'option_c': row_data[6],
        'next_c': row_data[7],
    }
    return message_data

# === КОНЕЦ ФУНКЦИЙ ДЛЯ ТАБЛИЦЫ ===

# Словарь для хранения текущего состояния пользователей
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    user_id = update.effective_user.id
    user_states[user_id] = "M1"
    await send_message(update, context, "M1")

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: str):
    """Основная функция отправки сообщения и клавиатуры"""
    user_id = update.effective_user.id
    data = get_message_data(message_id)

    if not data:
        await update.message.reply_text("Сообщение не найдено. Ошибка в структуре.")
        return

    # Отправляем текст
    await update.message.reply_text(f"{data['text']}")

    # Создаем клавиатуру с вариантами ответа
    keyboard = []
    if data['option_a']:
        keyboard.append([f"A: {data['option_a']}"])
    if data['option_b']:
        keyboard.append([f"B: {data['option_b']}"])
    if data['option_c']:
        keyboard.append([f"C: {data['option_c']}"])

    # Отправляем клавиатуру
    if keyboard:
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Выберите путь:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Путешествие завершено.", reply_markup=ReplyKeyboardRemove())

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор пользователя (A, B, C)"""
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    
    if not text:
        return
        
    choice = text[0]  # Берем первый символ

    if user_id not in user_states:
        await update.message.reply_text("Начните путешествие с помощью /start")
        return

    current_message_id = user_states[user_id]
    data = get_message_data(current_message_id)

    if not data:
        await update.message.reply_text("Ошибка навигации.")
        return

    # Определяем следующий ID сообщения на основе выбора
    next_id = None
    if choice == 'A' and data['next_a']:
        next_id = data['next_a']
    elif choice == 'B' and data['next_b']:
        next_id = data['next_b']
    elif choice == 'C' and data['next_c']:
        next_id = data['next_c']

    if next_id:
        user_states[user_id] = next_id
        await send_message(update, context, next_id)
    else:
        await update.message.reply_text("Неверный выбор. Попробуйте снова.")

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
