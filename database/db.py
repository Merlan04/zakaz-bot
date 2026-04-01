import sqlite3
import logging
from datetime import datetime
from config import DB_NAME, DEFAULT_SETTINGS, DEFAULT_TARIFFS
from time import time

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_db()

    def init_db(self):
        """Инициализация таблиц"""
        self.conn = self.get_connection()
        self.cursor = self.conn.cursor()

        try:
            # ... все CREATE TABLE ...

            self.conn.commit()

            # ✅ Добавь эту строку после commit
            self.migrate_add_status_column()

            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            self.conn.rollback()

    def get_connection(self):
        """Получить подключение к БД"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация таблиц"""
        self.conn = self.get_connection()
        self.cursor = self.conn.cursor()

        try:
            # Таблица пользователей
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, total_spent REAL DEFAULT 0)''')

            # Таблица заказов (старая система)
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                                  (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service_type TEXT, 
                                   link TEXT, quantity INTEGER, price REAL, hours INTEGER DEFAULT 0, status TEXT DEFAULT 'В ожидании', date TEXT)''')

            # Таблица настроек сервиса
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings
                                  (key TEXT PRIMARY KEY, value REAL)''')

            # Таблица тарифов просмотров
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS view_tarifs
                                  (type TEXT PRIMARY KEY, price REAL, duration INTEGER)''')

            # Таблица активных автопросмотров (старая версия)
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_view_tarif
                                  (user_id INTEGER, tarif_type TEXT, start_ts INTEGER, end_ts INTEGER, 
                                   channel_link TEXT, views_per_post INTEGER DEFAULT 0)''')

            # Таблица настроек пользователя (автопродление, уведомления)
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings
                                  (user_id INTEGER PRIMARY KEY, autoprod INTEGER DEFAULT 1, notifications INTEGER DEFAULT 1)''')

            # Таблица временных платежей
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS temp_payments
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   user_id INTEGER,
                                   amount REAL,
                                   crypto TEXT,
                                   created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

            # Таблица заблокированных пользователей
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_users
                                  (user_id INTEGER PRIMARY KEY,
                                   blocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                   reason TEXT)''')

            # Таблица заказов просмотров (на конкретный пост)
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS views_orders
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   user_id INTEGER NOT NULL,
                                   channel_name TEXT NOT NULL,
                                   message_link TEXT NOT NULL,
                                   views_count INTEGER NOT NULL,
                                   cost REAL NOT NULL,
                                   status TEXT DEFAULT 'pending',
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_user_views_orders ON views_orders(user_id)''')
            self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_views_orders_status ON views_orders(status)''')

            # Таблица автопросмотров (новая версия - тариф на весь канал)
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS auto_view_tarifs
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   user_id INTEGER NOT NULL,
                                   tarif_type TEXT NOT NULL,
                                   channel_name TEXT NOT NULL,
                                   views_per_post INTEGER NOT NULL,
                                   start_time INTEGER NOT NULL,
                                   end_time INTEGER NOT NULL,
                                   status TEXT DEFAULT 'pending',
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_user_auto_tarifs ON auto_view_tarifs(user_id)''')

            # Таблица расширенных настроек пользователя
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   user_id INTEGER NOT NULL UNIQUE,
                                   auto_renew INTEGER DEFAULT 1,
                                   notifications INTEGER DEFAULT 1)''')

            # Insert default settings
            for k, v in DEFAULT_SETTINGS.items():
                self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

            # Insert default tariffs
            for t, price, dur in DEFAULT_TARIFFS:
                self.cursor.execute("INSERT OR IGNORE INTO view_tarifs (type, price, duration) VALUES (?, ?, ?)",
                                    (t, price, dur))

            self.conn.commit()
            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            self.conn.rollback()

    # ================ БЛОКИРОВКА ПОЛЬЗОВАТЕЛЕЙ ================
    def block_user(self, user_id, reason=""):
        """Заблокировать пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO blocked_users (user_id, reason) VALUES (?, ?)",
                          (user_id, reason))
                conn.commit()
                logger.info(f"User {user_id} blocked")
        except Exception as e:
            logger.error(f"block_user error: {e}")

    def unblock_user(self, user_id):
        """Разблокировать пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
                conn.commit()
                logger.info(f"User {user_id} unblocked")
        except Exception as e:
            logger.error(f"unblock_user error: {e}")

    def is_user_blocked(self, user_id):
        """Проверить, заблокирован ли пользователь"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id FROM blocked_users WHERE user_id = ?", (user_id,))
                return c.fetchone() is not None
        except Exception as e:
            logger.error(f"is_user_blocked error: {e}")
            return False

    def get_blocked_users(self):
        """Получить список заблокированных пользователей"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, reason, blocked_at FROM blocked_users")
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_blocked_users error: {e}")
            return []

    # ================ СТАТИСТИКА ================
    def get_total_earned(self):
        """Получить общий доход"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT SUM(total_spent) FROM users")
                result = c.fetchone()
                return float(result[0]) if result and result[0] else 0.0
        except Exception as e:
            logger.error(f"get_total_earned error: {e}")
            return 0.0

    def get_total_orders(self):
        """Получить количество заказов"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM orders")
                result = c.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"get_total_orders error: {e}")
            return 0

    def get_orders_by_status(self, status):
        """Получить заказы по статусу"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT order_id, user_id, service_type, quantity, price, status, date FROM orders WHERE status = ? ORDER BY order_id DESC",
                    (status,))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_orders_by_status error: {e}")
            return []

    def get_all_orders(self, limit=50):
        """Получить все заказы"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT order_id, user_id, service_type, quantity, price, status, date FROM orders ORDER BY order_id DESC LIMIT ?",
                    (limit,))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_all_orders error: {e}")
            return []

    def get_user_info(self, user_id):
        """Получить полную информацию о пользователе"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, username, balance, total_spent FROM users WHERE user_id = ?", (user_id,))
                user = c.fetchone()

                if user:
                    c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,))
                    orders_count = c.fetchone()[0]
                    return {
                        'user_id': user[0],
                        'username': user[1],
                        'balance': user[2],
                        'total_spent': user[3],
                        'orders_count': orders_count
                    }
                return None
        except Exception as e:
            logger.error(f"get_user_info error: {e}")
            return None

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

    # ================ ORDERS (СТАРАЯ СИСТЕМА) ================
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

    def get_order_user_and_price(self, order_id):
        """Получить user_id и price заказа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, price FROM orders WHERE order_id=?", (order_id,))
                return c.fetchone()
        except Exception as e:
            logger.error(f"get_order_user_and_price error: {e}")
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

    # ================ AUTO VIEW TARIFFS (НОВАЯ ВЕРСИЯ) ================
    def create_auto_view_tarif(self, user_id, tarif_type, channel_name, views_count, duration_hours):
        """Создать новый тариф автопросмотров"""
        try:
            current_time = int(time())
            end_time = current_time + (30 * 86400)  # 30 дней по умолчанию

            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""INSERT INTO auto_view_tarifs 
                             (user_id, tarif_type, channel_name, views_per_post, start_time, end_time, status)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                          (user_id, tarif_type, channel_name, views_count, current_time, end_time, 'pending'))
                conn.commit()
                logger.info(f"Auto view tarif created for user {user_id}, channel {channel_name}")
                return c.lastrowid
        except Exception as e:
            logger.error(f"create_auto_view_tarif error: {e}")
            return None

    def get_active_auto_view_tarifs(self, user_id, current_time):
        """Получить все активные тарифы пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT id, tarif_type, channel_name, end_time, views_per_post
                             FROM auto_view_tarifs
                             WHERE user_id = ? AND end_time > ? AND status = 'approved'
                             ORDER BY end_time DESC""", (user_id, current_time))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_active_auto_view_tarifs error: {e}")
            return []

    def get_auto_view_tarif(self, tarif_id):
        """Получить информацию о конкретном тарифе"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT tarif_type, channel_name, views_per_post
                             FROM auto_view_tarifs
                             WHERE id = ?""", (tarif_id,))
                return c.fetchone()
        except Exception as e:
            logger.error(f"get_auto_view_tarif error: {e}")
            return None

    def get_auto_view_tarif_full(self, tarif_id):
        """Получить полную информацию о тарифе"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT user_id, tarif_type, channel_name, views_per_post, 0
                             FROM auto_view_tarifs WHERE id = ?""", (tarif_id,))
                return c.fetchone()
        except Exception as e:
            logger.error(f"get_auto_view_tarif_full error: {e}")
            return None

    def update_auto_view_status(self, tarif_id, status):
        """Обновить статус тарифа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE auto_view_tarifs SET status = ? WHERE id = ?", (status, tarif_id))
                conn.commit()
        except Exception as e:
            logger.error(f"update_auto_view_status error: {e}")

    def update_auto_view_views(self, tarif_id, views_count):
        """Обновить количество просмотров"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""UPDATE auto_view_tarifs
                             SET views_per_post = ?
                             WHERE id = ?""", (views_count, tarif_id))
                conn.commit()
        except Exception as e:
            logger.error(f"update_auto_view_views error: {e}")

    def get_auto_view_remaining_time(self, tarif_id):
        """Получить оставшееся время тарифа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT end_time FROM auto_view_tarifs WHERE id = ?", (tarif_id,))
                result = c.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"get_auto_view_remaining_time error: {e}")
            return None

    def prolong_auto_view_new(self, tarif_id, days):
        """Продлить тариф на N дней"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""UPDATE auto_view_tarifs
                             SET end_time = end_time + ?
                             WHERE id = ?""", (days * 86400, tarif_id))
                conn.commit()
        except Exception as e:
            logger.error(f"prolong_auto_view_new error: {e}")

    def get_expiring_auto_view_tarifs(self, current_time, expiring_in=86400):
        """Получить тарифы, которые истекают через expiring_in секунд"""
        try:
            expiring_time = current_time + expiring_in

            with self.get_connection() as conn:
                c = conn.cursor()

                # Проверяем есть ли колонка status
                c.execute("PRAGMA table_info(auto_view_tarifs)")
                columns = [col[1] for col in c.fetchall()]

                if 'status' not in columns:
                    # Добавляем колонку если её нет
                    c.execute("ALTER TABLE auto_view_tarifs ADD COLUMN status TEXT DEFAULT 'approved'")
                    conn.commit()

                c.execute("""SELECT user_id, id, tarif_type, channel_name, end_time
                             FROM auto_view_tarifs
                             WHERE end_time <= ? AND end_time > ?""",
                          (expiring_time, current_time))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_expiring_auto_view_tarifs error: {e}")
            return []

    # ================ USER PREFERENCES ================
    def get_user_setting(self, user_id, setting_name, default=True):
        """Получить настройку пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if setting_name == "auto_renew":
                    c.execute("SELECT auto_renew FROM user_preferences WHERE user_id = ?", (user_id,))
                elif setting_name == "notifications":
                    c.execute("SELECT notifications FROM user_preferences WHERE user_id = ?", (user_id,))

                result = c.fetchone()
                if result:
                    return bool(result[0])
                return default
        except Exception as e:
            logger.error(f"get_user_setting error: {e}")
            return default

    def set_user_setting(self, user_id, setting_name, value):
        """Установить настройку пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()

                # Проверяем есть ли уже запись
                c.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
                exists = c.fetchone()

                if setting_name == "auto_renew":
                    if exists:
                        c.execute("UPDATE user_preferences SET auto_renew = ? WHERE user_id = ?",
                                  (1 if value else 0, user_id))
                    else:
                        c.execute("INSERT INTO user_preferences (user_id, auto_renew, notifications) VALUES (?, ?, ?)",
                                  (user_id, 1 if value else 0, 1))

                elif setting_name == "notifications":
                    if exists:
                        c.execute("UPDATE user_preferences SET notifications = ? WHERE user_id = ?",
                                  (1 if value else 0, user_id))
                    else:
                        c.execute("INSERT INTO user_preferences (user_id, auto_renew, notifications) VALUES (?, ?, ?)",
                                  (user_id, 1, 1 if value else 0))

                conn.commit()
        except Exception as e:
            logger.error(f"set_user_setting error: {e}")

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

    # ================ VIEWS ORDERS (НОВАЯ СИСТЕМА) ================
    def create_views_order(self, user_id, channel_name, message_link, views_count, cost):
        """Создать заказ просмотров"""
        try:
            current_time = int(time())
            created_at = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')

            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""INSERT INTO views_orders 
                             (user_id, channel_name, message_link, views_count, cost, status, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                          (user_id, channel_name, message_link, views_count, cost, "pending", created_at))
                conn.commit()
                logger.info(f"Views order created for user {user_id}")
                return c.lastrowid
        except Exception as e:
            logger.error(f"create_views_order error: {e}")
            return None

    def get_views_order(self, order_id):
        """Получить информацию о заказе"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT user_id, channel_name, message_link, views_count, cost, status
                             FROM views_orders
                             WHERE id = ?""", (order_id,))
                return c.fetchone()
        except Exception as e:
            logger.error(f"get_views_order error: {e}")
            return None

    def get_user_views_orders(self, user_id):
        """Получить все заказы пользователя"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT id, channel_name, views_count, status, created_at
                             FROM views_orders
                             WHERE user_id = ?
                             ORDER BY created_at DESC""", (user_id,))
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_user_views_orders error: {e}")
            return []

    def update_views_order_status(self, order_id, status):
        """Обновить статус заказа"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""UPDATE views_orders
                             SET status = ?
                             WHERE id = ?""", (status, order_id))
                conn.commit()
                logger.info(f"Views order {order_id} status updated to {status}")
        except Exception as e:
            logger.error(f"update_views_order_status error: {e}")

    def get_pending_views_orders(self):
        """Получить все заказы в ожидании (для админа)"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT id, user_id, channel_name, views_count, cost
                             FROM views_orders
                             WHERE status = 'pending'
                             ORDER BY created_at DESC""")
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_pending_views_orders error: {e}")
            return []


def migrate_add_status_column(self):
    """Добавить колонку status если её нет"""
    try:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(auto_view_tarifs)")
            columns = [col[1] for col in c.fetchall()]

            if 'status' not in columns:
                logger.info("Migrating: Adding status column to auto_view_tarifs")
                c.execute("ALTER TABLE auto_view_tarifs ADD COLUMN status TEXT DEFAULT 'approved'")
                conn.commit()
                logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration error: {e}")
    def get_pending_views_orders(self):
        """Получить все заказы в ожидании (для админа)"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT id, user_id, channel_name, views_count, cost
                             FROM views_orders
                             WHERE status = 'pending'
                             ORDER BY created_at DESC""")
                return c.fetchall()
        except Exception as e:
            logger.error(f"get_pending_views_orders error: {e}")
            return []

    # ✅ ПРАВИЛЬНОЕ МЕСТО ДЛЯ ЭТОЙ ФУНКЦИИ (ВНУТРИ КЛАССА!)
    def migrate_add_status_column(self):
        """Добавить колонку status если её нет"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(auto_view_tarifs)")
                columns = [col[1] for col in c.fetchall()]

                if 'status' not in columns:
                    logger.info("Migrating: Adding status column to auto_view_tarifs")
                    c.execute("ALTER TABLE auto_view_tarifs ADD COLUMN status TEXT DEFAULT 'approved'")
                    conn.commit()
                    logger.info("Migration completed successfully")
        except Exception as e:
            logger.error(f"Migration error: {e}")


# ✅ ВСЕ ОСТАЛЬНОЕ УДАЛИ - оно не должно быть в файле db.py!
# Удали эти строки в конце файла:
# if __name__ == '__main__':
#     logger.info("=== BOT STARTED ===")
#     ...
#     bot.polling(...)
#     ...
#     db = Database()

# В конце db.py должно быть только:
# Глобальный объект БД
db = Database()