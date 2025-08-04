"""
Менеджер уведомлений для отправки изменений в веб-интерфейс
Использует Server-Sent Events для real-time обновлений
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from queue import Queue
import threading
from json_utils import safe_json_dumps

class NotificationManager:
    """Управляет уведомлениями и очередью событий"""
    
    def __init__(self):
        self.listeners = []  # Список активных SSE подключений
        self.event_queue = Queue()  # Очередь событий
        self.is_running = False
        self._lock = threading.Lock()
        
    def add_listener(self, queue):
        """Добавляет нового слушателя"""
        with self._lock:
            self.listeners.append(queue)
            
    def remove_listener(self, queue):
        """Удаляет слушателя"""
        with self._lock:
            if queue in self.listeners:
                self.listeners.remove(queue)
                
    def notify(self, event_type: str, data: Dict[str, Any]):
        """Отправляет уведомление всем слушателям"""
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Добавляем в очередь
        self.event_queue.put(event)
        
        # Отправляем всем активным слушателям
        with self._lock:
            dead_listeners = []
            for listener_queue in self.listeners:
                try:
                    listener_queue.put_nowait(safe_json_dumps(event))
                except:
                    # Если не удалось отправить, помечаем для удаления
                    dead_listeners.append(listener_queue)
                    
            # Удаляем неактивные подключения
            for dead in dead_listeners:
                self.listeners.remove(dead)
                
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Возвращает последние события из очереди"""
        events = []
        temp_queue = Queue()
        
        # Переносим события во временную очередь
        while not self.event_queue.empty() and len(events) < limit:
            try:
                event = self.event_queue.get_nowait()
                events.append(event)
                temp_queue.put(event)
            except:
                break
                
        # Возвращаем события обратно
        while not temp_queue.empty():
            self.event_queue.put(temp_queue.get())
            
        return events

# Глобальный экземпляр менеджера уведомлений
_notification_manager = NotificationManager()

def get_notification_manager() -> NotificationManager:
    """Возвращает глобальный экземпляр менеджера уведомлений"""
    return _notification_manager