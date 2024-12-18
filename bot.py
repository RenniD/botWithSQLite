from telegram import InputMediaPhoto, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import sqlite3

# Стадії конверсії
DATE_START, DATE_END, GUESTS, ROOM_TYPE = range(4)

# Ініціалізація бота
app = ApplicationBuilder().token("7407148766:AAEZoEiCxU43aOPNU2VbZWI1llqN7PWkTf8").build()

# Налаштування бази даних
def setup_database():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    # Створення таблиці користувачів
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        chat_id INTEGER NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Створення таблиці бронювань
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date_start TEXT NOT NULL,
        date_end TEXT NOT NULL,
        guests INTEGER NOT NULL,
        room_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    connection.commit()
    connection.close()
    print("База даних успішно налаштована.")

# Функція додавання користувача
def add_user(username, chat_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO users (username, chat_id)
        VALUES (?, ?)
        """, (username, chat_id))
        connection.commit()
        print(f"Користувач {username} успішно доданий.")
    except sqlite3.Error as e:
        print(f"Помилка при додаванні користувача: {e}")
    finally:
        connection.close()

# Функція додавання бронювання
def add_booking(chat_id, date_start, date_end, guests, room_type):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    try:
        # Отримання user_id за chat_id
        cursor.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
        user_id = cursor.fetchone()
        if user_id:
            user_id = user_id[0]
            cursor.execute("""
            INSERT INTO bookings (user_id, date_start, date_end, guests, room_type)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, date_start, date_end, guests, room_type))
            connection.commit()
            print("Бронювання успішно додано.")
        else:
            print("Користувача не знайдено в базі.")
    except sqlite3.Error as e:
        print(f"Помилка при додаванні бронювання: {e}")
    finally:
        connection.close()

# Команда /start із збереженням користувача
async def start_command(update, context):
    username = update.effective_user.username or "NoUsername"
    chat_id = update.effective_user.id

    # Додавання користувача в базу даних
    add_user(username, chat_id)

    inline_keyboard = [
        [InlineKeyboardButton("Забронировать номер", callback_data="book")],
        [InlineKeyboardButton("Услуги", callback_data="services")],
        [InlineKeyboardButton("Контакты", callback_data="contacts")],
        [InlineKeyboardButton("Наш сайт", url="https://example.com")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        "Добро пожаловать в отель 'Dream Stay'! Выберите действие:",
        reply_markup=markup
    )

# Обробник кнопок
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "book":
        await query.message.reply_text(
            "Для бронирования номера введите дату заезда (например, 2023-12-01):"
        )
        return DATE_START
    elif query.data == "services":
        await query.message.reply_text(
            "У нас доступны следующие услуги:\n"
            "- Завтраки\n"
            "- Бассейн и SPA\n"
            "- Трансфер из/в аэропорт"
        )
    elif query.data == "contacts":
        await query.message.reply_text(
            "Наши контактные данные:\n"
            "- Телефон: +123456789\n"
            "- Электронная почта: contact@dreamstay.com\n"
            "- Адрес: ул. Мира, 10, Киев"
        )

# Сбор данных для бронирования
async def date_start(update, context):
    context.user_data['date_start'] = update.message.text
    await update.message.reply_text("Введите дату выезда (например, 2023-12-10):")
    return DATE_END

async def date_end(update, context):
    context.user_data['date_end'] = update.message.text
    await update.message.reply_text("Сколько гостей будет проживать?")
    return GUESTS

async def guests(update, context):
    context.user_data['guests'] = update.message.text
    reply_keyboard = [["Стандарт", "Люкс", "Семейный"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите тип номера:", reply_markup=markup)
    return ROOM_TYPE

async def room_type(update, context):
    chat_id = update.effective_user.id
    context.user_data['room_type'] = update.message.text

    # Збереження бронювання в базі
    add_booking(
        chat_id,
        context.user_data['date_start'],
        context.user_data['date_end'],
        context.user_data['guests'],
        context.user_data['room_type']
    )

    booking_details = (
        f"Ваши данные для бронирования:\n"
        f"- Дата заезда: {context.user_data['date_start']}\n"
        f"- Дата выезда: {context.user_data['date_end']}\n"
        f"- Количество гостей: {context.user_data['guests']}\n"
        f"- Тип номера: {context.user_data['room_type']}\n"
        "Если все верно, наш администратор свяжется с вами для подтверждения."
    )
    await update.message.reply_text(booking_details, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("Бронирование отменено. Возвращайтесь, когда будете готовы!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Ініціалізація бази даних
setup_database()

# Реєстрація обробників команд і дій
app.add_handler(CommandHandler("start", start_command))

# Обробник конверсій для бронирования
booking_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler, pattern="^book$")],
    states={
        DATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_start)],
        DATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_end)],
        GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, guests)],
        ROOM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, room_type)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
app.add_handler(booking_handler)

# Запуск бота
if __name__ == "__main__":
    app.run_polling()
