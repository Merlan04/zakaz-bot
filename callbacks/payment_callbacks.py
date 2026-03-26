from telebot import types
import logging
from database import db
from utils.formatters import format_admin_payment_request
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def register_payment_callbacks(bot, user_states):
    """Регистрировать callbacks платежей"""

    @bot.callback_query_handler(func=lambda call: call.data == "deposit_crypto")
    def deposit_crypto_menu(call):
        bot.answer_callback_query(call.id)

        from config import CRYPTO_ADDRESSES
        markup = types.InlineKeyboardMarkup(row_width=2)

        for crypto in CRYPTO_ADDRESSES.keys():
            markup.add(types.InlineKeyboardButton(crypto, callback_data=f"select_crypto_{crypto}"))

        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_balance"))

        bot.edit_message_text("Выберите криптовалюту:", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_crypto_"))
    def select_crypto(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        crypto = call.data.replace("select_crypto_", "")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(crypto)
        markup.add("🔚 Домой")

        user_states[user_id] = {"step": "deposit_crypto"}

        bot.send_message(call.message.chat.id,
                         f"✅ Выбрана криптовалюта: {crypto}\n\n👉 Подтвердите выбор нажатием кнопки ниже:",
                         reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_balance")
    def back_to_balance(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        balance = db.get_user_balance(user_id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Криптовалюты", callback_data="deposit_crypto"),
            types.InlineKeyboardButton("📜 История", callback_data="history")
        )

        bot.edit_message_text(f"💳 Ваш баланс: {balance:.2f}$\n\nВыберите способ пополнения баланса:",
                              call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("accept_payment_"))
    def accept_payment(call):
        bot.answer_callback_query(call.id)

        # Только админ может принять платеж
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return

        target_user_id = int(call.data.replace("accept_payment_", ""))
        amount = db.get_temp_payment(target_user_id)

        if amount > 0:
            db.update_balance(target_user_id, amount, 0)
            db.delete_temp_payment(target_user_id)

            bot.send_message(target_user_id, f"💳 Ваш счёт пополнен на {amount}$")
            bot.edit_message_text(call.message.text + "\n\n✅ Принято",
                                  call.message.chat.id, call.message.message_id, reply_markup=None)
            logger.info(f"Payment of {amount}$ accepted for user {target_user_id}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_payment_"))
    def reject_payment(call):
        bot.answer_callback_query(call.id)

        # Только админ может отклонить платеж
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return

        target_user_id = int(call.data.replace("reject_payment_", ""))

        db.delete_temp_payment(target_user_id)
        bot.send_message(target_user_id,
                         "❌ Ваш платеж отклонен.\nПожалуйста, обратите внимание на минимальную сумму или адрес.")

        bot.edit_message_text(call.message.text + "\n\n❌ Отклонено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)
        logger.info(f"Payment rejected for user {target_user_id}")