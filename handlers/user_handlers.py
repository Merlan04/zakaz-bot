from telebot import types
import logging
from database import db
from utils import reset_state
from config import ADMIN_ID, PAYMENT_GROUP_ID

logger = logging.getLogger(__name__)


def get_main_menu():
    """Получить главное меню с кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👥 Подписчики", "👀 Просмотры")
    markup.add("❤ Голоса/Реакции", "⚙ Мои заказы")
    markup.add("💳 Баланс", "❓ Задать вопрос")
    return markup


def register_user_handlers(bot, user_states):
    """Регистрировать обработчики пользователя"""

    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        db.create_user_if_not_exists(user_id, message.from_user.username)
        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "👋 Добро пожаловать!\nВыберите услугу:",
                         reply_markup=get_main_menu())
        logger.info(f"✅ START command from user {user_id}")

    # ================== VIEWS BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "👀 Просмотры")
    def show_views_info(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "ℹ️ Базовый тариф позволяет делать просмотры на любое количество постов из любого количества каналов. Для заказа просмотров в базовом тарифе нужно переслать нужную публикацию боту.\n\n"
            "ℹ️ Автопросмотры — дополнительная платная опция, которая подхватывает новые посты в канале автоматически. Больше информации в меню 👁‍🗨 Автопросмотры\n\n"
            "ℹ️ Максимальное количество просмотров на каждый пост определяется купленным тарифом. Количество просмотров и скорость накрутки выбираете сами\n\n"
            "❗️ Пример: после покупки тарифа «1000 просмотров» вы можете делать до 1000 просмотров на любое количество постов из 1 канала в течение 10 дней\n\n"
            "👁 У вас нет активного тарифа\n\n"
            "👉 Перейдите в меню «Базовый тариф» для покупки"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📊 Базовый тариф", callback_data="show_tariffs_no_balance"),
            types.InlineKeyboardButton("👁️‍🗨️ Автопросмотры", callback_data="order_auto_views"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed views menu")

        # ================== REACTIONS BUTTON ==================

    @bot.message_handler(func=lambda message: message.text == "❤ Голоса/Реакции")
    def show_reactions_info(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "❤ <b>Голоса/Реакции</b>\n\n"
            "❤️ Голоса и реакции появятся в ближайшее время!\n"
            "Свяжитесь с администратором."
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed reactions menu")
    # ================ REACTIONS CALLBACK ==================
    @bot.callback_query_handler(func=lambda call: call.data == "reactions_info")
    def reactions_callback(call):
        """Callback для кнопки Голоса/Реакции"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "❤ <b>Голоса/Реакции</b>\n\n"
            "❤️ ��олоса и реакции появятся в ближайшее время!\n"
            "Свяжитесь с администратором."
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

        bot.send_message(call.message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed reactions menu (callback)")

    # ================== MY ORDERS BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "⚙ Мои заказы")
    def show_my_orders(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "⚙️ <b>МОИ ЗАКАЗЫ</b>\n\n"
            "У вас пока нет заказов."
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed orders menu")

    # ================== BALANCE BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "💳 Баланс")
    def show_balance(message):
        user_id = message.from_user.id
        balance = db.get_user_balance(user_id)
        reset_state(user_states, user_id)

        info_message = (
            "💳 <b>ВАШ БАЛАНС</b>\n\n"
            f"💰 Ваш баланс: {balance:.2f}$\n\n"
            "Выберите способ пополнения баланса:"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🪙 Криптовалюта", callback_data="deposit_crypto"),
            types.InlineKeyboardButton("📜 История", callback_data="balance_history"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed balance")

    # ================== ASK QUESTION BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "❓ Задать вопрос")
    def ask_question(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "❓ <b>ТЕХНИЧЕСКАЯ ПОДДЕРЖКА</b>\n\n"
            "1️⃣ Прочитайте справку в меню «⚙ Мои заказы». Она короткая\n"
            "2️⃣ Если вопрос о просмотрах — внимательно прочитайте информацию в меню «👀 Просмотры»\n"
            "3️⃣ Бот не продаётся, скидок нет. На вопросы, не касающиеся работы бота, не отвечаем\n\n"
            "👉 Если у вас есть вопросы, оставьте их здесь и отправьте одним сообщением. Приветствия необязательны."
        )

        bot.send_message(message.chat.id, info_message, parse_mode='HTML')
        user_states[user_id] = {"step": "ask_admin"}
        logger.info(f"User {user_id} entered ask_admin mode")

    # ================== ОБРАБОТЧИКИ КОНТЕНТА ==================
    # ⭐ КРИТИЧНЫЙ ПОРЯДОК: Video → Document → Photo → Text

    # 4️⃣ Видео
    @bot.message_handler(content_types=['video'],
                         func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "ask_admin")
    def ask_admin_video_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username or "No username"
        video_text = message.caption or "Видео без описания"

        question_header = (
            f"❓ <b>Новый вопрос от пользователя</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👤 Username: @{username}\n"
            f"🎥 Тип: Видео\n\n"
            f"<b>Описание:</b>\n{video_text}"
        )

        try:
            file_id = message.video.file_id
            bot.send_video(PAYMENT_GROUP_ID, file_id, caption=question_header, parse_mode='HTML')
            logger.info(f"✅ Video from {user_id} sent to PAYMENT_GROUP")
            bot.send_message(message.chat.id,
                             "✅ Ваше видео отправлено администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                             reply_markup=get_main_menu())
        except Exception as e:
            logger.error(f"❌ Video error: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки.", reply_markup=get_main_menu())

        reset_state(user_states, user_id)

    # 3️⃣ Документы
    @bot.message_handler(content_types=['document'],
                         func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "ask_admin")
    def ask_admin_file_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username or "No username"
        file_name = message.document.file_name
        file_text = message.caption or "Файл без описания"

        question_header = (
            f"❓ <b>Новый вопрос от пользователя</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👤 Username: @{username}\n"
            f"📄 Тип: Файл\n"
            f"📛 Название: <code>{file_name}</code>\n\n"
            f"<b>Описание:</b>\n{file_text}"
        )

        try:
            file_id = message.document.file_id
            bot.send_document(PAYMENT_GROUP_ID, file_id, caption=question_header, parse_mode='HTML')
            logger.info(f"✅ Document from {user_id} sent to PAYMENT_GROUP")
            bot.send_message(message.chat.id,
                             "✅ Ваш файл отправлен администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                             reply_markup=get_main_menu())
        except Exception as e:
            logger.error(f"❌ Document error: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки.", reply_markup=get_main_menu())

        reset_state(user_states, user_id)

    # 2️⃣ Фото
    @bot.message_handler(content_types=['photo'],
                         func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "ask_admin")
    def ask_admin_photo_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username or "No username"
        photo_text = message.caption or "Фото без описания"

        question_header = (
            f"❓ <b>Новый вопрос от пользователя</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👤 Username: @{username}\n"
            f"📸 Тип: Фото\n\n"
            f"<b>Описание:</b>\n{photo_text}"
        )

        try:
            file_id = message.photo[-1].file_id
            bot.send_photo(PAYMENT_GROUP_ID, file_id, caption=question_header, parse_mode='HTML')
            logger.info(f"✅ Photo from {user_id} sent to PAYMENT_GROUP")
            bot.send_message(message.chat.id,
                             "✅ Ваше фото отправлено администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                             reply_markup=get_main_menu())
        except Exception as e:
            logger.error(f"❌ Photo error: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки.", reply_markup=get_main_menu())

        reset_state(user_states, user_id)

    # 1️⃣ Текст (ПОСЛЕДНИЙ!)
    @bot.message_handler(content_types=['text'],
                         func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "ask_admin")
    def ask_admin_text_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username or "No username"

        question_header = (
            f"❓ <b>Новый вопрос от пользователя</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👤 Username: @{username}\n"
            f"📝 Тип: Текст\n\n"
            f"<b>Сообщение:</b>\n{message.text}"
        )

        try:
            bot.send_message(PAYMENT_GROUP_ID, question_header, parse_mode='HTML')
            logger.info(f"✅ Text from {user_id} sent to PAYMENT_GROUP")
            bot.send_message(message.chat.id,
                             "✅ Ваш вопрос отправлен администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                             reply_markup=get_main_menu())
        except Exception as e:
            logger.error(f"❌ Text error: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки.", reply_markup=get_main_menu())

        reset_state(user_states, user_id)

    # ================== CALLBACK HANDLERS ==================
    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_to_main_callback(call):
        logger.info(f"back_to_main clicked by {call.from_user.id}")
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)

        bot.send_message(call.message.chat.id, "📋 Главное меню:", reply_markup=get_main_menu())
        logger.info(f"Main menu sent to {user_id}")