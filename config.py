"""
Конфигурация для Telegram Parser
"""
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# API данные Telegram (получить на https://my.telegram.org)
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Настройки парсинга
MAX_MESSAGES = 1000  # Максимальное количество сообщений для парсинга
OUTPUT_DIR = "parsed_data"  # Папка для сохранения результатов

# Форматы экспорта
EXPORT_FORMATS = {
    'json': True,   # Экспорт в JSON
    'csv': True,    # Экспорт в CSV
    'txt': False    # Экспорт в текстовый файл
}