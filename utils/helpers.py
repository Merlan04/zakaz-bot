import telebot
import logging

logger = logging.getLogger(__name__)


def get_channel_name(bot, link):
    """Получить название канала"""
    from utils.validators import extract_channel

    try:
        channel = extract_channel(link)
        chat = bot.get_chat(channel)
        return chat.title or "Без названия"
    except Exception as e:
        logger.debug(f"Cannot get channel name: {e}")
        return extract_channel(link) or "Частный канал"


def check_sufficient_balance(user_id, required_amount, db):
    """Проверить достаточность баланса"""
    balance = db.get_user_balance(user_id)
    return balance >= required_amount, balance


def get_possible_quantity(balance, price_per_unit, unit_size=1000):
    """Получить возможное количество покупок"""
    return int((balance / price_per_unit) * unit_size)


def reset_state(user_states, user_id):
    """Очистить состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
    logger.debug(f"State reset for user {user_id}")