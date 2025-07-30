"""
Telegram Parser - основная логика парсинга чатов
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from telethon import TelegramClient
from telethon.tl.types import Message, User, Chat, Channel
from database import TelegramDatabase
import config

class TelegramParser:
    """
    Класс для парсинга чатов Telegram
    """
    
    def __init__(self):
        """Инициализация парсера"""
        self.client = None
        self.session_name = 'telegram_parser_session'
        self.db = None
        if config.ENABLE_HISTORY_TRACKING:
            db_path = os.path.join(config.OUTPUT_DIR, config.DB_FILENAME)
            self.db = TelegramDatabase(db_path)
        
    async def initialize(self):
        """
        Подключение к Telegram
        """
        print("🔗 Подключаемся к Telegram...")
        
        # Создаем клиента Telegram
        self.client = TelegramClient(
            self.session_name, 
            config.API_ID, 
            config.API_HASH
        )
        
        # Подключаемся
        await self.client.start(phone=config.PHONE_NUMBER)
        print("✅ Успешно подключились к Telegram!")
        
    async def get_chats_list(self) -> List[Dict]:
        """
        Получаем список всех доступных чатов
        """
        print("📋 Получаем список чатов...")
        chats = []
        
        async for dialog in self.client.iter_dialogs():
            chat_info = {
                'id': dialog.id,
                'name': dialog.name,
                'type': type(dialog.entity).__name__,
                'unread_count': dialog.unread_count
            }
            chats.append(chat_info)
            
            # Сохраняем информацию о чате в БД
            if self.db:
                self.db.save_chat(chat_info)
            
        print(f"📁 Найдено {len(chats)} чатов")
        return chats
    
    async def parse_chat_messages(self, chat_id: int, limit: int = None, session_id: str = None) -> List[Dict]:
        """
        Парсим сообщения из конкретного чата с отслеживанием изменений
        
        Args:
            chat_id: ID чата
            limit: Максимальное количество сообщений (по умолчанию из config)
            session_id: ID сессии парсинга для трекинга изменений
        """
        if limit is None:
            limit = config.MAX_MESSAGES
            
        print(f"💬 Парсим сообщения из чата {chat_id} (лимит: {limit})...")
        
        messages = []
        current_message_ids = []
        
        async for message in self.client.iter_messages(chat_id, limit=limit):
            if isinstance(message, Message):
                # Сохраняем информацию об отправителе
                if message.sender and self.db:
                    await self._save_user_info(message.sender)
                
                message_data = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'text': message.text or '',
                    'sender_id': message.sender_id,
                    'chat_id': chat_id,
                    'reply_to': message.reply_to_msg_id if message.reply_to else None,
                    'media_type': type(message.media).__name__ if message.media else None,
                    'views': getattr(message, 'views', 0),
                    'forwards': getattr(message, 'forwards', 0)
                }
                
                messages.append(message_data)
                current_message_ids.append(message.id)
                
                # Сохраняем в БД с отслеживанием изменений
                if self.db and session_id:
                    self.db.save_message_with_history(message_data, session_id)
        
        # Помечаем удаленные сообщения
        if self.db and session_id:
            deleted_count = self.db.mark_deleted_messages(chat_id, current_message_ids, session_id)
            if deleted_count > 0:
                print(f"🗑️ Обнаружено {deleted_count} удаленных сообщений")
                
        print(f"✅ Спарсили {len(messages)} сообщений")
        return messages
    
    async def parse_all_chats(self) -> Dict[str, Any]:
        """
        Парсим все доступные чаты с отслеживанием изменений
        """
        print("🚀 Начинаем полный парсинг всех чатов...")
        
        # Создаем сессию парсинга
        session_id = None
        if self.db:
            session_id = self.db.create_scan_session()
        
        # Получаем список чатов
        chats = await self.get_chats_list()
        
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'total_chats': len(chats),
            'chats': {},
            'session_id': session_id
        }
        
        changes_detected = 0
        total_messages = 0
        
        # Парсим каждый чат
        for i, chat in enumerate(chats, 1):
            print(f"\n📊 Прогресс: {i}/{len(chats)} - Парсим '{chat['name']}'")
            
            try:
                messages = await self.parse_chat_messages(chat['id'], session_id=session_id)
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'messages': messages,
                    'total_messages': len(messages)
                }
                total_messages += len(messages)
                
            except Exception as e:
                print(f"❌ Ошибка при парсинге чата '{chat['name']}': {e}")
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'error': str(e),
                    'messages': [],
                    'total_messages': 0
                }
        
        # Закрываем сессию парсинга
        if self.db and session_id:
            stats = {
                'total_chats': len(chats),
                'total_messages': total_messages,
                'changes_detected': changes_detected
            }
            self.db.close_scan_session(session_id, stats)
            
            # Получаем сводку изменений
            changes_summary = self.db.get_changes_summary()
            all_data['changes_summary'] = changes_summary
        
        return all_data
    
    async def _save_user_info(self, user):
        """Сохраняет информацию о пользователе"""
        if not isinstance(user, User) or not self.db:
            return
            
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute('''
                INSERT OR IGNORE INTO users (id, username, first_name, last_name, phone)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user.id,
                getattr(user, 'username', None),
                getattr(user, 'first_name', None),
                getattr(user, 'last_name', None),
                getattr(user, 'phone', None)
            ))
    
    async def close(self):
        """Закрываем соединение"""
        if self.client:
            await self.client.disconnect()
            print("👋 Отключились от Telegram")