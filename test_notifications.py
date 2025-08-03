#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы уведомлений
"""
import asyncio
import logging
from datetime import datetime
from notification_manager import get_notification_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_notifications():
    """Тест отправки уведомлений"""
    notification_manager = get_notification_manager()
    
    # Тест 1: Уведомление о редактировании
    logger.info("Отправляем тестовое уведомление о редактировании...")
    notification_manager.notify('message_edited', {
        'chat_id': -1001234567890,
        'chat_name': 'Тестовый чат',
        'message_id': 12345,
        'text': 'Это тестовое изменённое сообщение для проверки уведомлений'
    })
    
    await asyncio.sleep(2)
    
    # Тест 2: Уведомление об удалении
    logger.info("Отправляем тестовое уведомление об удалении...")
    notification_manager.notify('message_deleted', {
        'chat_id': -1001234567890,
        'chat_name': 'Тестовый чат',
        'message_id': 12346
    })
    
    logger.info("Тестовые уведомления отправлены!")
    logger.info("Откройте http://localhost:5001/realtime-monitor в браузере")
    logger.info("Вы должны увидеть всплывающие уведомления")

if __name__ == "__main__":
    asyncio.run(test_notifications())