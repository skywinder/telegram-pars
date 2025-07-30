"""
Расширенная версия Telegram Parser с аналитикой и AI экспортом
Запуск: python main_advanced.py
"""
import asyncio
import sys
import os
from telegram_parser import TelegramParser
from data_exporter import DataExporter
from analytics import TelegramAnalytics
from ai_exporter import AIExporter
from database import TelegramDatabase
import config

async def main():
    """
    Главная функция программы
    """
    print("🚀 TELEGRAM CHAT PARSER - РАСШИРЕННАЯ ВЕРСИЯ")
    print("=" * 50)
    
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
    
    # Инициализируем аналитику и AI экспорт если есть БД
    analytics = None
    ai_exporter = None
    if parser.db:
        analytics = TelegramAnalytics(parser.db.db_path)
        ai_exporter = AIExporter(parser.db.db_path)
    
    try:
        # 1. Подключаемся к Telegram
        await parser.initialize()
        
        # 2. Главное меню
        while True:
            show_main_menu()
            choice = input("\n👉 Выбери действие (1-9): ").strip()
            
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
                # Аналитика
                await show_analytics_menu(analytics, ai_exporter)
                
            elif choice == "5":
                # AI экспорт
                await ai_export_menu(ai_exporter, analytics)
                
            elif choice == "6":
                # История изменений
                await show_changes_history(analytics)
                
            elif choice == "7":
                # Статистика базы данных
                await show_database_stats(analytics)
                
            elif choice == "8":
                # Настройки
                await show_settings_menu()
                
            elif choice == "9":
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

def show_main_menu():
    """Показывает главное меню"""
    print("\n" + "="*50)
    print("📋 ГЛАВНОЕ МЕНЮ:")
    print("="*50)
    print("🔍 ПАРСИНГ:")
    print("  1. 📋 Показать список чатов")
    print("  2. 💬 Спарсить конкретный чат")
    print("  3. 🚀 Спарсить ВСЕ чаты")
    print()
    print("📊 АНАЛИТИКА:")
    print("  4. 📈 Аналитика и статистика")
    print("  5. 🤖 Экспорт для AI анализа")
    print("  6. 📝 История изменений")
    print("  7. 🗄️ Статистика базы данных")
    print()
    print("⚙️ ПРОЧЕЕ:")
    print("  8. ⚙️ Настройки")
    print("  9. ❌ Выход")
    print("="*50)

async def show_chats_list(parser: TelegramParser):
    """Показывает список доступных чатов"""
    chats = await parser.get_chats_list()
    
    print(f"\n📋 СПИСОК ЧАТОВ ({len(chats)} штук):")
    print("-" * 80)
    print(f"{'№':>3} {'Название':30} {'Тип':15} {'Непрочитанные':12} {'ID':15}")
    print("-" * 80)
    
    for i, chat in enumerate(chats[:30], 1):  # Показываем первые 30
        name = chat['name'][:28] + '..' if len(chat['name']) > 30 else chat['name']
        print(f"{i:>3}. {name:30} {chat['type']:15} {chat['unread_count']:>12} {chat['id']:>15}")
    
    if len(chats) > 30:
        print(f"... и еще {len(chats) - 30} чатов")
    
    input("\n📱 Нажми Enter чтобы вернуться в меню...")

async def parse_single_chat(parser: TelegramParser, exporter: DataExporter):
    """Парсинг одного конкретного чата"""
    print("\n🎯 ПАРСИНГ ОДНОГО ЧАТА")
    
    chats = await parser.get_chats_list()
    
    print("\n📋 Доступные чаты:")
    for i, chat in enumerate(chats[:15], 1):
        print(f"{i:>2}. {chat['name'][:40]:40} (ID: {chat['id']})")
    
    try:
        choice = int(input(f"\n👉 Выбери чат (1-{min(15, len(chats))}): "))
        if 1 <= choice <= min(15, len(chats)):
            selected_chat = chats[choice - 1]
            
            limit = input(f"📊 Сколько сообщений спарсить? (Enter = {config.MAX_MESSAGES}): ").strip()
            if limit:
                limit = int(limit)
            else:
                limit = config.MAX_MESSAGES
            
            print(f"\n🚀 Парсим чат '{selected_chat['name']}'...")
            
            # Создаем сессию если есть БД
            session_id = None
            if parser.db:
                session_id = parser.db.create_scan_session()
            
            # Парсим чат
            messages = await parser.parse_chat_messages(selected_chat['id'], limit, session_id)
            
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
            
            # Предлагаем создать AI экспорт
            if parser.db:
                create_ai = input("\n🤖 Создать файлы для AI анализа? (y/N): ").strip().lower()
                if create_ai in ['y', 'yes', 'да', 'д']:
                    ai_exp = AIExporter(parser.db.db_path)
                    ai_files = ai_exp.create_complete_ai_package(selected_chat['id'])
                    print("✅ AI файлы созданы!")
            
        else:
            print("❌ Неверный номер чата")
            
    except ValueError:
        print("❌ Введи корректный номер")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def parse_all_chats(parser: TelegramParser, exporter: DataExporter):
    """Парсинг всех чатов"""
    print("\n🚀 ПОЛНЫЙ ПАРСИНГ ВСЕХ ЧАТОВ")
    print("⚠️  Это может занять много времени и места на диске!")
    
    chats = await parser.get_chats_list()
    print(f"📊 Будет обработано {len(chats)} чатов")
    
    confirm = input("🤔 Продолжить? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', 'да', 'д']:
        print("❌ Отменено")
        return
    
    try:
        # Парсим все чаты
        all_data = await parser.parse_all_chats()
        
        # Экспортируем результаты
        exported_files = exporter.export_all_formats(all_data)
        
        # Показываем сводку изменений если есть
        if 'changes_summary' in all_data:
            print("\n📝 ОБНАРУЖЕННЫЕ ИЗМЕНЕНИЯ:")
            changes = all_data['changes_summary']
            for change_type in changes.get('changes_by_type', []):
                print(f"  {change_type['action_type']}: {change_type['count']} изменений")
        
        # Предлагаем создать AI анализ
        if parser.db:
            create_ai = input("\n🤖 Создать общий AI анализ? (y/N): ").strip().lower()
            if create_ai in ['y', 'yes', 'да', 'д']:
                ai_exp = AIExporter(parser.db.db_path)
                ai_files = ai_exp.create_complete_ai_package()
                print("✅ AI анализ создан!")
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")

async def show_analytics_menu(analytics: TelegramAnalytics, ai_exporter: AIExporter):
    """Меню аналитики"""
    if not analytics:
        print("❌ Аналитика недоступна - нет базы данных")
        input("Нажми Enter...")
        return
        
    while True:
        print("\n" + "="*40)
        print("📈 МЕНЮ АНАЛИТИКИ:")
        print("1. 🏆 Самые активные чаты")
        print("2. ⏰ Анализ активности по времени")
        print("3. 🏷️ Анализ тем разговоров")
        print("4. 👥 Статистика пользователей")
        print("5. 💬 Кто начинает диалоги")
        print("6. 😀 Анализ эмодзи и смайликов")
        print("7. 📊 Полный отчет по чату")
        print("8. ← Назад в главное меню")
        print("="*40)
        
        choice = input("\n👉 Выбери (1-8): ").strip()
        
        if choice == "1":
            await show_active_chats(analytics)
        elif choice == "2":
            await show_time_analysis(analytics)
        elif choice == "3":
            await show_topics_analysis(analytics)
        elif choice == "4":
            await show_users_stats(analytics)
        elif choice == "5":
            await show_conversation_starters(analytics)
        elif choice == "6":
            await show_emoji_analysis(analytics)
        elif choice == "7":
            await show_chat_report(analytics)
        elif choice == "8":
            break
        else:
            print("❌ Неверный выбор")

async def show_active_chats(analytics: TelegramAnalytics):
    """Показывает самые активные чаты"""
    print("\n🏆 САМЫЕ АКТИВНЫЕ ЧАТЫ:")
    
    period = input("За какой период? (7/30/всё время): ").strip()
    days = None
    if period == "7":
        days = 7
    elif period == "30":
        days = 30
    
    active_chats = analytics.get_most_active_chats(limit=10, days=days)
    
    if not active_chats:
        print("📭 Нет данных для отображения")
        return
    
    print(f"\n{'№':>2} {'Чат':25} {'Сообщений':>10} {'Пользователей':>12} {'Активных дней':>12}")
    print("-" * 65)
    
    for i, chat in enumerate(active_chats, 1):
        name = chat['chat_name'][:23] + '..' if len(chat['chat_name']) > 25 else chat['chat_name']
        print(f"{i:>2}. {name:25} {chat['message_count']:>10} {chat['unique_users']:>12} {chat['active_days']:>12}")
    
    input("\nНажми Enter...")

async def show_time_analysis(analytics: TelegramAnalytics):
    """Показывает анализ активности по времени"""
    print("\n⏰ АНАЛИЗ АКТИВНОСТИ ПО ВРЕМЕНИ:")
    
    activity = analytics.get_activity_by_time()
    
    print("\n📊 По часам дня:")
    for hour_data in activity['by_hour']:
        bar_length = min(30, hour_data['count'] // 10)  # Простая визуализация
        bar = "█" * bar_length
        print(f"{hour_data['hour']:>2}:00 | {bar} {hour_data['count']}")
    
    print("\n📅 По дням недели:")
    for day_data in activity['by_weekday']:
        bar_length = min(30, day_data['count'] // 50)
        bar = "█" * bar_length
        print(f"{day_data['weekday']:12} | {bar} {day_data['count']}")
    
    input("\nНажми Enter...")

async def show_topics_analysis(analytics: TelegramAnalytics):
    """Показывает анализ тем"""
    print("\n🏷️ АНАЛИЗ ТЕМ РАЗГОВОРОВ:")
    
    topics = analytics.analyze_conversation_topics()
    
    if not topics['top_words']:
        print("📭 Нет данных для анализа тем")
        return
    
    print(f"📊 Проанализировано {topics['total_messages_analyzed']} сообщений")
    print(f"🔤 Уникальных слов: {topics['unique_words']}")
    
    print("\n🔥 Топ слов:")
    for i, word_data in enumerate(topics['top_words'][:20], 1):
        print(f"{i:>2}. {word_data['word']:15} - {word_data['count']:>4} раз")
    
    input("\nНажми Enter...")

async def show_users_stats(analytics: TelegramAnalytics):
    """Показывает статистику пользователей"""
    print("\n👥 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:")
    
    users = analytics.get_user_statistics()
    
    if not users:
        print("📭 Нет данных о пользователях")
        return
    
    print(f"\n{'№':>2} {'Имя':20} {'Сообщений':>10} {'Ср. длина':>10}")
    print("-" * 45)
    
    for i, user in enumerate(users[:15], 1):
        name = user['full_name'].strip() or user['username'] or f"User_{user['user_id']}"
        name = name[:18] + '..' if len(name) > 20 else name
        print(f"{i:>2}. {name:20} {user['message_count']:>10} {user['avg_message_length'] or 0:>10.1f}")
    
    input("\nНажми Enter...")

async def show_conversation_starters(analytics: TelegramAnalytics):
    """Показывает кто чаще начинает диалоги"""
    print("\n💬 АНАЛИЗ ИНИЦИАЦИИ ДИАЛОГОВ:")
    
    chat_id = input("ID чата (Enter для всех чатов): ").strip()
    if chat_id:
        try:
            chat_id = int(chat_id)
        except ValueError:
            print("❌ Неверный ID чата")
            return
    else:
        chat_id = None
    
    analysis = analytics.analyze_conversation_starters(chat_id)
    
    if 'error' in analysis:
        print(f"❌ {analysis['error']}")
        return
    
    print(f"\n📊 Всего диалогов проанализировано: {analysis['total_conversations']}")
    print(f"⏰ Средний промежуток между диалогами: {analysis['average_gap_hours']} часов")
    
    print(f"\n🏁 КТО ЧАЩЕ НАЧИНАЕТ ДИАЛОГИ:")
    print("-" * 60)
    
    for i, starter in enumerate(analysis['conversation_starters'], 1):
        name = starter['sender_name'][:25] + '...' if len(starter['sender_name']) > 28 else starter['sender_name']
        print(f"{i:>2}. {name:30} {starter['percentage']:>5.1f}% ({starter['conversations_started']} раз)")
    
    input("\nНажми Enter...")

async def show_emoji_analysis(analytics: TelegramAnalytics):
    """Показывает анализ эмодзи и смайликов"""
    print("\n😀 АНАЛИЗ ЭМОДЗИ И СМАЙЛИКОВ:")
    
    chat_id = input("ID чата (Enter для всех чатов): ").strip()
    if chat_id:
        try:
            chat_id = int(chat_id)
        except ValueError:
            print("❌ Неверный ID чата")
            return
    else:
        chat_id = None
    
    analysis = analytics.analyze_emoji_and_expressions(chat_id)
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    global_stats = analysis['global_stats']
    print(f"📝 Сообщений проанализировано: {global_stats['total_messages_analyzed']}")
    print(f"😀 Уникальных эмодзи найдено: {global_stats['total_unique_emojis']}")
    
    print(f"\n🔥 САМЫЕ ПОПУЛЯРНЫЕ ЭМОДЗИ:")
    for i, emoji_data in enumerate(global_stats['most_used_emojis'][:10], 1):
        print(f"{i:>2}. {emoji_data['emoji']} - {emoji_data['count']} раз")
    
    if global_stats['most_used_text_smilies']:
        print(f"\n😄 ПОПУЛЯРНЫЕ ТЕКСТОВЫЕ СМАЙЛИКИ:")
        for i, smiley_data in enumerate(global_stats['most_used_text_smilies'][:5], 1):
            print(f"{i:>2}. {smiley_data['smiley']} - {smiley_data['count']} раз")
    
    print(f"\n👥 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ:")
    print("-" * 80)
    print(f"{'Имя':20} {'Эмодзи %':>8} {'Смайлы %':>8} {'Гифки %':>8} {'Ср.эмодзи':>10}")
    print("-" * 80)
    
    for user in analysis['user_expression_stats'][:10]:
        name = user['sender_name'][:18] + '..' if len(user['sender_name']) > 20 else user['sender_name']
        emoji_pct = user['emoji_usage']['emoji_frequency_percent']
        smiley_pct = user['text_smilies_usage']['smilies_frequency_percent']
        gif_pct = user['gif_sticker_usage']['gif_frequency_percent']
        avg_emoji = user['emoji_usage']['avg_emoji_per_message']
        
        print(f"{name:20} {emoji_pct:>7.1f}% {smiley_pct:>7.1f}% {gif_pct:>7.1f}% {avg_emoji:>9.2f}")
    
    input("\nНажми Enter...")

async def show_chat_report(analytics: TelegramAnalytics):
    """Показывает полный отчет по чату"""
    print("\n📊 ПОЛНЫЙ ОТЧЕТ ПО ЧАТУ:")
    
    try:
        chat_id = int(input("Введи ID чата: "))
        report = analytics.generate_chat_report(chat_id)
        
        if 'error' in report:
            print(f"❌ {report['error']}")
            return
        
        print(f"\n📋 Чат: {report['chat_info']['name']}")
        print(f"📧 Тип: {report['chat_info']['type']}")
        
        if report['user_stats']:
            print(f"👥 Участников: {len(report['user_stats'])}")
            print(f"💬 Всего сообщений: {sum(u['message_count'] for u in report['user_stats'])}")
        
        # Сохраняем отчет в файл
        import json
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_report_{chat_id}_{timestamp}.json"
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Отчет сохранен: {filename}")
        
    except ValueError:
        print("❌ Неверный ID чата")
    
    input("\nНажми Enter...")

async def ai_export_menu(ai_exporter: AIExporter, analytics: TelegramAnalytics):
    """Меню AI экспорта"""
    if not ai_exporter:
        print("❌ AI экспорт недоступен - нет базы данных")
        input("Нажми Enter...")
        return
    
    while True:
        print("\n" + "="*40)
        print("🤖 AI ЭКСПОРТ:")
        print("1. 📊 Общий обзор для AI")
        print("2. 💬 Анализ конкретного чата")
        print("3. 🏷️ Анализ тем")
        print("4. 📝 Фрагмент разговора")
        print("5. 📦 Полный пакет для AI")
        print("6. ← Назад")
        print("="*40)
        
        choice = input("\n👉 Выбери (1-6): ").strip()
        
        if choice == "1":
            ai_exporter.create_overview_file()
            print("✅ Обзор создан!")
            
        elif choice == "2":
            try:
                chat_id = int(input("ID чата: "))
                ai_exporter.create_chat_analysis_file(chat_id)
                print("✅ Анализ чата создан!")
            except ValueError:
                print("❌ Неверный ID")
                
        elif choice == "3":
            ai_exporter.create_topic_analysis_file()
            print("✅ Анализ тем создан!")
            
        elif choice == "4":
            try:
                chat_id = int(input("ID чата: "))
                days = int(input("За сколько дней (по умолчанию 7): ") or "7")
                ai_exporter.create_conversation_snippet(chat_id, days)
                print("✅ Фрагмент создан!")
            except ValueError:
                print("❌ Неверные параметры")
                
        elif choice == "5":
            chat_id = input("ID чата (Enter для общего анализа): ").strip()
            if chat_id:
                try:
                    chat_id = int(chat_id)
                except ValueError:
                    print("❌ Неверный ID")
                    continue
            else:
                chat_id = None
            
            ai_exporter.create_complete_ai_package(chat_id)
            print("✅ Полный пакет создан!")
            
        elif choice == "6":
            break
        else:
            print("❌ Неверный выбор")
        
        input("\nНажми Enter...")

async def show_changes_history(analytics: TelegramAnalytics):
    """Показывает историю изменений"""
    if not analytics:
        print("❌ История недоступна")
        return
    
    print("\n📝 ИСТОРИЯ ИЗМЕНЕНИЙ:")
    
    changes = analytics.get_message_changes_analytics()
    
    print("\n📊 Общая статистика:")
    for change in changes['changes_summary']:
        print(f"  {change['action_type']}: {change['count']} изменений в {change['affected_chats']} чатах")
    
    if changes['most_active_chats']:
        print("\n🔥 Чаты с наибольшими изменениями:")
        for chat in changes['most_active_chats'][:5]:
            print(f"  {chat['chat_name']}: {chat['total_changes']} изменений")
    
    input("\nНажми Enter...")

async def show_database_stats(analytics: TelegramAnalytics):
    """Показывает статистику базы данных"""
    if not analytics:
        print("❌ БД недоступна")
        return
    
    print("\n🗄️ СТАТИСТИКА БАЗЫ ДАННЫХ:")
    
    stats = analytics.get_chat_statistics()
    
    if not stats:
        print("📭 Нет данных в базе")
        return
    
    total_messages = sum(s['total_messages'] for s in stats)
    total_chats = len(stats)
    
    print(f"📊 Всего чатов: {total_chats}")
    print(f"💬 Всего сообщений: {total_messages}")
    print(f"📈 Среднее сообщений на чат: {total_messages / total_chats:.1f}")
    
    print(f"\n🏆 Топ-5 чатов:")
    for i, stat in enumerate(stats[:5], 1):
        print(f"  {i}. {stat['name']}: {stat['total_messages']} сообщений")
    
    input("\nНажми Enter...")

async def show_settings_menu():
    """Меню настроек"""
    print("\n⚙️ НАСТРОЙКИ:")
    print(f"📊 Максимум сообщений: {config.MAX_MESSAGES}")
    print(f"📁 Папка результатов: {config.OUTPUT_DIR}")
    print(f"🗄️ Отслеживание истории: {'Включено' if config.ENABLE_HISTORY_TRACKING else 'Выключено'}")
    
    print("\nФорматы экспорта:")
    for fmt, enabled in config.EXPORT_FORMATS.items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {fmt}")
    
    input("\nНажми Enter...")

def check_python_version():
    """Проверяем версию Python"""
    if sys.version_info < (3, 7):
        print("❌ Нужен Python 3.7 или новее!")
        print(f"Твоя версия: {sys.version}")
        sys.exit(1)

if __name__ == "__main__":
    # Проверяем версию Python
    check_python_version()
    
    print("🐍 Python версия OK")
    print("📦 Запускаем расширенный парсер...")
    
    # Запускаем основную программу
    asyncio.run(main())