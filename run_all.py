#!/usr/bin/env python3
"""
Запускает парсер с веб-интерфейсом и мониторингом
"""
import sys
import threading
import time
import webbrowser
from web_interface import app, init_app

def run_web_interface():
    """Запускает веб-интерфейс в отдельном потоке"""
    if init_app():
        print("✅ Веб-интерфейс готов!")
        print("🌐 Открывается в браузере: http://localhost:5001")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        # Открываем браузер через 2 секунды
        threading.Timer(2.0, lambda: webbrowser.open('http://localhost:5001')).start()
        
        # Запускаем Flask в тихом режиме
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)
    else:
        print("❌ Не удалось запустить веб-интерфейс")
        print("💡 Сначала запустите парсинг для создания базы данных")

def main():
    """Главная функция"""
    print("🚀 TELEGRAM PARSER - ПОЛНЫЙ РЕЖИМ")
    print("=" * 50)
    print()
    print("Выберите режим запуска:")
    print("1. Парсер (основная программа)")
    print("2. Веб-интерфейс + Мониторинг")
    print("3. Все вместе (парсер в одном окне, веб в другом)")
    print()
    
    choice = input("Ваш выбор (1-3): ").strip()
    
    if choice == "1":
        # Запускаем основной парсер
        import asyncio
        from main import main as parser_main
        asyncio.run(parser_main())
        
    elif choice == "2":
        # Запускаем веб-интерфейс
        run_web_interface()
        
    elif choice == "3":
        print()
        print("📝 Инструкция:")
        print("1. Откройте новый терминал")
        print("2. Активируйте виртуальное окружение:")
        print("   source venv/bin/activate  # Linux/Mac")
        print("   venv\\Scripts\\activate     # Windows")
        print("3. Запустите парсер: python main.py")
        print()
        print("Сейчас запускается веб-интерфейс...")
        time.sleep(3)
        run_web_interface()
        
    else:
        print("❌ Неверный выбор")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Программа остановлена")