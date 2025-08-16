"""
Конфигурация логирования для Telegram Parser
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Создаем директорию для логов если её нет
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def setup_logger(name, log_file, level=logging.INFO):
    """Настройка логгера с ротацией файлов"""
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Создаем handler с ротацией (максимум 10MB на файл, хранить 5 файлов)
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, log_file),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Создаем console handler для критических ошибок
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    
    # Настраиваем логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Создаем логгеры для разных компонентов
parser_logger = setup_logger('parser', 'parser.log')
web_logger = setup_logger('web', 'web_interface.log')
monitor_logger = setup_logger('monitor', 'monitor.log')
error_logger = setup_logger('errors', 'errors.log', logging.ERROR)

def log_error(component, error, context=None):
    """Логирование ошибки с контекстом"""
    error_msg = f"[{component}] {error}"
    if context:
        error_msg += f" | Context: {context}"
    
    error_logger.error(error_msg, exc_info=True)
    
    # Также логируем в компонентный логгер
    if component == 'parser':
        parser_logger.error(error_msg)
    elif component == 'web':
        web_logger.error(error_msg)
    elif component == 'monitor':
        monitor_logger.error(error_msg)

def log_info(component, message):
    """Логирование информационного сообщения"""
    if component == 'parser':
        parser_logger.info(message)
    elif component == 'web':
        web_logger.info(message)
    elif component == 'monitor':
        monitor_logger.info(message)

def log_warning(component, message):
    """Логирование предупреждения"""
    if component == 'parser':
        parser_logger.warning(message)
    elif component == 'web':
        web_logger.warning(message)
    elif component == 'monitor':
        monitor_logger.warning(message)