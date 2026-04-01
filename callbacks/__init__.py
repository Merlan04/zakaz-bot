from callbacks.admin_callbacks import register_admin_callbacks
from callbacks.order_callbacks import register_order_callbacks
from callbacks.payment_callbacks import register_payment_callbacks
from callbacks.views_callbacks import register_views_callbacks


def register_all_callbacks(bot, user_states):
    """Регистрировать все callbacks"""
    register_admin_callbacks(bot, user_states)
    register_order_callbacks(bot, user_states)
    register_payment_callbacks(bot, user_states)
    register_views_callbacks(bot, user_states)