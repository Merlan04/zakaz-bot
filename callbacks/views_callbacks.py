from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state
from time import time

logger = logging.getLogger(__name__)


def register_views_callbacks(bot, user_states):
    """Регистрировать callbacks просмотров"""

    # ================ ПРОДЛЕНИЕ ТАРИФА ================
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

        db.update_balance(user_id, -price, price)
        new_balance = db.get_user_balance(user_id)

        db.prolong_auto_view_new(tarif_id, 30)

        bot.send_message(call.message.chat.id,
                       f"✅ <b>ТАРИФ ПРОДЛЁН</b>\n\n"
                       f"Канал: {channel_name}\n"
                       f"Сумма: ${price:.2f}\n"
                       f"Новый баланс: ${new_balance:.2f}",
                       parse_mode='HTML')

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

        bot.send_message(message.chat.id,
                       f"✅ <b>ЗАПРОС ОТПРАВЛЕН</b>\n\n"
                       f"Старый канал: {old_channel}\n"
                       f"Новый канал: {new_channel}\n\n"
                       f"⏳ Ожидайте одобрения администратора",
                       parse_mode='HTML')

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

    # ================ BACK TO VIEWS MAIN ================
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