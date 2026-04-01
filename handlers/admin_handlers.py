from telebot import types
import logging
from database import db
from config import ADMIN_ID

logger = logging.getLogger(__name__)


def register_admin_handlers(bot, user_states):
    """Регистрировать обработчики админа"""

    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        """Главное меню админ-панели"""
        if message.from_user.id != ADMIN_ID:
            bot.send_message(message.chat.id, "❌ Доступ запрещен")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("💰 Ручной платеж", callback_data="manual_payment"),
            types.InlineKeyboardButton("📦 Buyurtmalar", callback_data="admin_buyurtmalar"),
            types.InlineKeyboardButton("📋 Заказы", callback_data="admin_view_orders"),
            types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast_menu"),
            types.InlineKeyboardButton("👥 Баланс", callback_data="admin_balance_menu")
        )

        bot.send_message(message.chat.id, "⚙️ **АДМИН-ПАНЕЛЬ**", reply_markup=markup, parse_mode='Markdown')

    @bot.message_handler(regexp=r'^/edit_order_(\d+)$')
    def edit_order(message):
        """Редактировать статус заказа"""
        if message.from_user.id != ADMIN_ID:
            return

        order_id = int(message.text.split('_')[2])
        order = db.get_order(order_id)

        if not order:
            bot.send_message(message.chat.id, "❌ Заказ не найден")
            return

        service_type, quantity, price, hours, status = order

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⏳ В ожидании", callback_data=f"set_order_status_{order_id}_В ожидании"),
            types.InlineKeyboardButton("🔄 В процессе", callback_data=f"set_order_status_{order_id}_В процессе"),
            types.InlineKeyboardButton("✅ Завершен", callback_data=f"set_order_status_{order_id}_Завершен"),
            types.InlineKeyboardButton("❌ Отменен", callback_data=f"set_order_status_{order_id}_Отменен")
        )

        text = (f"📋 **ЗАКАЗ #{order_id}**\n\n"
                f"Услуга: {service_type}\n"
                f"Кол-во: {quantity}\n"
                f"Цена: ${price:.2f}\n"
                f"Текущий статус: {status}\n\n"
                f"Выберите новый статус:")

        bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_order_status_"))
    def set_order_status(call):
        bot.answer_callback_query(call.id)
        parts = call.data.split('_')
        order_id = int(parts[3])
        new_status = '_'.join(parts[4:])

        db.update_order_status(order_id, new_status)
        bot.send_message(call.message.chat.id, f"✅ Статус заказа #{order_id} изменен на: {new_status}")

    @bot.message_handler(regexp=r'^/user_info_(\d+)$')
    def user_info_cmd(message):
        """Информация о пользователе"""
        if message.from_user.id != ADMIN_ID:
            return

        target_user_id = int(message.text.split('_')[2])
        user_info = db.get_user_info(target_user_id)

        if user_info:
            text = (f"👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n\n"
                    f"ID: {user_info['user_id']}\n"
                    f"Username: @{user_info['username'] or 'N/A'}\n"
                    f"💰 Баланс: ${user_info['balance']:.2f}\n"
                    f"💵 Всего потрачено: ${user_info['total_spent']:.2f}\n"
                    f"📦 Заказов: {user_info['orders_count']}")

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💵 Изменить баланс",
                                                  callback_data=f"change_balance_{target_user_id}"))

            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("change_balance_"))
    def change_balance(call):
        bot.answer_callback_query(call.id)
        target_user_id = int(call.data.replace("change_balance_", ""))
        msg = bot.send_message(call.message.chat.id,
                               f"Введите сумму для пользователя {target_user_id}:\n(+100 - добавить, -50 - вычесть)")
        bot.register_next_step_handler(msg, process_change_balance, bot, user_states, target_user_id)

    def process_change_balance(message, bot, user_states, target_user_id):
        user_id = message.from_user.id
        try:
            amount = float(message.text.strip())
            db.update_balance(target_user_id, amount, 0)
            new_balance = db.get_user_balance(target_user_id)

            bot.send_message(user_id,
                             f"✅ Баланс пользователя {target_user_id} изменен на ${amount:+.2f}\n"
                             f"Новый баланс: ${new_balance:.2f}")

            try:
                bot.send_message(target_user_id,
                                 f"💰 Администратор изменил ваш баланс на ${amount:+.2f}\n"
                                 f"Новый баланс: ${new_balance:.2f}")
            except:
                pass
        except:
            bot.send_message(user_id, "❌ Ошибка!")