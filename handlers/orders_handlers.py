from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state

logger = logging.getLogger(__name__)


def register_orders_handlers(bot, user_states):
    """Регистрировать обработчики заказов"""

    # ================ МОИ ЗАКАЗЫ (ГЛАВНОЕ МЕНЮ) ================
    @bot.callback_query_handler(func=lambda call: call.data == "my_orders_main")
    def my_orders_main(call):
        """Главное меню 'Мои заказы'"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("<<<", callback_data="orders_prev_page"),
            types.InlineKeyboardButton(">>>", callback_data="orders_next_page"),
            types.InlineKeyboardButton("⚙️ В работе", callback_data="orders_in_progress"),
            types.InlineKeyboardButton("🔧 Отменить/Изменить", callback_data="orders_cancel_menu")
        )

        markup.add(
            types.InlineKeyboardButton("👥 Подписчики", callback_data="orders_filter_subs_0"),
            types.InlineKeyboardButton("👀 Просмотры", callback_data="orders_filter_views_0"),
            types.InlineKeyboardButton("❤️ Лайки", callback_data="orders_filter_likes_0"),
            types.InlineKeyboardButton("❓ Вопрос", callback_data="orders_ask_admin")
        )

        markup.add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        )

        message_text = (
            "📋 <b>МОИ ЗАКАЗЫ</b>\n\n"
            "Выберите фильтр или действие:\n\n"
            "👥 Подписчики — заказы подписчиков\n"
            "👀 Просмотры — заказы просмотров\n"
            "❤️ Лайки — заказы лайков\n"
            "❓ Вопрос — вопрос администратору"
        )

        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} opened orders menu")

    # ================ ФИЛЬТР: ПОДПИСЧИКИ ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("orders_filter_subs_"))
    def orders_filter_subs(call):
        """Показать заказы подписчиков"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        page = int(call.data.split("_")[-1])

        # Получаем все заказы пользователя
        all_orders = db.get_user_orders(user_id, limit=100)

        # Фильтруем по типу услуги
        filtered_orders = [o for o in all_orders if o[1] == "Подписчики"]

        # Пагинация (5 заказов на странице)
        items_per_page = 5
        total_pages = (len(filtered_orders) + items_per_page - 1) // items_per_page

        if total_pages == 0:
            bot.send_message(call.message.chat.id,
                             "❌ <b>НЕТ ЗАКАЗОВ</b>\n\n"
                             "У вас нет заказов подписчиков",
                             parse_mode='HTML')
            return

        # Проверка страницы
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0

        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_orders = filtered_orders[start_idx:end_idx]

        # Формируем сообщение
        orders_text = f"👥 <b>МОИ ЗАКАЗЫ - ПОДПИСЧИКИ</b>\n"
        orders_text += f"Страница {page + 1}/{total_pages}\n\n"

        for order_id, service_type, quantity, status, date in page_orders:
            status_emoji = "✅" if status == "Завершен" else "⏳" if status == "В процессе" else "⏸️"
            orders_text += (
                f"{status_emoji} <b>#{order_id}</b> | {quantity:,} подписчиков\n"
                f"📊 Статус: {status}\n"
                f"🕐 Дата: {date}\n\n"
            )

        # Кнопки навигации
        markup = types.InlineKeyboardMarkup(row_width=2)

        # Кнопки переключения страниц
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_filter_subs_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"orders_filter_subs_{page + 1}"))

        if nav_buttons:
            markup.add(*nav_buttons)

        markup.add(
            types.InlineKeyboardButton("👥 Подписчики", callback_data="orders_filter_subs_0"),
            types.InlineKeyboardButton("👀 Просмотры", callback_data="orders_filter_views_0"),
            types.InlineKeyboardButton("❤️ Лайки", callback_data="orders_filter_likes_0"),
            types.InlineKeyboardButton("❓ Вопрос", callback_data="orders_ask_admin")
        )

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main"))

        bot.send_message(call.message.chat.id, orders_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed subscribers orders page {page + 1}")

    # ================ ФИЛЬТР: ПРОСМОТРЫ ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("orders_filter_views_"))
    def orders_filter_views(call):
        """Показать заказы просмотров"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        page = int(call.data.split("_")[-1])

        all_orders = db.get_user_orders(user_id, limit=100)
        filtered_orders = [o for o in all_orders if o[1] == "Просмотры"]

        items_per_page = 5
        total_pages = (len(filtered_orders) + items_per_page - 1) // items_per_page

        if total_pages == 0:
            bot.send_message(call.message.chat.id,
                             "❌ <b>НЕТ ЗАКАЗОВ</b>\n\n"
                             "У вас нет заказов просмотров",
                             parse_mode='HTML')
            return

        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0

        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_orders = filtered_orders[start_idx:end_idx]

        orders_text = f"👀 <b>МОИ ЗАКАЗЫ - ПРОСМОТРЫ</b>\n"
        orders_text += f"Страница {page + 1}/{total_pages}\n\n"

        for order_id, service_type, quantity, status, date in page_orders:
            status_emoji = "✅" if status == "Завершен" else "⏳" if status == "В процессе" else "⏸️"
            orders_text += (
                f"{status_emoji} <b>#{order_id}</b> | {quantity:,} просмотров\n"
                f"📊 Статус: {status}\n"
                f"🕐 Дата: {date}\n\n"
            )

        markup = types.InlineKeyboardMarkup(row_width=2)

        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_filter_views_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"orders_filter_views_{page + 1}"))

        if nav_buttons:
            markup.add(*nav_buttons)

        markup.add(
            types.InlineKeyboardButton("👥 Подписчики", callback_data="orders_filter_subs_0"),
            types.InlineKeyboardButton("👀 Просмотры", callback_data="orders_filter_views_0"),
            types.InlineKeyboardButton("❤️ Лайки", callback_data="orders_filter_likes_0"),
            types.InlineKeyboardButton("❓ Вопрос", callback_data="orders_ask_admin")
        )

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main"))

        bot.send_message(call.message.chat.id, orders_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed views orders page {page + 1}")

    # ================ ФИЛЬТР: ЛАЙКИ ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("orders_filter_likes_"))
    def orders_filter_likes(call):
        """Показать заказы лайков"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        page = int(call.data.split("_")[-1])

        all_orders = db.get_user_orders(user_id, limit=100)
        filtered_orders = [o for o in all_orders if o[1] == "Лайки"]

        items_per_page = 5
        total_pages = (len(filtered_orders) + items_per_page - 1) // items_per_page

        if total_pages == 0:
            bot.send_message(call.message.chat.id,
                             "❌ <b>НЕТ ЗАКАЗОВ</b>\n\n"
                             "У вас нет заказов лайков",
                             parse_mode='HTML')
            return

        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0

        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_orders = filtered_orders[start_idx:end_idx]

        orders_text = f"❤️ <b>МОИ ЗАКАЗЫ - ЛАЙКИ</b>\n"
        orders_text += f"Страница {page + 1}/{total_pages}\n\n"

        for order_id, service_type, quantity, status, date in page_orders:
            status_emoji = "✅" if status == "Завершен" else "⏳" if status == "В процессе" else "⏸️"
            orders_text += (
                f"{status_emoji} <b>#{order_id}</b> | {quantity:,} лайков\n"
                f"📊 Статус: {status}\n"
                f"🕐 Дата: {date}\n\n"
            )

        markup = types.InlineKeyboardMarkup(row_width=2)

        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_filter_likes_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"orders_filter_likes_{page + 1}"))

        if nav_buttons:
            markup.add(*nav_buttons)

        markup.add(
            types.InlineKeyboardButton("👥 Подписчики", callback_data="orders_filter_subs_0"),
            types.InlineKeyboardButton("👀 Просмотры", callback_data="orders_filter_views_0"),
            types.InlineKeyboardButton("❤️ Лайки", callback_data="orders_filter_likes_0"),
            types.InlineKeyboardButton("❓ Вопрос", callback_data="orders_ask_admin")
        )

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main"))

        bot.send_message(call.message.chat.id, orders_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed likes orders page {page + 1}")

    # ================ ВОПРОС АДМИНИСТРАТОРУ ================
    @bot.callback_query_handler(func=lambda call: call.data == "orders_ask_admin")
    def orders_ask_admin(call):
        """Спросить администратора о заказе"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        msg = bot.send_message(call.message.chat.id,
                               "🆔 <b>ВВЕДИТЕ НОМЕР ЗАКАЗА</b>\n\n"
                               "Напишите ID заказа, по которому у вас есть вопрос:\n\n"
                               "<i>Пример:</i> 123",
                               parse_mode='HTML')

        user_states[user_id] = {"step": "order_question_id"}
        bot.register_next_step_handler(msg, process_order_question_id, bot, user_states)

    def process_order_question_id(message, bot, user_states):
        """Обработка номера заказа для вопроса"""
        user_id = message.from_user.id

        try:
            order_id = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id,
                             "❌ <b>ОШИБКА</b>\n\n"
                             "Введите корректный номер заказа (число)",
                             parse_mode='HTML')
            return

        # Проверяем, принадлежит ли заказ пользователю
        user_orders = db.get_user_orders(user_id, limit=100)
        order_exists = any(o[0] == order_id for o in user_orders)

        if not order_exists:
            bot.send_message(message.chat.id,
                             "❌ <b>ЗАКАЗ НЕ НАЙДЕН</b>\n\n"
                             "Заказ с таким ID не принадлежит вам",
                             parse_mode='HTML')
            return

        user_states[user_id]["order_id"] = order_id

        msg = bot.send_message(message.chat.id,
                               f"❓ <b>КАКОЙ У ВАС ВОПРОС?</b>\n\n"
                               f"Заказ: #{order_id}\n\n"
                               f"Напишите ваш вопрос администратору:",
                               parse_mode='HTML')

        user_states[user_id]["step"] = "order_question_text"
        bot.register_next_step_handler(msg, process_order_question_text, bot, user_states)

    def process_order_question_text(message, bot, user_states):
        """Обработка текста вопроса и отправка админу"""
        user_id = message.from_user.id
        order_id = user_states.get(user_id, {}).get("order_id")
        question_text = message.text

        # Отправляем вопрос администратору
        admin_message = (
            "❓ <b>ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
            f"👤 ID пользователя: <code>{user_id}</code>\n"
            f"👤 Username: @{message.from_user.username or 'N/A'}\n"
            f"🆔 ID заказа: <code>{order_id}</code>\n\n"
            f"❓ <b>Вопрос:</b>\n{question_text}"
        )

        markup_admin = types.InlineKeyboardMarkup(row_width=1)
        markup_admin.add(
            types.InlineKeyboardButton("💬 Ответить", callback_data=f"admin_reply_question_{user_id}_{order_id}")
        )

        try:
            bot.send_message(ADMIN_ID, admin_message, reply_markup=markup_admin, parse_mode='HTML')
            logger.info(f"❓ Question from user {user_id} about order #{order_id} sent to admin")
        except Exception as e:
            logger.error(f"Error sending question to admin: {e}")

        # Подтверждение пользователю
        bot.send_message(message.chat.id,
                         f"✅ <b>ВОПРОС ОТПРАВЛЕН</b>\n\n"
                         f"Ваш вопрос о заказе #{order_id} отправлен администратору\n\n"
                         f"⏳ Ожидайте ответа в течение 24 часов",
                         parse_mode='HTML')

        reset_state(user_states, user_id)

    # ================ ОТМЕНИТЬ/ИЗМЕНИТЬ ЗАКАЗ ================
    @bot.callback_query_handler(func=lambda call: call.data == "orders_cancel_menu")
    def orders_cancel_menu(call):
        """Меню отмены/изменения заказа"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        msg = bot.send_message(call.message.chat.id,
                               "🆔 <b>ВВЕДИТЕ НОМЕР ЗАКАЗА</b>\n\n"
                               "Введите ID заказа, который вы хотите отменить или изменить:",
                               parse_mode='HTML')

        user_states[user_id] = {"step": "cancel_order_id"}
        bot.register_next_step_handler(msg, process_cancel_order_id, bot, user_states)

    def process_cancel_order_id(message, bot, user_states):
        """Обработка выбора заказа для отмены"""
        user_id = message.from_user.id

        try:
            order_id = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id,
                             "❌ <b>ОШИБКА</b>\n\n"
                             "Введите корректный номер заказа (число)",
                             parse_mode='HTML')
            return

        # Проверяем, принадлежит ли заказ пользователю
        user_orders = db.get_user_orders(user_id, limit=100)
        order_data = next((o for o in user_orders if o[0] == order_id), None)

        if not order_data:
            bot.send_message(message.chat.id,
                             "❌ <b>ЗАКАЗ НЕ НАЙДЕН</b>\n\n"
                             "Заказ с таким ID не принадлежит вам",
                             parse_mode='HTML')
            return

        order_id, service_type, quantity, status, date = order_data

        # Если заказ уже завершен, нельзя отменить
        if status == "Завершен":
            bot.send_message(message.chat.id,
                             "❌ <b>НЕВОЗМОЖНО ОТМЕНИТЬ</b>\n\n"
                             f"Заказ #{order_id} уже завершен\n"
                             f"Статус: {status}",
                             parse_mode='HTML')
            return

        user_states[user_id]["order_id"] = order_id
        user_states[user_id]["service_type"] = service_type
        user_states[user_id]["quantity"] = quantity
        user_states[user_id]["status"] = status

        # Показываем опции
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("❌ Отменить заказ", callback_data=f"confirm_cancel_{order_id}"),
            types.InlineKeyboardButton("✏️ Изменить", callback_data=f"change_order_{order_id}"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main")
        )

        cancel_message = (
            f"🆔 <b>ЗАКАЗ #{order_id}</b>\n\n"
            f"📦 Услуга: {service_type}\n"
            f"📊 Количество: {quantity:,}\n"
            f"⏳ Ст��тус: {status}\n\n"
            f"Что вы хотите сделать?"
        )

        bot.send_message(message.chat.id, cancel_message, reply_markup=markup, parse_mode='HTML')

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_cancel_"))
    def confirm_cancel_order(call):
        """Подтверждение отмены заказа"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        order_id = int(call.data.replace("confirm_cancel_", ""))

        # Обновляем статус заказа
        db.update_order_status(order_id, "Отменен")

        # Возвращаем деньги (получаем цену заказа)
        order_info = db.get_order_user_and_price(order_id)
        if order_info:
            _, price = order_info
            db.update_balance(user_id, price, 0)

        bot.send_message(call.message.chat.id,
                         f"✅ <b>ЗАКАЗ ОТМЕНЕН</b>\n\n"
                         f"Заказ #{order_id} успешно отменен\n"
                         f"💰 Средства возвращены на ваш баланс",
                         parse_mode='HTML')

        logger.info(f"User {user_id} cancelled order #{order_id}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("change_order_"))
    def change_order(call):
        """Изменение заказа (количество)"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        order_id = int(call.data.replace("change_order_", ""))

        user_states[user_id]["order_id"] = order_id

        msg = bot.send_message(call.message.chat.id,
                               f"📝 <b>ВВЕДИТЕ НОВОЕ КОЛИЧЕСТВО</b>\n\n"
                               f"Заказ: #{order_id}\n\n"
                               f"Введите новое количество:",
                               parse_mode='HTML')

        user_states[user_id]["step"] = "change_quantity"
        bot.register_next_step_handler(msg, process_change_quantity, bot, user_states)

    def process_change_quantity(message, bot, user_states):
        """Обработка изменения количества"""
        user_id = message.from_user.id
        order_id = user_states.get(user_id, {}).get("order_id")

        try:
            new_quantity = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id,
                             "❌ <b>ОШИБКА</b>\n\n"
                             "Введите корректное число",
                             parse_mode='HTML')
            return

        # TODO: Обновить заказ в БД (нужна функция для обновления количества)
        # Пока просто уведомляем пользователя

        bot.send_message(message.chat.id,
                         f"✅ <b>ЗАПРОС ОТПРАВЛЕН</b>\n\n"
                         f"Ваш запрос на изменение заказа #{order_id} отправлен администратору\n"
                         f"Новое количество: {new_quantity:,}\n\n"
                         f"⏳ Ожидайте ответа в течение 24 часов",
                         parse_mode='HTML')

        reset_state(user_states, user_id)

    # ================ В РАБОТЕ ================
    @bot.callback_query_handler(func=lambda call: call.data == "orders_in_progress")
    def orders_in_progress(call):
        """Показать заказы в процессе"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        all_orders = db.get_user_orders(user_id, limit=100)
        in_progress = [o for o in all_orders if o[3] == "В процессе"]

        if not in_progress:
            bot.send_message(call.message.chat.id,
                             "❌ <b>НЕТ ЗАКАЗОВ</b>\n\n"
                             "У вас нет заказов в процессе",
                             parse_mode='HTML')
            return

        orders_text = "⚙️ <b>ЗАКАЗЫ В ПРОЦЕССЕ</b>\n\n"

        for order_id, service_type, quantity, status, date in in_progress:
            orders_text += (
                f"🔄 <b>#{order_id}</b> | {service_type}\n"
                f"📊 Количество: {quantity:,}\n"
                f"🕐 Дата: {date}\n\n"
            )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main")
        )

        bot.send_message(call.message.chat.id, orders_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewed orders in progress")

        # ================ ФИЛЬТР: ПОДПИСЧИКИ ================
        @bot.callback_query_handler(func=lambda call: call.data.startswith("orders_filter_subs_"))
        def orders_filter_subs(call):
            """Показать заказы подписчиков"""
            bot.answer_callback_query(call.id)
            user_id = call.from_user.id
            page = int(call.data.split("_")[-1])

            all_orders = db.get_user_orders(user_id, limit=100)
            filtered_orders = [o for o in all_orders if o[1] == "Подписчики"]

            items_per_page = 5
            total_pages = (len(filtered_orders) + items_per_page - 1) // items_per_page

            if total_pages == 0:
                bot.send_message(call.message.chat.id,
                                 "❌ <b>НЕТ ЗАКАЗОВ</b>\n\n"
                                 "У вас нет заказов подписчиков",
                                 parse_mode='HTML')
                return

            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0

            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            page_orders = filtered_orders[start_idx:end_idx]

            # Формируем сообщение
            orders_text = f"📦 <b>Ваши заказы:</b>\n\n"

            for order_id, service_type, quantity, status, date in page_orders:
                # Преобразуем статусы для отображения
                if status == "Завершен" or status == "Выполнено":
                    display_status = "Выполнено"
                elif status == "В процессе" or status == "В ожидании":
                    display_status = "В ожидании"
                elif status == "Отмена" or status == "Отклонен":
                    display_status = "Отмена"
                else:
                    display_status = status

                orders_text += (
                    f"• Подписчики ({1} ч) — {quantity:,} шт\n"  # ← часы из заказа если нужно
                    f"   Статус: {display_status}\n"
                    f"   Дата: {date}\n\n"
                )

            # Кнопки навигации
            markup = types.InlineKeyboardMarkup(row_width=2)

            nav_buttons = []
            if page > 0:
                nav_buttons.append(
                    types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_filter_subs_{page - 1}"))
            if page < total_pages - 1:
                nav_buttons.append(
                    types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"orders_filter_subs_{page + 1}"))

            if nav_buttons:
                markup.add(*nav_buttons)

            markup.add(
                types.InlineKeyboardButton("👥 Подписчики", callback_data="orders_filter_subs_0"),
                types.InlineKeyboardButton("👀 Просмотры", callback_data="orders_filter_views_0"),
                types.InlineKeyboardButton("❤️ Лайки", callback_data="orders_filter_likes_0"),
                types.InlineKeyboardButton("❓ Вопрос", callback_data="orders_ask_admin")
            )

            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="my_orders_main"))

            bot.send_message(call.message.chat.id, orders_text, reply_markup=markup, parse_mode='HTML')
            logger.info(f"User {user_id} viewed subscribers orders page {page + 1}")