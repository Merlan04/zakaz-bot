from telebot import types
import logging
from database import db
from utils import reset_state, format_payment_message
from utils.formatters import format_user_question
from config import CRYPTO_ADDRESSES, ADMIN_ID, GROUP_ID, PAYMENT_GROUP_ID

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

    @bot.message_handler(commands=['admin'])
    def admin_start(message):
        if message.from_user.id == ADMIN_ID:
            reset_state(user_states, message.from_user.id)
            from callbacks.admin_callbacks import get_admin_menu
            bot.send_message(message.chat.id, "🔐 Admin paneli", reply_markup=get_admin_menu())

    # ================== SUBSCRIBERS BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "👥 Подписчики")
    def show_subscribers_info(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "👥 <b>ПОДПИСЧИКИ</b>\n\n"
            "Услуга добавления подписчиков на ваш канал\n\n"
            "📊 Характеристики:\n"
            "  • Минимум: 100 подписчиков\n"
            "  • Максимум: 50,000+ подписчиков\n"
            "  • Скорость: 50-500 в день\n"
            "  • Время жизни: постоянные\n\n"
            "⏱️ Обработка: 1-24 часа\n"
            "✅ Гарантия: 30 дней\n"
            "💰 Цена: от $2.00\n\n"
            "Нажмите для создания заказа 👇"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Создать заказ", callback_data="order_subscribers"),
            types.InlineKeyboardButton("📋 Мои заказы подписчиков", callback_data="my_subs_orders"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed subscribers menu")

    # ================== VIEWS BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "👀 Просмотры")
    def show_views_info(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "👀 <b>ПРОСМОТРЫ</b>\n\n"
            "Увеличение количества просмотров ваших видео\n\n"
            "📊 Характеристики:\n"
            "  • Минимум: 10 просмотров\n"
            "  • Максимум: 100,000+ просмотров\n"
            "  • Скорость: 100-2,000 в день\n"
            "  • Сохранение: гарантированное\n\n"
            "⏱️ Обработка: 1-24 часа\n"
            "✅ Гарантия: 45 дней\n"
            "💰 Цена: от $1.50\n\n"
            "Нажмите для создания заказа 👇"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Создать заказ", callback_data="order_views"),
            types.InlineKeyboardButton("📋 Мои заказы просмотров", callback_data="my_views_orders"),
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
            "❤️ <b>ГОЛОСА/РЕАКЦИИ</b>\n\n"
            "Добавление лайков и реакций на ваш контент\n\n"
            "📊 Характеристики:\n"
            "  • Типы реакций: ❤️ 👍 😂 😮 😢\n"
            "  • Минимум: 50 реакций\n"
            "  • Максимум: 10,000+ реакций\n"
            "  • Скорость: 20-200 в день\n\n"
            "⏱️ Обработка: 2-48 часов\n"
            "✅ Гарантия: 30 дней\n"
            "💰 Цена: от $3.00\n\n"
            "⚠️ <b>Статус: Скоро доступно!</b>"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔔 Уведомить когда откроется", callback_data="notify_reactions"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed reactions menu")

    # ================== MY ORDERS BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "⚙ Мои заказы")
    def show_my_orders(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "⚙️ <b>МОИ ЗАКАЗЫ</b>\n\n"
            "Управление и отслеживание всех ваших заказов\n\n"
            "📊 Доступные функции:\n"
            "  • Просмотр всех заказов\n"
            "  • Отслеживание статуса\n"
            "  • Время выполнения\n"
            "  • История платежей\n"
            "  • Справка и инструкции\n\n"
            "💡 Советы:\n"
            "  • Проверяйте ссылку на контент\n"
            "  • Убедитесь в доступности\n"
            "  • Следите за статусом\n"
        )

        orders = db.get_user_orders(user_id, limit=5)

        if orders:
            orders_text = "📦 <b>Ваши последние заказы:</b>\n\n"
            for order in orders:
                order_id, service_type, quantity, status, date = order
                status_emoji = "✅" if status == "completed" else "⏳" if status == "processing" else "❌"
                orders_text += f"{status_emoji} #{order_id} • {service_type} — {quantity} шт\n"
                orders_text += f"   Статус: {status} | Дата: {date}\n\n"

            full_message = info_message + "\n" + orders_text
        else:
            full_message = info_message + "\n\n❌ <b>У вас пока нет заказов</b>"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 Все заказы", callback_data="all_orders"),
            types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_orders"),
            types.InlineKeyboardButton("❓ Инструкция", callback_data="orders_help"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        bot.send_message(message.chat.id, full_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed orders menu")

    # ================== BALANCE BUTTON ==================
    @bot.message_handler(func=lambda message: message.text == "💳 Баланс")
    def show_balance(message):
        user_id = message.from_user.id
        balance = db.get_user_balance(user_id)
        reset_state(user_states, user_id)

        info_message = (
            "💳 <b>ВАШ БАЛАНС</b>\n\n"
            f"💰 Текущий баланс: <b>${balance:.2f}</b>\n\n"
            "📊 Информация:\n"
            "  • Минимальное пополнение: $5.00\n"
            "  • Поддерживаемые криптовалюты:\n"
            "    🪙 USDT (Tron)\n"
            "    🪙 BTC (Bitcoin)\n"
            "    🪙 LTC (Litecoin)\n"
            "    🪙 ETH (Ethereum)\n\n"
            "⚡ Пополнение моментальное\n"
            "✅ Без комиссий\n"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Пополнить", callback_data="deposit_crypto"),
            types.InlineKeyboardButton("📜 История", callback_data="balance_history"),
            types.InlineKeyboardButton("💎 Курсы", callback_data="crypto_rates"),
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
            "Свяжитесь с администратором по любым вопросам\n\n"
            "📋 <b>Перед отправкой вопроса:</b>\n"
            "1️⃣ Прочитайте справку в меню «⚙ Мои заказы»\n"
            "2️⃣ Проверьте информацию в разделе услуги\n"
            "3️⃣ Убедитесь что вопрос не в FAQ\n\n"
            "⚠️ <b>Важно:</b>\n"
            "  • На вопросы о продаже бота не отвечаем\n"
            "  • Скидок нет\n"
            "  • Отвечаем 24-48 часов\n\n"
            "📎 <b>Вы можете отправить:</b>\n"
            "  • Текстовое сообщение\n"
            "  • Фото\n"
            "  • Файл\n"
            "  • Видео\n\n"
            "👉 Отправьте ваше сообщение ниже:"
        )

        bot.send_message(message.chat.id, info_message, parse_mode='HTML')
        user_states[user_id] = {"step": "ask_admin"}

    # Обработчик текста
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get(
        "step") == "ask_admin" and message.content_type == 'text')
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
            logger.info(f"Text question from user {user_id} (@{username}) sent to PAYMENT_GROUP")
        except Exception as e:
            logger.error(f"Error sending text question to group: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки. Попробуйте позже.", reply_markup=get_main_menu())
            return

        bot.send_message(message.chat.id,
                         "✅ Ваш вопрос отправлен администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                         reply_markup=get_main_menu())
        reset_state(user_states, user_id)

    # Обработчик фото
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get(
        "step") == "ask_admin" and message.content_type == 'photo')
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
            # Получаем самое качественное фото
            file_id = message.photo[-1].file_id
            bot.send_photo(PAYMENT_GROUP_ID, file_id, caption=question_header, parse_mode='HTML')
            logger.info(f"Photo question from user {user_id} (@{username}) sent to PAYMENT_GROUP")
        except Exception as e:
            logger.error(f"Error sending photo question to group: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки. Попробуйте позже.", reply_markup=get_main_menu())
            return

        bot.send_message(message.chat.id,
                         "✅ Ваше фото отправлено администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                         reply_markup=get_main_menu())
        reset_state(user_states, user_id)

    # Обработчик файлов
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get(
        "step") == "ask_admin" and message.content_type == 'document')
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
            logger.info(f"File question from user {user_id} (@{username}) sent to PAYMENT_GROUP")
        except Exception as e:
            logger.error(f"Error sending file question to group: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки. Попробуйте позже.", reply_markup=get_main_menu())
            return

        bot.send_message(message.chat.id,
                         "✅ Ваш файл отправлен администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                         reply_markup=get_main_menu())
        reset_state(user_states, user_id)

    # Обработчик видео
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get(
        "step") == "ask_admin" and message.content_type == 'video')
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
            logger.info(f"Video question from user {user_id} (@{username}) sent to PAYMENT_GROUP")
        except Exception as e:
            logger.error(f"Error sending video question to group: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка отправки. Попробуйте позже.", reply_markup=get_main_menu())
            return

        bot.send_message(message.chat.id,
                         "✅ Ваше видео отправлено администратору.\n⏳ Ожидайте ответа в течение 24-48 часов.",
                         reply_markup=get_main_menu())
        reset_state(user_states, user_id)
    # ================== CALLBACK HANDLERS ==================

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    def back_to_main_callback(call):
        user_id = call.from_user.id
        reset_state(user_states, user_id)
        bot.edit_message_text("Главное меню:", call.message.chat.id, call.message.message_id,
                              reply_markup=get_main_menu())