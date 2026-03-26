from telebot import types
import logging
from database import db
from utils import reset_state, format_payment_message
from utils.formatters import format_user_question
from config import CRYPTO_ADDRESSES, ADMIN_ID

logger = logging.getLogger(__name__)


def register_user_handlers(bot, user_states):
    """Регистрировать обработчики пользователя"""

    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        db.create_user_if_not_exists(user_id, message.from_user.username)
        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "👋 Добро пожаловать!\nВыберите услугу:",
                         reply_markup=get_main_menu())

    @bot.message_handler(commands=['admin'])
    def admin_start(message):
        if message.from_user.id == ADMIN_ID:
            reset_state(user_states, message.from_user.id)
            from callbacks.admin_callbacks import get_admin_menu
            bot.send_message(message.chat.id, "🔐 Admin paneli", reply_markup=get_admin_menu())

    @bot.message_handler(func=lambda message: message.text == "💳 Баланс")
    def show_balance(message):
        user_id = message.from_user.id
        balance = db.get_user_balance(user_id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Криптовалюты", callback_data="deposit_crypto"),
            types.InlineKeyboardButton("📜 История", callback_data="history")
        )

        bot.send_message(message.chat.id,
                         f"💳 Ваш баланс: {balance:.2f}$\n\nВыберите способ пополнения баланса:",
                         reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == "❓ Задать вопрос")
    def ask_question(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        bot.send_message(message.chat.id,
                         "1️⃣ Прочитайте справку в меню «⚙ Мои заказы». Она короткая\n"
                         "2️⃣ Если вопрос о просмотрах — внимательно прочитайте информацию в меню «👀 Просмотры»\n"
                         "3️⃣ Бот не продаётся, скидо�� нет. На вопросы, не касающиеся работы бота, не отвечаем\n\n"
                         "👉 Если у вас есть вопросы, оставьте их здесь и отправьте одним сообщением. Приветствия необязательны.")

        user_states[user_id] = {"step": "ask_admin"}

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "ask_admin")
    def ask_admin_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username

        # 🔴 ОТПРАВИТЬ ВОПРОС АДМИНУ (не в группу!)
        question_header = format_user_question(user_id, username)
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, question_header)

        bot.send_message(message.chat.id, "✅ Ваш вопрос отправлен администратору. Ожидайте ответа здесь.")
        logger.info(f"Question from user {user_id} (@{username}) sent to admin")
        reset_state(user_states, user_id)

    @bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.reply_to_message)
    def admin_reply_handler(message):
        if message.reply_to_message.forward_from and message.reply_to_message.forward_from.id:
            user_id = message.reply_to_message.forward_from.id
            if message.text:
                bot.send_message(user_id, message.text)
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            else:
                bot.send_message(user_id, "Admin sizga javob yubordi.")
            bot.reply_to(message, f"Javob {user_id} ga yuborildi.")
            logger.info(f"Admin reply sent to user {user_id}")
        else:
            bot.reply_to(message, "Bu xabarga reply qilish orqali javob berish mumkin emas.")

    @bot.message_handler(func=lambda message: message.text in ["❤ Голоса/Реакции"])
    def coming_soon(message):
        bot.send_message(message.chat.id,
                         "❤️ Голоса и реакции появятся в ближайшее время!\nСвяжитесь с администратором.",
                         reply_markup=get_main_menu())

    @bot.message_handler(func=lambda message: message.text == "⚙ Мои заказы")
    def show_my_orders(message):
        user_id = message.from_user.id
        orders = db.get_user_orders(user_id, limit=10)

        if orders:
            res = "📦 Ваши заказы:\n\n"
            for order in orders:
                order_id, service_type, quantity, status, date = order
                res += f"#{order_id} • {service_type} — {quantity} шт\n   Статус: {status}\n   Дата: {date}\n\n"
        else:
            res = "У вас пока нет заказов."

        bot.send_message(message.chat.id, res, reply_markup=get_main_menu())

    @bot.message_handler(func=lambda message: message.text in ["🔙 Назад", "🔚 Домой"])
    def go_back(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_menu())

    # ================== DEPOSIT HANDLERS ==================

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "deposit_crypto")
    def deposit_crypto_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if text in ["🔚 Домой", "/start"]:
            reset_state(user_states, user_id)
            bot.send_message(message.chat.id, "Главное меню", reply_markup=get_main_menu())
            return

        if text in CRYPTO_ADDRESSES:
            msg = bot.send_message(message.chat.id,
                                   f"💰 Введите сумму пополнения (минимум {db.get_setting('min_deposit')}$):")
            user_states[user_id] = {"step": "deposit_amount", "crypto": text}
            bot.register_next_step_handler(msg, deposit_amount_handler, bot, user_states)
        else:
            bot.send_message(message.chat.id, "⚠️ Выберите валюту из предложенных:")

    def deposit_amount_handler(message, bot, user_states):
        user_id = message.from_user.id
        text = message.text.strip()

        if text in ["🔚 Домой", "/start"]:
            reset_state(user_states, user_id)
            bot.send_message(message.chat.id, "Главное меню", reply_markup=get_main_menu())
            return

        if not text.replace('.', '', 1).isdigit():
            bot.send_message(message.chat.id, "⚠️ Неправильное число. Введите правильное:")
            return

        amount = float(text)
        min_dep = db.get_setting('min_deposit')

        if amount < min_dep:
            bot.send_message(message.chat.id, f"⚠️ Введите число больше {min_dep}")
            return

        crypto = user_states[user_id]["crypto"]
        db.create_temp_payment(user_id, amount, crypto)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Я заплатил")
        markup.add("🔚 Домой")

        payment_msg = format_payment_message(amount, crypto)
        bot.send_message(message.chat.id, payment_msg, reply_markup=markup, parse_mode='Markdown')

        user_states[user_id] = {"step": "deposit_confirm", "amount": amount, "crypto": crypto}

    @bot.message_handler(
        func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "deposit_confirm")
    def deposit_confirm_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if text in ["🔚 Домой", "/start"]:
            reset_state(user_states, user_id)
            bot.send_message(message.chat.id, "Главное меню", reply_markup=get_main_menu())
            return

        if text == "✅ Я заплатил":
            amount = user_states[user_id].get("amount", 0)
            crypto = user_states[user_id].get("crypto", "")

            # 🔴 ОТПРАВИТЬ ЗАПРОС ПЛАТЕЖА АДМИНУ (не в группу!)
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_payment_{user_id}"),
                types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_payment_{user_id}")
            )

            payment_request = format_admin_payment_request(user_id, amount, crypto)
            bot.send_message(ADMIN_ID, payment_request, reply_markup=markup)
            logger.info(f"Payment request from user {user_id}: {amount}$ {crypto}")

            bot.send_message(user_id, "⏳ Проверка...\nВаш счет будет автоматически пополнен в течение 1-3 минут.",
                             reply_markup=get_main_menu())
            reset_state(user_states, user_id)
            return

        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "Пополнение отменено.", reply_markup=get_main_menu())


def get_main_menu():
    """Получить главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👥 Подписчики", "👀 Просмотры")
    markup.add("❤ Голоса/Реакции", "⚙ Мои заказы")
    markup.add("💳 Баланс", "❓ Задать вопрос")
    return markup