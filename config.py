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
MAX_MESSAGES = None  # None = парсить все доступные сообщения
OUTPUT_DIR = "parsed_data"  # Папка для сохранения результатов

# Настройки безопасности и ограничений
RATE_LIMITING = {
    'delay_between_chats': 2,  # Задержка между чатами (секунды)
    'delay_between_requests': 0.5,  # Задержка между запросами (секунды)
    'max_flood_wait': 300,  # Максимальное время ожидания FloodWait (5 минут)
    'backoff_multiplier': 1.5,  # Множитель для экспоненциального отката
    'check_account_restrictions': True  # Проверять ограничения аккаунта
}

# Настройки базы данных
DB_FILENAME = "telegram_history.db"  # Имя файла базы данных
ENABLE_HISTORY_TRACKING = True  # Включить отслеживание истории изменений
ENABLE_REALTIME_MONITOR = True  # Включить мониторинг изменений в реальном времени

# Форматы экспорта
EXPORT_FORMATS = {
    'json': True,   # Экспорт в JSON
    'csv': True,    # Экспорт в CSV
    'txt': False,   # Экспорт в текстовый файл
    'ai_ready': True  # Создавать файлы для AI анализа
}

# Настройки автоматизации
AUTO_CREATE_AI_ANALYSIS = False  # Автоматически создавать AI анализ после парсинга (отключено)

# Настройки аналитики
ANALYTICS_SETTINGS = {
    'min_word_length': 4,  # Минимальная длина слова для анализа тем
    'max_messages_for_ai': 200,  # Максимум сообщений для AI анализа
    'activity_period_days': 30   # Период для анализа активности
}