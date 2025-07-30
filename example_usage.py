#!/usr/bin/env python3
"""
Пример использования улучшенного Telegram Parser с обработкой ограничений
"""
import asyncio
from telegram_parser import TelegramParser

async def main():
    # Создаем парсер
    parser = TelegramParser()
    
    try:
        # Инициализация с проверкой аккаунта
        await parser.initialize()
        
        print("\n" + "="*60)
        print("ВЫБЕРИТЕ РЕЖИМ ПАРСИНГА:")
        print("="*60)
        print("1. Умный парсинг (пропускает уже кэшированные чаты)")
        print("2. Полный парсинг (принудительно парсит все)")
        print("3. Проверка изменений (только редактирование/удаление)")
        print("4. Показать статистику базы данных")
        print("5. Выход")
        
        choice = input("\nВведите номер (1-5): ").strip()
        
        if choice == "1":
            print("\n🧠 Запускаем умный парсинг...")
            result = await parser.parse_all_chats(force_full_scan=False)
            
            print(f"\n✅ Результаты умного парсинга:")
            print(f"📊 Обработано чатов: {result['parsing_statistics']['chats_parsed']}")
            print(f"⏭️ Пропущено чатов: {result['parsing_statistics']['chats_skipped']}")
            print(f"💬 Всего сообщений: {result['parsing_statistics']['total_messages']}")
            
        elif choice == "2":
            print("\n🔄 Запускаем полный парсинг...")
            result = await parser.parse_all_chats(force_full_scan=True)
            
            print(f"\n✅ Результаты полного парсинга:")
            print(f"📊 Обработано чатов: {result['parsing_statistics']['chats_parsed']}")
            print(f"💬 Всего сообщений: {result['parsing_statistics']['total_messages']}")
            
        elif choice == "3":
            print("\n🔍 Проверяем изменения...")
            hours = input("За сколько часов проверить? (по умолчанию 24): ").strip()
            hours = int(hours) if hours.isdigit() else 24
            
            result = await parser.check_for_changes(hours_threshold=hours)
            
            if 'error' not in result:
                print(f"\n✅ Результаты проверки изменений:")
                print(f"🔄 Проверено чатов: {result['chats_checked']}")
                print(f"📝 Найдено изменений: {result['total_changes']}")
            else:
                print(f"❌ Ошибка: {result['error']}")
                
        elif choice == "4":
            if parser.db:
                stats = parser.db.get_parsing_statistics()
                print(f"\n📊 Статистика базы данных:")
                print(f"📁 Всего чатов: {stats['total_statistics'].get('total_chats', 0)}")
                print(f"💬 Всего сообщений: {stats['total_statistics'].get('total_messages', 0)}")
                print(f"🗑️ Удаленных сообщений: {stats['total_statistics'].get('deleted_messages', 0)}")
                
                print(f"\n📈 Последние сессии:")
                for session in stats['recent_sessions'][:3]:
                    print(f"  {session.get('start_time', 'N/A')}: {session.get('total_messages', 0)} сообщений")
            else:
                print("❌ База данных отключена")
                
        elif choice == "5":
            print("👋 До свидания!")
        else:
            print("❌ Неверный выбор")
    
    except KeyboardInterrupt:
        print("\n⚠️ Прерывание пользователем...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        # Закрываем подключение
        await parser.close()

if __name__ == "__main__":
    asyncio.run(main())