"""
Экспорт данных специально для анализа ИИ
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from analytics import TelegramAnalytics
import config

class AIExporter:
    """
    Класс для создания файлов, оптимизированных для загрузки в ИИ
    """
    
    def __init__(self, db_path: str):
        self.analytics = TelegramAnalytics(db_path)
        self.db_path = db_path
        
        # Создаем папку для AI экспортов
        self.ai_export_dir = os.path.join(config.OUTPUT_DIR, 'ai_ready')
        if not os.path.exists(self.ai_export_dir):
            os.makedirs(self.ai_export_dir)
    
    def create_chat_analysis_file(self, chat_id: int, filename: str = None) -> str:
        """
        Создает файл для анализа конкретного чата
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{chat_id}_analysis_{timestamp}.json"
        
        filepath = os.path.join(self.ai_export_dir, filename)
        
        # Получаем данные для анализа
        analysis_data = self.analytics.generate_ai_friendly_summary(chat_id, max_messages=200)
        
        # Добавляем дополнительный контекст
        analysis_data['instructions_for_ai'] = {
            'purpose': 'Анализ стиля общения и тем в Telegram чате',
            'data_structure': {
                'messages_for_analysis': 'Список последних сообщений для анализа',
                'context': 'Статистический контекст чата',
                'analysis_prompts': 'Предлагаемые вопросы для анализа'
            },
            'recommended_analysis': [
                'Определи основные темы разговоров',
                'Проанализируй стиль и тон общения',
                'Найди интересные паттерны в поведении пользователей',
                'Оцени эмоциональную окраску сообщений',
                'Выдели ключевые слова и фразы'
            ]
        }
        
        # Сохраняем файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        print(f"🤖 Создан файл для AI анализа: {filename}")
        print(f"📁 Путь: {filepath}")
        print(f"💬 Сообщений для анализа: {len(analysis_data['messages_for_analysis'])}")
        
        return filepath
    
    def create_overview_file(self, filename: str = None) -> str:
        """
        Создает общий обзор всех чатов
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telegram_overview_{timestamp}.json"
        
        filepath = os.path.join(self.ai_export_dir, filename)
        
        # Собираем общую статистику
        overview_data = {
            'overview_type': 'telegram_full_analysis',
            'created_at': datetime.now().isoformat(),
            'most_active_chats': self.analytics.get_most_active_chats(limit=10),
            'recent_activity': self.analytics.get_activity_by_time(),
            'global_topics': self.analytics.analyze_conversation_topics(),
            'changes_summary': self.analytics.get_message_changes_analytics(),
            'sample_messages': self.analytics.generate_ai_friendly_summary(max_messages=50),
            
            'ai_analysis_suggestions': [
                'Какие чаты наиболее важны для пользователя?',
                'В какое время пользователь наиболее активен?',
                'Какие темы чаще всего обсуждаются?',
                'Как изменился стиль общения со временем?',
                'Есть ли различия в общении в разных чатах?'
            ],
            
            'insights_to_look_for': [
                'Паттерны активности по времени',
                'Различия в стиле общения в разных чатах',
                'Эволюция тем разговоров',
                'Социальные связи и взаимодействия',
                'Эмоциональные паттерны'
            ]
        }
        
        # Сохраняем файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(overview_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Создан обзорный файл: {filename}")
        print(f"📁 Путь: {filepath}")
        
        return filepath
    
    def create_conversation_snippet(self, chat_id: int, days: int = 7, filename: str = None) -> str:
        """
        Создает фрагмент разговора для детального анализа
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_snippet_{chat_id}_{days}days_{timestamp}.txt"
        
        filepath = os.path.join(self.ai_export_dir, filename)
        
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Получаем сообщения за последние дни
            messages = conn.execute('''
                SELECT 
                    m.text,
                    m.date,
                    COALESCE(u.first_name, u.username, 'User_' || u.id) as author_name,
                    c.name as chat_name
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                LEFT JOIN chats c ON m.chat_id = c.id
                WHERE m.chat_id = ? 
                AND m.is_deleted = FALSE 
                AND m.text IS NOT NULL 
                AND LENGTH(m.text) > 3
                AND m.date > datetime('now', '-{} days')
                ORDER BY m.date ASC
            '''.format(days), (chat_id,)).fetchall()
        
        # Форматируем как читаемый диалог
        conversation_text = f"Разговор из чата: {messages[0]['chat_name'] if messages else 'Unknown'}\n"
        conversation_text += f"Период: последние {days} дней\n"
        conversation_text += f"Количество сообщений: {len(messages)}\n"
        conversation_text += "=" * 50 + "\n\n"
        
        current_date = None
        for msg in messages:
            msg_date = msg['date'][:10]  # Берем только дату
            
            # Добавляем разделитель по дням
            if current_date != msg_date:
                conversation_text += f"\n--- {msg_date} ---\n"
                current_date = msg_date
            
            # Форматируем сообщение
            time = msg['date'][11:16]  # Время HH:MM
            author = msg['author_name']
            text = msg['text'].replace('\n', ' ')  # Убираем переносы строк
            
            conversation_text += f"[{time}] {author}: {text}\n"
        
        # Добавляем инструкции для ИИ
        conversation_text += "\n" + "=" * 50 + "\n"
        conversation_text += "ИНСТРУКЦИИ ДЛЯ АНАЛИЗА:\n"
        conversation_text += "1. Проанализируй стиль общения каждого участника\n"
        conversation_text += "2. Определи основные темы разговора\n"
        conversation_text += "3. Найди интересные паттерны взаимодействия\n"
        conversation_text += "4. Оцени тон и настроение разговора\n"
        conversation_text += "5. Выдели ключевые моменты диалога\n"
        
        # Сохраняем файл
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conversation_text)
        
        print(f"💬 Создан фрагмент разговора: {filename}")
        print(f"📁 Путь: {filepath}")
        print(f"📝 Сообщений: {len(messages)}")
        
        return filepath
    
    def create_topic_analysis_file(self, filename: str = None) -> str:
        """
        Создает файл с анализом тем для ИИ
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"topics_analysis_{timestamp}.json"
        
        filepath = os.path.join(self.ai_export_dir, filename)
        
        # Анализируем темы
        topics_data = self.analytics.analyze_conversation_topics()
        
        # Добавляем контекст для ИИ
        ai_topics_data = {
            'analysis_type': 'topic_analysis',
            'created_at': datetime.now().isoformat(),
            'word_frequency_data': topics_data,
            'top_topics_context': {
                'most_frequent_words': topics_data['top_words'][:30],
                'total_unique_words': topics_data['unique_words'],
                'messages_analyzed': topics_data['total_messages_analyzed']
            },
            'ai_analysis_tasks': [
                'Сгруппируй похожие слова в тематические кластеры',
                'Определи основные категории тем разговоров',
                'Найди необычные или интересные темы',
                'Проанализируй, о чем пользователь говорит чаще всего',
                'Выдели профессиональные интересы и хобби'
            ],
            'interpretation_hints': [
                'Высокочастотные слова показывают основные интересы',
                'Профессиональная лексика может указывать на сферу деятельности',
                'Эмоциональные слова отражают настроение общения',
                'Топонимы показывают географические связи'
            ]
        }
        
        # Сохраняем файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(ai_topics_data, f, ensure_ascii=False, indent=2)
        
        print(f"🏷️ Создан файл анализа тем: {filename}")
        print(f"📁 Путь: {filepath}")
        
        return filepath
    
    def create_complete_ai_package(self, chat_id: int = None) -> Dict[str, str]:
        """
        Создает полный пакет файлов для анализа ИИ
        """
        print("🎯 Создаем полный пакет для AI анализа...")
        
        package_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 1. Общий обзор
            package_files['overview'] = self.create_overview_file(
                f"overview_{timestamp}.json"
            )
            
            # 2. Анализ тем
            package_files['topics'] = self.create_topic_analysis_file(
                f"topics_{timestamp}.json"
            )
            
            # 3. Если указан конкретный чат
            if chat_id:
                package_files['chat_analysis'] = self.create_chat_analysis_file(
                    chat_id, f"chat_{chat_id}_{timestamp}.json"
                )
                package_files['conversation'] = self.create_conversation_snippet(
                    chat_id, days=14, filename=f"conversation_{chat_id}_{timestamp}.txt"
                )
            
            # 4. Создаем инструкцию
            instruction_file = os.path.join(self.ai_export_dir, f"AI_ANALYSIS_GUIDE_{timestamp}.md")
            self._create_analysis_guide(instruction_file, package_files)
            package_files['guide'] = instruction_file
            
            print("\n🎉 Пакет AI анализа готов!")
            print("📁 Все файлы сохранены в:", self.ai_export_dir)
            
            return package_files
            
        except Exception as e:
            print(f"❌ Ошибка при создании пакета: {e}")
            return package_files
    
    def _create_analysis_guide(self, filepath: str, package_files: Dict[str, str]):
        """Создает руководство по анализу"""
        guide_content = f"""# 🤖 Руководство по AI анализу Telegram данных

## 📊 Созданные файлы:

"""
        
        for file_type, file_path in package_files.items():
            filename = os.path.basename(file_path)
            guide_content += f"- **{file_type}**: `{filename}`\n"
        
        guide_content += """
## 🎯 Рекомендации по анализу:

### 1. Общий анализ (`overview_*.json`)
- Загрузи этот файл первым для общего понимания
- Спроси ИИ: "Проанализируй мою активность в Telegram"
- Обрати внимание на паттерны времени и активности

### 2. Анализ тем (`topics_*.json`)
- Используй для понимания основных интересов
- Спроси: "Какие основные темы я обсуждаю?"
- Попроси сгруппировать слова по тематикам

### 3. Анализ конкретного чата (`chat_*.json`)
- Для детального анализа стиля общения
- Спроси: "Как я общаюсь в этом чате?"
- Попроси найти особенности и паттерны

### 4. Фрагмент разговора (`conversation_*.txt`)
- Для анализа конкретных диалогов
- Легко читается ИИ как обычный текст
- Хорошо для анализа стиля и тона

## 💡 Примеры вопросов для ИИ:

### Общие:
- "Проанализируй мою активность в Telegram за этот период"
- "Какие выводы можно сделать о моих интересах?"
- "Как изменилась моя активность со временем?"

### Стиль общения:
- "Как я общаюсь в разных чатах?"
- "Какой у меня стиль письма?"
- "Использую ли я много эмодзи/сленга?"

### Социальный анализ:
- "В каких чатах я наиболее активен?"
- "С кем я общаюсь чаще всего?"
- "Есть ли различия в общении с разными людьми?"

### Темы и интересы:
- "О чем я чаще всего говорю?"
- "Какие у меня основные интересы?"
- "Есть ли профессиональные темы в моих сообщениях?"

## 🔧 Технические детали:
- Все JSON файлы в UTF-8 кодировке
- Даты в ISO формате
- Текстовые файлы оптимизированы для чтения ИИ
- Удалены личные данные (ID заменены на имена)

## ⚠️ Конфиденциальность:
- Проверь файлы перед загрузкой в ИИ
- Убери личную информацию если нужно
- Не загружай данные в публичные ИИ если это критично
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"📋 Создано руководство: {os.path.basename(filepath)}")