"""
Экспорт данных в различные форматы для анализа
"""
import json
import csv
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import config

class DataExporter:
    """
    Класс для экспорта спарсенных данных
    """
    
    def __init__(self):
        """Инициализация экспортера"""
        # Создаем папку для результатов, если её нет
        if not os.path.exists(config.OUTPUT_DIR):
            os.makedirs(config.OUTPUT_DIR)
            print(f"📁 Создана папка {config.OUTPUT_DIR}")
    
    def export_to_json(self, data: Dict[str, Any], filename: str = None) -> str:
        """
        Экспорт в JSON формат
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telegram_export_{timestamp}.json"
        
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        print(f"💾 Сохраняем данные в JSON: {filename}")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON файл сохранен: {filepath}")
        return filepath
    
    def export_to_csv(self, data: Dict[str, Any], filename: str = None) -> str:
        """
        Экспорт в CSV формат (все сообщения в одной таблице)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telegram_messages_{timestamp}.csv"
        
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        print(f"📊 Создаем CSV файл: {filename}")
        
        # Собираем все сообщения в один список
        all_messages = []
        for chat_id, chat_data in data['chats'].items():
            if 'messages' in chat_data:
                for message in chat_data['messages']:
                    # Добавляем информацию о чате к каждому сообщению
                    message_with_chat = message.copy()
                    message_with_chat['chat_name'] = chat_data['info']['name']
                    message_with_chat['chat_type'] = chat_data['info']['type']
                    all_messages.append(message_with_chat)
        
        # Создаем DataFrame и сохраняем в CSV
        if all_messages:
            df = pd.DataFrame(all_messages)
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✅ CSV файл сохранен: {filepath} ({len(all_messages)} сообщений)")
        else:
            print("⚠️ Нет сообщений для экспорта в CSV")
        
        return filepath
    
    def export_chat_summary(self, data: Dict[str, Any], filename: str = None) -> str:
        """
        Создаем сводку по чатам
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chats_summary_{timestamp}.csv"
        
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        print(f"📈 Создаем сводку по чатам: {filename}")
        
        # Создаем сводку
        summary = []
        for chat_id, chat_data in data['chats'].items():
            summary_row = {
                'chat_id': chat_id,
                'chat_name': chat_data['info']['name'],
                'chat_type': chat_data['info']['type'],
                'total_messages': chat_data.get('total_messages', 0),
                'unread_count': chat_data['info'].get('unread_count', 0),
                'has_error': 'error' in chat_data
            }
            summary.append(summary_row)
        
        # Сохраняем в CSV
        if summary:
            df = pd.DataFrame(summary)
            df = df.sort_values('total_messages', ascending=False)  # Сортируем по количеству сообщений
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✅ Сводка сохранена: {filepath}")
        
        return filepath
    
    def export_all_formats(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Экспорт во все включенные форматы
        """
        print("🎯 Экспортируем данные во все форматы...")
        
        exported_files = {}
        
        # JSON экспорт
        if config.EXPORT_FORMATS.get('json', False):
            exported_files['json'] = self.export_to_json(data)
        
        # CSV экспорт
        if config.EXPORT_FORMATS.get('csv', False):
            exported_files['csv_messages'] = self.export_to_csv(data)
            exported_files['csv_summary'] = self.export_chat_summary(data)
        
        # Выводим статистику
        self.print_export_summary(data, exported_files)
        
        return exported_files
    
    def print_export_summary(self, data: Dict[str, Any], exported_files: Dict[str, str]):
        """
        Выводим сводку по экспорту
        """
        print("\n" + "="*50)
        print("📊 СВОДКА ПО ЭКСПОРТУ")
        print("="*50)
        
        # Общая статистика
        total_chats = data.get('total_chats', 0)
        total_messages = sum([
            chat_data.get('total_messages', 0) 
            for chat_data in data['chats'].values()
        ])
        
        print(f"📁 Всего чатов: {total_chats}")
        print(f"💬 Всего сообщений: {total_messages}")
        print(f"📅 Время экспорта: {data.get('timestamp', 'не указано')}")
        
        # Файлы
        print(f"\n📄 Созданные файлы:")
        for file_type, filepath in exported_files.items():
            print(f"   {file_type}: {filepath}")
        
        print("\n🎉 Экспорт завершен! Данные готовы для анализа.")
        print("="*50)