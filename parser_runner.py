"""
Автоматический запуск парсера для веб-интерфейса
Поддерживает запуск в фоновом режиме с различными параметрами
"""
import asyncio
import argparse
import sys
import signal
import os
from datetime import datetime
from telegram_parser import TelegramParser
from data_exporter import DataExporter
from status_manager import set_active_parser, clear_active_parser, StatusManager
import config

async def run_parser(args):
    """Запуск парсера с заданными параметрами"""
    parser = TelegramParser()
    exporter = DataExporter()
    
    try:
        # Инициализация
        await parser.initialize()
        set_active_parser(parser)
        
        # Создаем сессию парсинга
        session_id = parser.db.create_scan_session() if parser.db else None
        
        if args.all:
            # Парсинг всех чатов
            print("🔄 Запуск полного парсинга всех чатов...")
            dialogs = await parser.get_dialogs()
            
            for dialog in dialogs:
                if StatusManager.is_interruption_requested():
                    print("⚠️ Парсинг прерван пользователем")
                    break
                    
                await parser.parse_chat(
                    dialog,
                    limit=args.limit,
                    force_full_scan=args.force_full_scan
                )
                
        elif args.check_changes:
            # Проверка изменений
            print("🔍 Проверка изменений в сообщениях...")
            hours = args.hours or 24
            await parser.check_for_changes(hours_threshold=hours)
            
        elif args.chats:
            # Парсинг конкретных чатов
            print(f"📋 Парсинг выбранных чатов: {args.chats}")
            for chat_id in args.chats:
                if StatusManager.is_interruption_requested():
                    print("⚠️ Парсинг прерван пользователем")
                    break
                    
                try:
                    chat_id = int(chat_id)
                    dialogs = await parser.get_dialogs()
                    dialog = next((d for d in dialogs if d.id == chat_id), None)
                    
                    if dialog:
                        await parser.parse_chat(
                            dialog,
                            limit=args.limit,
                            force_full_scan=args.force_full_scan
                        )
                    else:
                        print(f"❌ Чат с ID {chat_id} не найден")
                except ValueError:
                    print(f"❌ Неверный ID чата: {chat_id}")
                    
        # Завершаем сессию
        if parser.db and session_id:
            parser.db.close_scan_session(session_id)
            
        print("✅ Парсинг завершен")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        StatusManager.update_status({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
    finally:
        clear_active_parser()
        await parser.disconnect()

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Telegram Parser Runner')
    
    # Режимы работы
    parser.add_argument('--auto', action='store_true', help='Автоматический режим (без интерактивного меню)')
    parser.add_argument('--all', action='store_true', help='Парсить все чаты')
    parser.add_argument('--check-changes', action='store_true', help='Проверить изменения')
    parser.add_argument('--chats', nargs='+', help='ID чатов для парсинга')
    
    # Опции
    parser.add_argument('--limit', type=int, help='Лимит сообщений для парсинга')
    parser.add_argument('--force-full-scan', action='store_true', help='Полное сканирование (игнорировать кэш)')
    parser.add_argument('--hours', type=int, default=24, help='Часов для проверки изменений (по умолчанию 24)')
    
    args = parser.parse_args()
    
    # Проверяем настройки
    if not config.API_ID or not config.API_HASH:
        print("❌ Ошибка: не настроены API ключи!")
        print("Создайте файл .env с API_ID и API_HASH")
        sys.exit(1)
    
    # Запускаем парсер
    try:
        asyncio.run(run_parser(args))
    except KeyboardInterrupt:
        print("\n✋ Прервано пользователем")
        StatusManager.request_interruption()
        sys.exit(0)

if __name__ == "__main__":
    main()