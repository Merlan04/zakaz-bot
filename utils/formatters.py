from datetime import datetime, timedelta
import time


def format_order_message(order_id, service_type, quantity, price, hours, link, user_id):
    """Форматировать сообщение о заказе для группы"""
    return (
        f"🆕 Заказ #{order_id}\n"
        f"👤 User: {user_id}\n"
        f"📝 Тип: {service_type}\n"
        f"📊 Кол-во: {quantity}\n"
        f"🔗 Ссылка: {link}\n"
        f"⏱️ Часы: {hours}\n"
        f"💰 Сумма: {price}$"
    )


def format_order_details(order_info):
    """Форматировать детали заказа"""
    if not order_info:
        return None
    service_type, quantity, price, hours, status = order_info
    return (
        f"🆕 Заказ\n"
        f"Тип: {service_type}\n"
        f"Кол-во: {quantity}\n"
        f"Сумма: {price}$\n"
        f"Часы: {hours}\n"
        f"Статус: {status}"
    )


def format_time_remaining(end_ts):
    """Форматировать оставшееся время"""
    now = int(time.time())
    remaining = end_ts - now

    if remaining <= 0:
        return "Истекло"

    d = remaining // 86400
    h = (remaining % 86400) // 3600
    m = (remaining % 3600) // 60

    return f"{d} д, {h} ч, {m} мин"


def format_payment_message(amount, crypto):
    """Форматировать сообщение о платеже"""
    crypto_addresses = {
        "USDT": "TJH1kg6w5qXupx4nQ9keCQUFxkEUJXvubG",
        "BTC": "163hvzR8NGyGkjcwDbgqG3B5jfk8TcYWRx",
        "LTC": "LZdEEnowWPfrzC4FNWi7Z5t8Uzjffu1vNK",
        "ETH": "0x4c76fb5e2978797a4ad45eef0f9b58ea94bf6d89"
    }

    addr = crypto_addresses.get(crypto, crypto_addresses["USDT"])

    return (
        f"ℹ️ Перевод будет зачислен автоматически\n\n"
        f"👉 Отправьте {crypto} на этот адрес:\n\n"
        f"`{addr}`"
    )


def format_active_tarifs(tarifs):
    """Форматировать активные тарифы"""
    if not tarifs:
        return ""

    from config import TARIFF_VIEWS_MAP

    txt = "👁 Каналы с автопросмотрами:\n\n"
    for tar, end, link, views in tarifs:
        max_views = TARIFF_VIEWS_MAP.get(tar, 1000)
        time_remaining = format_time_remaining(end)
        txt += f"*{link}* • {views}/{max_views} • ⏳ {time_remaining}\n\n"

    return txt


def format_admin_payment_request(user_id, amount, crypto):
    """Форматировать запрос платежа для админа"""
    return (
        f"🆕 Новый запрос на пополнение\n"
        f"👤 User: {user_id}\n"
        f"💰 Сумма: {amount}$\n"
        f"💸 Криптовалюта: {crypto}"
    )


def format_user_question(user_id, username):
    """Форматировать вопрос пользователя для админа"""
    return (
        f"❓ Новый вопрос\n"
        f"👤 User: {user_id}\n"
        f"👤 Username: @{username or 'Не указано'}"
    )