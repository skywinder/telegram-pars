"""
Пример использования методов для просмотра истории изменений сообщений
"""
from database import TelegramDatabase
from datetime import datetime, timedelta
import json

def view_message_changes_demo():
    """Демонстрация работы с историей изменений сообщений"""
    
    # Инициализация базы данных
    db = TelegramDatabase()
    
    print("=== ДЕМОНСТРАЦИЯ ПРОСМОТРА ИЗМЕНЕНИЙ СООБЩЕНИЙ ===\n")
    
    # 1. Получение всех отредактированных сообщений
    print("1. Последние отредактированные сообщения:")
    edited_messages = db.get_edited_messages(limit=10)
    
    for msg in edited_messages[:5]:  # Показываем первые 5
        print(f"\n  Сообщение ID: {msg['message_id']}")
        print(f"  Чат: {msg['chat_name']}")
        print(f"  Автор: {msg.get('username') or msg.get('first_name', 'Unknown')}")
        print(f"  Количество редактирований: {msg['edit_count']}")
        print(f"  Последнее редактирование: {msg['last_edit_time']}")
        print(f"  Текущий текст: {msg['current_text'][:100]}...")
    
    # 2. Получение истории конкретного сообщения
    if edited_messages:
        first_msg = edited_messages[0]
        print(f"\n\n2. Полная история изменений сообщения {first_msg['message_id']}:")
        
        history = db.get_message_history(
            message_id=first_msg['message_id'],
            chat_id=first_msg['chat_id']
        )
        
        for change in history:
            print(f"\n  [{change['timestamp']}] {change['action_type'].upper()}")
            if change['action_type'] == 'edited':
                print(f"  Старый текст: {change['old_text'][:100] if change['old_text'] else 'N/A'}")
                print(f"  Новый текст: {change['new_text'][:100] if change['new_text'] else 'N/A'}")
            elif change['action_type'] == 'created':
                print(f"  Текст: {change['new_text'][:100] if change['new_text'] else 'N/A'}")
            elif change['action_type'] == 'deleted':
                print(f"  Удаленный текст: {change['old_text'][:100] if change['old_text'] else 'N/A'}")
    
    # 3. Получение удаленных сообщений
    print("\n\n3. Последние удаленные сообщения:")
    deleted_messages = db.get_deleted_messages(limit=10)
    
    for msg in deleted_messages[:5]:
        print(f"\n  Сообщение ID: {msg['message_id']}")
        print(f"  Чат: {msg['chat_name']}")
        print(f"  Автор: {msg.get('username') or msg.get('first_name', 'Unknown')}")
        print(f"  Удалено: {msg['deletion_time']}")
        print(f"  Текст: {msg['deleted_text'][:100] if msg['deleted_text'] else 'N/A'}...")
    
    # 4. Получение изменений за последние 7 дней
    print("\n\n4. Изменения за последние 7 дней:")
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent_changes = db.get_message_changes_by_date(start_date=week_ago)
    
    # Группируем по типу действия
    changes_by_type = {}
    for change in recent_changes:
        action = change['action_type']
        if action not in changes_by_type:
            changes_by_type[action] = 0
        changes_by_type[action] += 1
    
    for action, count in changes_by_type.items():
        print(f"  {action}: {count} изменений")
    
    # 5. Статистика изменений для конкретного чата
    if edited_messages:
        chat_id = edited_messages[0]['chat_id']
        print(f"\n\n5. Статистика изменений для чата {edited_messages[0]['chat_name']}:")
        
        stats = db.get_chat_change_statistics(chat_id)
        
        print("\n  Общая статистика:")
        for stat in stats['change_statistics']:
            print(f"    {stat['action_type']}: {stat['count']}")
        
        print("\n  Самые редактируемые сообщения:")
        for msg in stats['most_edited_messages'][:3]:
            print(f"    ID {msg['message_id']}: {msg['edit_count']} редактирований")
            print(f"    Автор: {msg.get('username', 'Unknown')}")
            print(f"    Текст: {msg['current_text'][:50]}...")

def create_html_report():
    """Создание HTML отчета с изменениями"""
    db = TelegramDatabase()
    
    # Получаем данные
    edited = db.get_edited_messages(limit=50)
    deleted = db.get_deleted_messages(limit=50)
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Telegram Messages History Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .edited { background-color: #fff3cd; }
        .deleted { background-color: #f8d7da; }
        .message-text { max-width: 400px; overflow: hidden; text-overflow: ellipsis; }
    </style>
</head>
<body>
    <h1>История изменений сообщений Telegram</h1>
    <p>Отчет создан: {}</p>
    
    <h2>Отредактированные сообщения</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Чат</th>
            <th>Автор</th>
            <th>Дата сообщения</th>
            <th>Редактирований</th>
            <th>Последнее изменение</th>
            <th>Текущий текст</th>
        </tr>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    for msg in edited:
        html += f"""
        <tr class="edited">
            <td>{msg['message_id']}</td>
            <td>{msg['chat_name']}</td>
            <td>{msg.get('username') or msg.get('first_name', 'Unknown')}</td>
            <td>{msg['message_date']}</td>
            <td>{msg['edit_count']}</td>
            <td>{msg['last_edit_time']}</td>
            <td class="message-text">{msg['current_text']}</td>
        </tr>
"""
    
    html += """
    </table>
    
    <h2>Удаленные сообщения</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Чат</th>
            <th>Автор</th>
            <th>Дата сообщения</th>
            <th>Удалено</th>
            <th>Текст сообщения</th>
        </tr>
"""
    
    for msg in deleted:
        html += f"""
        <tr class="deleted">
            <td>{msg['message_id']}</td>
            <td>{msg['chat_name']}</td>
            <td>{msg.get('username') or msg.get('first_name', 'Unknown')}</td>
            <td>{msg['message_date']}</td>
            <td>{msg['deletion_time']}</td>
            <td class="message-text">{msg['deleted_text'] or 'N/A'}</td>
        </tr>
"""
    
    html += """
    </table>
</body>
</html>
"""
    
    # Сохраняем отчет
    report_path = 'output/message_changes_report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML отчет сохранен: {report_path}")

if __name__ == "__main__":
    # Запускаем демонстрацию
    view_message_changes_demo()
    
    # Создаем HTML отчет
    print("\n\n=== СОЗДАНИЕ HTML ОТЧЕТА ===")
    create_html_report()