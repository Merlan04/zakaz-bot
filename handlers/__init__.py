from handlers.user_handlers import register_user_handlers
from handlers.subs_handlers import register_subs_handlers
from handlers.views_handlers import register_views_handlers
from handlers.admin_handlers import register_admin_handlers

def register_all_handlers(bot, user_states):
    """Регистрировать все обработчики"""
    register_user_handlers(bot, user_states)
    register_subs_handlers(bot, user_states)
    register_views_handlers(bot, user_states)
    register_admin_handlers(bot, user_states)

__all__ = ['register_all_handlers']