import telebot
import logging
from logging.handlers import RotatingFileHandler
import sys
from config import TOKEN, ADMIN_ID
from database import db
from utils import reset_state
from handlers.user_handlers import get_main_menu
from handlers import register_all_handlers
from callbacks import register_all_callbacks
# ====================== SETUP LOGGING ======================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler("bot.log", maxBytes=10485760, backupCount=5)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logging()

# ====================== BOT INITIALIZATION ======================
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
user_states = {}

logger.info(f"Bot initialized successfully")

# ====================== SET COMMANDS ======================
try:
    commands = [
        telebot.types.BotCommand("start", "Запустить бота"),
        telebot.types.BotCommand("admin", "Админ панель"),
    ]
    bot.set_my_commands(commands)
    logger.info("✅ Commands set successfully")
except Exception as e:
    logger.error(f"❌ Failed to set commands: {e}")


# ====================== SIMPLE TEST HANDLERS ======================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    db.create_user_if_not_exists(user_id, message.from_user.username)
    reset_state(user_states, user_id)

    menu = get_main_menu()
    logger.info(f"DEBUG: Menu object: {menu}")
    logger.info(f"DEBUG: Menu type: {type(menu)}")

    bot.send_message(message.chat.id, "👋 Добро пожаловать!\nВыберите услугу:",
                     reply_markup=menu)
    logger.info(f"✅ Message sent to {user_id} with menu")


@bot.message_handler(commands=['test'])
def test_echo(message):
    logger.info(f"✅ TEST command from user {message.from_user.id}")
    bot.send_message(message.chat.id, "🤖 Тест работает!")


# ====================== REGISTER HANDLERS & CALLBACKS ======================
logger.info("Registering handlers...")
try:
    register_all_handlers(bot, user_states)
    logger.info("✅ All handlers registered")
except Exception as e:
    logger.error(f"❌ Failed to register handlers: {e}", exc_info=True)

logger.info("Registering callbacks...")
try:
    register_all_callbacks(bot, user_states)
    logger.info("✅ All callbacks registered")
except Exception as e:
    logger.error(f"❌ Failed to register callbacks: {e}", exc_info=True)

# ====================== START BOT ======================
if __name__ == '__main__':
    logger.info("=== BOT STARTED ===")
    print("\n" + "=" * 60)
    print("🤖 BOT STARTED SUCCESSFULLY!")
    print(f"Token: {TOKEN[:20]}...")
    print("Ready to receive messages")
    print("Press Cmd+C to stop")
    print("=" * 60 + "\n")

    try:
        bot.polling(none_stop=True, skip_pending=False, timeout=30)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n🛑 Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)