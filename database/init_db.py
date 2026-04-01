from database.db import db


# Добавь эту таблицу в init_db
def init_auto_views_tables():
    """Инициализирует таблицы для автопросмотров"""
    with db.get_connection() as conn:
        c = conn.cursor()

        # Таблица автопросмотров
        c.execute('''CREATE TABLE IF NOT EXISTS auto_views
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       channel_link TEXT,
                       views_per_post INTEGER,
                       duration_hours INTEGER,
                       price_per_day REAL DEFAULT 0.1,
                       start_ts INTEGER,
                       end_ts INTEGER,
                       status TEXT DEFAULT 'active',
                       created_at TEXT)''')

        # Таблица продлений
        c.execute('''CREATE TABLE IF NOT EXISTS auto_views_transactions
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       auto_view_id INTEGER,
                       user_id INTEGER,
                       days_added INTEGER,
                       amount REAL,
                       created_at TEXT)''')

        # Таблица заблокированных пользователей (НОВОЕ)
        c.execute('''CREATE TABLE IF NOT EXISTS blocked_users
                      (user_id INTEGER PRIMARY KEY,
                       blocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                       reason TEXT)''')

        conn.commit()


# Вызови при инициализации
init_auto_views_tables()

__all__ = ['db']