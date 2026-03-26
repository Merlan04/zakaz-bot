from telebot import types
import logging
from database import db
from utils import reset_state
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def register_admin_handlers(bot, user_states):
    """Регистрировать обработчики админа"""

    @bot.message_handler(
        func=lambda message: message.from_user.id == ADMIN_ID and user_states.get(message.from_user.id, {}).get(
            "step") == "edit_setting")
    def admin_edit_setting(message):
        user_id = message.from_user.id
        text = message.text.strip()
        key = user_states[user_id].get("setting_key")

        try:
            value = float(text) if 'price' in key else int(text)
            db.set_setting(key, value)
            bot.send_message(message.chat.id, f"✅ {key} обновлено: {value}")
            reset_state(user_states, user_id)
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            bot.send_message(message.chat.id, "❌ Неверное значение!")

    @bot.message_handler(
        func=lambda message: message.from_user.id == ADMIN_ID and user_states.get(message.from_user.id, {}).get(
            "step") == "edit_tarif_price")
    def admin_edit_tarif_price(message):
        user_id = message.from_user.id
        text = message.text.strip()
        tarif_type = user_states[user_id].get("tarif_type")

        try:
            price = float(text)
            db.update_tarif_price(tarif_type, price)
            bot.send_message(message.chat.id, f"✅ {tarif_type.upper()} tarifi {price}$ ga o'zgartirildi")
            reset_state(user_states, user_id)
        except Exception as e:
            logger.error(f"Error updating tarif price: {e}")
            bot.send_message(message.chat.id, "❌ Faqat son kiriting!")

    @bot.message_handler(
        func=lambda message: message.from_user.id == ADMIN_ID and user_states.get(message.from_user.id, {}).get(
            "step") == "manual_pay_id")
    def admin_manual_pay_id(message):
        user_id = message.from_user.id
        text = message.text.strip()

        try:
            target_user_id = int(text)
            msg = bot.send_message(message.chat.id,
                                   f"💰 ID: {target_user_id}\n\nQancha o'zgartirish kerak?\n(+100 - qo'shish, -50 - ayirish, 0 - tekshirish)")
            bot.register_next_step_handler(msg, admin_manual_pay_amount, bot, user_states, target_user_id)
        except Exception as e:
            logger.error(f"Error in manual pay: {e}")
            bot.send_message(message.chat.id, "❌ Noto'g'ri ID!")

    def admin_manual_pay_amount(message, bot, user_states, target_user_id):
        user_id = message.from_user.id
        text = message.text.strip()

        try:
            amount = float(text)

            if amount == 0:
                balance = db.get_user_balance(target_user_id)
                bot.send_message(message.chat.id, f"✅ {target_user_id} ning balans: {balance:.2f}$")
            else:
                db.update_balance(target_user_id, amount, 0)
                new_balance = db.get_user_balance(target_user_id)
                bot.send_message(message.chat.id,
                                 f"✅ {target_user_id} hisobi {amount}$ ga o'zgartirildi!\nYangi balans: {new_balance:.2f}$")

                try:
                    bot.send_message(target_user_id,
                                     f"💰 Admin sizning balansingizni o'zgartirdi!\nO'zgarish: {amount}$\nYangi balans: {new_balance:.2f}$")
                except:
                    pass

            reset_state(user_states, user_id)
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            bot.send_message(message.chat.id, "❌ Noto'g'ri summa!")

    @bot.message_handler(
        func=lambda message: message.from_user.id == ADMIN_ID and user_states.get(message.from_user.id, {}).get(
            "step") == "cancel_refund")
    def admin_cancel_refund(message):
        user_id = message.from_user.id
        text = message.text.strip()

        try:
            refund_amount = float(text)
            order_id = user_states[user_id].get("order_id")
            target_user_id = user_states[user_id].get("user_id")

            # Вернуть деньги
            db.update_balance(target_user_id, refund_amount, 0)
            db.update_order_status(order_id, "Отменено")

            bot.send_message(message.chat.id, f"✅ Заказ #{order_id} отменен. {refund_amount}$ возвращено пользователю.")
            bot.send_message(target_user_id,
                             f"❌ Ваш заказ #{order_id} был отменен. {refund_amount}$ возвращено на ваш счет.")

            reset_state(user_states, user_id)
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            bot.send_message(message.chat.id, "❌ Неверная сумма!")