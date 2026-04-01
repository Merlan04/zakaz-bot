import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.db import db

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Запускает планировщик"""
    scheduler.add_job(db.check_and_renew_auto_views, 'interval', minutes=5)
    scheduler.start()
    print("⏲️ Планировщик запущен")

async def shutdown_scheduler():
    """Останавливает планировщик"""
    scheduler.shutdown()
    print("⏲️ Планировщик остановлен")