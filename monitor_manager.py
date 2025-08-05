"""
Менеджер для управления статусом мониторинга между процессами
Использует файл для синхронизации состояния
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

MONITOR_STATUS_FILE = 'monitor_status.json'

class MonitorManager:
    """Управление статусом мониторинга через файл"""
    
    @staticmethod
    def set_status(is_active: bool, chat_ids: Optional[list] = None, stats: Optional[Dict] = None):
        """Установить статус мониторинга"""
        status = {
            'is_active': is_active,
            'last_updated': datetime.now().isoformat(),
            'chat_ids': chat_ids or [],
            'mode': 'selected' if chat_ids else 'all',
            'stats': stats or {}
        }
        
        try:
            with open(MONITOR_STATUS_FILE, 'w') as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Error saving monitor status: {e}")
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Получить текущий статус мониторинга"""
        if not os.path.exists(MONITOR_STATUS_FILE):
            return {
                'is_active': False,
                'last_updated': None,
                'chat_ids': [],
                'mode': 'all',
                'stats': {}
            }
        
        try:
            with open(MONITOR_STATUS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                'is_active': False,
                'last_updated': None,
                'chat_ids': [],
                'mode': 'all',
                'stats': {}
            }
    
    @staticmethod
    def update_stats(edited: int = 0, deleted: int = 0):
        """Обновить статистику мониторинга"""
        status = MonitorManager.get_status()
        
        if 'stats' not in status:
            status['stats'] = {}
        
        status['stats']['edited'] = status['stats'].get('edited', 0) + edited
        status['stats']['deleted'] = status['stats'].get('deleted', 0) + deleted
        status['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(MONITOR_STATUS_FILE, 'w') as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Error updating monitor stats: {e}")