from telebot import types
import logging
from database import db
from utils import reset_state
from utils.formatters import format_admin_payment_request
from config import ADMIN_ID, GROUP_ID

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

        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_balance"))

        bot.edit_message_text("Выберите криптовалюту:", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_crypto_"))
    def select_crypto(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        crypto = call.data.replace("select_crypto_", "")

        # Сохраняем выбранную валюту
        user_states[user_id] = {"step": "entering_amount", "crypto": crypto}

        msg = bot.send_message(call.message.chat.id,
                               f"💰 <b>Введите сумму в {crypto}</b>\n\n"
                               f"⚠️ Минимальная сумма: $5.0",
                               parse_mode='HTML')

        bot.register_next_step_handler(msg, process_payment_amount, bot, user_states)

    def process_payment_amount(message, bot, user_states):
        """Обработка введённой суммы"""
        user_id = message.from_user.id
        crypto = user_states.get(user_id, {}).get("crypto", "Unknown")

        try:
            amount = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректное число")
            return

        # Проверка минимальной суммы
        if amount < 5.0:
            msg = bot.send_message(message.chat.id,
                                   f"❌ Минимальная сумма: $5.0\n"
                                   f"Вы ввели: ${amount:.2f}\n\n"
                                   f"👉 Введите число от 5$",
                                   parse_mode='HTML')
            bot.register_next_step_handler(msg, process_payment_amount, bot, user_states)
            return

        # Сохраняем сумму
        user_states[user_id]["amount"] = amount

        # Показываем кошелек
        from config import CRYPTO_ADDRESSES
        wallet_address = CRYPTO_ADDRESSES.get(crypto, "Address not found")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ Я отправил", callback_data=f"payment_sent_{crypto}"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="deposit_crypto")
        )

        message_text = (
            f"💰 <b>Выбрана криптовалюта: {crypto}</b>\n\n"
            f"📊 <b>Сумма:</b> ${amount:.2f}\n\n"
            f"📍 <b>Адрес кошелька:</b>\n"
            f"<code>{wallet_address}</code>\n\n"
            f"⚠️ <b>Инструкция:</b>\n"
            f"1️⃣ Скопируйте адрес выше\n"
            f"2️⃣ Отправьте ровно ${amount:.2f}\n"
            f"3️⃣ Нажмите кнопку ниже\n\n"
            f"⏳ Платеж обрабатывается 5-15 минут"
        )

        user_states[user_id]["step"] = "waiting_payment"

        bot.send_message(message.chat.id, message_text, reply_markup=markup, parse_mode='HTML')
        logger.info(f"User {user_id} entered amount ${amount:.2f} for {crypto}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("payment_sent_"))
    def payment_sent(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        crypto = call.data.replace("payment_sent_", "")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📸 Отправить скриншот")
        markup.add("🔙 Отмена")

        bot.send_message(call.message.chat.id,
                         "📸 <b>Отправьте скриншот транзакции</b>\n\n"
                         "Используйте кнопку скрепки 📎 для отправки фото",
                         reply_markup=markup, parse_mode='HTML')

        user_states[user_id] = {"step": "waiting_payment_proof", "crypto": crypto}
        logger.info(f"User {user_id} waiting for payment proof for {crypto}")

    # ✅ ОБРАБОТЧИК ФОТО ПРИ ПЛАТЕЖЕ
    @bot.message_handler(content_types=['photo'],
                         func=lambda message: user_states.get(message.from_user.id, {}).get(
                             "step") == "waiting_payment_proof")
    def payment_photo_handler(message):
        user_id = message.from_user.id
        username = message.from_user.username or "No username"
        photo_text = message.caption or "Скриншот платежа"
        crypto = user_states.get(user_id, {}).get("crypto", "Unknown")

        # ✅ ПОЛУЧАЕМ СУММУ ИЗ user_states
        amount = user_states.get(user_id, {}).get("amount", 0)

        # ✅ СОХРАНЯЕМ СУММУ В БД ПЕРЕД ОТПРАВКОЙ АДМИНУ
        if amount > 0:
            db.create_temp_payment(user_id, amount, crypto)
            logger.info(f"Temp payment created: user {user_id}, amount ${amount:.2f}")

        payment_header = (
            f"💳 <b>Новый платёж от пользователя</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👤 Username: @{username}\n"
            f"💰 Криптовалюта: {crypto}\n"
            f"💵 Заявленная сумма: ${amount:.2f}\n"
            f"📸 Тип: Скриншот платежа\n\n"
            f"<b>Описание:</b>\n{photo_text}"
        )

        try:
            file_id = message.photo[-1].file_id

            # ✅ ДОБАВЛЯЕМ КНОПКИ ПРИНЯТЬ/ОТКЛОНИТЬ ДЛЯ АДМИНА
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_payment_{user_id}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_payment_{user_id}")
            )

            bot.send_photo(ADMIN_ID, file_id, caption=payment_header, reply_markup=markup, parse_mode='HTML')
            logger.info(f"✅ Payment photo from user {user_id} (@{username}) sent to admin with buttons")

            bot.send_message(message.chat.id,
                             "✅ Спасибо! Ваш скриншот отправлен на проверку.\n⏳ Администратор проверит платёж в течение 15-30 минут.",
                             reply_markup=types.ReplyKeyboardRemove())
        except Exception as e:
            logger.error(f"❌ Error sending payment photo: {e}")
            bot.send_message(message.chat.id, f"❌ Ошибка отправки: {e}")

        from handlers.user_handlers import get_main_menu
        import time
        time.sleep(1)
        bot.send_message(message.chat.id, "📋 Главное меню:", reply_markup=get_main_menu())
        reset_state(user_states, user_id)

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

        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return

        target_user_id = int(call.data.replace("accept_payment_", ""))

        # ✅ ЗАПРАШИВАЕМ У АДМИНА СУММУ
        msg = bot.send_message(call.message.chat.id,
                               f"👤 Пользователь: {target_user_id}\n\n"
                               f"Введите сумму для пополнения (например: 10.5):")

        user_states[call.from_user.id] = {"target_user_id": target_user_id, "step": "entering_accept_amount"}
        bot.register_next_step_handler(msg, process_accept_amount, bot, user_states)

    def process_accept_amount(message, bot, user_states):
        """Обработка суммы пополнения от админа"""
        admin_id = message.from_user.id

        try:
            amount = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму (например: 10.5)")
            return

        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть больше 0")
            return

        target_user_id = user_states.get(admin_id, {}).get("target_user_id")

        if not target_user_id:
            bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден")
            return

        # ✅ ПОПОЛНЯЕМ БАЛАНС
        db.update_balance(target_user_id, amount, 0)
        new_balance = db.get_user_balance(target_user_id)

        # ✅ УДАЛЯЕМ ВРЕМЕННЫЙ ПЛАТЕЖ
        db.delete_temp_payment(target_user_id)

        # ✅ УВЕДОМЛЯЕМ ПОЛЬЗОВАТЕЛЯ
        bot.send_message(target_user_id,
                         f"💳 Ваш счёт пополнен на ${amount:.2f}\n"
                         f"💰 Новый баланс: ${new_balance:.2f}",
                         parse_mode='HTML')

        # ✅ ПОДТВЕРЖДЕНИЕ АДМИНУ
        bot.send_message(message.chat.id,
                         f"✅ <b>ПЛАТЕЖ ПРИНЯТ</b>\n\n"
                         f"👤 Пользователь: {target_user_id}\n"
                         f"💵 Пополнено: ${amount:.2f}\n"
                         f"💰 Новый баланс: ${new_balance:.2f}",
                         parse_mode='HTML')

        logger.info(f"✅ Admin {admin_id} accepted payment of ${amount:.2f} for user {target_user_id}")
        reset_state(user_states, admin_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_payment_"))
    def reject_payment(call):
        bot.answer_callback_query(call.id)

        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return

        target_user_id = int(call.data.replace("reject_payment_", ""))

        db.delete_temp_payment(target_user_id)

        # ✅ УВЕДОМЛЯЕМ ПОЛЬЗОВАТЕЛЯ
        bot.send_message(target_user_id,
                         "❌ Ваш платеж отклонен.\nПожалуйста, обратите внимание на минимальную сумму или адрес.")

        # ✅ ОБНОВЛЯЕМ СООБЩЕНИЕ АДМИНА
        bot.edit_message_text(call.message.text + "\n\n❌ Отклонено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)
        logger.info(f"❌ Payment rejected for user {target_user_id}")