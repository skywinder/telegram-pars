#!/usr/bin/env python3
"""
Единая точка входа для Telegram Parser
Запускает веб-интерфейс со всей функциональностью
"""
import os
import sys
import webbrowser
import time
from threading import Timer

def check_requirements():
    """Проверка зависимостей"""
    try:
        import flask
        import telethon
        import emoji
        import aiofiles
        return True
    except ImportError as e:
        print(f"❌ Отсутствуют зависимости: {e}")
        print("📦 Установите зависимости командой: pip install -r requirements.txt")
        return False

def check_config():
    """Проверка конфигурации"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📋 Создайте файл .env по примеру .env.example")
        print("   и добавьте свои API_ID и API_HASH от Telegram")
        return False
    
    # Проверяем наличие ключей
    from dotenv import load_dotenv
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ В файле .env не заданы TELEGRAM_API_ID и TELEGRAM_API_HASH")
        print("📋 Получите их на https://my.telegram.org")
        return False
    
    return True

def open_browser():
    """Открыть браузер через 2 секунды"""
    time.sleep(2)
    webbrowser.open('http://localhost:5001')

def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 TELEGRAM PARSER - ВЕБ ВЕРСИЯ")
    print("=" * 60)
    
    # Проверки
    if not check_requirements():
        sys.exit(1)
    
    if not check_config():
        sys.exit(1)
    
    print("✅ Все проверки пройдены")
    print()
    print("🌐 Запуск веб-интерфейса...")
    print("=" * 60)
    print()
    print("📌 Интерфейс будет доступен по адресу: http://localhost:5001")
    print("🌐 Браузер откроется автоматически через 2 секунды...")
    print()
    print("⏹️  Для остановки нажмите Ctrl+C")
    print()
    print("=" * 60)
    
    # Запускаем браузер в отдельном потоке
    Timer(2.0, open_browser).start()
    
    # Создаем папку для логов если её нет
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("📁 Создана папка для логов")
    
    # Запускаем веб-сервер
    try:
        # Импортируем и запускаем приложение
        from web_interface import app, init_app
        from logger_config import log_info
        
        # Инициализируем приложение
        if init_app():
            print("✅ База данных подключена")
        else:
            print("⚠️  База данных не найдена. Создайте её через веб-интерфейс")
        
        log_info('web', "Запуск веб-сервера на http://localhost:5001")
        print("\n📄 Логи сохраняются в папке logs/:")
        print("   - logs/web_interface.log - основные события веб-интерфейса")
        print("   - logs/parser.log - события парсера")
        print("   - logs/errors.log - все ошибки")
        
        # Запускаем сервер
        app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n✋ Сервер остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()