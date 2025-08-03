#!/usr/bin/env python3
"""
Скрипт для проверки работы системы мониторинга
"""
import sqlite3
import json
from datetime import datetime, timedelta
from database import TelegramDatabase
from notification_manager import get_notification_manager
import time

def check_database_tables():
    """Проверяет наличие необходимых таблиц в БД"""
    print("\n=== Проверка таблиц БД ===")
    db = TelegramDatabase()
    
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем таблицу realtime_changes_log
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='realtime_changes_log'
            """)
            
            if cursor.fetchone():
                print("✅ Таблица realtime_changes_log существует")
                
                # Проверяем количество записей
                count = cursor.execute("SELECT COUNT(*) FROM realtime_changes_log").fetchone()[0]
                print(f"   Записей в таблице: {count}")
                
                if count > 0:
                    # Показываем последние изменения
                    recent = cursor.execute("""
                        SELECT chat_name, action_type, detected_at 
                        FROM realtime_changes_log 
                        ORDER BY detected_at DESC 
                        LIMIT 5
                    """).fetchall()
                    
                    print("\n   Последние изменения:")
                    for r in recent:
                        print(f"   - {r[0]}: {r[1]} at {r[2]}")
            else:
                print("❌ Таблица realtime_changes_log НЕ существует")
                
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")

def check_monitor_instance():
    """Проверяет состояние экземпляра монитора"""
    print("\n=== Проверка монитора ===")
    
    try:
        from realtime_monitor import get_monitor_instance
        monitor = get_monitor_instance()
        
        if monitor:
            print(f"✅ Монитор существует")
            print(f"   Статус: {'Активен' if monitor.is_running else 'Неактивен'}")
            print(f"   Отслеживаемые чаты: {len(monitor.monitored_chats) if monitor.monitored_chats else 'Все'}")
        else:
            print("❌ Монитор не инициализирован")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке монитора: {e}")

def test_notification_system():
    """Тестирует систему уведомлений"""
    print("\n=== Тест системы уведомлений ===")
    
    try:
        notification_manager = get_notification_manager()
        print("✅ NotificationManager загружен")
        
        # Проверяем количество слушателей
        print(f"   Активных слушателей: {len(notification_manager.listeners)}")
        
        # Отправляем тестовое уведомление
        print("\n   Отправляем тестовое уведомление...")
        notification_manager.notify('test', {
            'message': 'Это тестовое уведомление',
            'timestamp': datetime.now().isoformat()
        })
        
        print("✅ Уведомление отправлено")
        
    except Exception as e:
        print(f"❌ Ошибка в системе уведомлений: {e}")

def simulate_message_change():
    """Симулирует изменение сообщения для проверки"""
    print("\n=== Симуляция изменения сообщения ===")
    
    try:
        db = TelegramDatabase()
        notification_manager = get_notification_manager()
        
        # Создаем фиктивное изменение в БД
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Убеждаемся, что таблица существует
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS realtime_changes_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    old_content TEXT,
                    new_content TEXT,
                    detected_at TEXT NOT NULL,
                    user_id INTEGER,
                    chat_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем тестовую запись
            test_data = {
                'chat_id': -1001234567890,
                'message_id': 99999,
                'action_type': 'edited',
                'old_content': json.dumps({'text': 'Старый текст сообщения'}),
                'new_content': json.dumps({'text': 'Новый текст сообщения'}),
                'detected_at': datetime.now().isoformat(),
                'user_id': 12345,
                'chat_name': 'Тестовый чат'
            }
            
            cursor.execute("""
                INSERT INTO realtime_changes_log 
                (chat_id, message_id, action_type, old_content, new_content, 
                 detected_at, user_id, chat_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_data['chat_id'],
                test_data['message_id'],
                test_data['action_type'],
                test_data['old_content'],
                test_data['new_content'],
                test_data['detected_at'],
                test_data['user_id'],
                test_data['chat_name']
            ))
            
            conn.commit()
            print("✅ Тестовое изменение добавлено в БД")
            
        # Отправляем уведомление
        notification_manager.notify('message_edited', {
            'chat_id': test_data['chat_id'],
            'chat_name': test_data['chat_name'],
            'message_id': test_data['message_id'],
            'text': 'Новый текст сообщения'
        })
        
        print("✅ Уведомление об изменении отправлено")
        
    except Exception as e:
        print(f"❌ Ошибка при симуляции: {e}")

def main():
    """Основная функция проверки"""
    print("=== ПРОВЕРКА СИСТЕМЫ МОНИТОРИНГА ===")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Выполняем все проверки
    check_database_tables()
    check_monitor_instance()
    test_notification_system()
    simulate_message_change()
    
    print("\n=== РЕКОМЕНДАЦИИ ===")
    print("1. Убедитесь, что веб-интерфейс запущен (http://localhost:5001)")
    print("2. Откройте страницу мониторинга (/realtime-monitor)")
    print("3. Откройте консоль браузера (F12) для просмотра логов")
    print("4. Запустите мониторинг через консоль (python main.py -> пункт 10)")
    print("\nЕсли уведомления не работают:")
    print("- Проверьте, что разрешены уведомления в браузере")
    print("- Убедитесь, что нет ошибок CORS")
    print("- Проверьте логи в консоли браузера")

if __name__ == "__main__":
    main()