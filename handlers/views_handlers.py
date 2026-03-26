from telebot import types
import logging
import time
from database import db
from utils import (
    validate_channel_link, extract_channel, validate_number, reset_state,
    get_channel_name, format_active_tarifs, format_time_remaining
)
from utils.formatters import format_order_message
from config import ADMIN_ID, GROUP_ID, TARIFF_VIEWS_MAP

logger = logging.getLogger(__name__)


def register_views_handlers(bot, user_states):
    """Регистрировать обработчики просмотров"""

    @bot.message_handler(func=lambda message: message.text == "👀 Просмотры")
    def show_views_menu(message):
        user_id = message.from_user.id
        current_time = int(time.time())
        active = db.get_active_view_tarifs(user_id, current_time)

        txt = (
            "ℹ️ Базовый тариф позволяет делать просмотры на любое количество постов из любого количества каналов. "
            "Для заказа просмотров в базовом тарифе нужно переслать нужную публикацию боту.\n\n"
            "ℹ️ Автопросмотры — дополнительная платная опция, которая подхватывает новые посты в канале автоматически. "
            "Больше информации в меню 👁‍🗨 Автопросмотры\n\n"
            "ℹ️ Максимальное количество просмотров на каждый пост определяется купленным тарифом. "
            "Количество просмотров и скорость накрутки выбираете сами\n\n"
            "❗️ Пример: после покупки тарифа «1000 просмотров» вы можете делать до 1000 просмотров на любое количество постов "
            "из 1 канала в течение 10 дней\n\n"
        )

        if active:
            txt += f"👁 Активные тарифы: {len(active)}\n\n"

        txt += "👉 Для заказа просмотров сделайте сюда репост или вставьте ссылку:"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👁️ Базовый тариф", "👁️‍🗨️ Автопросмотры")
        markup.add("🔙 Назад")

        bot.send_message(message.chat.id, txt, reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == "👁️ Базовый тариф")
    def show_basic_tariffs(message):
        markup = types.InlineKeyboardMarkup(row_width=2)
        tarifs = db.get_view_tarifs()
        buttons = [types.InlineKeyboardButton(f"{t.upper()} • ${price}", callback_data=f"buy_tarif_{t}")
                   for t, price in tarifs]

        if len(buttons) >= 4:
            markup.row(buttons[0], buttons[2])
            markup.row(buttons[1], buttons[3])
            if len(buttons) > 4:
                markup.row(buttons[4])

        bot.send_message(message.chat.id, "Выберите тариф для базовых просмотров:", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == "👁️‍🗨️ Автопросмотры")
    def show_auto_views(message):
        user_id = message.from_user.id
        current_time = int(time.time())
        active = db.get_active_view_tarifs(user_id, current_time)

        info = (
            "ℹ️ Автопросмотры - дополнительная опция, работает только с купленным базовым тарифом и оплачивается отдельно 0.1$/день за каждый канал (кнопка «Продлить»)\n\n"
            "ℹ️ На каналах с автопросмотрами накрутка на новые посты начинается автоматически в течение 3 мин после публикации (если добавите бота @susunodbot в админы - будет быстрей и стабильней, нужны любые права), на старые посты делайте вручную репостом\n\n"
            "ℹ️ Вы выставляете желаемое количество просмотров, но цифры на разных постах будут различаться для реалистичности.\n\n"
            "ℹ️ При подхвате репоста из другого канала в канал на автопросмотрах — снимается 0.01$ с баланса, если баланс пустой — репосты пропускаются\n\n"
            "ℹ️ При отключении канала деньги за оставшиеся полные дни возвращаются\n\n"
            "ℹ️ Опция защита от копирования в настройках канала должна быть выключена"
        )

        bot.send_message(message.chat.id, info)

        if active:
            txt = format_active_tarifs(active)
            markup = types.InlineKeyboardMarkup(row_width=2)

            for tar, end, link, views in active:
                markup.add(
                    types.InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_auto_{link}"),
                    types.InlineKeyboardButton("📆 Продлить", callback_data=f"prolong_auto_{link}")
                )

            bot.send_message(message.chat.id, txt, reply_markup=markup)

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "auto_view_link")
    def auto_view_link_handler(message):
        user_id = message.from_user.id
        link = message.text.strip()

        if not validate_channel_link(link):
            bot.send_message(message.chat.id, "⚠️ Неправильный формат.\n👉 Введите правильную ссылку:")
            return

        channel = extract_channel(link)
        ch_name = get_channel_name(bot, link)

        current_time = int(time.time())
        active = db.get_active_view_tarifs(user_id, current_time)

        for _, _, ex_link, _ in active:
            if ex_link == channel:
                bot.send_message(message.chat.id,
                                 f"⚠️ Ваш канал: *{ch_name}*\nАвтопросмотры на этот канал уже подключены.\n\n👉 Управляйте уже созданным заказом или сначала отключите его",
                                 parse_mode='HTML')
                reset_state(user_states, user_id)
                return

        tarif = user_states[user_id]["tarif"]
        max_views = TARIFF_VIEWS_MAP.get(tarif, 1000)

        bot.send_message(message.chat.id,
                         f"✅ Ваш канал: {ch_name}\n\n"
                         f"🌀 Ваш тариф позволяет делать до {max_views} просмотров на каждый пост.\n\n"
                         f"👉 Введите желаемое количество просмотров:")

        user_states[user_id]["step"] = "auto_view_qty"
        user_states[user_id]["link"] = channel
        user_states[user_id]["ch_name"] = ch_name

    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "auto_view_qty")
    def auto_view_qty_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if not text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Неправильное число. Введите правильное:")
            return

        qty = int(text)
        tarif = user_states[user_id]["tarif"]
        max_views = TARIFF_VIEWS_MAP.get(tarif, 1000)

        if qty < 1 or qty > max_views:
            bot.send_message(message.chat.id, f"⚠️ Введите число больше 0 и меньше {max_views}")
            return

        user_states[user_id]["qty"] = qty
        user_states[user_id]["step"] = "auto_view_hours"

        bot.send_message(message.chat.id,
                         "⏱️ На сколько часов растянуть просмотры на 1 пост?\n"
                         "👉 Укажите количество часов или 0, если хотите максимальную скорость:")

    @bot.message_handler(
        func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "auto_view_hours")
    def auto_view_hours_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if not text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Неправильное число. Введите правильное:")
            return

        hrs = int(text)
        min_h = int(db.get_setting('subs_min_hrs'))
        max_h = int(db.get_setting('subs_max_hrs'))

        if hrs < min_h or hrs > max_h:
            bot.send_message(message.chat.id, f"⚠️ Введите число от {min_h} до {max_h}")
            return

        qty = user_states[user_id]["qty"]
        tarif = user_states[user_id]["tarif"]
        link = user_states[user_id]["link"]
        price = user_states[user_id]["price"]

        real_balance = db.get_user_balance(user_id)

        if real_balance < price:
            reset_state(user_states, user_id)
            bot.send_message(message.chat.id, "❌ Недостаточно средств",
                             reply_markup=get_views_menu_markup())
            return

        # Обновить баланс
        db.update_balance(user_id, -price, price)

        # Создать тариф автопросмотров
        current_time = int(time.time())
        duration = 10 * 24 * 3600  # 10 days
        db.create_auto_view_tarif(user_id, tarif, link, qty, current_time, duration)

        # Создать заказ
        order_id = db.create_order(
            user_id,
            f"Автопросмотры ({tarif.upper()})",
            link,
            qty,
            price,
            hrs
        )

        reset_state(user_states, user_id)
        bot.send_message(message.chat.id, "✅ Заказ принят. Можете посмотреть статус в меню «Автопросмотры»",
                         reply_markup=get_views_menu_markup())

        # 🔴 УВЕДОМИТЬ ГРУППУ (не админа!)
        from callbacks.order_callbacks import get_status_markup
        order_details = format_order_message(order_id, f"Автопросмотры ({tarif.upper()})", qty, price, hrs, link,
                                             user_id)

        try:
            bot.send_message(GROUP_ID, order_details, reply_markup=get_status_markup(order_id))
            logger.info(f"Auto-view order #{order_id} sent to group {GROUP_ID}")
        except Exception as e:
            logger.error(f"Failed to send auto-view order to group: {e}")
            # Если группа недоступна, отправить админу
            bot.send_message(ADMIN_ID, f"⚠️ Не удалось отправить в группу:\n{order_details}",
                             reply_markup=get_status_markup(order_id))

    @bot.message_handler(
        func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "change_views_qty")
    def change_views_qty_handler(message):
        user_id = message.from_user.id
        text = message.text.strip()

        if not text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Неправильное число. Введите правильное:")
            return

        qty = int(text)
        max_v = TARIFF_VIEWS_MAP.get(user_states[user_id]["tarif"], 1000)

        if qty < 1 or qty > max_v:
            bot.send_message(message.chat.id, f"⚠️ Введите число больше 0 и меньше {max_v}")
            return

        channel_link = user_states[user_id]["channel_link"]
        db.update_auto_view_views(user_id, channel_link, qty)

        bot.send_message(message.chat.id, "✅ Изменения сохранены")
        reset_state(user_states, user_id)


def get_views_menu_markup():
    """Получить меню просмотров"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👁️ Базовый тариф", "👁️‍🗨️ Автопросмотры")
    markup.add("🔙 Назад")
    return markup