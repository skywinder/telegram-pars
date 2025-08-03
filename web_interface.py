"""
Веб-интерфейс для Telegram Parser
Запуск: python web_interface.py
"""
import os
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, Response
from analytics import TelegramAnalytics
from ai_exporter import AIExporter
from database import TelegramDatabase
from status_manager import StatusManager
import config
from realtime_monitor import get_monitor_instance
from notification_manager import get_notification_manager
from queue import Queue, Empty
import time

# Создаем Flask приложение
app = Flask(__name__)
app.secret_key = 'telegram_parser_secret_key_2024'  # Для flash сообщений

# Отключаем кеширование для разработки
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response

# Глобальные объекты
analytics = None
ai_exporter = None
db = None
active_parser = None  # Ссылка на активный парсер для мониторинга статуса

def init_app():
    """Инициализация приложения"""
    global analytics, ai_exporter, db

    # Проверяем есть ли база данных
    db_path = os.path.join(config.OUTPUT_DIR, config.DB_FILENAME)
    if os.path.exists(db_path):
        try:
            analytics = TelegramAnalytics(db_path)
            ai_exporter = AIExporter(db_path)
            db = TelegramDatabase(db_path)
            print("✅ База данных подключена")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    else:
        print("⚠️ База данных не найдена. Запустите сначала парсинг.")
        return False

def transform_chat_data(raw_chat):
    """Преобразует данные чата из формата БД в формат для шаблонов"""
    if not raw_chat:
        return None
    
    return {
        'id': raw_chat.get('chat_id', 0),
        'name': raw_chat.get('chat_name', 'Неизвестный чат'),
        'type': raw_chat.get('chat_type', 'unknown'),
        'total_messages': raw_chat.get('message_count', 0),
        'unique_senders': raw_chat.get('unique_users', 0),
        'last_message': raw_chat.get('last_message', ''),
        'active_days': raw_chat.get('active_days', 0),
        'edited_count': raw_chat.get('edited_count', 0),
        'deleted_count': raw_chat.get('deleted_count', 0)
    }

@app.route('/')
def index():
    """Главная страница"""
    if not analytics:
        return render_template('no_data.html')

    try:
                # Получаем базовую статистику
        raw_stats = analytics.get_most_active_chats(limit=10)  # Топ 10 чатов
        
        # Преобразуем данные к ожидаемому формату
        stats = [transform_chat_data(chat) for chat in raw_stats if chat]

        # Общая статистика
        all_chats = analytics.get_most_active_chats(limit=1000)  # Большой лимит для подсчета всех
        total_chats = len(all_chats) if all_chats else 0
        total_messages = sum(s.get('message_count', 0) for s in all_chats) if all_chats else 0

        # Последние изменения
        changes_summary = analytics.get_message_changes_analytics()

        return render_template('dashboard.html',
                             stats=stats,
                             total_chats=total_chats,
                             total_messages=total_messages,
                             changes_summary=changes_summary)
    except Exception as e:
        flash(f'Ошибка загрузки данных: {e}', 'error')
        return render_template('dashboard.html', stats=[], total_chats=0, total_messages=0)

@app.route('/chats')
def chats():
    """Страница со списком чатов"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        raw_chats = analytics.get_most_active_chats(limit=1000)  # Все чаты
        
        # Преобразуем данные к ожидаемому формату
        chats_data = [transform_chat_data(chat) for chat in raw_chats]
        
        return render_template('chats.html', chats=chats_data)
    except Exception as e:
        flash(f'Ошибка загрузки чатов: {e}', 'error')
        return render_template('chats.html', chats=[])

@app.route('/chat/<chat_id>')
def chat_detail(chat_id):
    try:
        chat_id = int(chat_id)
    except ValueError:
        flash('Неверный ID чата', 'error')
        return redirect(url_for('chats'))
    """Детальная информация о чате"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        # Получаем подробную информацию
        report = analytics.generate_chat_report(chat_id)

        if 'error' in report:
            flash(f"Чат не найден: {report['error']}", 'error')
            return redirect(url_for('chats'))

        # Анализ стартеров диалогов
        starters = analytics.analyze_conversation_starters(chat_id)

        # Анализ эмодзи
        emoji_analysis = analytics.analyze_emoji_and_expressions(chat_id)

        return render_template('chat_detail.html',
                             report=report,
                             starters=starters,
                             emoji_analysis=emoji_analysis,
                             chat_id=chat_id)
    except Exception as e:
        flash(f'Ошибка загрузки чата: {e}', 'error')
        return redirect(url_for('chats'))

@app.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        # Активные чаты
        raw_active_chats = analytics.get_most_active_chats(limit=15)
        
        # Преобразуем данные к ожидаемому формату
        active_chats = []
        for chat in raw_active_chats:
            active_chats.append({
                'chat_name': chat['chat_name'],
                'chat_type': chat['chat_type'],
                'message_count': chat['message_count'],
                'unique_users': chat['unique_users'],
                'active_days': chat.get('active_days', 0)
            })

        # Анализ времени
        time_analysis = analytics.get_activity_by_time()

        # Топ темы
        topics = analytics.analyze_conversation_topics()

        # Изменения
        changes = analytics.get_message_changes_analytics()

        return render_template('analytics.html',
                             active_chats=active_chats,
                             time_analysis=time_analysis,
                             topics=topics,
                             changes=changes)
    except Exception as e:
        flash(f'Ошибка загрузки аналитики: {e}', 'error')
        return render_template('analytics.html', 
                             active_chats=[], 
                             time_analysis={'by_hour': [], 'by_weekday': []},
                             topics={'top_words': [], 'total_messages_analyzed': 0, 'unique_words': 0},
                             changes={})

@app.route('/emoji-stats')
def emoji_stats():
    """Страница статистики эмодзи"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        emoji_analysis = analytics.analyze_emoji_and_expressions()
        return render_template('emoji_stats.html', emoji_analysis=emoji_analysis)
    except Exception as e:
        flash(f'Ошибка загрузки статистики эмодзи: {e}', 'error')
        return render_template('emoji_stats.html', emoji_analysis=None)

@app.route('/conversation-starters')
def conversation_starters():
    """Страница анализа инициаторов диалогов"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        starters = analytics.analyze_conversation_starters()
        return render_template('conversation_starters.html', starters=starters)
    except Exception as e:
        flash(f'Ошибка загрузки анализа диалогов: {e}', 'error')
        return render_template('conversation_starters.html', starters=None)

@app.route('/export')
def export_page():
    """Страница экспорта"""
    return render_template('export.html')

@app.route('/api/export/<export_type>')
def api_export(export_type):
    """API для экспорта данных"""
    if not ai_exporter:
        return jsonify({'error': 'AI Exporter недоступен'}), 500

    try:
        chat_id = request.args.get('chat_id', type=int)

        if export_type == 'overview':
            filename = ai_exporter.create_overview_file()
        elif export_type == 'topics':
            filename = ai_exporter.create_topic_analysis_file()
        elif export_type == 'chat' and chat_id:
            filename = ai_exporter.create_chat_analysis_file(chat_id)
        elif export_type == 'conversation' and chat_id:
            days = request.args.get('days', 7, type=int)
            filename = ai_exporter.create_conversation_snippet(chat_id, days)
        elif export_type == 'package':
            files = ai_exporter.create_complete_ai_package(chat_id)
            return jsonify({'success': True, 'files': files})
        else:
            return jsonify({'error': 'Неверный тип экспорта'}), 400

        return jsonify({'success': True, 'filename': os.path.basename(filename)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat-stats/<chat_id>')
def api_chat_stats(chat_id):
    try:
        chat_id = int(chat_id)
    except ValueError:
        return jsonify({'error': 'Неверный ID чата'}), 400
    """API для получения статистики чата"""
    if not analytics:
        return jsonify({'error': 'Analytics недоступен'}), 500

    try:
        # Базовая статистика
        stats = analytics.get_most_active_chats(limit=1000)
        chat_stats = next((s for s in stats if s.get('chat_id') == chat_id), None)

        if not chat_stats:
            return jsonify({'error': 'Чат не найден'}), 404

        # Анализ времени для этого чата
        time_data = analytics.get_activity_by_time(chat_id)

        return jsonify({
            'basic_stats': chat_stats,
            'time_analysis': time_data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def api_search():
    """API для поиска по сообщениям"""
    if not db:
        return jsonify({'error': 'База данных недоступна'}), 500

    query = request.args.get('q', '').strip()
    chat_id = request.args.get('chat_id', type=int)
    limit = request.args.get('limit', 20, type=int)

    if not query or len(query) < 3:
        return jsonify({'error': 'Запрос должен содержать минимум 3 символа'}), 400

    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row

            chat_filter = f"AND m.chat_id = {chat_id}" if chat_id else ""

            results = conn.execute(f'''
                SELECT
                    m.id, m.text, m.date, m.chat_id,
                    c.name as chat_name,
                    COALESCE(u.first_name, u.username, 'User_' || u.id) as sender_name
                FROM messages m
                LEFT JOIN chats c ON m.chat_id = c.id
                LEFT JOIN users u ON m.sender_id = u.id
                WHERE m.text LIKE ?
                AND m.is_deleted = FALSE {chat_filter}
                ORDER BY m.date DESC
                LIMIT ?
            ''', (f'%{query}%', limit)).fetchall()

            return jsonify({
                'results': [dict(row) for row in results],
                'total': len(results),
                'query': query
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search')
def search_page():
    """Страница поиска"""
    return render_template('search.html')

@app.route('/status')
def status_page():
    """Страница мониторинга статуса парсинга"""
    return render_template('status.html')

@app.route('/message-changes')
def message_changes():
    """Страница со списком измененных сообщений"""
    if not db:
        return redirect(url_for('index'))
    
    try:
        # Получаем фильтры из параметров запроса
        action_type = request.args.get('type', 'all')  # all, edited, deleted
        chat_id = request.args.get('chat_id', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Получаем измененные сообщения
        if action_type == 'edited':
            changes = db.get_edited_messages(chat_id, limit)
        elif action_type == 'deleted':
            changes = db.get_deleted_messages(chat_id, limit)
        else:
            # Получаем все изменения
            edited = db.get_edited_messages(chat_id, limit//2)
            deleted = db.get_deleted_messages(chat_id, limit//2)
            
            # Нормализуем поля timestamp для сортировки
            for msg in edited:
                msg['timestamp'] = msg.get('last_edit_time', '')
                msg['change_type'] = 'edited'
            for msg in deleted:
                msg['timestamp'] = msg.get('deletion_time', '')
                msg['change_type'] = 'deleted'
            
            changes = edited + deleted
            changes.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            changes = changes[:limit]
        
        # Получаем список чатов для фильтра
        chats_list = analytics.get_most_active_chats(limit=1000) if analytics else []
        
        return render_template('message_changes.html', 
                             changes=changes,
                             action_type=action_type,
                             selected_chat_id=chat_id,
                             chats_list=chats_list)
    except Exception as e:
        flash(f'Ошибка загрузки изменений: {e}', 'error')
        return render_template('message_changes.html', changes=[], chats_list=[])

@app.route('/message-history/<int:chat_id>/<int:message_id>')
def message_history(chat_id, message_id):
    """История изменений конкретного сообщения"""
    if not db:
        return redirect(url_for('index'))
    
    try:
        history = db.get_message_history(message_id, chat_id)
        
        if not history:
            flash('История изменений не найдена', 'warning')
            return redirect(url_for('message_changes'))
        
        # Получаем информацию о чате
        chat_info = None
        if analytics:
            report = analytics.generate_chat_report(chat_id)
            if 'chat_info' in report:
                chat_info = report['chat_info']
        
        return render_template('message_history.html',
                             history=history,
                             message_id=message_id,
                             chat_id=chat_id,
                             chat_info=chat_info)
    except Exception as e:
        flash(f'Ошибка загрузки истории: {e}', 'error')
        return redirect(url_for('message_changes'))

@app.route('/chat/<chat_id>/messages')
def chat_messages(chat_id):
    try:
        chat_id = int(chat_id)
    except ValueError:
        flash('Неверный ID чата', 'error')
        return redirect(url_for('chats'))
    """Просмотр сообщений чата с подсветкой изменений"""
    if not db:
        return redirect(url_for('index'))
    
    try:
        # Получаем параметры пагинации
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        
        # Получаем сообщения чата
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Базовый запрос
            query = '''
                SELECT 
                    m.id,
                    m.text,
                    m.date,
                    m.is_deleted,
                    m.media_type,
                    m.views,
                    m.forwards,
                    u.username,
                    u.first_name,
                    u.last_name,
                    (SELECT COUNT(*) FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited') as edit_count,
                    (SELECT MAX(timestamp) FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited') as last_edit
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                WHERE m.chat_id = ?
            '''
            
            params = [chat_id]
            
            # Добавляем поиск если есть
            if search:
                query += ' AND m.text LIKE ?'
                params.append(f'%{search}%')
            
            # Сортировка и пагинация
            query += ' ORDER BY m.date DESC LIMIT ? OFFSET ?'
            params.extend([per_page, (page - 1) * per_page])
            
            messages = conn.execute(query, params).fetchall()
            
            # Подсчитываем общее количество
            count_query = 'SELECT COUNT(*) FROM messages WHERE chat_id = ?'
            count_params = [chat_id]
            if search:
                count_query += ' AND text LIKE ?'
                count_params.append(f'%{search}%')
            
            total_count = conn.execute(count_query, count_params).fetchone()[0]
        
        # Получаем информацию о чате
        chat_info = None
        if analytics:
            report = analytics.generate_chat_report(chat_id)
            if 'chat_info' in report:
                chat_info = report['chat_info']
        
        # Вычисляем пагинацию
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('chat_messages.html',
                             messages=[dict(m) for m in messages],
                             chat_info=chat_info,
                             chat_id=chat_id,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total_count=total_count,
                             search=search)
    except Exception as e:
        flash(f'Ошибка загрузки сообщений: {e}', 'error')
        return redirect(url_for('chats'))

@app.route('/api/message-changes/<int:chat_id>')
def api_get_message_changes(chat_id):
    """API для получения измененных сообщений чата"""
    if not db:
        return jsonify({'error': 'База данных недоступна'}), 500
    
    try:
        action_type = request.args.get('type', 'all')
        limit = request.args.get('limit', 50, type=int)
        
        if action_type == 'edited':
            changes = db.get_edited_messages(chat_id, limit)
        elif action_type == 'deleted':
            changes = db.get_deleted_messages(chat_id, limit)
        else:
            edited = db.get_edited_messages(chat_id, limit//2)
            deleted = db.get_deleted_messages(chat_id, limit//2)
            
            # Нормализуем поля timestamp для сортировки
            for msg in edited:
                msg['timestamp'] = msg.get('last_edit_time', '')
                msg['change_type'] = 'edited'
            for msg in deleted:
                msg['timestamp'] = msg.get('deletion_time', '')
                msg['change_type'] = 'deleted'
            
            changes = edited + deleted
            changes.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            changes = changes[:limit]
        
        return jsonify({
            'success': True,
            'changes': changes,
            'total': len(changes)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-updates', methods=['POST'])
def api_check_updates():
    """API для проверки обновлений сообщений"""
    if not active_parser:
        return jsonify({
            'error': 'Парсер не активен. Запустите парсинг для проверки обновлений.'
        }), 400
    
    try:
        chat_id = request.json.get('chat_id')
        if not chat_id:
            return jsonify({'error': 'Не указан chat_id'}), 400
        
        # Запускаем проверку обновлений для конкретного чата
        # Это будет использовать активный парсер для проверки
        return jsonify({
            'success': True,
            'message': 'Проверка обновлений запущена. Следите за статусом парсинга.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_get_status():
    """API для получения текущего статуса парсинга"""
    # Читаем статус из файла вместо прямого обращения к парсеру
    status_data = StatusManager.get_status()
    
    if not status_data:
        return jsonify({
            'status': 'no_active_parser',
            'message': 'Нет активного парсера'
        })

    try:
        # Если есть активный парсер в этом процессе, получаем детальный статус
        if active_parser and hasattr(active_parser, 'get_current_status'):
            detailed_status = active_parser.get_current_status()
            return jsonify({
                'status': 'success',
                'data': detailed_status
            })
        else:
            # Иначе возвращаем статус из файла
            return jsonify({
                'status': 'success',
                'data': status_data
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/status/interrupt', methods=['POST'])
def api_request_interrupt():
    """API для запроса прерывания парсинга"""
    # Используем StatusManager для запроса прерывания
    status_data = StatusManager.get_status()
    
    if not status_data:
        return jsonify({
            'status': 'error',
            'message': 'Нет активного парсера для прерывания'
        }), 400

    try:
        StatusManager.request_interruption()
        
        # Если есть активный парсер в этом процессе, вызываем его метод
        if active_parser and hasattr(active_parser, 'request_interruption'):
            active_parser.request_interruption()
            
        return jsonify({
            'status': 'success',
            'message': 'Запрошено изящное прерывание операции'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/check-for-changes', methods=['POST'])
def api_check_for_changes():
    """API для получения последних изменений из БД"""
    if not db:
        return jsonify({
            'success': False,
            'error': 'База данных недоступна'
        }), 400
    
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        hours_threshold = data.get('hours_threshold', 24)
        
        # Получаем последние изменения из БД
        start_date = (datetime.now() - timedelta(hours=hours_threshold)).isoformat()
        
        # Получаем изменения за период
        changes = db.get_message_changes_by_date(
            start_date=start_date,
            action_type=None  # Все типы изменений
        )
        
        # Фильтруем по chat_id если указан
        if chat_id:
            changes = [c for c in changes if c.get('chat_id') == chat_id]
        
        # Подсчитываем статистику
        edited_count = len([c for c in changes if c.get('action_type') == 'edited'])
        deleted_count = len([c for c in changes if c.get('action_type') == 'deleted'])
        
        return jsonify({
            'success': True,
            'changes_found': {
                'total_changes': len(changes),
                'edited_messages': edited_count,
                'deleted_messages': deleted_count,
                'changes': changes[:100]  # Последние 100 изменений
            },
            'message': f'Найдено {len(changes)} изменений за последние {hours_threshold} часов'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/<chat_id>/messages-with-changes')
def api_get_chat_messages_with_changes(chat_id):
    try:
        chat_id = int(chat_id)
    except ValueError:
        return jsonify({'error': 'Неверный ID чата'}), 400
    """API для получения всех сообщений чата с информацией об изменениях"""
    if not db:
        return jsonify({'error': 'База данных недоступна'}), 500
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        filter_type = request.args.get('filter', 'all')  # all, changed, unchanged
        
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Основной запрос для получения сообщений с информацией об изменениях
            query = '''
                SELECT 
                    m.id,
                    m.text,
                    m.date,
                    m.is_deleted,
                    m.sender_id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    COALESCE(
                        (SELECT COUNT(*) FROM message_history 
                         WHERE message_id = m.id AND chat_id = m.chat_id 
                         AND action_type = 'edited'), 0
                    ) as edit_count,
                    (SELECT MAX(timestamp) FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited') as last_edit_time,
                    (SELECT old_text FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited'
                     ORDER BY timestamp DESC LIMIT 1) as previous_text
                FROM messages m
                LEFT JOIN users u ON m.sender_id = u.id
                WHERE m.chat_id = ?
            '''
            
            params = [chat_id]
            
            # Применяем фильтр
            if filter_type == 'changed':
                query += ''' AND (m.is_deleted = TRUE OR EXISTS (
                    SELECT 1 FROM message_history 
                    WHERE message_id = m.id AND chat_id = m.chat_id
                ))'''
            elif filter_type == 'unchanged':
                query += ''' AND m.is_deleted = FALSE AND NOT EXISTS (
                    SELECT 1 FROM message_history 
                    WHERE message_id = m.id AND chat_id = m.chat_id
                )'''
            
            # Пагинация
            query += ' ORDER BY m.date DESC LIMIT ? OFFSET ?'
            params.extend([per_page, (page - 1) * per_page])
            
            messages = conn.execute(query, params).fetchall()
            
            # Получаем общее количество
            count_query = 'SELECT COUNT(*) FROM messages WHERE chat_id = ?'
            total_count = conn.execute(count_query, [chat_id]).fetchone()[0]
            
            # Получаем информацию о чате
            chat_info = conn.execute(
                'SELECT name, type FROM chats WHERE id = ?', 
                [chat_id]
            ).fetchone()
        
        return jsonify({
            'success': True,
            'chat': dict(chat_info) if chat_info else None,
            'messages': [dict(m) for m in messages],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/parsing')
def parsing_page():
    """Страница управления парсингом"""
    return render_template('parsing.html')

@app.route('/api/start-parsing', methods=['POST'])
def api_start_parsing():
    """API для запуска парсинга"""
    import subprocess
    import threading
    
    try:
        data = request.get_json()
        parsing_type = data.get('type', 'all')  # all, single, check_changes
        chat_id = data.get('chat_id')
        options = data.get('options', {})
        
        # Формируем команду для запуска
        cmd = ['python', 'main.py']
        
        # Добавляем параметры в зависимости от типа
        if parsing_type == 'single' and chat_id:
            # Для одного чата нужно будет модифицировать main.py
            cmd.extend(['--chat', str(chat_id)])
        elif parsing_type == 'check_changes':
            cmd.extend(['--check-changes'])
        elif parsing_type == 'all':
            cmd.extend(['--all'])
            
        # Добавляем опции
        if options.get('force_full_scan'):
            cmd.append('--force-full-scan')
        if options.get('limit'):
            cmd.extend(['--limit', str(options['limit'])])
            
        # Запускаем процесс в фоне
        def run_parsing():
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Сохраняем PID для возможности остановки
                with open('parsing.pid', 'w') as f:
                    f.write(str(process.pid))
            except Exception as e:
                print(f"Ошибка запуска парсинга: {e}")
        
        thread = threading.Thread(target=run_parsing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Парсинг запущен',
            'type': parsing_type
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop-parsing', methods=['POST'])
def api_stop_parsing():
    """API для остановки парсинга"""
    try:
        # Используем StatusManager для запроса прерывания
        StatusManager.request_interruption()
        
        # Также пытаемся остановить процесс если есть PID
        import signal
        try:
            with open('parsing.pid', 'r') as f:
                pid = int(f.read())
                os.kill(pid, signal.SIGINT)
        except:
            pass
            
        return jsonify({
            'success': True,
            'message': 'Запрошена остановка парсинга'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/parsing-options')
def api_get_parsing_options():
    """API для получения доступных опций парсинга"""
    try:
        # Получаем список чатов если БД доступна
        chats = []
        if analytics:
            raw_chats = analytics.get_most_active_chats(limit=1000)
            chats = [{'id': chat['chat_id'], 'name': chat['chat_name']} for chat in raw_chats]
            
        return jsonify({
            'success': True,
            'chats': chats,
            'options': {
                'force_full_scan': {
                    'label': 'Полное сканирование (игнорировать кэш)',
                    'description': 'Перепроверить все сообщения, включая старые',
                    'default': False
                },
                'limit': {
                    'label': 'Лимит сообщений',
                    'description': 'Максимальное количество сообщений для парсинга',
                    'default': None,
                    'type': 'number'
                },
                'check_changes_hours': {
                    'label': 'Проверка изменений за N часов',
                    'description': 'При проверке изменений смотреть за последние N часов',
                    'default': 24,
                    'type': 'number'
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def set_active_parser(parser):
    """Устанавливает активный парсер для мониторинга"""
    global active_parser
    active_parser = parser

def clear_active_parser():
    """Очищает ссылку на активный парсер"""
    global active_parser
    active_parser = None

@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибки"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибки"""
    return render_template('500.html'), 500

@app.route('/realtime-monitor')
def realtime_monitor_page():
    """Страница мониторинга изменений в реальном времени"""
    monitor = get_monitor_instance()
    
    # Получаем статистику если монитор активен
    if monitor:
        stats = asyncio.run(monitor.get_statistics())
        recent_changes = asyncio.run(monitor.get_recent_changes(hours=24))
    else:
        stats = None
        recent_changes = []
    
    return render_template('realtime_monitor.html', 
                         monitor=monitor,
                         stats=stats,
                         recent_changes=recent_changes)

@app.route('/api/monitor/status')
def api_monitor_status():
    """API для получения статуса мониторинга"""
    monitor = get_monitor_instance()
    
    if not monitor:
        return jsonify({
            'is_active': False,
            'message': 'Монитор не инициализирован'
        })
    
    return jsonify({
        'is_active': monitor.is_running,
        'monitored_chats': len(monitor.monitored_chats) if monitor.monitored_chats else 'all'
    })

@app.route('/api/monitor/recent-changes')
def api_monitor_recent_changes():
    """API для получения последних изменений"""
    monitor = get_monitor_instance()
    
    if not monitor:
        return jsonify({'error': 'Монитор не инициализирован'}), 404
    
    hours = request.args.get('hours', 24, type=int)
    chat_id = request.args.get('chat_id', type=int)
    
    try:
        changes = asyncio.run(monitor.get_recent_changes(hours=hours, chat_id=chat_id))
        return jsonify({'changes': changes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monitor/stream')
def monitor_stream():
    """Server-Sent Events для real-time уведомлений"""
    def generate():
        # Создаем очередь для этого клиента
        client_queue = Queue()
        notification_manager = get_notification_manager()
        notification_manager.add_listener(client_queue)
        
        try:
            # Отправляем начальное сообщение
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Подключено к потоку уведомлений'})}\n\n"
            
            while True:
                try:
                    # Ждем событие с таймаутом
                    event = client_queue.get(timeout=30)
                    yield f"data: {event}\n\n"
                except Empty:
                    # Отправляем heartbeat каждые 30 секунд
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
        except GeneratorExit:
            # Клиент отключился
            notification_manager.remove_listener(client_queue)
            
    return Response(generate(), mimetype="text/event-stream")

@app.route('/api/monitor/control', methods=['POST'])
def monitor_control():
    """API для управления мониторингом из веб-интерфейса"""
    data = request.get_json()
    action = data.get('action')
    
    # Здесь пока просто возвращаем сообщение
    # В будущем можно добавить управление через отдельный процесс
    if action == 'start':
        return jsonify({
            'success': False,
            'message': 'Для запуска мониторинга используйте консольное приложение (python main.py → пункт 10)'
        })
    elif action == 'stop':
        return jsonify({
            'success': False,
            'message': 'Для остановки мониторинга используйте консольное приложение'
        })
    else:
        return jsonify({'error': 'Неизвестное действие'}), 400

if __name__ == '__main__':
    print("🌐 Запуск веб-интерфейса Telegram Parser...")

    # Создаем папки если их нет
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Инициализируем приложение
    if init_app():
        print("✅ Приложение готово!")
        print("🌐 Открой в браузере: http://localhost:5001")
        print("⏹️  Для остановки нажми Ctrl+C")

        # Запускаем в режиме разработки
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("❌ Не удалось запустить приложение")
        print("💡 Подсказка: Сначала запустите парсинг для создания базы данных")
        print("   python main.py")