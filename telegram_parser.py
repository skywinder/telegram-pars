"""
Telegram Parser - основная логика парсинга чатов
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from telethon import TelegramClient
from telethon.tl.types import Message
import config

class TelegramParser:
    """
    Класс для парсинга чатов Telegram
    """
    
    def __init__(self):
        """Инициализация парсера"""
        self.client = None
        self.session_name = 'telegram_parser_session'
        
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
            
        print(f"📁 Найдено {len(chats)} чатов")
        return chats
    
    async def parse_chat_messages(self, chat_id: int, limit: int = None) -> List[Dict]:
        """
        Парсим сообщения из конкретного чата
        
        Args:
            chat_id: ID чата
            limit: Максимальное количество сообщений (по умолчанию из config)
        """
        if limit is None:
            limit = config.MAX_MESSAGES
            
        print(f"💬 Парсим сообщения из чата {chat_id} (лимит: {limit})...")
        
        messages = []
        async for message in self.client.iter_messages(chat_id, limit=limit):
            if isinstance(message, Message):
                message_data = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'text': message.text or '',
                    'sender_id': message.sender_id,
                    'chat_id': chat_id,
                    'reply_to': message.reply_to_msg_id if message.reply_to else None,
                    'media_type': type(message.media).__name__ if message.media else None
                }
                messages.append(message_data)
                
        print(f"✅ Спарсили {len(messages)} сообщений")
        return messages
    
    async def parse_all_chats(self) -> Dict[str, Any]:
        """
        Парсим все доступные чаты
        """
        print("🚀 Начинаем полный парсинг всех чатов...")
        
        # Получаем список чатов
        chats = await self.get_chats_list()
        
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'total_chats': len(chats),
            'chats': {}
        }
        
        # Парсим каждый чат
        for i, chat in enumerate(chats, 1):
            print(f"\n📊 Прогресс: {i}/{len(chats)} - Парсим '{chat['name']}'")
            
            try:
                messages = await self.parse_chat_messages(chat['id'])
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'messages': messages,
                    'total_messages': len(messages)
                }
            except Exception as e:
                print(f"❌ Ошибка при парсинге чата '{chat['name']}': {e}")
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'error': str(e),
                    'messages': [],
                    'total_messages': 0
                }
        
        return all_data
    
    async def close(self):
        """Закрываем соединение"""
        if self.client:
            await self.client.disconnect()
            print("👋 Отключились от Telegram")