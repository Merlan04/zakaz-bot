from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state
from time import time
import re

logger = logging.getLogger(__name__)


def register_auto_views_handlers(bot, user_states):
    """Регистрировать обработчики автопросмотров"""

    # ================ МЕНЮ АВТОПРОСМОТРОВ ================
    @bot.callback_query_handler(func=lambda call: call.data == "order_auto_views")
    def auto_views_menu(call):
        """Меню автопросмотров"""
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        reset_state(user_states, user_id)

        balance = db.get_user_balance(user_id)  # ✅ ПРОВЕРЯЕМ БАЛАНС

        if balance <= 0:  # ✅ ЕСЛИ БАЛАНС = 0
            auto_views_message = (
                "👁️‍🗨️ <b>АВТОПРОСМОТРЫ</b>\n\n"
                "У вас пока нет автоматического тарифа.\n"
                "Приобретите через базовый тариф."
            )

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="order_views"))

            bot.send_message(call.message.chat.id, auto_views_message, reply_markup=markup, parse_mode='HTML')
            logger.info(f"User {user_id} tried to access auto_views without balance")

        else:  # ✅ ЕСЛИ БАЛАНС > 0 (добавим позже)
            pass


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


def start_auto_renew_task(bot):
    """Фоновый таск для автопродления"""
    import threading

    def auto_renew_check():
        while True:
            try:
                current_time = int(time())
                expiring = db.get_expiring_auto_view_tarifs(current_time)

                for user_id, tarif_id, tarif_type, channel_name, end_ts in expiring:
                    if not db.get_user_setting(user_id, "auto_renew", True):
                        continue

                    cost = 1.0  # Стоимость продления
                    balance = db.get_user_balance(user_id)

                    if balance < cost:
                        if db.get_user_setting(user_id, "notifications", True):
                            max_views = get_max_views_for_tarif(tarif_type)
                            bot.send_message(user_id,
                                             f"⚠️ Недостаточно средств\n"
                                             f"👁 Тариф «{max_views:,} просмотров»",
                                             parse_mode='HTML')
                    else:
                        db.update_balance(user_id, -cost, cost)
                        db.prolong_auto_view_new(tarif_id, 30)
                        logger.info(f"Auto-renewed tarif {tarif_id}")

                import time as time_module
                time_module.sleep(3600)
            except Exception as e:
                logger.error(f"Auto-renew error: {e}")
                import time as time_module
                time_module.sleep(3600)

    thread = threading.Thread(target=auto_renew_check, daemon=True)
    thread.start()