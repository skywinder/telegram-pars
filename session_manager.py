"""
Менеджер сессий для хранения недавних чатов и пользовательских настроек
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SessionManager:
    def __init__(self, session_file: str = "user_session.json"):
        self.session_file = session_file
        self.session_data = self._load_session()
        
    def _load_session(self) -> Dict:
        """Загружает данные сессии из файла"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Структура по умолчанию
        return {
            'recent_chats': [],
            'favorite_chats': [],
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_session(self):
        """Сохраняет данные сессии в файл"""
        self.session_data['last_updated'] = datetime.now().isoformat()
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
    
    def add_recent_chat(self, chat_id: int, chat_name: str, chat_type: str = 'private'):
        """Добавляет чат в недавние"""
        recent_chats = self.session_data.get('recent_chats', [])
        
        # Удаляем если уже есть в списке
        recent_chats = [c for c in recent_chats if c['id'] != chat_id]
        
        # Добавляем в начало
        recent_chats.insert(0, {
            'id': chat_id,
            'name': chat_name,
            'type': chat_type,
            'last_visited': datetime.now().isoformat(),
            'visit_count': self._get_visit_count(chat_id) + 1
        })
        
        # Ограничиваем количество недавних чатов
        self.session_data['recent_chats'] = recent_chats[:20]
        self._save_session()
    
    def _get_visit_count(self, chat_id: int) -> int:
        """Получает количество посещений чата"""
        for chat in self.session_data.get('recent_chats', []):
            if chat['id'] == chat_id:
                return chat.get('visit_count', 0)
        return 0
    
    def get_recent_chats(self, limit: int = 10) -> List[Dict]:
        """Возвращает список недавних чатов"""
        recent = self.session_data.get('recent_chats', [])
        
        # Фильтруем слишком старые (более 30 дней)
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered = []
        
        for chat in recent[:limit]:
            try:
                visit_date = datetime.fromisoformat(chat['last_visited'])
                if visit_date > cutoff_date:
                    filtered.append(chat)
            except:
                pass
                
        return filtered
    
    def remove_recent_chat(self, chat_id: int):
        """Удаляет чат из недавних"""
        self.session_data['recent_chats'] = [
            c for c in self.session_data.get('recent_chats', []) 
            if c['id'] != chat_id
        ]
        self._save_session()
    
    def toggle_favorite_chat(self, chat_id: int, chat_name: str, chat_type: str = 'private') -> bool:
        """Переключает статус избранного чата. Возвращает True если добавлен, False если удален"""
        favorites = self.session_data.get('favorite_chats', [])
        
        # Проверяем есть ли уже в избранном
        existing = next((f for f in favorites if f['id'] == chat_id), None)
        
        if existing:
            # Удаляем из избранного
            self.session_data['favorite_chats'] = [
                f for f in favorites if f['id'] != chat_id
            ]
            self._save_session()
            return False
        else:
            # Добавляем в избранное
            favorites.append({
                'id': chat_id,
                'name': chat_name,
                'type': chat_type,
                'added_at': datetime.now().isoformat()
            })
            self.session_data['favorite_chats'] = favorites
            self._save_session()
            return True
    
    def get_favorite_chats(self) -> List[Dict]:
        """Возвращает список избранных чатов"""
        return self.session_data.get('favorite_chats', [])
    
    def is_favorite(self, chat_id: int) -> bool:
        """Проверяет является ли чат избранным"""
        favorites = self.session_data.get('favorite_chats', [])
        return any(f['id'] == chat_id for f in favorites)
    
    def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """Получает информацию о чате из недавних или избранных"""
        # Сначала ищем в недавних
        for chat in self.session_data.get('recent_chats', []):
            if chat['id'] == chat_id:
                return chat
        
        # Потом в избранных
        for chat in self.session_data.get('favorite_chats', []):
            if chat['id'] == chat_id:
                return chat
                
        return None
    
    def clear_recent_chats(self):
        """Очищает список недавних чатов"""
        self.session_data['recent_chats'] = []
        self._save_session()
    
    def get_stats(self) -> Dict:
        """Возвращает статистику по сессии"""
        return {
            'recent_count': len(self.session_data.get('recent_chats', [])),
            'favorite_count': len(self.session_data.get('favorite_chats', [])),
            'last_updated': self.session_data.get('last_updated', 'Unknown')
        }