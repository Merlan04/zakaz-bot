from telebot import types
import logging
from database import db
from config import ADMIN_ID
from utils import reset_state
from time import time

logger = logging.getLogger(__name__)


def register_admin_callbacks(bot, user_states):
    """Регистрировать callbacks админа"""

    # ================ АДМИН ПАНЕЛЬ ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_menu")
    def admin_menu(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("💰 Ручной платеж", callback_data="manual_payment"),
            types.InlineKeyboardButton("📦 Buyurtmalar", callback_data="admin_buyurtmalar"),
            types.InlineKeyboardButton("📋 Заказы", callback_data="admin_view_orders"),
            types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast_menu"),
            types.InlineKeyboardButton("👥 Баланс", callback_data="admin_balance_menu")
        )

        bot.edit_message_text("⚙️ **АДМИН-ПАНЕЛЬ**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    # ================ ОТВЕТ НА ВОПРОС ПОЛЬЗОВАТЕЛЯ ================
    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reply_question_"))
    def admin_reply_question(call):
        """Ответить на вопрос пользователя"""
        bot.answer_callback_query(call.id)

        try:
            parts = call.data.split("_")
            user_id = int(parts[3])
            order_id = int(parts[4])
        except (ValueError, IndexError):
            bot.send_message(call.message.chat.id,
                             "❌ <b>ОШИБКА</b>\n\n"
                             "Не удалось распарсить данные",
                             parse_mode='HTML')
            return

        msg = bot.send_message(call.message.chat.id,
                               f"📝 <b>ОТВЕТИТЬ ПОЛЬЗОВАТЕЛЮ</b>\n\n"
                               f"👤 ID пользователя: <code>{user_id}</code>\n"
                               f"🆔 ID заказа: <code>{order_id}</code>\n\n"
                               f"Напишите ваш ответ:",
                               parse_mode='HTML')

        bot.register_next_step_handler(msg, process_admin_reply, bot, user_states, user_id, order_id)

    def process_admin_reply(message, bot, user_states, user_id, order_id):
        """Обработка ответа администратора"""
        admin_id = message.from_user.id
        reply_text = message.text

        # Отправляем ответ пользователю
        user_message = (
            f"💬 <b>ОТВЕТ ОТ АДМИНИСТРАТОРА</b>\n\n"
            f"🆔 Заказ: #{order_id}\n\n"
            f"<b>Ответ:</b>\n{reply_text}"
        )

        try:
            bot.send_message(user_id, user_message, parse_mode='HTML')
            logger.info(f"✅ Reply from admin {admin_id} sent to user {user_id}")

            # Подтверждение администратору
            bot.send_message(admin_id,
                             f"✅ <b>ОТВЕТ ОТПРАВЛЕН</b>\n\n"
                             f"👤 Пользователю: {user_id}\n"
                             f"🆔 Заказ: #{order_id}\n\n"
                             f"Ваш ответ успешно доставлен",
                             parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error sending reply to user {user_id}: {e}")
            bot.send_message(admin_id,
                             f"❌ <b>ОШИБКА</b>\n\n"
                             f"Не удалось отправить ответ пользователю {user_id}\n\n"
                             f"Ошибка: {str(e)}",
                             parse_mode='HTML')

    # ================ СТАТИСТИКА ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_stats")
    def admin_stats_menu(call):
        bot.answer_callback_query(call.id)

        users_count = len(db.get_users_list(limit=10000))
        total_earned = db.get_total_earned()
        total_orders = db.get_total_orders()

        text = (f"📊 **СТАТИСТИКА**\n\n"
                f"👥 Всего пользователей: {users_count}\n"
                f"💰 Всего заработано: ${total_earned:.2f}\n"
                f"📦 Всего заказов: {total_orders}")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🏆 Топ пользователей", callback_data="stat_top_users"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
        )

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "stat_top_users")
    def stat_top_users(call):
        bot.answer_callback_query(call.id)
        users = db.get_users_list(limit=10000)
        top_users = sorted(users, key=lambda x: float(x[2]), reverse=True)[:10]

        text = "🏆 **ТОП 10 ПОЛЬЗОВАТЕЛЕЙ**\n\n"
        for i, (user_id, username, balance) in enumerate(top_users, 1):
            username_str = username or "N/A"
            text += f"{i}. @{username_str} (ID: {user_id})\n   💰 Потрачено: ${float(balance):.2f}\n\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_stats"))

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    # ================ РУЧНОЙ ПЛАТЕЖ ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "manual_payment")
    def manual_payment(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя для изменения баланса:")
        bot.register_next_step_handler(msg, process_manual_payment_user, bot, user_states)

    def process_manual_payment_user(message, bot, user_states):
        user_id = message.from_user.id
        try:
            target_user_id = int(message.text.strip())
            balance = db.get_user_balance(target_user_id)
            user_states[user_id] = {'target_user_id': target_user_id}

            text = (f"💰 **ИЗМЕНЕНИЕ БАЛАНСА**\n\n"
                    f"Пользователь: {target_user_id}\n"
                    f"Текущий баланс: ${balance:.2f}\n\n"
                    f"Введите сумму:\n"
                    f"(+100 - добавить 100, -50 - вычесть 50)")

            msg = bot.send_message(message.chat.id, text, parse_mode='Markdown')
            bot.register_next_step_handler(msg, process_manual_payment_amount, bot, user_states)
        except:
            bot.send_message(message.chat.id, "❌ Неверный ID!")

    def process_manual_payment_amount(message, bot, user_states):
        user_id = message.from_user.id
        try:
            amount = float(message.text.strip())
            target_user_id = user_states.get(user_id, {}).get('target_user_id')

            db.update_balance(target_user_id, amount, 0)
            new_balance = db.get_user_balance(target_user_id)

            text = (f"✅ **БАЛАНС ИЗМЕНЕН**\n\n"
                    f"Пользователь: {target_user_id}\n"
                    f"Изменение: ${amount:+.2f}\n"
                    f"Новый баланс: ${new_balance:.2f}")

            bot.send_message(message.chat.id, text, parse_mode='Markdown')

            try:
                bot.send_message(target_user_id,
                                 f"💰 Администратор изменил ваш баланс на ${amount:+.2f}\n"
                                 f"Новый баланс: ${new_balance:.2f}")
            except:
                pass
        except:
            bot.send_message(message.chat.id, "❌ Неверная сумма!")

    # ================ BUYURTMALAR ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_buyurtmalar")
    def admin_buyurtmalar(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📊 Все подписчики", callback_data="view_all_subs_orders"),
            types.InlineKeyboardButton("⚙️ Условия заказов", callback_data="orders_conditions"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
        )

        bot.edit_message_text("📦 **BUYURTMALAR**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "view_all_subs_orders")
    def view_all_subs_orders(call):
        bot.answer_callback_query(call.id)

        subs_price = db.get_setting('subs_price')
        subs_min = int(db.get_setting('subs_min_qty'))
        subs_max = int(db.get_setting('subs_max_qty'))
        subs_min_hrs = int(db.get_setting('subs_min_hrs'))
        subs_max_hrs = int(db.get_setting('subs_max_hrs'))

        text = (f"📊 **ПОДПИСЧИКИ**\n\n"
                f"💵 Цена: ${subs_price:.2f}\n"
                f"📉 Минимум: {subs_min}\n"
                f"📈 Максимум: {subs_max}\n"
                f"⏱ Мин. часов: {subs_min_hrs}\n"
                f"⏱ Макс. часов: {subs_max_hrs}\n\n")

        tarifs = db.get_view_tarifs()
        text += "📈 **ТАРИФЫ ПРОСМОТРОВ**\n\n"
        for tarif_type, price in tarifs:
            text += f"• {tarif_type.upper()}: ${price:.2f}\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_buyurtmalar"))

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "orders_conditions")
    def orders_conditions(call):
        bot.answer_callback_query(call.id)

        text = "⚙️ **УСЛОВИЯ ЗАКАЗОВ**\n\nВыберите что изменить:"

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ Цена подписчиков", callback_data="edit_subs_price_cond"),
            types.InlineKeyboardButton("✏️ Мин. подписчиков", callback_data="edit_subs_min_qty_cond"),
            types.InlineKeyboardButton("✏️ Макс. подписчиков", callback_data="edit_subs_max_qty_cond"),
            types.InlineKeyboardButton("✏️ Мин. часов", callback_data="edit_subs_min_hrs_cond"),
            types.InlineKeyboardButton("✏️ Макс. часов", callback_data="edit_subs_max_hrs_cond"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="admin_buyurtmalar")
        )

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("edit_") and call.data.endswith(
            "_cond"))
    def edit_condition(call):
        bot.answer_callback_query(call.id)
        setting_name = call.data.replace("edit_", "").replace("_cond", "")
        current_value = db.get_setting(setting_name)

        msg = bot.send_message(call.message.chat.id,
                               f"Введите новое значение для {setting_name}:\nТекущее значение: {current_value}")
        bot.register_next_step_handler(msg, process_edit_condition, bot, user_states, setting_name)

    def process_edit_condition(message, bot, user_states, setting_name):
        user_id = message.from_user.id
        try:
            value = float(message.text.strip())
            db.set_setting(setting_name, value)
            bot.send_message(message.chat.id, f"✅ {setting_name} обновлено на: {value}")
        except:
            bot.send_message(message.chat.id, "❌ Неверное значение!")

    # ================ ЗАКАЗЫ ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_view_orders")
    def admin_view_orders(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📊 Подписчики и тарифы", callback_data="view_subs_orders"),
            types.InlineKeyboardButton("⚙️ Условия", callback_data="view_orders_conditions"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
        )

        bot.edit_message_text("📋 **ЗАКАЗЫ**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "view_subs_orders")
    def view_subs_orders(call):
        bot.answer_callback_query(call.id)
        orders = db.get_all_orders(limit=20)

        if not orders:
            bot.send_message(call.message.chat.id, "❌ Заказов нет")
            return

        text = "📊 **ЗАКАЗЫ ПОДПИСЧИКОВ**\n\n"
        for order_id, user_id, service_type, qty, price, status, date in orders[:15]:
            text += f"#{order_id} | Пользователь: {user_id}\n"
            text += f"Услуга: {service_type}\n"
            text += f"Кол-во: {qty} | Цена: ${price:.2f}\n"
            text += f"Статус: {status} | Дата: {date}\n"
            text += f"---\n"

        text += "\n📈 **ДОСТУПНЫЕ ТАРИФЫ**\n\n"
        tarifs = db.get_view_tarifs()
        for tarif_type, tarif_price in tarifs:
            text += f"• {tarif_type.upper()}: ${tarif_price:.2f}\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_view_orders"))

        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data == "view_orders_conditions")
    def view_orders_conditions(call):
        bot.answer_callback_query(call.id)
        orders = db.get_all_orders(limit=50)

        if not orders:
            bot.send_message(call.message.chat.id, "❌ Заказов нет")
            return

        text = "⚙️ **ЗАКАЗЫ И СТАТУСЫ**\n\n"
        for order_id, user_id, service_type, qty, price, status, date in orders[:10]:
            text += f"#{order_id}\n"
            text += f"Пользователь: {user_id}\n"
            text += f"Услуга: {service_type}\n"
            text += f"Статус: {status}\n"
            text += f"/edit_order_{order_id}\n"
            text += f"---\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_view_orders"))

        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    # ================ РАССЫЛКА ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_broadcast_menu")
    def admin_broadcast_menu(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📢 Для всех клиентов", callback_data="broadcast_all"),
            types.InlineKeyboardButton("👤 Для конкретного клиента", callback_data="broadcast_user"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
        )

        bot.edit_message_text("📢 **РАССЫЛКА**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "broadcast_all")
    def broadcast_all(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введите сообщение для рассылки всем пользователям:")
        bot.register_next_step_handler(msg, process_broadcast_all, bot, user_states)

    def process_broadcast_all(message, bot, user_states):
        user_id = message.from_user.id
        broadcast_text = message.text
        users = db.get_users_list(limit=10000)

        success = 0
        failed = 0

        for user_id_target, _, _ in users:
            try:
                bot.send_message(user_id_target, f"📢 **ОБЪЯВЛЕНИЕ**\n\n{broadcast_text}", parse_mode='Markdown')
                success += 1
            except:
                failed += 1

        result_text = (f"✅ **РАССЫЛКА ЗАВЕРШЕНА**\n\n"
                       f"✅ Доставлено: {success}\n"
                       f"❌ Ошибок: {failed}")
        bot.send_message(user_id, result_text, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "broadcast_user")
    def broadcast_user(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя для рассылки:")
        bot.register_next_step_handler(msg, process_broadcast_user_id, bot, user_states)

    def process_broadcast_user_id(message, bot, user_states):
        user_id = message.from_user.id
        try:
            target_user_id = int(message.text.strip())
            user_states[user_id] = {'broadcast_target': target_user_id}
            msg = bot.send_message(message.chat.id, "Введите сообщение для отправки:")
            bot.register_next_step_handler(msg, process_broadcast_user_message, bot, user_states)
        except:
            bot.send_message(message.chat.id, "❌ Неверный ID!")

    def process_broadcast_user_message(message, bot, user_states):
        user_id = message.from_user.id
        target_user_id = user_states.get(user_id, {}).get('broadcast_target')
        broadcast_text = message.text

        try:
            bot.send_message(target_user_id, f"📢 **СООБЩЕНИЕ**\n\n{broadcast_text}", parse_mode='Markdown')
            bot.send_message(user_id, f"✅ Сообщение отправлено пользователю {target_user_id}")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка отправки пользователю {target_user_id}: {e}")

    # ================ БАЛАНС ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "admin_balance_menu")
    def admin_balance_menu(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📋 Показать всех", callback_data="view_all_users"),
            types.InlineKeyboardButton("🔒 Блокировка", callback_data="user_blocking_menu"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
        )

        bot.edit_message_text("👥 **БАЛАНС**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "view_all_users")
    def view_all_users(call):
        bot.answer_callback_query(call.id)
        users = db.get_users_list(limit=50)

        if not users:
            bot.send_message(call.message.chat.id, "❌ Нет пользователей")
            return

        text = "👥 **ВСЕ ПОЛЬЗОВАТЕЛИ**\n\n"
        for user_id, username, balance in users:
            username_str = username or "N/A"
            text += f"ID: {user_id}\n"
            text += f"Username: @{username_str}\n"
            text += f"💰 Баланс: ${float(balance):.2f}\n"
            text += f"/user_info_{user_id}\n"
            text += f"---\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_balance_menu"))

        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "user_blocking_menu")
    def user_blocking_menu(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔒 Заблокировать", callback_data="block_user_action"),
            types.InlineKeyboardButton("🔓 Разблокировать", callback_data="unblock_user_action"),
            types.InlineKeyboardButton("📋 Список заблокированных", callback_data="view_blocked_users"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="admin_balance_menu")
        )

        bot.edit_message_text("🔒 **БЛОКИРОВКА ПОЛЬЗОВАТЕЛЕЙ**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "block_user_action")
    def block_user_action(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя для блокировки:")
        bot.register_next_step_handler(msg, process_block_user, bot, user_states)

    def process_block_user(message, bot, user_states):
        user_id = message.from_user.id
        try:
            target_user_id = int(message.text.strip())
            msg = bot.send_message(message.chat.id, "Введите причину блокировки (опционально):")
            bot.register_next_step_handler(msg, process_block_user_reason, bot, user_states, target_user_id)
        except:
            bot.send_message(message.chat.id, "❌ Неверный ID!")

    def process_block_user_reason(message, bot, user_states, target_user_id):
        user_id = message.from_user.id
        reason = message.text if message.text else "Без причины"
        db.block_user(target_user_id, reason)
        bot.send_message(user_id, f"🔒 Пользователь {target_user_id} заблокирован\nПричина: {reason}")
        try:
            bot.send_message(target_user_id, f"❌ Вы заблокированы администратором\nПричина: {reason}")
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "unblock_user_action")
    def unblock_user_action(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя для разблокировки:")
        bot.register_next_step_handler(msg, process_unblock_user, bot, user_states)

    def process_unblock_user(message, bot, user_states):
        user_id = message.from_user.id
        try:
            target_user_id = int(message.text.strip())
            db.unblock_user(target_user_id)
            bot.send_message(user_id, f"🔓 Пользователь {target_user_id} разблокирован")
            try:
                bot.send_message(target_user_id, "✅ Вы разблокированы администратором")
            except:
                pass
        except:
            bot.send_message(user_id, "❌ Неверный ID!")

    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "view_blocked_users")
    def view_blocked_users(call):
        bot.answer_callback_query(call.id)
        blocked = db.get_blocked_users()

        if not blocked:
            bot.send_message(call.message.chat.id, "✅ Нет заблокированных пользователей")
            return

        text = "📋 **ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ**\n\n"
        for user_id, reason, blocked_at in blocked:
            text += f"ID: {user_id}\nПричина: {reason}\nДата: {blocked_at}\n\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="user_blocking_menu"))

        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    # ================ BACK TO ADMIN ================
    @bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID and call.data == "back_to_admin")
    def back_to_admin(call):
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("💰 Ручной платеж", callback_data="manual_payment"),
            types.InlineKeyboardButton("📦 Buyurtmalar", callback_data="admin_buyurtmalar"),
            types.InlineKeyboardButton("📋 Заказы", callback_data="admin_view_orders"),
            types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast_menu"),
            types.InlineKeyboardButton("👥 Баланс", callback_data="admin_balance_menu")
        )

        bot.edit_message_text("⚙️ **АДМИН-ПАНЕЛЬ**", call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode='Markdown')
        logger.info(f"Admin {call.from_user.id} returned to main panel")

    # ================ НАЧАЛО АДМИН ПАНЕЛИ (КОМАНДА) ================
    @bot.message_handler(commands=['admin'])
    def admin_start(message):
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

    # ================ ОБРАБОТКА ЗАКАЗОВ ПОДПИСЧИКОВ ================

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_complete_order_"))
    def admin_complete_order(call):
        """Отметить заказ как выполненный"""
        bot.answer_callback_query(call.id)
        order_id = int(call.data.replace("admin_complete_order_", ""))

        db.update_order_status(order_id, "Завершен")

        order = db.get_order(order_id)

        bot.edit_message_text(
            f"✅ <b>ЗАКАЗ #{order_id} ВЫПОЛНЕН</b>\n\n"
            f"Статус: Завершен\n"
            f"Услуга: {order[0]}\n"
            f"Количество: {order[1]:,}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )

        logger.info(f"✅ Admin completed order #{order_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reject_order_"))
    def admin_reject_order(call):
        """Отклонить заказ"""
        bot.answer_callback_query(call.id)
        order_id = int(call.data.replace("admin_reject_order_", ""))

        order_info = db.get_order_user_and_price(order_id)
        if not order_info:
            bot.send_message(call.message.chat.id, "❌ Заказ не найден")
            return

        user_id, price = order_info

        db.update_order_status(order_id, "Отклонен")

        db.update_balance(user_id, price, 0)

        order = db.get_order(order_id)

        bot.edit_message_text(
            f"❌ <b>ЗАКАЗ #{order_id} ОТКЛОНЕН</b>\n\n"
            f"Статус: Отклонен\n"
            f"Услуга: {order[0]}\n"
            f"Количество: {order[1]:,}\n"
            f"Сумма возвращена: ${price:.2f}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )

        try:
            bot.send_message(user_id,
                             f"❌ <b>ЗАКАЗ #{order_id} ОТКЛОНЕН</b>\n\n"
                             f"Услуга: {order[0]}\n"
                             f"Количество: {order[1]:,}\n"
                             f"💰 Сумма возвращена: ${price:.2f}",
                             parse_mode='HTML')
        except:
            pass

        logger.info(f"❌ Admin rejected order #{order_id}, returned ${price:.2f} to user {user_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_approve_subs_"))
    def admin_approve_subs(call):
        """✅ Выполнено - заказ готов"""
        bot.answer_callback_query(call.id)
        order_id = int(call.data.replace("admin_approve_subs_", ""))

        db.update_order_status(order_id, "Выполнено")

        order_info = db.get_order_user_and_price(order_id)
        if not order_info:
            bot.send_message(call.message.chat.id, "❌ Заказ не найден")
            return

        user_id, price = order_info
        order = db.get_order(order_id)
        service_type, quantity, _, hours, _ = order

        admin_text = (
            f"Заказ #{order_id}\n"
            f"User: {user_id}\n"
            f"Кол-во: {quantity}\n"
            f"Часов: {hours if hours > 0 else '∞'}\n"
            f"Сумма: {price:.2f}$\n\n"
            f"✅ Выполнено"
        )

        bot.edit_message_text(admin_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

        try:
            bot.send_message(user_id,
                             f"✅ Заказ #{order_id} выполнен!\n\n"
                             f"Подписчики: {quantity}\n"
                             f"Статус: Выполнено",
                             parse_mode='HTML')
        except:
            pass

        logger.info(f"✅ Admin approved subs order #{order_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_in_progress_subs_"))
    def admin_in_progress_subs(call):
        """🔄 В процессе - заказ выполняется"""
        bot.answer_callback_query(call.id)
        order_id = int(call.data.replace("admin_in_progress_subs_", ""))

        db.update_order_status(order_id, "В ожидании")

        order_info = db.get_order_user_and_price(order_id)
        if not order_info:
            bot.send_message(call.message.chat.id, "❌ Заказ не найден")
            return

        user_id, price = order_info
        order = db.get_order(order_id)
        service_type, quantity, _, hours, _ = order

        admin_text = (
            f"Заказ #{order_id}\n"
            f"User: {user_id}\n"
            f"Кол-во: {quantity}\n"
            f"Часов: {hours if hours > 0 else '∞'}\n"
            f"Сумма: {price:.2f}$\n\n"
            f"🔄 В процессе"
        )

        bot.edit_message_text(admin_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

        try:
            bot.send_message(user_id,
                             f"🔄 Заказ #{order_id} в процессе!\n\n"
                             f"Подписчики: {quantity}\n"
                             f"Статус: В ожидании",
                             parse_mode='HTML')
        except:
            pass

        logger.info(f"🔄 Admin set subs order #{order_id} in progress")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reject_subs_"))
    def admin_reject_subs(call):
        """❌ Отменить - запрос суммы возврата"""
        bot.answer_callback_query(call.id)
        order_id = int(call.data.replace("admin_reject_subs_", ""))

        msg = bot.send_message(call.message.chat.id,
                               f"Заказ #{order_id} отменен.\n\n"
                               f"Qancha pul qaytarish kerak? (masalan 1.3)")

        user_states[call.from_user.id] = {"order_id": order_id, "step": "waiting_refund_amount"}
        bot.register_next_step_handler(msg, process_refund_amount, bot, user_states)

    def process_refund_amount(message, bot, user_states):
        """Обработка суммы возврата"""
        admin_id = message.from_user.id

        try:
            refund_amount = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную сумму (например: 1.3)")
            return

        order_id = user_states.get(admin_id, {}).get("order_id")

        if not order_id:
            bot.send_message(message.chat.id, "❌ Ошибка: заказ не найден")
            return

        order_info = db.get_order_user_and_price(order_id)
        if not order_info:
            bot.send_message(message.chat.id, "❌ Заказ не найден в БД")
            return

        user_id, original_price = order_info
        order = db.get_order(order_id)
        service_type, quantity, _, hours, _ = order

        db.update_order_status(order_id, "Отмена")

        db.update_balance(user_id, refund_amount, 0)
        new_balance = db.get_user_balance(user_id)

        admin_confirm_text = (
            f"Заказ #{order_id}\n"
            f"User: {user_id}\n"
            f"Кол-во: {quantity}\n"
            f"Оригинальная сумма: {original_price:.2f}$\n"
            f"Возвращено: {refund_amount:.2f}$\n\n"
            f"❌ Отмена"
        )

        bot.send_message(message.chat.id, admin_confirm_text, parse_mode='HTML')

        try:
            bot.send_message(user_id,
                             f"❌ Заказ #{order_id} отменен\n\n"
                             f"Подписчики: {quantity}\n"
                             f"Статус: Отмена\n"
                             f"💰 Возвращено: ${refund_amount:.2f}\n"
                             f"💳 Новый баланс: ${new_balance:.2f}",
                             parse_mode='HTML')
        except:
            pass

        logger.info(f"❌ Admin rejected subs order #{order_id}, refunded ${refund_amount:.2f} to user {user_id}")
        reset_state(user_states, admin_id)

    # ================ ОБРАБОТЧИКИ ПРОСМОТРОВ - НА ОДНОМ УРОВНЕ С ОСТАЛЬНЫМИ ================

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_approve_auto_view_"))
    def admin_approve_auto_view(call):
        """Одобрить заказ просмотров"""
        bot.answer_callback_query(call.id)
        tarif_id = int(call.data.replace("admin_approve_auto_view_", ""))

        db.update_auto_view_status(tarif_id, "approved")

        bot.edit_message_text(call.message.text + "\n\n✅ Одобрено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"✅ Admin approved auto view tarif #{tarif_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reject_auto_view_"))
    def admin_reject_auto_view(call):
        """Отклонить заказ просмотров"""
        bot.answer_callback_query(call.id)
        tarif_id = int(call.data.replace("admin_reject_auto_view_", ""))

        tarif_info = db.get_auto_view_tarif_full(tarif_id)
        if tarif_info:
            user_id, tarif_type, channel_name, views_per_post, _ = tarif_info
            price = db.get_tarif_price(tarif_type)

            db.update_balance(user_id, price, 0)

            db.update_auto_view_status(tarif_id, "rejected")

            try:
                bot.send_message(user_id,
                                 f"❌ Заказ просмотров отклонён администратором\n\n"
                                 f"Канал: {channel_name}\n"
                                 f"💰 Возвращено: ${price:.2f}",
                                 parse_mode='HTML')
            except:
                pass

        bot.edit_message_text(call.message.text + "\n\n❌ Отклонено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"❌ Admin rejected auto view tarif #{tarif_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_approve_prolong_"))
    def admin_approve_prolong(call):
        """Одобрить продление"""
        bot.answer_callback_query(call.id)
        tarif_id = int(call.data.replace("admin_approve_prolong_", ""))

        bot.edit_message_text(call.message.text + "\n\n✅ Продление одобрено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"✅ Admin approved prolong for tarif #{tarif_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reject_prolong_"))
    def admin_reject_prolong(call):
        """Отклонить продление"""
        bot.answer_callback_query(call.id)
        tarif_id = int(call.data.replace("admin_reject_prolong_", ""))

        tarif_info = db.get_auto_view_tarif_full(tarif_id)
        if tarif_info:
            user_id, tarif_type, channel_name, views_per_post, _ = tarif_info
            price = db.get_tarif_price(tarif_type)

            db.update_balance(user_id, price, 0)

            try:
                bot.send_message(user_id,
                                 f"❌ Продление отклонено администратором\n\n"
                                 f"Канал: {channel_name}\n"
                                 f"💰 Возвращено: ${price:.2f}",
                                 parse_mode='HTML')
            except:
                pass

        bot.edit_message_text(call.message.text + "\n\n❌ Продление отклонено",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"❌ Admin rejected prolong for tarif #{tarif_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_approve_channel_"))
    def admin_approve_channel(call):
        """Одобрить изменение канала"""
        bot.answer_callback_query(call.id)

        parts = call.data.split("_", 4)
        tarif_id = int(parts[3])
        new_channel = parts[4] if len(parts) > 4 else ""

        tarif_info = db.get_auto_view_tarif(tarif_id)
        if tarif_info:
            user_id = None
            current_time = int(time())
            all_active = db.get_active_auto_view_tarifs(user_id or 1, current_time)

            try:
                bot.send_message(user_id,
                                 f"✅ Канал успешно изменён\n\n"
                                 f"Новый канал: {new_channel}",
                                 parse_mode='HTML')
            except:
                pass

        bot.edit_message_text(call.message.text + "\n\n✅ Канал одобрен",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"✅ Admin approved channel change for tarif #{tarif_id}")

    @bot.callback_query_handler(
        func=lambda call: call.from_user.id == ADMIN_ID and call.data.startswith("admin_reject_channel_"))
    def admin_reject_channel(call):
        """Отклонить изменение канала"""
        bot.answer_callback_query(call.id)
        tarif_id = int(call.data.replace("admin_reject_channel_", ""))

        bot.edit_message_text(call.message.text + "\n\n❌ Канал отклонен",
                              call.message.chat.id, call.message.message_id, reply_markup=None)

        logger.info(f"❌ Admin rejected channel change for tarif #{tarif_id}")