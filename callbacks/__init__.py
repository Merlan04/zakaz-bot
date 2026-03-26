from callbacks.payment_callbacks import register_payment_callbacks
from callbacks.order_callbacks import register_order_callbacks
from callbacks.admin_callbacks import register_admin_callbacks

def register_all_callbacks(bot, user_states):
    """Регистрировать все callback обработчики"""
    register_payment_callbacks(bot, user_states)
    register_order_callbacks(bot, user_states)
    register_admin_callbacks(bot, user_states)

__all__ = ['register_all_callbacks']