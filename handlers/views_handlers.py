from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state
from time import time
import re

logger = logging.getLogger(__name__)


def register_views_handlers(bot, user_states):
    """Регистрировать обработчики просмотров"""

    # ================ ГЛАВНОЕ МЕНЮ ПРОСМОТРОВ (ВЫБОР МЕЖДУ БАЗОВЫМ И АВТОПРОСМОТРАМИ) ================
    @bot.message_handler(func=lambda message: message.text == "👀 Просмотры")
    def views_main_menu(message):
        """Главное меню просмотров - две кнопки"""
        bot.answer_callback_query(message.from_user.id)
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        balance = db.get_user_balance(user_id)

        info_message = (
            "ℹ️ <b>Базовый тариф</b> позволяет делать просмотры на любое количество постов из любого количества каналов.\n\n"
            "ℹ️ <b>Автопросмотры</b> — это список активных тарифов, которые вы подключили.\n\n"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👁️ Базовый тариф", callback_data="views_basic_tariff"),
            types.InlineKeyboardButton("👁️‍🗨️ Автопросмотры", callback_data="views_auto_menu")
        )
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

        bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} opened views main menu (balance: ${balance:.2f})")

    # ================ БАЗОВЫЙ ТАРИФ - ВЫБОР ТАРИФА ================
    @bot.callback_query_handler(func=lambda call: call.data == "views_basic_tariff")
    def views_basic_tariff(call):
        """Выбор тарифа для базового тарифа"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        balance = db.get_user_balance(user_id)

        if balance <= 0:
            bot.send_message(call.message.chat.id,
                           "⚠️ <b>Необходимо пополнить баланс для заказа услуг</b>",
                           parse_mode='HTML')
            return

        tariffs = db.get_view_tarifs()

        tariff_message = "👁️ <b>Базовый тариф</b>\n\nВыберите тариф для автоматических просмотров:\n\n"

        markup = types.InlineKeyboardMarkup(row_width=2)

        for tarif_type, price in tariffs:
            max_views = get_max_views_for_tarif(tarif_type)
            tariff_message += f"• <b>{max_views:,}</b> • ${price:.2f}\n"
            markup.add(types.InlineKeyboardButton(f"{max_views:,}  •  ${price:.2f}",
                                                  callback_data=f"select_views_tarif_{tarif_type}"))

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_views_main"))

        bot.send_message(call.message.chat.id, tariff_message, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewing basic tariff selection")

    # ================ ВЫБРАН ТАРИФ - ВВОД КАНАЛА ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_views_tarif_"))
    def select_views_tarif(call):
        """Выбор тарифа - просит ссылку канала"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        tarif_type = call.data.replace("select_views_tarif_", "")
        price = db.get_tarif_price(tarif_type)
        balance = db.get_user_balance(user_id)
        max_views = get_max_views_for_tarif(tarif_type)

        if balance < price:
            bot.send_message(call.message.chat.id,
                           f"❌ <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
                           f"💰 Необходимо: ${price:.2f}\n"
                           f"💰 Баланс: ${balance:.2f}",
                           parse_mode='HTML')
            return

        user_states[user_id] = {
            "step": "entering_views_channel",
            "tarif_type": tarif_type,
            "price": price,
            "max_views": max_views
        }

        msg = bot.send_message(call.message.chat.id,
                             f"👁️ <b>Базовый тариф</b>\n\n"
                             f"👉 Введите ссылку на канал, чтобы подключить функцию автоматического просмотра к каналу для этого тарифного плана:",
                             parse_mode='HTML')

        bot.register_next_step_handler(msg, process_views_channel, bot, user_states)

    def process_views_channel(message, bot, user_states):
        """Обработка ссылки канала"""
        user_id = message.from_user.id
        channel_link = message.text.strip()

        if not channel_link:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите ссылку на канал")
            return

        if not (channel_link.startswith('https://') or channel_link.startswith('@')):
            bot.send_message(message.chat.id, "❌ Неверный формат ссылки\nПримеры: https://t.me/channel или @channel")
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        user_states[user_id]["channel_link"] = channel_link
        user_states[user_id]["step"] = "entering_views_count"

        max_views = user_states[user_id].get("max_views", 1000)

        msg = bot.send_message(message.chat.id,
                             f"✅ Ваш канал: {channel_link}\n\n"
                             f"🌀 Ваш тариф позволяет делать до {max_views:,} просмотров на каждый пост.\n\n"
                             f"👉 Введите желаемое количество просмотров:",
                             parse_mode='HTML')

        bot.register_next_step_handler(msg, process_views_count, bot, user_states)

    def process_views_count(message, bot, user_states):
        """Обработка количества просмотров"""
        user_id = message.from_user.id

        try:
            views_count = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите число")
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        max_views = user_states[user_id].get("max_views", 1000)

        if views_count < 100:
            msg = bot.send_message(message.chat.id, f"⚠️ Введите число больше 100:")
            bot.register_next_step_handler(msg, process_views_count, bot, user_states)
            return

        if views_count > max_views:
            msg = bot.send_message(message.chat.id,
                                 f"⚠️ Максимум для вашего тарифа: {max_views:,}\n\n"
                                 f"👉 Введите число до {max_views:,}:")
            bot.register_next_step_handler(msg, process_views_count, bot, user_states)
            return

        user_states[user_id]["views_count"] = views_count
        user_states[user_id]["step"] = "entering_views_hours"

        msg = bot.send_message(message.chat.id,
                             f"⏱️ <b>На сколько часов растянуть просмотры на 1 пост?</b>\n\n"
                             f"👉 Укажите количество часов или 0, если хотите максимальную скорость:",
                             parse_mode='HTML')

        bot.register_next_step_handler(msg, process_views_hours, bot, user_states)

    def process_views_hours(message, bot, user_states):
        """Обработка часов и СПИСАНИЕ ДЕНЕГ"""
        user_id = message.from_user.id

        try:
            hours = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите число")
            return

        if hours < 0:
            bot.send_message(message.chat.id, "❌ Число не может быть отрицательным")
            return

        if hours > 5 and hours != 0:
            msg = bot.send_message(message.chat.id, "⚠️ Введите число от 1 до 5")
            bot.register_next_step_handler(msg, process_views_hours, bot, user_states)
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        channel_link = user_states[user_id].get("channel_link")
        views_count = user_states[user_id].get("views_count")
        tarif_type = user_states[user_id].get("tarif_type")
        price = user_states[user_id].get("price")
        max_views = user_states[user_id].get("max_views")
        balance = db.get_user_balance(user_id)

        if balance < price:
            bot.send_message(message.chat.id,
                           f"❌ <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
                           f"Баланс изменился. Попробуйте снова.",
                           parse_mode='HTML')
            reset_state(user_states, user_id)
            return

        # ✅ СПИСЫВАЕМ ДЕНЬГИ
        db.update_balance(user_id, -price, price)
        new_balance = db.get_user_balance(user_id)

        # ✅ СОЗДАЕМ ЗАКАЗ ПРОСМОТРОВ В БД (как автопросмотр на канал)
        current_time = int(time())
        end_time = current_time + (30 * 86400)  # 30 дней

        auto_tarif_id = db.create_auto_view_tarif(
            user_id=user_id,
            tarif_type=tarif_type,
            channel_name=channel_link,
            views_count=views_count,
            duration_hours=hours
        )

        # ✅ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ
        bot.send_message(message.chat.id,
                       f"✅ Заказ принят. Можете посмотреть статус в меню «Автопросмотры»",
                       parse_mode='HTML')

        # ✅ УВЕДОМЛЕНИЕ АДМИНУ
        admin_message = (
            f"Новый заказ просмотров\n"
            f"Тариф ID: #{auto_tarif_id}\n"
            f"User: {user_id}\n"
            f"Канал: {channel_link}\n"
            f"Просмотров: {views_count:,}\n"
            f"Часов: {hours if hours > 0 else '∞'}\n"
            f"Тариф: {max_views:,} просмотров\n"
            f"Сумма: ${price:.2f}"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_auto_view_{auto_tarif_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_auto_view_{auto_tarif_id}")
        )

        bot.send_message(ADMIN_ID, admin_message, reply_markup=markup, parse_mode='HTML')

        logger.info(f"User {user_id} created views order, balance charged ${price:.2f}")
        reset_state(user_states, user_id)

    # ================ АВТОПРОСМОТРЫ - ПОКАЗАТЬ СПИСОК АКТИВНЫХ ================
    @bot.callback_query_handler(func=lambda call: call.data == "views_auto_menu")
    def views_auto_menu(call):
        """Меню автопросмотров - список активных тарифов"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)

        current_time = int(time())
        active_tarifs = db.get_active_auto_view_tarifs(user_id, current_time)

        if not active_tarifs:
            msg = "👁️‍🗨️ <b>АВТОПРОСМОТРЫ</b>\n\n"
            msg += "У вас пока нет активных тарифов.\n"
            msg += "Приобретите через 👁️ Базовый тариф"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_views_main"))

            bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='HTML')
            return

        # Показываем список с кнопками
        msg = "👁️‍🗨️ <b>АВТОПРОСМОТРЫ</b>\n\n"

        markup = types.InlineKeyboardMarkup(row_width=1)

        for tarif_id, tarif_type, channel_name, end_time, views_per_post in active_tarifs:
            max_views = get_max_views_for_tarif(tarif_type)
            remaining_time = format_remaining_time(end_time - current_time)

            msg += (
                f"📌 <b>{channel_name}</b>\n"
                f"👁️ {views_per_post:,} просмотров ({max_views:,} макс)\n"
                f"⏱️ Осталось: {remaining_time}\n\n"
            )

            markup.add(
                types.InlineKeyboardButton("📝 Изменить", callback_data=f"views_edit_{tarif_id}"),
                types.InlineKeyboardButton("🔄 Продлить", callback_data=f"views_prolong_{tarif_id}")
            )

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_views_main"))

        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} viewing auto views ({len(active_tarifs)} active)")

    # ================ ПРОДЛИТЬ ТАРИФ ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("views_prolong_"))
    def views_prolong(call):
        """Продление тарифа"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        tarif_id = int(call.data.replace("views_prolong_", ""))

        user_states[user_id] = {"step": "confirming_prolong", "tarif_id": tarif_id}

        msg = (
            "⚠️ <b>ПРОДЛЕНИЕ ТАРИФ</b>\n\n"
            "После подтверждения тариф продлится еще на 30 дней и средства будут списаны с вашего баланса.\n\n"
            "Продолжить?"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, продлить", callback_data=f"confirm_views_prolong_{tarif_id}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_views_prolong")
        )

        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='HTML')

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_views_prolong_"))
    def confirm_views_prolong(call):
        """Подтвердить продление"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        tarif_id = int(call.data.replace("confirm_views_prolong_", ""))

        tarif_info = db.get_auto_view_tarif(tarif_id)
        if not tarif_info:
            bot.send_message(call.message.chat.id, "❌ Тариф не найден")
            return

        tarif_type, channel_name, views_per_post = tarif_info
        price = db.get_tarif_price(tarif_type)
        balance = db.get_user_balance(user_id)

        if balance < price:
            bot.send_message(call.message.chat.id,
                           f"❌ <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
                           f"💰 Необходимо: ${price:.2f}\n"
                           f"💰 Баланс: ${balance:.2f}",
                           parse_mode='HTML')
            return

        # ✅ СПИСЫВАЕМ ДЕНЬГИ
        db.update_balance(user_id, -price, price)
        new_balance = db.get_user_balance(user_id)

        # ✅ ПРОДЛЯЕМ ТАРИФ
        db.prolong_auto_view_new(tarif_id, 30)

        # ✅ УВЕДОМЛЯЕМ ПОЛЬЗОВАТЕЛЯ
        bot.send_message(call.message.chat.id,
                       f"✅ <b>ТАРИФ ПРОДЛЁН</b>\n\n"
                       f"Канал: {channel_name}\n"
                       f"Сумма: ${price:.2f}\n"
                       f"Новый баланс: ${new_balance:.2f}",
                       parse_mode='HTML')

        # ✅ УВЕДОМЛЯЕМ АДМИНА
        admin_msg = (
            f"Продление тарифа\n"
            f"User: {user_id}\n"
            f"Тариф ID: #{tarif_id}\n"
            f"Канал: {channel_name}\n"
            f"Сумма: ${price:.2f}\n"
            f"Статус: На одобрение"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_prolong_{tarif_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_prolong_{tarif_id}")
        )

        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode='HTML')

        reset_state(user_states, user_id)
        logger.info(f"User {user_id} requested prolong for tarif {tarif_id}")

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_views_prolong")
    def cancel_views_prolong(call):
        """Отмена продления"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)
        bot.send_message(call.message.chat.id, "❌ Продление отменено")

    # ================ ИЗМЕНИТЬ КАНАЛ ================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("views_edit_"))
    def views_edit(call):
        """Изменить канал тарифа"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        tarif_id = int(call.data.replace("views_edit_", ""))

        user_states[user_id] = {"step": "entering_new_channel", "tarif_id": tarif_id}

        msg = bot.send_message(call.message.chat.id,
                             "👉 Введите новую ссылку на канал:",
                             parse_mode='HTML')

        bot.register_next_step_handler(msg, process_edit_channel, bot, user_states)

    def process_edit_channel(message, bot, user_states):
        """Обработка новой ссылки канала"""
        user_id = message.from_user.id
        new_channel = message.text.strip()

        if not new_channel:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите ссылку на канал")
            return

        if not (new_channel.startswith('https://') or new_channel.startswith('@')):
            bot.send_message(message.chat.id, "❌ Неверный формат ссылки")
            return

        tarif_id = user_states.get(user_id, {}).get("tarif_id")
        if not tarif_id:
            bot.send_message(message.chat.id, "❌ Ошибка: тариф не найден")
            return

        tarif_info = db.get_auto_view_tarif(tarif_id)
        if not tarif_info:
            bot.send_message(message.chat.id, "❌ Тариф не найден в БД")
            return

        tarif_type, old_channel, views_per_post = tarif_info

        # ✅ УВЕДОМЛЯЕМ ПОЛЬЗОВАТЕЛЯ
        bot.send_message(message.chat.id,
                       f"✅ <b>ЗАПРОС ОТПРАВЛЕН</b>\n\n"
                       f"Старый канал: {old_channel}\n"
                       f"Новый канал: {new_channel}\n\n"
                       f"⏳ Ожидайте одобрения администратора",
                       parse_mode='HTML')

        # ✅ УВЕДОМЛЯЕМ АДМИНА
        admin_msg = (
            f"Изменение канала в тарифе\n"
            f"User: {user_id}\n"
            f"Тариф ID: #{tarif_id}\n"
            f"Старый канал: {old_channel}\n"
            f"Новый канал: {new_channel}\n"
            f"Статус: На одобрение"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_channel_{tarif_id}_{new_channel}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_channel_{tarif_id}")
        )

        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode='HTML')

        reset_state(user_states, user_id)
        logger.info(f"User {user_id} requested channel change for tarif {tarif_id}")

    # ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================
    @bot.callback_query_handler(func=lambda call: call.data == "back_to_views_main")
    def back_to_views_main(call):
        """Назад в главное меню просмотров"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)

        info_message = (
            "ℹ️ <b>Базовый тариф</b> позволяет делать просмотры на любое количество постов из любого количества каналов.\n\n"
            "ℹ️ <b>Автопросмотры</b> — это список активных тарифов, которые вы подключили.\n\n"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👁️ Базовый тариф", callback_data="views_basic_tariff"),
            types.InlineKeyboardButton("👁️‍🗨️ Автопросмотры", callback_data="views_auto_menu")
        )
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

        bot.send_message(call.message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')


def get_max_views_for_tarif(tarif_type):
    """Максимум просмотров для тарифа"""
    return {
        '1k': 1000, '5k': 5000, '10k': 10000,
        '15k': 15000, '20k': 20000
    }.get(tarif_type, 1000)


def format_remaining_time(seconds):
    """Форматировать время"""
    if seconds <= 0:
        return "Истёк"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    if days > 0:
        return f"{days}д {hours}ч"
    return f"{hours}ч"