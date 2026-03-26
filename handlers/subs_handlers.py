from telebot import types
import logging
from database import db
from utils import (
    validate_channel_link, extract_channel, validate_quantity_in_range,
    validate_number, reset_state, get_channel_name, get_possible_quantity
)
from utils.formatters import format_order_message
from config import ADMIN_ID, GROUP_ID

logger = logging.getLogger(__name__)


def register_subs_handlers(bot, user_states):
    """Регистрировать обработчики подписчиков"""

    @bot.message_handler(func=lambda message: message.text == "👥 Подписчики")
    def show_subs_menu(message):
        user_id = message.from_user.id
        reset_state(user_states, user_id)

        balance = db.get_user_balance(user_id)
        price = db.get_setting('subs_price')
        min_qty = int(db.get_setting('subs_min_qty'))
        min_price = (min_qty / 1000.0) * price

        if balance < min_price:
            bot.send_message(message.chat.id,
                             "👥 Подписчики:\n\n"
                             f"• Цена: {price}$ / 1 000 подписчиков\n"
                             "• Неактивные, без отписок\n"
                             "• Можно на открытые и закрытые каналы, чаты и боты\n\n"
                             "⚠️ Необходимо пополнить баланс для заказа услуг",
                             reply_markup=get_subs_menu())
            return

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔚 Домой")

        bot.send_message(message.chat.id,
                         f"👥 Подписчики:\n\n"
                         f"• Цена: {price}$ / 1 000 подписчиков\n"
                         f"• Неактивные, без отписок\n"
                         f"• Можно на открытые и закрытые каналы, чаты и боты\n\n"
                         f"👉 Введите ссылку на канал, чат или бот:",
                         reply_markup=kb)

        user_states[user_id] = {"step": "subs_link"}

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "subs_link")
    def subs_link_handler(message):
        user_id = message.from_user.id
        link = message.text.strip()

        if not validate_channel_link(link):
            bot.send_message(message.chat.id, "⚠️ Неправильный формат.\n\n👉 Введите правильную ссылку:")
            return

        channel = extract_channel(link)
        ch_name = get_channel_name(bot, link)
        balance = db.get_user_balance(user_id)
        price = db.get_setting('subs_price')
        possible = get_possible_quantity(balance, price)

        bot.send_message(message.chat.id,
                         f"✅ Ваш канал: {ch_name}\n\n"
                         f"🌀 Ваш баланс позволяет купить {possible} подписчиков.\n\n"
                         f"👉 Введите желаемое количество подписчиков:")

        user_states[user_id] = {
            "step": "subs_qty",
            "link": channel,
            "ch_name": ch_name,
            "balance": balance
        }

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "subs_qty")
    def subs_qty_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if not text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Неправильное число. Введите правильное:")
            return

        qty = int(text)
        min_q = int(db.get_setting('subs_min_qty'))
        max_q = int(db.get_setting('subs_max_qty'))

        if qty < min_q:
            bot.send_message(message.chat.id, f"⚠️ Введите число больше {min_q}:")
            return

        if qty > max_q:
            bot.send_message(message.chat.id, f"⚠️ Введите число меньше {max_q}:")
            return

        price_per = db.get_setting('subs_price')
        max_possible = get_possible_quantity(user_states[user_id]["balance"], price_per)

        if qty > max_possible:
            bot.send_message(message.chat.id,
                             f"⚠️ Ваш баланс позволяет купить {max_possible} подписчиков.\n\nВведите число не более {max_possible}")
            return

        user_states[user_id]["qty"] = qty
        user_states[user_id]["step"] = "subs_hours"

        bot.send_message(message.chat.id,
                         "⏱️ За сколько выполнить заказ? (может быть выполнен медленнее, но не быстрее чем указанное время)\n\n"
                         "👉 Введите количество часов или 0 для выполнения без огран��чений по времени:")

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "subs_hours")
    def subs_hours_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if not text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Введите только число:")
            return

        hrs = int(text)
        min_h = int(db.get_setting('subs_min_hrs'))
        max_h = int(db.get_setting('subs_max_hrs'))

        if hrs < min_h or hrs > max_h:
            bot.send_message(message.chat.id, f"⚠️ Введите число от {min_h} до {max_h}")
            return

        qty = user_states[user_id]["qty"]
        link = user_states[user_id]["link"]
        price = (qty / 1000.0) * db.get_setting('subs_price')
        real_balance = db.get_user_balance(user_id)

        if real_balance < price:
            reset_state(user_states, user_id)
            bot.send_message(message.chat.id, "❌ Недостаточно средств",
                             reply_markup=get_main_menu_for_subs())
            return

        # Обновить баланс
        db.update_balance(user_id, -price, price)

        # Создать заказ
        order_id = db.create_order(
            user_id,
            f"Подписчики ({hrs} ч)",
            link,
            qty,
            price,
            hrs
        )

        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "✅ Заказ принят. Можете посмотреть статус в меню «Мои заказы»",
                         reply_markup=get_main_menu_for_subs())

        # 🔴 УВЕДОМИТЬ ГРУППУ (не админа!)
        from callbacks.order_callbacks import get_status_markup
        order_details = format_order_message(order_id, f"Подписчики ({hrs} ч)", qty, price, hrs, link, user_id)

        try:
            bot.send_message(GROUP_ID, order_details, reply_markup=get_status_markup(order_id))
            logger.info(f"Order #{order_id} sent to group {GROUP_ID}")
        except Exception as e:
            logger.error(f"Failed to send order to group: {e}")
            # Если группа недоступна, отправить админу
            bot.send_message(ADMIN_ID, f"⚠️ Не удалось отправить в группу:\n{order_details}",
                             reply_markup=get_status_markup(order_id))


def get_subs_menu():
    """Получить меню подписчиков"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔚 Домой")
    return markup


def get_main_menu_for_subs():
    """Получить главное меню"""
    from handlers.user_handlers import get_main_menu
    return get_main_menu()