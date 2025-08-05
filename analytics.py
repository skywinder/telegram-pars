"""
Модуль аналитики для Telegram данных
"""
import sqlite3
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json
from collections import Counter, defaultdict
import re
import emoji

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
                    c.id as chat_id,
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

            # Стоп-слова (расширенный список)
            stop_words = {'что', 'как', 'где', 'когда', 'кто', 'это', 'для', 'или',
                         'так', 'уже', 'все', 'еще', 'вот', 'там', 'тут', 'она',
                         'они', 'его', 'ему', 'нее', 'них', 'мне', 'нас', 'вас',
                         'the', 'and', 'you', 'that', 'was', 'for', 'are', 'with',
                         'https', 'http', 'www', 'com', 'org', 'net', 'status',
                         'this', 'they', 'from', 'have', 'been', 'will', 'more',
                         'чем', 'тем', 'том', 'под', 'при', 'без', 'над', 'про'}

            for (text,) in messages:
                if text:
                    # Извлекаем слова (только буквы, минимум нужной длины)
                    words = re.findall(r'[а-яёa-z]+', text.lower())

                    # Фильтруем по длине и стоп-словам
                    filtered_words = [w for w in words
                                    if len(w) >= min_word_length and w not in stop_words]
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

    def get_message_changes_analytics(self, chat_id: int = None) -> Dict:
        """
        Анализ изменений сообщений (редактирования, удаления)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Фильтр для конкретного чата
            chat_filter = ""
            params = []
            if chat_id:
                chat_filter = "WHERE chat_id = ?"
                params = [chat_id]

            # Общая статистика изменений
            changes_stats = conn.execute(f'''
                SELECT
                    action_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT chat_id) as affected_chats,
                    COUNT(DISTINCT message_id) as affected_messages
                FROM message_history
                {chat_filter}
                GROUP BY action_type
            ''', params).fetchall()

            # Чаты с наибольшим количеством изменений
            if chat_id:
                # Для конкретного чата показываем статистику по дням
                most_edited_chats = conn.execute('''
                    SELECT
                        DATE(timestamp) as date,
                        COUNT(*) as total_changes,
                        COUNT(CASE WHEN action_type = 'edited' THEN 1 END) as edits,
                        COUNT(CASE WHEN action_type = 'deleted' THEN 1 END) as deletions
                    FROM message_history
                    WHERE chat_id = ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    LIMIT 30
                ''', [chat_id]).fetchall()
            else:
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
            recent_changes_query = f'''
                SELECT
                    DATE(timestamp) as date,
                    action_type,
                    COUNT(*) as count
                FROM message_history
                {chat_filter}
                {"AND" if chat_filter else "WHERE"} timestamp > datetime('now', '-30 days')
                GROUP BY DATE(timestamp), action_type
                ORDER BY date DESC
            '''
            recent_changes = conn.execute(recent_changes_query, params).fetchall()

            return {
                'changes_summary': [dict(row) for row in changes_stats],
                'most_active_chats': [dict(row) for row in most_edited_chats],
                'recent_activity': [dict(row) for row in recent_changes]
            }
    
    def get_chat_changes_count(self, chat_id: int) -> int:
        """
        Получает количество изменений для конкретного чата
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute('''
                SELECT COUNT(*) as count
                FROM message_history
                WHERE chat_id = ?
            ''', (chat_id,)).fetchone()
            
            return result['count'] if result else 0

    def get_chat_statistics(self, chat_id: int) -> Dict:
        """
        Получает статистику для конкретного чата
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            stats = conn.execute('''
                SELECT
                    c.id as chat_id,
                    c.name as chat_name,
                    c.type as chat_type,
                    COUNT(m.id) as message_count,
                    COUNT(DISTINCT m.sender_id) as unique_users,
                    COUNT(DISTINCT DATE(m.date)) as active_days,
                    MIN(m.date) as first_message,
                    MAX(m.date) as last_message,
                    ROUND(AVG(LENGTH(m.text)), 2) as avg_message_length
                FROM chats c
                LEFT JOIN messages m ON c.id = m.chat_id AND m.is_deleted = FALSE
                WHERE c.id = ?
                GROUP BY c.id
            ''', (chat_id,)).fetchone()
            
            return dict(stats) if stats else {}

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
                'activity_stats': self.get_chat_statistics(chat_id),
                'time_analysis': self.get_activity_by_time(chat_id),
                'topic_analysis': self.analyze_conversation_topics(chat_id),
                'user_stats': self.get_user_statistics(chat_id),
                'changes_analytics': self.get_message_changes_analytics(chat_id),
                'changes_count': self.get_chat_changes_count(chat_id)
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

    def analyze_conversation_starters(self, chat_id: int = None) -> Dict:
        """
        Анализирует кто чаще всего начинает диалоги
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            chat_filter = f"AND m.chat_id = {chat_id}" if chat_id else ""

            # Получаем сообщения отсортированные по времени
            messages = conn.execute(f'''
                SELECT
                    m.sender_id,
                    m.date,
                    m.text,
                    COALESCE(u.first_name, u.username, 'User_' || u.id) as sender_name
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                WHERE m.is_deleted = FALSE
                AND m.text IS NOT NULL
                AND LENGTH(m.text) > 0 {chat_filter}
                ORDER BY m.date ASC
            ''').fetchall()

            if not messages:
                return {'error': 'Нет сообщений для анализа'}

            # Анализируем инициацию диалогов
            conversation_starters = Counter()
            last_sender = None
            conversation_gaps = []  # Промежутки между сообщениями

            for i, msg in enumerate(messages):
                current_time = datetime.fromisoformat(msg['date'])

                # Если это первое сообщение или прошло много времени с последнего
                if i == 0:
                    conversation_starters[msg['sender_id']] += 1
                    last_sender = msg['sender_id']
                    continue

                prev_time = datetime.fromisoformat(messages[i-1]['date'])
                time_gap = (current_time - prev_time).total_seconds() / 3600  # в часах

                # Если прошло больше 2 часов - считаем новым диалогом
                if time_gap > 2 or msg['sender_id'] != last_sender:
                    conversation_starters[msg['sender_id']] += 1

                last_sender = msg['sender_id']
                conversation_gaps.append(time_gap)

            # Статистика по пользователям
            total_conversations = sum(conversation_starters.values())
            starter_stats = []

            for sender_id, count in conversation_starters.most_common():
                sender_name = next((msg['sender_name'] for msg in messages if msg['sender_id'] == sender_id), f'User_{sender_id}')
                percentage = (count / total_conversations) * 100
                starter_stats.append({
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'conversations_started': count,
                    'percentage': round(percentage, 1)
                })

            return {
                'total_conversations': total_conversations,
                'conversation_starters': starter_stats,
                'average_gap_hours': round(sum(conversation_gaps) / len(conversation_gaps), 2) if conversation_gaps else 0,
                'analysis_period': {
                    'from': messages[0]['date'] if messages else None,
                    'to': messages[-1]['date'] if messages else None,
                    'total_messages': len(messages)
                }
            }

    def analyze_emoji_and_expressions(self, chat_id: int = None) -> Dict:
        """
        Анализирует использование эмодзи, гифок и текстовых смайликов
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            chat_filter = f"AND m.chat_id = {chat_id}" if chat_id else ""

            # Получаем сообщения с текстом
            messages = conn.execute(f'''
                SELECT
                    m.sender_id,
                    m.text,
                    m.media_type,
                    COALESCE(u.first_name, u.username, 'User_' || u.id) as sender_name
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                WHERE m.is_deleted = FALSE
                AND m.text IS NOT NULL {chat_filter}
            ''').fetchall()

            # Паттерны для текстовых смайликов
            text_smilies = [
                r':\)', r':\(', r':D', r':P', r':p', r';\)', r':\|',
                r'=\)', r'=\(', r'=D', r'=P', r'=p', r';\(',
                r'xD', r'XD', r':o', r':O', r':\*', r'<3',
                r'\)\)', r'\(\(', r':\/', r':\\', r':\|',
                r':-\)', r':-\(', r':-D', r':-P', r':-p', r';\-\)',
                r':-\|', r':-o', r':-O', r':\-\*'
            ]

            # Статистика по пользователям
            user_stats = defaultdict(lambda: {
                'total_messages': 0,
                'emoji_count': 0,
                'emoji_messages': 0,
                'text_smilies_count': 0,
                'text_smilies_messages': 0,
                'gif_sticker_messages': 0,
                'unique_emojis': set(),
                'sender_name': ''
            })

            all_emojis = Counter()
            all_text_smilies = Counter()

            for msg in messages:
                sender_id = msg['sender_id']
                text = msg['text'] or ''
                media_type = msg['media_type'] or ''

                user_stats[sender_id]['total_messages'] += 1
                user_stats[sender_id]['sender_name'] = msg['sender_name']

                # Анализ эмодзи
                emojis_in_msg = [char for char in text if char in emoji.EMOJI_DATA]
                if emojis_in_msg:
                    user_stats[sender_id]['emoji_messages'] += 1
                    user_stats[sender_id]['emoji_count'] += len(emojis_in_msg)
                    user_stats[sender_id]['unique_emojis'].update(emojis_in_msg)
                    all_emojis.update(emojis_in_msg)

                # Анализ текстовых смайликов
                text_smilies_found = []
                for smiley_pattern in text_smilies:
                    matches = re.findall(smiley_pattern, text)
                    text_smilies_found.extend(matches)

                if text_smilies_found:
                    user_stats[sender_id]['text_smilies_messages'] += 1
                    user_stats[sender_id]['text_smilies_count'] += len(text_smilies_found)
                    all_text_smilies.update(text_smilies_found)

                # Анализ гифок и стикеров
                if 'gif' in media_type.lower() or 'sticker' in media_type.lower():
                    user_stats[sender_id]['gif_sticker_messages'] += 1

            # Преобразуем в удобный формат
            result_stats = []
            for sender_id, stats in user_stats.items():
                if stats['total_messages'] > 0:
                    emoji_freq = (stats['emoji_messages'] / stats['total_messages']) * 100
                    text_smiley_freq = (stats['text_smilies_messages'] / stats['total_messages']) * 100
                    gif_freq = (stats['gif_sticker_messages'] / stats['total_messages']) * 100

                    result_stats.append({
                        'sender_id': sender_id,
                        'sender_name': stats['sender_name'],
                        'total_messages': stats['total_messages'],
                        'emoji_usage': {
                            'messages_with_emoji': stats['emoji_messages'],
                            'total_emoji_count': stats['emoji_count'],
                            'emoji_frequency_percent': round(emoji_freq, 1),
                            'unique_emojis_count': len(stats['unique_emojis']),
                            'avg_emoji_per_message': round(stats['emoji_count'] / stats['total_messages'], 2)
                        },
                        'text_smilies_usage': {
                            'messages_with_smilies': stats['text_smilies_messages'],
                            'total_smilies_count': stats['text_smilies_count'],
                            'smilies_frequency_percent': round(text_smiley_freq, 1)
                        },
                        'gif_sticker_usage': {
                            'gif_sticker_messages': stats['gif_sticker_messages'],
                            'gif_frequency_percent': round(gif_freq, 1)
                        }
                    })

            # Сортируем по общей частоте использования эмодзи
            result_stats.sort(key=lambda x: x['emoji_usage']['emoji_frequency_percent'], reverse=True)

            return {
                'user_expression_stats': result_stats,
                'global_stats': {
                    'most_used_emojis': [{'emoji': e, 'count': c} for e, c in all_emojis.most_common(20)],
                    'most_used_text_smilies': [{'smiley': s, 'count': c} for s, c in all_text_smilies.most_common(10)],
                    'total_unique_emojis': len(all_emojis),
                    'total_messages_analyzed': sum(stats['total_messages'] for stats in user_stats.values())
                }
            }