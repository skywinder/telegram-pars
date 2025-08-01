"""
Модуль для мониторинга изменений сообщений в реальном времени
Отслеживает редактирование и удаление сообщений через Telegram API
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from database import TelegramDatabase
import config
from notification_manager import get_notification_manager

# Настройка логирования
logger = logging.getLogger('realtime_monitor')
logger.setLevel(logging.INFO)

# Создаем обработчик для записи в файл
file_handler = logging.FileHandler('logs/realtime_monitor.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Создаем форматтер
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(file_handler)


class RealtimeMonitor:
    """Класс для мониторинга изменений сообщений в реальном времени"""
    
    def __init__(self, client: TelegramClient, db: TelegramDatabase):
        self.client = client
        self.db = db
        self.is_running = False
        self.monitored_chats: List[int] = []
        self.callbacks = []  # Список callback функций для уведомлений
        
        # Регистрируем обработчики событий
        self._register_handlers()
        
    def _register_handlers(self):
        """Регистрирует обработчики событий Telegram"""
        
        @self.client.on(events.MessageEdited)
        async def handle_message_edited(event):
            """Обработчик редактирования сообщений"""
            try:
                # Проверяем, что чат отслеживается
                if self.monitored_chats and event.chat_id not in self.monitored_chats:
                    return
                
                # Получаем информацию о сообщении
                message_data = await self._extract_message_data(event.message)
                
                # Логируем изменение
                logger.info(f"Message edited in chat {event.chat_id}: {event.message.id}")
                
                # Сохраняем в БД
                if self.db:
                    await self._log_message_change(
                        chat_id=event.chat_id,
                        message_id=event.message.id,
                        action_type='edited',
                        old_content=None,  # Старое содержимое берется из БД
                        new_content=message_data
                    )
                
                # Вызываем callbacks
                await self._notify_callbacks('message_edited', {
                    'chat_id': event.chat_id,
                    'message_id': event.message.id,
                    'message': message_data,
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Error handling message edit: {e}")
        
        @self.client.on(events.MessageDeleted)
        async def handle_message_deleted(event):
            """Обработчик удаления сообщений"""
            try:
                # Проверяем, что чат отслеживается
                if self.monitored_chats and event.chat_id not in self.monitored_chats:
                    return
                
                # Для удаленных сообщений у нас есть только ID
                for message_id in event.deleted_ids:
                    logger.info(f"Message deleted in chat {event.chat_id}: {message_id}")
                    
                    # Сохраняем в БД
                    if self.db:
                        await self._log_message_change(
                            chat_id=event.chat_id,
                            message_id=message_id,
                            action_type='deleted',
                            old_content=None,  # Берется из БД
                            new_content=None
                        )
                    
                    # Вызываем callbacks
                    await self._notify_callbacks('message_deleted', {
                        'chat_id': event.chat_id,
                        'message_id': message_id,
                        'timestamp': datetime.now()
                    })
                    
            except Exception as e:
                logger.error(f"Error handling message deletion: {e}")
    
    async def _extract_message_data(self, message) -> Dict[str, Any]:
        """Извлекает данные из сообщения"""
        data = {
            'id': message.id,
            'text': message.text or message.message,
            'date': message.date,
            'edit_date': message.edit_date,
            'from_id': message.from_id.user_id if message.from_id else None,
            'views': message.views,
            'forwards': message.forwards,
            'media_type': None
        }
        
        # Определяем тип медиа
        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                data['media_type'] = 'photo'
            elif isinstance(message.media, MessageMediaDocument):
                data['media_type'] = 'document'
            else:
                data['media_type'] = 'other'
        
        return data
    
    async def _log_message_change(self, chat_id: int, message_id: int, 
                                 action_type: str, old_content: Optional[Dict], 
                                 new_content: Optional[Dict]):
        """Сохраняет изменение в базу данных"""
        try:
            # Создаем таблицу для логирования если её нет
            await self._ensure_changes_log_table()
            
            # Получаем старое содержимое из БД если не передано
            if old_content is None and action_type in ['edited', 'deleted']:
                old_content = await self._get_message_from_db(chat_id, message_id)
            
            # Сохраняем запись об изменении
            query = """
            INSERT INTO realtime_changes_log 
            (chat_id, message_id, action_type, old_content, new_content, 
             detected_at, user_id, chat_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Получаем информацию о чате
            chat_info = await self._get_chat_info(chat_id)
            
            import json
            import sqlite3
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    chat_id,
                    message_id,
                    action_type,
                    json.dumps(old_content, ensure_ascii=False) if old_content else None,
                    json.dumps(new_content, ensure_ascii=False) if new_content else None,
                    datetime.now().isoformat(),
                    new_content.get('from_id') if new_content else 
                        old_content.get('from_id') if old_content else None,
                    chat_info.get('name', 'Unknown')
                ))
                conn.commit()
                
            logger.info(f"Logged {action_type} for message {message_id} in chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error logging message change: {e}")
    
    async def _ensure_changes_log_table(self):
        """Создает таблицу для логирования изменений если её нет"""
        query = """
        CREATE TABLE IF NOT EXISTS realtime_changes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,  -- 'edited' или 'deleted'
            old_content TEXT,  -- JSON со старым содержимым
            new_content TEXT,  -- JSON с новым содержимым
            detected_at TEXT NOT NULL,  -- Когда обнаружено изменение
            user_id INTEGER,  -- Кто сделал изменение
            chat_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute(query)
            
            # Создаем индексы
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_realtime_changes_chat_id 
                ON realtime_changes_log(chat_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_realtime_changes_detected_at 
                ON realtime_changes_log(detected_at)
            """)
            conn.commit()
    
    async def _get_message_from_db(self, chat_id: int, message_id: int) -> Optional[Dict]:
        """Получает сообщение из базы данных"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                result = cursor.execute("""
                    SELECT * FROM messages 
                    WHERE chat_id = ? AND id = ?
                """, (chat_id, message_id)).fetchone()
                
                if result:
                    return dict(result)
                
        except Exception as e:
            logger.error(f"Error getting message from DB: {e}")
        
        return None
    
    async def _get_chat_info(self, chat_id: int) -> Dict[str, Any]:
        """Получает информацию о чате"""
        try:
            entity = await self.client.get_entity(chat_id)
            return {
                'id': chat_id,
                'name': getattr(entity, 'title', None) or 
                       getattr(entity, 'username', None) or 
                       f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip(),
                'type': entity.__class__.__name__
            }
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return {'id': chat_id, 'name': 'Unknown', 'type': 'Unknown'}
    
    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Вызывает зарегистрированные callback функции"""
        for callback in self.callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def add_callback(self, callback):
        """Добавляет callback функцию для уведомлений"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Удаляет callback функцию"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start_monitoring(self, chat_ids: Optional[List[int]] = None):
        """Запускает мониторинг изменений"""
        if self.is_running:
            logger.warning("Monitor is already running")
            return
        
        self.monitored_chats = chat_ids or []
        self.is_running = True
        
        logger.info(f"Started monitoring {len(self.monitored_chats) if self.monitored_chats else 'all'} chats")
        
        # Клиент уже должен быть запущен в основном приложении
        # Здесь мы просто отмечаем что мониторинг активен
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        logger.info("Stopped monitoring")
    
    async def get_recent_changes(self, hours: int = 24, chat_id: Optional[int] = None) -> List[Dict]:
        """Получает недавние изменения из лога"""
        try:
            import sqlite3
            from datetime import timedelta
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            query = """
            SELECT * FROM realtime_changes_log 
            WHERE detected_at > ?
            """
            params = [since]
            
            if chat_id:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            query += " ORDER BY detected_at DESC"
            
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                results = cursor.execute(query, params).fetchall()
                
                changes = []
                for row in results:
                    change = dict(row)
                    # Парсим JSON поля
                    import json
                    if change['old_content']:
                        change['old_content'] = json.loads(change['old_content'])
                    if change['new_content']:
                        change['new_content'] = json.loads(change['new_content'])
                    changes.append(change)
                
                return changes
                
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по изменениям"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                total_changes = cursor.execute(
                    "SELECT COUNT(*) FROM realtime_changes_log"
                ).fetchone()[0]
                
                # По типам
                by_type = cursor.execute("""
                    SELECT action_type, COUNT(*) as count 
                    FROM realtime_changes_log 
                    GROUP BY action_type
                """).fetchall()
                
                # Топ чатов по изменениям
                top_chats = cursor.execute("""
                    SELECT chat_name, chat_id, COUNT(*) as count 
                    FROM realtime_changes_log 
                    GROUP BY chat_id 
                    ORDER BY count DESC 
                    LIMIT 10
                """).fetchall()
                
                # За последние 24 часа
                since_24h = (datetime.now() - timedelta(hours=24)).isoformat()
                changes_24h = cursor.execute("""
                    SELECT COUNT(*) FROM realtime_changes_log 
                    WHERE detected_at > ?
                """, (since_24h,)).fetchone()[0]
                
                return {
                    'total_changes': total_changes,
                    'changes_by_type': [{'type': t[0], 'count': t[1]} for t in by_type],
                    'top_chats': [{'name': t[0], 'chat_id': t[1], 'count': t[2]} for t in top_chats],
                    'changes_24h': changes_24h,
                    'is_monitoring': self.is_running,
                    'monitored_chats_count': len(self.monitored_chats) if self.monitored_chats else 'all'
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


# Глобальный экземпляр монитора
_monitor_instance: Optional[RealtimeMonitor] = None


def get_monitor_instance() -> Optional[RealtimeMonitor]:
    """Возвращает глобальный экземпляр монитора"""
    return _monitor_instance


def set_monitor_instance(monitor: RealtimeMonitor):
    """Устанавливает глобальный экземпляр монитора"""
    global _monitor_instance
    _monitor_instance = monitor