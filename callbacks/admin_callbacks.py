from telebot import types
import logging
from database import db
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def register_admin_callbacks(bot, user_states):
    """Регистрировать callbacks админа"""

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_prices")
    def admin_prices(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("👥 Подписчики sozlamalari", callback_data="set_subs"))
        markup.add(types.InlineKeyboardButton("👀 Просмотры tariflari", callback_data="set_views"))
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back"))

        bot.edit_message_text("🛠 Xizmatlar sozlamalari", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "set_subs")
    def set_subs_settings(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(f"1000 uchun narx: {db.get_setting('subs_price')}$",
                                              callback_data="edit_subs_price"))
        markup.add(types.InlineKeyboardButton(f"Min. soni: {int(db.get_setting('subs_min_qty'))}",
                                              callback_data="edit_subs_min_qty"))
        markup.add(types.InlineKeyboardButton(f"Maks. soni: {int(db.get_setting('subs_max_qty'))}",
                                              callback_data="edit_subs_max_qty"))
        markup.add(types.InlineKeyboardButton(f"Min. soat: {int(db.get_setting('subs_min_hrs'))}",
                                              callback_data="edit_subs_min_hrs"))
        markup.add(types.InlineKeyboardButton(f"Maks. soat: {int(db.get_setting('subs_max_hrs'))}",
                                              callback_data="edit_subs_max_hrs"))
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="admin_prices"))

        bot.edit_message_text("⚙ Подписчики sozlamalari", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "set_views")
    def set_views_settings(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        for t, price in db.get_view_tarifs():
            markup.add(types.InlineKeyboardButton(f"👁️{t.upper()} - {price}$",
                                                  callback_data=f"edit_tarif_{t}"))
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="admin_prices"))

        bot.edit_message_text("⚙ Просмотры tariflari", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("edit_subs_"))
    def admin_edit_subs_setting(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        key = call.data.replace("edit_", "")

        msg = bot.send_message(call.message.chat.id, f"{key} uchun yangi qiymatni kiriting:")
        user_states[user_id] = {"step": "edit_setting", "setting_key": key}
        bot.register_next_step_handler(msg, lambda m: None)  # Обработчик в admin_handlers.py

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("edit_tarif_"))
    def admin_edit_tarif_price(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        tarif_type = call.data.replace("edit_tarif_", "")

        msg = bot.send_message(call.message.chat.id, f"{tarif_type.upper()} tarifi uchun yangi narxni kiriting:")
        user_states[user_id] = {"step": "edit_tarif_price", "tarif_type": tarif_type}
        bot.register_next_step_handler(msg, lambda m: None)  # Обработчик в admin_handlers.py

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_back")
    def admin_back(call):
        bot.answer_callback_query(call.id)
        bot.edit_message_text("Admin paneli", call.message.chat.id, call.message.message_id,
                              reply_markup=get_admin_menu())

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_users")
    def admin_users(call):
        bot.answer_callback_query(call.id)
        users = db.get_users_list(limit=50)

        txt = "👥 Foydalanuvchilar:\n"
        for u in users:
            txt += f"{u[0]} | @{u[1] or '—'} | {u[2]}$\n"

        bot.send_message(call.message.chat.id, txt)

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_manualpay")
    def admin_manualpay(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        msg = bot.send_message(call.message.chat.id, "👤 Foydalanuvchi Telegram ID sini kiriting:")
        user_states[user_id] = {"step": "manual_pay_id"}
        bot.register_next_step_handler(msg, lambda m: None)  # Обработчик в admin_handlers.py

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data in
                                                  ["admin_balance", "admin_orders", "admin_stats", "admin_broadcast",
                                                   "admin_edit_texts"])
    def admin_coming_soon(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔧 Bu bo'lim hozircha ishlab chiqilmoqda.")


def get_admin_menu():
    """Получить админ меню"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        ("👥 Foydalanuvchilar", "admin_users"),
        ("💰 Balanslar", "admin_balance"),
        ("💸 Ручной платеж", "admin_manualpay"),
        ("⚙ Narx sozlamalari", "admin_prices"),
        ("📦 Buyurtmalar", "admin_orders"),
        ("📊 Statistika", "admin_stats"),
        ("✉ Рассылка", "admin_broadcast"),
        ("📝 Matnlar tahriri", "admin_edit_texts")
    ]
    for text, data in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=data))
    return markup