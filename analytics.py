"""
Модуль аналитики для Telegram данных
"""
import sqlite3
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json
from collections import Counter, defaultdict
import re

class TelegramAnalytics:
    """
    Класс для анализа данных Telegram
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_most_active_chats(self, limit: int = 10, days: int = None) -> List[Dict]:
        """
        Находит самые активные чаты
        
        Args:
            limit: Количество чатов в результате
            days: Период в днях (None = все время)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            date_filter = ""
            params = []
            
            if days:
                date_filter = "AND m.date > datetime('now', '-{} days')".format(days)
            
            query = f'''
                SELECT 
                    c.name as chat_name,
                    c.type as chat_type,
                    COUNT(m.id) as message_count,
                    COUNT(DISTINCT m.sender_id) as unique_users,
                    COUNT(DISTINCT DATE(m.date)) as active_days,
                    MIN(m.date) as first_message,
                    MAX(m.date) as last_message,
                    ROUND(AVG(LENGTH(m.text)), 2) as avg_message_length
                FROM chats c
                JOIN messages m ON c.id = m.chat_id
                WHERE m.is_deleted = FALSE {date_filter}
                GROUP BY c.id, c.name, c.type
                ORDER BY message_count DESC
                LIMIT ?
            '''
            
            params.append(limit)
            results = conn.execute(query, params).fetchall()
            
            return [dict(row) for row in results]
    
    def get_activity_by_time(self, chat_id: int = None) -> Dict:
        """
        Анализирует активность по времени (часы, дни недели)
        """
        with sqlite3.connect(self.db_path) as conn:
            chat_filter = f"AND chat_id = {chat_id}" if chat_id else ""
            
            # Активность по часам
            hours_query = f'''
                SELECT 
                    strftime('%H', date) as hour,
                    COUNT(*) as message_count
                FROM messages 
                WHERE is_deleted = FALSE {chat_filter}
                GROUP BY hour
                ORDER BY hour
            '''
            
            # Активность по дням недели (0=воскресенье, 6=суббота)
            weekdays_query = f'''
                SELECT 
                    strftime('%w', date) as weekday,
                    COUNT(*) as message_count
                FROM messages 
                WHERE is_deleted = FALSE {chat_filter}
                GROUP BY weekday
                ORDER BY weekday
            '''
            
            hours_data = conn.execute(hours_query).fetchall()
            weekdays_data = conn.execute(weekdays_query).fetchall()
            
            # Преобразуем дни недели в названия
            weekday_names = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 
                           'Четверг', 'Пятница', 'Суббота']
            
            return {
                'by_hour': [{'hour': int(h), 'count': c} for h, c in hours_data],
                'by_weekday': [
                    {'weekday': weekday_names[int(w)], 'count': c} 
                    for w, c in weekdays_data
                ]
            }
    
    def analyze_conversation_topics(self, chat_id: int = None, min_word_length: int = 4) -> Dict:
        """
        Анализирует темы разговоров через частотность слов
        """
        with sqlite3.connect(self.db_path) as conn:
            chat_filter = f"AND chat_id = {chat_id}" if chat_id else ""
            
            messages = conn.execute(f'''
                SELECT text FROM messages 
                WHERE is_deleted = FALSE AND text IS NOT NULL 
                AND LENGTH(text) > 10 {chat_filter}
            ''').fetchall()
            
            # Обработка текста
            word_counter = Counter()
            total_messages = len(messages)
            
            # Стоп-слова (можно расширить)
            stop_words = {'что', 'как', 'где', 'когда', 'кто', 'это', 'для', 'или', 
                         'так', 'уже', 'все', 'еще', 'вот', 'там', 'тут', 'она', 
                         'они', 'его', 'ему', 'нее', 'них', 'мне', 'нас', 'вас',
                         'the', 'and', 'you', 'that', 'was', 'for', 'are', 'with'}
            
            for (text,) in messages:
                if text:
                    # Извлекаем слова (только буквы, минимум 4 символа)
                    words = re.findall(r'\b[а-яёa-z]{' + str(min_word_length) + ',}\b', 
                                     text.lower())
                    
                    # Фильтруем стоп-слова
                    filtered_words = [w for w in words if w not in stop_words]
                    word_counter.update(filtered_words)
            
            # Топ слов
            top_words = word_counter.most_common(50)
            
            return {
                'total_messages_analyzed': total_messages,
                'unique_words': len(word_counter),
                'top_words': [{'word': word, 'count': count} for word, count in top_words],
                'word_frequency': dict(word_counter)
            }
    
    def get_user_statistics(self, chat_id: int = None) -> List[Dict]:
        """
        Статистика по пользователям
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            chat_filter = f"AND m.chat_id = {chat_id}" if chat_id else ""
            
            query = f'''
                SELECT 
                    u.id as user_id,
                    COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '') as full_name,
                    u.username,
                    COUNT(m.id) as message_count,
                    MIN(m.date) as first_message,
                    MAX(m.date) as last_message,
                    ROUND(AVG(LENGTH(m.text)), 2) as avg_message_length,
                    COUNT(CASE WHEN m.media_type IS NOT NULL THEN 1 END) as media_messages
                FROM users u
                JOIN messages m ON u.id = m.sender_id
                WHERE m.is_deleted = FALSE {chat_filter}
                GROUP BY u.id, u.first_name, u.last_name, u.username
                ORDER BY message_count DESC
            '''
            
            results = conn.execute(query).fetchall()
            return [dict(row) for row in results]
    
    def get_message_changes_analytics(self) -> Dict:
        """
        Анализ изменений сообщений (редактирования, удаления)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Общая статистика изменений
            changes_stats = conn.execute('''
                SELECT 
                    action_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT chat_id) as affected_chats,
                    COUNT(DISTINCT message_id) as affected_messages
                FROM message_history
                GROUP BY action_type
            ''').fetchall()
            
            # Чаты с наибольшим количеством изменений
            most_edited_chats = conn.execute('''
                SELECT 
                    c.name as chat_name,
                    COUNT(mh.id) as total_changes,
                    COUNT(CASE WHEN mh.action_type = 'edited' THEN 1 END) as edits,
                    COUNT(CASE WHEN mh.action_type = 'deleted' THEN 1 END) as deletions
                FROM message_history mh
                JOIN chats c ON mh.chat_id = c.id
                GROUP BY c.id, c.name
                ORDER BY total_changes DESC
                LIMIT 10
            ''').fetchall()
            
            # Активность изменений по времени (последние 30 дней)
            recent_changes = conn.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    action_type,
                    COUNT(*) as count
                FROM message_history
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY DATE(timestamp), action_type
                ORDER BY date DESC
            ''').fetchall()
            
            return {
                'changes_summary': [dict(row) for row in changes_stats],
                'most_active_chats': [dict(row) for row in most_edited_chats],
                'recent_activity': [dict(row) for row in recent_changes]
            }
    
    def generate_chat_report(self, chat_id: int) -> Dict:
        """
        Генерирует полный отчет по чату
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Базовая информация о чате
            chat_info = conn.execute('''
                SELECT name, type FROM chats WHERE id = ?
            ''', (chat_id,)).fetchone()
            
            if not chat_info:
                return {'error': 'Chat not found'}
            
            # Собираем все данные
            report = {
                'chat_info': dict(chat_info),
                'chat_id': chat_id,
                'generated_at': datetime.now().isoformat(),
                'activity_stats': self.get_most_active_chats(limit=1)[0] if self.get_most_active_chats(limit=1) else {},
                'time_analysis': self.get_activity_by_time(chat_id),
                'topic_analysis': self.analyze_conversation_topics(chat_id),
                'user_stats': self.get_user_statistics(chat_id),
                'changes_analytics': self.get_message_changes_analytics()
            }
            
            return report
    
    def generate_ai_friendly_summary(self, chat_id: int = None, max_messages: int = 100) -> Dict:
        """
        Создает сводку, оптимизированную для анализа ИИ
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            chat_filter = f"AND m.chat_id = {chat_id}" if chat_id else ""
            
            # Получаем недавние сообщения
            recent_messages = conn.execute(f'''
                SELECT 
                    m.text,
                    m.date,
                    u.first_name,
                    u.username,
                    c.name as chat_name
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                LEFT JOIN chats c ON m.chat_id = c.id
                WHERE m.is_deleted = FALSE 
                AND m.text IS NOT NULL 
                AND LENGTH(m.text) > 5 {chat_filter}
                ORDER BY m.date DESC
                LIMIT ?
            ''', (max_messages,)).fetchall()
            
            # Статистика для контекста
            stats = self.get_most_active_chats(limit=5)
            topics = self.analyze_conversation_topics(chat_id)
            
            return {
                'summary_type': 'ai_analysis_ready',
                'created_at': datetime.now().isoformat(),
                'context': {
                    'chat_id': chat_id,
                    'message_count': len(recent_messages),
                    'active_chats_context': stats,
                    'detected_topics': topics['top_words'][:20] if topics else []
                },
                'messages_for_analysis': [
                    {
                        'text': msg['text'],
                        'date': msg['date'],
                        'author': msg['first_name'] or msg['username'] or 'Unknown',
                        'chat': msg['chat_name']
                    }
                    for msg in recent_messages
                ],
                'analysis_prompts': [
                    "Проанализируй стиль общения в этих сообщениях",
                    "Какие основные темы обсуждаются?",
                    "Какова эмоциональная окраска сообщений?",
                    "Есть ли повторяющиеся паттерны в общении?",
                    "Какие выводы можно сделать о характере участников?"
                ]
            }