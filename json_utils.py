"""
Утилиты для работы с JSON и сериализацией данных
"""
import json
from datetime import datetime, date
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSON энкодер с поддержкой datetime объектов"""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            # Для объектов Telethon и других
            return str(obj)
        return super().default(obj)


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Безопасная сериализация в JSON с поддержкой datetime
    
    Args:
        data: Данные для сериализации
        **kwargs: Дополнительные параметры для json.dumps
        
    Returns:
        str: JSON строка
    """
    return json.dumps(data, cls=DateTimeEncoder, ensure_ascii=False, **kwargs)


def safe_json_loads(data: str) -> Any:
    """
    Безопасная десериализация из JSON
    
    Args:
        data: JSON строка
        
    Returns:
        Any: Десериализованные данные
    """
    return json.loads(data)