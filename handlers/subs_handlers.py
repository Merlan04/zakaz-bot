from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state
from time import time

logger = logging.getLogger(__name__)


def register_subs_handlers(bot, user_states):
    """Регистрировать обработчики подписчиков"""

    # ================ КНОПКА ПОДПИСЧИКИ ================
    @bot.message_handler(func=lambda message: message.text == "👥 Подписчики")
    def subscribers_menu(message):
        """Главное меню подписчиков"""
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        balance = db.get_user_balance(user_id)
        subs_price = db.get_setting('subs_price')

        logger.info(f"=== SUBS MENU DEBUG ===")
        logger.info(f"User ID: {user_id}, Balance: {balance}, Subs Price: {subs_price}")
        logger.info(f"Balance > 0: {balance > 0}")
        logger.info(f"=== END DEBUG ===")

        if balance <= 0:
            # ❌ НЕ ДОСТАТОЧНО СРЕДСТВ
            info_message = (
                "👥 <b>Подписчики:</b>\n\n"
                f"• Цена: {subs_price}$ / 1 000 подписчиков\n"
                "• Неактивные, без отписок\n"
                "• Можно на открытые и закрытые каналы, чаты и боты\n\n"
                "⚠️ <b>Необходимо пополнить баланс для заказа услуг</b>"
            )

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

            bot.send_message(message.chat.id, info_message, reply_markup=markup, parse_mode='HTML')
            logger.info(f"User {user_id} → NO BALANCE PATH")

        else:
            # ✅ ДОСТАТОЧНО СРЕДСТВ - НАЧИНАЕМ ЗАКАЗ
            info_message = (
                "👥 <b>Подписчики:</b>\n\n"
                f"• Цена: {subs_price}$ / 1 000 подписчиков\n"
                "• Неактивные, без отписок\n"
                "• Можно на открытые и закрытые каналы, чаты и боты\n\n"
                "👉 Введите ссылку на канал, чат или бот:"
            )

            msg = bot.send_message(message.chat.id, info_message, parse_mode='HTML')

            user_states[user_id] = {"step": "entering_channel_link", "subs_price": subs_price}
            bot.register_next_step_handler(msg, process_channel_link, bot, user_states)
            logger.info(f"User {user_id} → HAS BALANCE PATH")


    def process_channel_link(message, bot, user_states):
        """Обработка ссылки на канал"""
        user_id = message.from_user.id
        channel_link = message.text.strip()

        if not channel_link:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите ссылку на канал")
            return

        # Проверяем формат ссылки
        if not (channel_link.startswith('https://') or channel_link.startswith('@')):
            bot.send_message(message.chat.id, "❌ Неверный формат ссылки\nПримеры: https://t.me/channel или @channel")
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        balance = db.get_user_balance(user_id)
        subs_price = user_states[user_id].get("subs_price", 0.1)
        max_subs = int((balance / subs_price) * 1000)

        user_states[user_id]["channel_link"] = channel_link
        user_states[user_id]["step"] = "entering_subs_count"

        info_message = (
            f"✅ Ваш канал: {channel_link}\n\n"
            f"🌀 Ваш баланс позволяет купить {max_subs:,} подписчиков.\n\n"
            f"👉 Введите желаемое количество подписчиков:"
        )

        msg = bot.send_message(message.chat.id, info_message, parse_mode='HTML')
        bot.register_next_step_handler(msg, process_subs_count, bot, user_states)

    def process_subs_count(message, bot, user_states):
        """Обработка количества подписчиков"""
        user_id = message.from_user.id

        try:
            subs_count = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите число")
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        # Проверка минимума (500)
        if subs_count < 500:
            msg = bot.send_message(message.chat.id, f"⚠️ Вве��ите число больше 500:")
            bot.register_next_step_handler(msg, process_subs_count, bot, user_states)
            return

        # Проверка баланса
        subs_price = user_states[user_id].get("subs_price", 0.1)
        cost = (subs_count / 1000) * subs_price
        balance = db.get_user_balance(user_id)

        if balance < cost:
            deficit = round(cost - balance, 2)
            bot.send_message(message.chat.id,
                             f"❌ <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
                             f"💰 Необходимо: ${cost:.2f}\n"
                             f"💰 Баланс: ${balance:.2f}\n"
                             f"❌ Не хватает: ${deficit:.2f}",
                             parse_mode='HTML')
            reset_state(user_states, user_id)
            return

        user_states[user_id]["subs_count"] = subs_count
        user_states[user_id]["cost"] = cost
        user_states[user_id]["step"] = "entering_hours"

        info_message = (
            "⏱️ <b>За сколько выполнить заказ?</b> (может быть выполнен медленнее, но не быстрее чем указанное время)\n\n"
            "👉 Введите количество часов или 0 для выполнения без ограничений по времени:"
        )

        msg = bot.send_message(message.chat.id, info_message, parse_mode='HTML')
        bot.register_next_step_handler(msg, process_hours, bot, user_states)

    def process_hours(message, bot, user_states):
        """Обработка времени выполнения и СПИСАНИЕ ДЕНЕГ"""
        user_id = message.from_user.id

        try:
            hours = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите число")
            return

        if hours < 0:
            bot.send_message(message.chat.id, "❌ Число не может быть отрицательным")
            return

        # ⚠️ ПРОВЕРКА: максимум 5 часов или 0
        if hours > 5 and hours != 0:
            msg = bot.send_message(message.chat.id, "⚠️ Введите число от 1 до 5")
            bot.register_next_step_handler(msg, process_hours, bot, user_states)
            return

        if user_id not in user_states:
            user_states[user_id] = {}

        # Получаем все данные
        channel_link = user_states[user_id].get("channel_link")
        subs_count = user_states[user_id].get("subs_count")
        cost = user_states[user_id].get("cost")
        balance = db.get_user_balance(user_id)

        # ФИНАЛЬНАЯ ПРОВЕРКА БАЛАНСА
        if balance < cost:
            bot.send_message(message.chat.id,
                             f"❌ <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
                             f"Баланс изменился. Попробуйте снова.",
                             parse_mode='HTML')
            reset_state(user_states, user_id)
            return

        # ✅ СПИСЫВАЕМ ДЕНЬГИ
        db.update_balance(user_id, -cost, cost)
        new_balance = db.get_user_balance(user_id)

        # ✅ СОЗДАЕМ ЗАКАЗ В БД
        order_id = db.create_order(
            user_id=user_id,
            service_type="Подписчики",
            link=channel_link,
            quantity=subs_count,
            price=cost,
            hours=hours
        )

        # ✅ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ
        success_message = (
            f"✅ Заказ принят. Можете посмотреть статус в меню «Мои заказы»"
        )

        bot.send_message(message.chat.id, success_message, parse_mode='HTML')

        # ✅ УВЕДОМЛЕНИЕ АДМИНУ
        admin_message = (
            f"Заказ #{order_id}\n"
            f"User: {user_id}\n"
            f"Канал: {channel_link}\n"
            f"Кол-во: {subs_count}\n"
            f"Часов: {hours if hours > 0 else '∞'}\n"
            f"Сумма: {cost:.2f}$"
        )

        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("✅ Выполнено", callback_data=f"admin_approve_subs_{order_id}"),
            types.InlineKeyboardButton("🔄 В процессе", callback_data=f"admin_in_progress_subs_{order_id}"),
            types.InlineKeyboardButton("❌ Отменить", callback_data=f"admin_reject_subs_{order_id}")
        )

        bot.send_message(ADMIN_ID, admin_message, reply_markup=markup, parse_mode='HTML')

        logger.info(f"User {user_id} created subs order #{order_id}, balance charged ${cost:.2f}")
        reset_state(user_states, user_id)