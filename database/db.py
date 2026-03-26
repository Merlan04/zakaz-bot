import sqlite3
import logging
from datetime import datetime
from config import DB_NAME, DEFAULT_SETTINGS, DEFAULT_TARIFFS

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Получить подключение к БД"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''CREATE TABLE IF NOT EXISTS users
                              (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, total_spent REAL DEFAULT 0)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                              (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service_type TEXT, 
                               link TEXT, quantity INTEGER, price REAL, hours INTEGER DEFAULT 0, status TEXT DEFAULT 'В ожидании', date TEXT)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS settings
                              (key TEXT PRIMARY KEY, value REAL)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS view_tarifs
                              (type TEXT PRIMARY KEY, price REAL, duration INTEGER)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS user_view_tarif
                              (user_id INTEGER, tarif_type TEXT, start_ts INTEGER, end_ts INTEGER, 
                               channel_link TEXT, views_per_post INTEGER DEFAULT 0)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings
                              (user_id INTEGER PRIMARY KEY, autoprod INTEGER DEFAULT 1, notifications INTEGER DEFAULT 1)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS temp_payments
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               user_id INTEGER,
                               amount REAL,
                               crypto TEXT,
                               created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

            # Insert default settings
            for k, v in DEFAULT_SETTINGS.items():
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

            # Insert default tariffs
            for t, price, dur in DEFAULT_TARIFFS:
                cursor.execute("INSERT OR IGNORE INTO view_tarifs (type, price, duration) VALUES (?, ?, ?)",
                               (t, price, dur))

            conn.commit()
        logger.info("Database initialized successfully")

    # ================ USERS ================
    def create_user_if_not_exists(self, user_id, username):
        """Создать пользователя если его нет"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
                conn.commit()
        except Exception as e:
            logger.error(f"create_user_if_not_exists error: {e}")

    def get_user_balance(self, user_id):
        """Получить баланс пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                row = c.fetchone()
                return float(row[0]) if row else 0.0
        except Exception as e:
            logger.error(f"get_user_balance error: {e}")
            return 0.0

    def update_balance(self, user_id, amount, spent=0):
        """Обновить баланс (amount - сумма изменения)"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET balance = balance + ?, total_spent = total_spent + ? WHERE user_id=?",
                          (amount, spent, user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"update_balance error: {e}")

    # ================ SETTINGS ================
    def get_setting(self, key):
        """Получить значение настройки"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = ?", (key,))
                res = c.fetchone()
                return float(res[0]) if res else 0.0
        except Exception as e:
            logger.error(f"get_setting error: {e}")
            return 0.0

    def set_setting(self, key, value):
        """Установить значение настройки"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
                conn.commit()
        except Exception as e:
            logger.error(f"set_setting error: {e}")

    # ================ TARIFFS ================
    def get_view_tarifs(self):
        """Получить все тарифы просмотров"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT type, price FROM view_tarifs ORDER BY price ASC")
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_view_tarifs error: {e}")
            return []

    def get_tarif_price(self, tarif_type):
        """Получить цену тарифа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT price FROM view_tarifs WHERE type = ?", (tarif_type,))
                row = c.fetchone()
                return float(row[0]) if row else 0.0
        except Exception as e:
            logger.error(f"get_tarif_price error: {e}")
            return 0.0

    def update_tarif_price(self, tarif_type, price):
        """Обновить цену тарифа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE view_tarifs SET price = ? WHERE type = ?", (price, tarif_type))
                conn.commit()
        except Exception as e:
            logger.error(f"update_tarif_price error: {e}")

    # ================ ORDERS ================
    def create_order(self, user_id, service_type, link, quantity, price, hours=0):
        """Создать заказ"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                date = datetime.now().strftime("%d.%m.%Y %H:%M")
                c.execute("""INSERT INTO orders (user_id, service_type, link, quantity, price, hours, status, date)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (user_id, service_type, link, quantity, price, hours, "В ожидании", date))
                conn.commit()
                return c.lastrowid
        except Exception as e:
            logger.error(f"create_order error: {e}")
            return None

    def get_order(self, order_id):
        """Получить информацию заказа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT service_type, quantity, price, hours, status FROM orders WHERE order_id=?",
                          (order_id,))
                return c.fetchone()
        except Exception as e:
            logger.error(f"get_order error: {e}")
            return None

    def update_order_status(self, order_id, status):
        """Обновить статус заказа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
                conn.commit()
        except Exception as e:
            logger.error(f"update_order_status error: {e}")

    def get_user_orders(self, user_id, limit=10):
        """Получить заказы пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT order_id, service_type, quantity, status, date FROM orders WHERE user_id=? ORDER BY order_id DESC LIMIT ?",
                    (user_id, limit))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_user_orders error: {e}")
            return []

    # ================ AUTO VIEW TARIFFS ================
    def get_active_view_tarifs(self, user_id, current_time):
        """Получить активные тарифы автопросмотров"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT tarif_type, end_ts, channel_link, views_per_post 
                             FROM user_view_tarif 
                             WHERE user_id = ? AND end_ts > ?""", (user_id, current_time))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_active_view_tarifs error: {e}")
            return []

    def create_auto_view_tarif(self, user_id, tarif_type, channel_link, views_per_post, current_time, duration):
        """Создать тариф автопросмотров"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                end_ts = current_time + duration
                c.execute("""INSERT INTO user_view_tarif 
                             (user_id, tarif_type, start_ts, end_ts, channel_link, views_per_post) 
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (user_id, tarif_type, current_time, end_ts, channel_link, views_per_post))
                conn.commit()
        except Exception as e:
            logger.error(f"create_auto_view_tarif error: {e}")

    def update_auto_view_views(self, user_id, channel_link, views_per_post):
        """Обновить количество просмотров"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""UPDATE user_view_tarif 
                             SET views_per_post = ? 
                             WHERE user_id=? AND channel_link=?""",
                          (views_per_post, user_id, channel_link))
                conn.commit()
        except Exception as e:
            logger.error(f"update_auto_view_views error: {e}")

    def prolong_auto_view(self, user_id, channel_link, prolong_days=10):
        """Продлить автопросмотры на N дней"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                prolong_seconds = prolong_days * 24 * 3600
                c.execute("""UPDATE user_view_tarif 
                             SET end_ts = end_ts + ? 
                             WHERE user_id=? AND channel_link=?""",
                          (prolong_seconds, user_id, channel_link))
                conn.commit()
        except Exception as e:
            logger.error(f"prolong_auto_view error: {e}")

    # ================ PAYMENTS ================
    def create_temp_payment(self, user_id, amount, crypto):
        """Создать временный платеж"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO temp_payments (user_id, amount, crypto) VALUES (?, ?, ?)",
                          (user_id, amount, crypto))
                conn.commit()
        except Exception as e:
            logger.error(f"create_temp_payment error: {e}")

    def get_temp_payment(self, user_id):
        """Получить временный платеж"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT amount FROM temp_payments WHERE user_id=?", (user_id,))
                row = c.fetchone()
                return float(row[0]) if row else 0.0
        except Exception as e:
            logger.error(f"get_temp_payment error: {e}")
            return 0.0

    def delete_temp_payment(self, user_id):
        """Удалить временный платеж"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM temp_payments WHERE user_id=?", (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"delete_temp_payment error: {e}")

    # ================ USERS LIST ================
    def get_users_list(self, limit=50):
        """Получить список пользователей (для админа)"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, username, balance FROM users LIMIT ?", (limit,))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_users_list error: {e}")
            return []


# Глобальный объект БД
db = Database()