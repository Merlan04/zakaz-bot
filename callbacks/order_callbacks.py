from telebot import types
import logging
from database import db
from utils import format_order_details
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def register_order_callbacks(bot, user_states):
    """Регистрировать callbacks заказов"""

    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_tarif_"))
    def buy_tarif(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        tarif = call.data.replace("buy_tarif_", "")

        price = db.get_tarif_price(tarif)
        balance = db.get_user_balance(user_id)

        if price <= 0:
            bot.send_message(user_id, "⚠️ Такой тариф не найден.")
            return

        if balance < price:
            bot.send_message(user_id, "⚠️ Необходимо пополнить баланс для покупки тарифа.")
            return

        bot.send_message(user_id,
                         "👉 Введите ссылку на канал, чтобы подключить функцию автоматического просмотра к каналу для этого тарифного плана:")

        user_states[user_id] = {"step": "auto_view_link", "tarif": tarif, "price": price}

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_auto_"))
    def edit_auto_views(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        channel_link = call.data.replace("edit_auto_", "")

        import time
        current_time = int(time.time())
        active = db.get_active_view_tarifs(user_id, current_time)

        for tar, end_ts, link, views in active:
            if link == channel_link:
                from config import TARIFF_VIEWS_MAP
                max_v = TARIFF_VIEWS_MAP.get(tar, 1000)

                bot.send_message(user_id,
                                 f"🌀 Ваш тариф позволяет делать до {max_v} просмотров на каждый пост.\n\n👉 Введите желаемое количество просмотров:")

                user_states[user_id] = {"step": "change_views_qty", "channel_link": channel_link, "tarif": tar}
                return

    @bot.callback_query_handler(func=lambda call: call.data.startswith("prolong_auto_"))
    def prolong_auto_views(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        channel_link = call.data.replace("prolong_auto_", "")

        import time
        current_time = int(time.time())
        active = db.get_active_view_tarifs(user_id, current_time)

        for tar, end_ts, link, views in active:
            if link == channel_link:
                user_states[user_id] = {"step": "prolong_confirm", "channel_link": channel_link, "tarif": tar}

                txt = (
                    "Внимание! После нажатия кнопки «✅ подтвердить» вы приобретете дополнительный тариф в дополнение к вашему основному тарифу. "
                    "Например: до окончания действия вашего тарифа осталось 2 дня, и вы нажали кнопку «✅ подтвердить», "
                    "до окончания действия вашего тарифа осталось 12 дней, и стоимость тарифа будет списана с вашего счета."
                )

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_prolong_{channel_link}"))
                markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_prolong"))

                bot.send_message(user_id, txt, reply_markup=markup)
                return

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_prolong_"))
    def confirm_prolong(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        channel_link = call.data.replace("confirm_prolong_", "")

        price = 1.0  # 0.1$ * 10 days
        balance = db.get_user_balance(user_id)

        if balance < price:
            bot.send_message(user_id, "⚠️ Недостаточно средств для продления.")
            return

        db.update_balance(user_id, -price, price)
        db.prolong_auto_view(user_id, channel_link, prolong_days=10)

        bot.send_message(user_id, "✅ Автопросмотры продлены на 10 д")
        user_states.pop(user_id, None)

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_prolong")
    def cancel_prolong(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ Продление отменено.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("cancel_", "progress_", "done_")))
    def update_order_status(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        if user_id != ADMIN_ID:
            return

        parts = call.data.split("_")
        action = parts[0]
        order_id = int(parts[1])

        status_map = {"cancel": "Отменено", "progress": "В процессе", "done": "Выполнено"}
        new_status = status_map.get(action)

        if not new_status:
            return

        order_info = db.get_order(order_id)
        if not order_info:
            return

        if new_status == "Отменено" and order_info[4] != "Отменено":
            order_price = order_info[2]
            bot.send_message(ADMIN_ID, f"Заказ #{order_id} bekor qilindi.\nQancha pul qaytarish kerak? (masalan 1.3)")
            user_states[ADMIN_ID] = {
                "step": "cancel_refund",
                "order_id": order_id,
                "user_id": order_info[0],
                "price": order_price
            }
            return

        db.update_order_status(order_id, new_status)

        try:
            bot.edit_message_text(
                call.message.text + f"\n\n✅ Статус изменён на: {new_status}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_back_markup(order_id)
            )
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.data.startswith("back_order_"))
    def back_order(call):
        bot.answer_callback_query(call.id)
        order_id = int(call.data.split("_")[2])
        order_info = db.get_order(order_id)

        if order_info:
            text = format_order_details(order_info)
            if text:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                      reply_markup=get_status_markup(order_id))


def get_status_markup(order_id):
    """Получить markup для изменения статуса заказа"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}"),
        types.InlineKeyboardButton("⏳ В процессе", callback_data=f"progress_{order_id}"),
        types.InlineKeyboardButton("✅ Выполнено", callback_data=f"done_{order_id}")
    )
    return markup


def get_back_markup(order_id):
    """Получить markup для возврата к заказу"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_order_{order_id}"))
    return markup