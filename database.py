"""
База данных для трекинга истории сообщений Telegram
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import config
import os

class TelegramDatabase:
    """
    Класс для работы с базой данных истории сообщений
    """
    
    def __init__(self, db_path: str = None):
        """Инициализация базы данных"""
        if db_path is None:
            # Создаем папку для БД если её нет
            if not os.path.exists(config.OUTPUT_DIR):
                os.makedirs(config.OUTPUT_DIR)
            db_path = os.path.join(config.OUTPUT_DIR, 'telegram_history.db')
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Создание таблиц в базе данных"""
        print(f"🗄️ Инициализация базы данных: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- Таблица чатов
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 0
                );
                
                -- Таблица пользователей
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Основная таблица сообщений
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER,
                    chat_id INTEGER NOT NULL,
                    sender_id INTEGER,
                    date TIMESTAMP NOT NULL,
                    text TEXT,
                    media_type TEXT,
                    reply_to_msg_id INTEGER,
                    views INTEGER,
                    forwards INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (id, chat_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (id),
                    FOREIGN KEY (sender_id) REFERENCES users (id)
                );
                
                -- История изменений сообщений
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL, -- 'created', 'edited', 'deleted'
                    old_text TEXT,
                    new_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scan_session TEXT, -- ID сессии парсинга
                    FOREIGN KEY (message_id, chat_id) REFERENCES messages (id, chat_id)
                );
                
                -- Реакции на сообщения
                CREATE TABLE IF NOT EXISTS message_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER,
                    reaction TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scan_session TEXT,
                    FOREIGN KEY (message_id, chat_id) REFERENCES messages (id, chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );
                
                -- Сессии парсинга для отслеживания изменений
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id TEXT PRIMARY KEY,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_chats INTEGER,
                    total_messages INTEGER,
                    changes_detected INTEGER DEFAULT 0
                );
                
                -- Индексы для быстрого поиска
                CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, date);
                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
                CREATE INDEX IF NOT EXISTS idx_history_message ON message_history(message_id, chat_id);
                CREATE INDEX IF NOT EXISTS idx_reactions_message ON message_reactions(message_id, chat_id);
            ''')
        
        print("✅ База данных инициализирована")
    
    def create_scan_session(self) -> str:
        """Создает новую сессию парсинга"""
        session_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO scan_sessions (id, start_time)
                VALUES (?, ?)
            ''', (session_id, datetime.now()))
        
        print(f"🔄 Создана сессия парсинга: {session_id}")
        return session_id
    
    def save_chat(self, chat_data: Dict) -> None:
        """Сохраняет информацию о чате"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO chats (id, name, type, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (
                chat_data['id'],
                chat_data['name'],
                chat_data['type'],
                datetime.now()
            ))
    
    def save_message_with_history(self, message_data: Dict, session_id: str) -> None:
        """
        Сохраняет сообщение и отслеживает изменения
        """
        message_id = message_data['id']
        chat_id = message_data['chat_id']
        current_text = message_data.get('text', '')
        
        with sqlite3.connect(self.db_path) as conn:
            # Проверяем, есть ли уже это сообщение
            existing = conn.execute('''
                SELECT text, is_deleted FROM messages 
                WHERE id = ? AND chat_id = ?
            ''', (message_id, chat_id)).fetchone()
            
            if existing:
                old_text, is_deleted = existing
                
                # Проверяем изменения
                if old_text != current_text and not is_deleted:
                    # Сообщение было отредактировано
                    self._log_message_change(
                        conn, message_id, chat_id, 'edited',
                        old_text, current_text, session_id
                    )
                    print(f"📝 Обнаружено редактирование сообщения {message_id}")
                
                # Обновляем сообщение
                conn.execute('''
                    UPDATE messages SET 
                        text = ?, date = ?, media_type = ?, 
                        reply_to_msg_id = ?, views = ?, forwards = ?
                    WHERE id = ? AND chat_id = ?
                ''', (
                    current_text,
                    message_data.get('date'),
                    message_data.get('media_type'),
                    message_data.get('reply_to'),
                    message_data.get('views', 0),
                    message_data.get('forwards', 0),
                    message_id,
                    chat_id
                ))
            else:
                # Новое сообщение
                conn.execute('''
                    INSERT INTO messages 
                    (id, chat_id, sender_id, date, text, media_type, 
                     reply_to_msg_id, views, forwards)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_id,
                    chat_id,
                    message_data.get('sender_id'),
                    message_data.get('date'),
                    current_text,
                    message_data.get('media_type'),
                    message_data.get('reply_to'),
                    message_data.get('views', 0),
                    message_data.get('forwards', 0)
                ))
                
                # Логируем создание
                self._log_message_change(
                    conn, message_id, chat_id, 'created',
                    None, current_text, session_id
                )
    
    def mark_deleted_messages(self, chat_id: int, current_message_ids: List[int], session_id: str) -> int:
        """
        Помечает сообщения как удаленные, если их нет в текущем парсинге
        """
        with sqlite3.connect(self.db_path) as conn:
            if current_message_ids:
                # Находим сообщения, которых нет в текущем списке
                placeholders = ','.join(['?' for _ in current_message_ids])
                deleted_messages = conn.execute(f'''
                    SELECT id, text FROM messages 
                    WHERE chat_id = ? AND is_deleted = FALSE 
                    AND id NOT IN ({placeholders})
                ''', [chat_id] + current_message_ids).fetchall()
            else:
                # Если нет текущих сообщений, все помечаем как удаленные
                deleted_messages = conn.execute('''
                    SELECT id, text FROM messages 
                    WHERE chat_id = ? AND is_deleted = FALSE
                ''', (chat_id,)).fetchall()
            
            # Помечаем как удаленные и логируем
            deleted_count = 0
            for msg_id, old_text in deleted_messages:
                conn.execute('''
                    UPDATE messages SET is_deleted = TRUE 
                    WHERE id = ? AND chat_id = ?
                ''', (msg_id, chat_id))
                
                self._log_message_change(
                    conn, msg_id, chat_id, 'deleted',
                    old_text, None, session_id
                )
                deleted_count += 1
            
            if deleted_count > 0:
                print(f"🗑️ Помечено как удаленные: {deleted_count} сообщений")
            
            return deleted_count
    
    def _log_message_change(self, conn, message_id: int, chat_id: int, 
                           action: str, old_text: str, new_text: str, session_id: str):
        """Логирует изменение сообщения"""
        conn.execute('''
            INSERT INTO message_history 
            (message_id, chat_id, action_type, old_text, new_text, scan_session)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, chat_id, action, old_text, new_text, session_id))
    
    def get_chat_statistics(self) -> List[Dict]:
        """Получает статистику по чатам"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            stats = conn.execute('''
                SELECT 
                    c.id, c.name, c.type,
                    COUNT(m.id) as total_messages,
                    COUNT(DISTINCT m.sender_id) as unique_senders,
                    MIN(m.date) as first_message,
                    MAX(m.date) as last_message,
                    COUNT(CASE WHEN mh.action_type = 'edited' THEN 1 END) as edited_count,
                    COUNT(CASE WHEN mh.action_type = 'deleted' THEN 1 END) as deleted_count
                FROM chats c
                LEFT JOIN messages m ON c.id = m.chat_id AND m.is_deleted = FALSE
                LEFT JOIN message_history mh ON m.id = mh.message_id AND m.chat_id = mh.chat_id
                GROUP BY c.id, c.name, c.type
                ORDER BY total_messages DESC
            ''').fetchall()
            
            return [dict(row) for row in stats]
    
    def get_changes_summary(self, days: int = 7) -> Dict:
        """Получает сводку изменений за последние дни"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Изменения за период
            changes = conn.execute('''
                SELECT 
                    action_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT chat_id) as affected_chats
                FROM message_history 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY action_type
            '''.format(days)).fetchall()
            
            # Самые активные чаты по изменениям
            active_chats = conn.execute('''
                SELECT 
                    c.name,
                    COUNT(mh.id) as changes_count
                FROM message_history mh
                JOIN chats c ON mh.chat_id = c.id
                WHERE mh.timestamp > datetime('now', '-{} days')
                GROUP BY c.id, c.name
                ORDER BY changes_count DESC
                LIMIT 10
            '''.format(days)).fetchall()
            
            return {
                'period_days': days,
                'changes_by_type': [dict(row) for row in changes],
                'most_active_chats': [dict(row) for row in active_chats]
            }
    
    def close_scan_session(self, session_id: str, stats: Dict):
        """Закрывает сессию парсинга"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE scan_sessions SET 
                    end_time = ?, 
                    total_chats = ?, 
                    total_messages = ?,
                    changes_detected = ?
                WHERE id = ?
            ''', (
                datetime.now(),
                stats.get('total_chats', 0),
                stats.get('total_messages', 0),
                stats.get('changes_detected', 0),
                session_id
            ))
        
        print(f"✅ Сессия {session_id} завершена")