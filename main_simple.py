"""
Простая версия Telegram Parser - только парсинг и экспорт
Запуск: python main_simple.py
"""
import asyncio
import sys
from telegram_parser import TelegramParser
from data_exporter import DataExporter
import config

async def main():
    """
    Главная функция программы
    """
    print("🚀 TELEGRAM CHAT PARSER - ПРОСТАЯ ВЕРСИЯ")
    print("=" * 40)

    # Проверяем настройки
    if not config.API_ID or not config.API_HASH:
        print("❌ Ошибка: не настроены API ключи!")
        print("📋 Инструкция:")
        print("1. Перейди на https://my.telegram.org")
        print("2. Создай приложение и получи API_ID и API_HASH")
        print("3. Создай файл .env по примеру .env.example")
        print("4. Заполни свои данные в .env файле")
        return

    # Создаем объекты для работы
    parser = TelegramParser()
    exporter = DataExporter()

    try:
        # 1. Подключаемся к Telegram
        await parser.initialize()

        # 2. Показываем меню
        while True:
            print("\n" + "="*40)
            print("📋 МЕНЮ ДЕЙСТВИЙ:")
            print("1. 📋 Показать список чатов")
            print("2. 💬 Спарсить конкретный чат")
            print("3. 🚀 Спарсить ВСЕ чаты")
            print("4. ❌ Выход")
            print("="*40)

            choice = input("\n👉 Выбери действие (1-4): ").strip()

            if choice == "1":
                # Показываем список чатов
                await show_chats_list(parser)

            elif choice == "2":
                # Парсим конкретный чат
                await parse_single_chat(parser, exporter)

            elif choice == "3":
                # Парсим все чаты
                await parse_all_chats(parser, exporter)

            elif choice == "4":
                print("👋 До свидания!")
                break

            else:
                print("❌ Неверный выбор, попробуй еще раз")

    except KeyboardInterrupt:
        print("\n⏹️ Программа остановлена пользователем")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
    finally:
        # Закрываем соединение
        await parser.close()

async def show_chats_list(parser: TelegramParser):
    """
    Показывает список доступных чатов
    """
    chats = await parser.get_chats_list()

    print(f"\n📋 СПИСОК ЧАТОВ ({len(chats)} штук):")
    print("-" * 60)

    for i, chat in enumerate(chats[:20], 1):  # Показываем первые 20
        print(f"{i:2}. 💬 {chat['name'][:30]:30} | {chat['type']:15} | ID: {chat['id']}")

    if len(chats) > 20:
        print(f"... и еще {len(chats) - 20} чатов")

    input("\n📱 Нажми Enter чтобы вернуться в меню...")

async def parse_single_chat(parser: TelegramParser, exporter: DataExporter):
    """
    Парсинг одного конкретного чата
    """
    print("\n🎯 ПАРСИНГ ОДНОГО ЧАТА")

    # Показываем список чатов для выбора
    chats = await parser.get_chats_list()

    print("\n📋 Доступные чаты:")
    for i, chat in enumerate(chats[:10], 1):  # Показываем первые 10
        print(f"{i}. {chat['name']} (ID: {chat['id']})")

    try:
        choice = int(input(f"\n👉 Выбери чат (1-{min(10, len(chats))}): "))
        if 1 <= choice <= min(10, len(chats)):
            selected_chat = chats[choice - 1]

            # Спрашиваем количество сообщений
            limit = input(f"📊 Сколько сообщений спарсить? (Enter = {config.MAX_MESSAGES}): ").strip()
            if limit:
                limit = int(limit)
            else:
                limit = config.MAX_MESSAGES

            print(f"\n🚀 Парсим чат '{selected_chat['name']}'...")

            # Парсим чат
            messages = await parser.parse_chat_messages(selected_chat['id'], limit)

            # Создаем структуру данных для экспорта
            export_data = {
                'timestamp': f"{__import__('datetime').datetime.now().isoformat()}",
                'total_chats': 1,
                'chats': {
                    str(selected_chat['id']): {
                        'info': selected_chat,
                        'messages': messages,
                        'total_messages': len(messages)
                    }
                }
            }

            # Экспортируем
            exported_files = exporter.export_all_formats(export_data)

        else:
            print("❌ Неверный номер чата")

    except ValueError:
        print("❌ Введи корректный номер")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def parse_all_chats(parser: TelegramParser, exporter: DataExporter):
    """
    Парсинг всех чатов
    """
    print("\n🚀 ПОЛНЫЙ ПАРСИНГ ВСЕХ ЧАТОВ")
    print("⚠️  Это может занять много времени!")

    confirm = input("🤔 Продолжить? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', 'да', 'д']:
        print("❌ Отменено")
        return

    try:
        # Парсим все чаты
        all_data = await parser.parse_all_chats()

        # Экспортируем результаты
        exported_files = exporter.export_all_formats(all_data)

    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")

def check_python_version():
    """
    Проверяем версию Python
    """
    if sys.version_info < (3, 7):
        print("❌ Нужен Python 3.7 или новее!")
        print(f"Твоя версия: {sys.version}")
        sys.exit(1)

if __name__ == "__main__":
    # Проверяем версию Python
    check_python_version()

    print("🐍 Python версия OK")
    print("📦 Запускаем простой парсер...")

    # Запускаем основную программу
    asyncio.run(main())