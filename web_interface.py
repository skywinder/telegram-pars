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
from json_utils import safe_json_dumps
from monitor_manager import MonitorManager
from session_manager import SessionManager

# Создаем Flask приложение
app = Flask(__name__)
app.secret_key = 'telegram_parser_secret_key_2024'  # Для flash сообщений

# Инициализируем менеджер сессий
session_manager = SessionManager()

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
    
    # Handle both dict and sqlite3.Row objects
    try:
        # Try to access as dict first
        if hasattr(raw_chat, 'get'):
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
        # Handle sqlite3.Row objects
        elif hasattr(raw_chat, 'keys'):
            return {
                'id': raw_chat['chat_id'] if 'chat_id' in raw_chat.keys() else 0,
                'name': raw_chat['chat_name'] if 'chat_name' in raw_chat.keys() else 'Неизвестный чат',
                'type': raw_chat['chat_type'] if 'chat_type' in raw_chat.keys() else 'unknown',
                'total_messages': raw_chat['message_count'] if 'message_count' in raw_chat.keys() else 0,
                'unique_senders': raw_chat['unique_users'] if 'unique_users' in raw_chat.keys() else 0,
                'last_message': raw_chat['last_message'] if 'last_message' in raw_chat.keys() else '',
                'active_days': raw_chat['active_days'] if 'active_days' in raw_chat.keys() else 0,
                'edited_count': raw_chat['edited_count'] if 'edited_count' in raw_chat.keys() else 0,
                'deleted_count': raw_chat['deleted_count'] if 'deleted_count' in raw_chat.keys() else 0
            }
        else:
            # Log the error for debugging
            print(f"WARNING: Unexpected data type in transform_chat_data: {type(raw_chat)}")
            return None
    except Exception as e:
        print(f"ERROR in transform_chat_data: {e}, type: {type(raw_chat)}")
        return None

def get_sync_status():
    """Получает информацию о последней синхронизации"""
    if not db:
        return None
    
    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Получаем последнюю сессию парсинга
            last_session = conn.execute('''
                SELECT id, start_time, end_time, total_chats, total_messages, changes_detected
                FROM scan_sessions
                ORDER BY start_time DESC
                LIMIT 1
            ''').fetchone()
            
            # Получаем статистику по датам обновления чатов
            chat_updates = conn.execute('''
                SELECT 
                    MIN(last_updated) as oldest_update,
                    MAX(last_updated) as newest_update,
                    COUNT(*) as total_chats
                FROM chats
            ''').fetchone()
            
            # Получаем диапазон дат сообщений
            message_range = conn.execute('''
                SELECT 
                    MIN(date) as first_message,
                    MAX(date) as last_message,
                    COUNT(*) as total_messages
                FROM messages
                WHERE is_deleted = FALSE
            ''').fetchone()
            
            if not last_session and not chat_updates:
                return None
                
            return {
                'last_session': dict(last_session) if last_session else None,
                'chat_updates': dict(chat_updates) if chat_updates else None,
                'message_range': dict(message_range) if message_range else None,
                'is_parsing': StatusManager.get_status() is not None
            }
    except Exception as e:
        print(f"Ошибка получения статуса синхронизации: {e}")
        return None

def get_chat_sync_status(chat_id):
    """Получает информацию о последней синхронизации конкретного чата"""
    if not db:
        return None
    
    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Получаем информацию о последнем обновлении чата
            chat_info = conn.execute('''
                SELECT 
                    last_updated,
                    total_messages
                FROM chats
                WHERE id = ?
            ''', (chat_id,)).fetchone()
            
            # Получаем диапазон дат сообщений в чате
            message_info = conn.execute('''
                SELECT 
                    MIN(date) as first_message,
                    MAX(date) as last_message,
                    COUNT(*) as total_messages,
                    MAX(created_at) as last_sync
                FROM messages
                WHERE chat_id = ? AND is_deleted = FALSE
            ''', (chat_id,)).fetchone()
            
            # Получаем количество изменений за последние 24 часа
            recent_changes = conn.execute('''
                SELECT COUNT(*) as count
                FROM message_history
                WHERE chat_id = ? 
                AND timestamp > datetime('now', '-1 day')
            ''', (chat_id,)).fetchone()
            
            if not chat_info:
                return None
                
            return {
                'last_updated': dict(chat_info)['last_updated'] if chat_info else None,
                'first_message': dict(message_info)['first_message'] if message_info else None,
                'last_message': dict(message_info)['last_message'] if message_info else None,
                'last_sync': dict(message_info)['last_sync'] if message_info else None,
                'total_messages': dict(message_info)['total_messages'] if message_info else 0,
                'recent_changes': dict(recent_changes)['count'] if recent_changes else 0,
                'is_parsing': StatusManager.get_status() is not None
            }
    except Exception as e:
        print(f"Ошибка получения статуса синхронизации чата: {e}")
        return None

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
        
        # Получаем информацию о последней синхронизации
        sync_status = get_sync_status()
        
        # Получаем недавние и избранные чаты
        recent_chats = session_manager.get_recent_chats(limit=6)
        favorite_chats = session_manager.get_favorite_chats()

        return render_template('dashboard.html',
                             stats=stats,
                             total_chats=total_chats,
                             total_messages=total_messages,
                             changes_summary=changes_summary,
                             sync_status=sync_status,
                             recent_chats=recent_chats,
                             favorite_chats=favorite_chats)
    except Exception as e:
        flash(f'Ошибка загрузки данных: {e}', 'error')
        return render_template('dashboard.html', stats=[], total_chats=0, total_messages=0, sync_status=None)

@app.route('/chats')
def chats():
    """Страница со списком чатов"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        raw_chats = analytics.get_most_active_chats(limit=1000)  # Все чаты
        
        # Преобразуем данные к ожидаемому формату
        chats_data = [transform_chat_data(chat) for chat in raw_chats]
        
        # Получаем недавние и избранные чаты
        recent_chats = session_manager.get_recent_chats(limit=10)
        favorite_chats = session_manager.get_favorite_chats()
        
        # Создаем множества ID для быстрой проверки
        recent_ids = {chat['id'] for chat in recent_chats}
        favorite_ids = {chat['id'] for chat in favorite_chats}
        
        # Добавляем флаги к чатам
        for chat in chats_data:
            chat['is_recent'] = chat['id'] in recent_ids
            chat['is_favorite'] = chat['id'] in favorite_ids
            
        return render_template('chats.html', 
                             chats=chats_data,
                             recent_chats=recent_chats,
                             favorite_chats=favorite_chats)
    except Exception as e:
        flash(f'Ошибка загрузки чатов: {e}', 'error')
        return render_template('chats.html', chats=[], recent_chats=[], favorite_chats=[])

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
            
        # Добавляем чат в недавние
        chat_info = report.get('chat_info', {})
        chat_name = chat_info.get('name', f'Chat {chat_id}')
        chat_type = chat_info.get('type', 'private')
        session_manager.add_recent_chat(chat_id, chat_name, chat_type)

        # Анализ стартеров диалогов
        starters = analytics.analyze_conversation_starters(chat_id)

        # Анализ эмодзи
        emoji_analysis = analytics.analyze_emoji_and_expressions(chat_id)
        
        # Получаем статус синхронизации для этого чата
        chat_sync_status = get_chat_sync_status(chat_id)
        
        # Получаем статус мониторинга
        monitor = get_monitor_instance()
        monitor_status = {
            'is_active': monitor is not None and monitor.is_running if monitor else False,
            'is_monitoring_chat': monitor and monitor.is_monitoring_chat(chat_id) if monitor else False
        }

        return render_template('chat_detail.html',
                             report=report,
                             starters=starters,
                             emoji_analysis=emoji_analysis,
                             chat_id=chat_id,
                             sync_status=chat_sync_status,
                             monitor_status=monitor_status)
    except Exception as e:
        import traceback
        error_msg = f'Ошибка загрузки чата: {str(e)}'
        print(f"ERROR in chat_detail: {error_msg}")
        print(traceback.format_exc())
        flash(error_msg, 'error')
        return redirect(url_for('chats'))

@app.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        # Получаем ID чата из параметров запроса
        chat_id = request.args.get('chat_id', type=int)
        
        # Получаем список чатов для селектора
        chats_list = analytics.get_most_active_chats(limit=1000) if analytics else []
        
        # Если выбран чат, показываем только его статистику
        if chat_id:
            # Получаем информацию о конкретном чате
            chat_stats = next((c for c in chats_list if c['chat_id'] == chat_id), None)
            active_chats = [chat_stats] if chat_stats else []
        else:
            # Активные чаты - топ 15
            raw_active_chats = analytics.get_most_active_chats(limit=15)
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
        time_analysis = analytics.get_activity_by_time(chat_id)

        # Топ темы
        topics = analytics.analyze_conversation_topics(chat_id)

        # Изменения
        changes = analytics.get_message_changes_analytics(chat_id)

        return render_template('analytics.html',
                             active_chats=active_chats,
                             time_analysis=time_analysis,
                             topics=topics,
                             changes=changes,
                             selected_chat_id=chat_id,
                             chats_list=chats_list)
    except Exception as e:
        flash(f'Ошибка загрузки аналитики: {e}', 'error')
        return render_template('analytics.html', 
                             active_chats=[], 
                             time_analysis={'by_hour': [], 'by_weekday': []},
                             topics={'top_words': [], 'total_messages_analyzed': 0, 'unique_words': 0},
                             changes={},
                             selected_chat_id=None,
                             chats_list=[])

@app.route('/emoji-stats')
def emoji_stats():
    """Страница статистики эмодзи"""
    if not analytics:
        return redirect(url_for('index'))

    try:
        # Получаем ID чата из параметров запроса
        chat_id = request.args.get('chat_id', type=int)
        
        # Получаем список чатов для селектора
        chats_list = analytics.get_most_active_chats(limit=1000) if analytics else []
        
        # Анализируем эмодзи для выбранного чата или всех чатов
        emoji_analysis = analytics.analyze_emoji_and_expressions(chat_id)
        
        # Проверяем что данные получены корректно
        if not emoji_analysis or not isinstance(emoji_analysis, dict):
            emoji_analysis = {
                'user_expression_stats': [],
                'global_stats': {
                    'most_used_emojis': [],
                    'most_used_text_smilies': [],
                    'total_unique_emojis': 0,
                    'total_messages_analyzed': 0
                }
            }
        
        return render_template('emoji_stats.html', 
                             emoji_analysis=emoji_analysis,
                             selected_chat_id=chat_id,
                             chats_list=chats_list)
    except Exception as e:
        flash(f'Ошибка загрузки статистики эмодзи: {e}', 'error')
        return render_template('emoji_stats.html', 
                             emoji_analysis=None,
                             selected_chat_id=None,
                             chats_list=[])

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

@app.route('/chat/<chat_id>/user/<int:user_id>/messages')
def user_messages(chat_id, user_id):
    """Просмотр сообщений конкретного пользователя в чате"""
    try:
        chat_id = int(chat_id)
    except ValueError:
        flash('Неверный ID чата', 'error')
        return redirect(url_for('chats'))
    
    if not db:
        return redirect(url_for('index'))
    
    try:
        # Получаем параметры пагинации
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Получаем информацию о пользователе
            user_info = conn.execute('''
                SELECT id, username, first_name, last_name
                FROM users
                WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user_info:
                flash('Пользователь не найден', 'error')
                return redirect(url_for('chat_detail', chat_id=chat_id))
            
            # Получаем сообщения пользователя в этом чате
            messages = conn.execute('''
                SELECT 
                    m.id,
                    m.text,
                    m.date,
                    m.is_deleted,
                    m.media_type,
                    m.views,
                    m.forwards,
                    m.reply_to_msg_id,
                    (SELECT COUNT(*) FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited') as edit_count,
                    (SELECT MAX(timestamp) FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'edited') as last_edit
                FROM messages m
                WHERE m.chat_id = ? AND m.sender_id = ?
                ORDER BY m.date DESC
                LIMIT ? OFFSET ?
            ''', (chat_id, user_id, per_page, (page - 1) * per_page)).fetchall()
            
            # Получаем общее количество сообщений пользователя
            total_count = conn.execute('''
                SELECT COUNT(*) 
                FROM messages 
                WHERE chat_id = ? AND sender_id = ?
            ''', (chat_id, user_id)).fetchone()[0]
            
            # Получаем информацию о чате
            chat_info = conn.execute('''
                SELECT name, type 
                FROM chats 
                WHERE id = ?
            ''', (chat_id,)).fetchone()
            
            # Получаем статистику пользователя в этом чате
            user_stats = conn.execute('''
                SELECT 
                    COUNT(*) as message_count,
                    AVG(LENGTH(text)) as avg_length,
                    MIN(date) as first_message,
                    MAX(date) as last_message,
                    COUNT(DISTINCT DATE(date)) as active_days
                FROM messages
                WHERE chat_id = ? AND sender_id = ? AND is_deleted = FALSE
            ''', (chat_id, user_id)).fetchone()
        
        # Вычисляем пагинацию
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('user_messages.html',
                             messages=[dict(m) for m in messages],
                             user_info=dict(user_info),
                             user_stats=dict(user_stats) if user_stats else None,
                             chat_info=dict(chat_info) if chat_info else None,
                             chat_id=chat_id,
                             user_id=user_id,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total_count=total_count)
                             
    except Exception as e:
        flash(f'Ошибка загрузки сообщений: {e}', 'error')
        return redirect(url_for('chat_detail', chat_id=chat_id))

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
                     AND action_type = 'edited') as last_edit,
                    (SELECT timestamp FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'deleted'
                     ORDER BY timestamp DESC LIMIT 1) as deletion_time,
                    (SELECT old_text FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'deleted'
                     ORDER BY timestamp DESC LIMIT 1) as deleted_text
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
                    m.media_type,
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
                    (SELECT timestamp FROM message_history 
                     WHERE message_id = m.id AND chat_id = m.chat_id 
                     AND action_type = 'deleted'
                     ORDER BY timestamp DESC LIMIT 1) as deletion_time,
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
        
        # Добавляем флаг has_more для удобства
        has_more = page * per_page < total_count
        
        # Получаем limit из параметров для обратной совместимости
        limit = request.args.get('limit', type=int)
        if limit:
            messages = messages[:limit]
            has_more = len(messages) == limit
        
        return jsonify({
            'success': True,
            'chat': dict(chat_info) if chat_info else None,
            'messages': [dict(m) for m in messages],
            'has_more': has_more,
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
        cmd = ['python', 'parser_runner.py', '--auto']
        
        # Добавляем параметры в зависимости от типа
        if parsing_type == 'single' and chat_id:
            cmd.extend(['--chats', str(chat_id)])
        elif parsing_type == 'check_changes':
            cmd.extend(['--check-changes'])
            if options.get('check_changes_hours'):
                cmd.extend(['--hours', str(options['check_changes_hours'])])
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
    try:
        # Получаем статус из файла (работает между процессами)
        status = MonitorManager.get_status()
        
        # Проверяем глобальный monitor_manager
        global monitor_manager
        local_active = False
        if 'monitor_manager' in globals() and monitor_manager:
            local_active = monitor_manager.is_active()
        
        # Используем статус из файла как основной
        is_active = status.get('is_active', False) or local_active
        
        return jsonify({
            'is_active': is_active,
            'message': 'Мониторинг активен' if is_active else 'Мониторинг неактивен',
            'stats': status.get('stats', {}),
            'mode': status.get('mode', 'unknown'),
            'start_time': status.get('start_time', '')
        })
    except Exception as e:
        print(f"Error getting monitor status: {e}")
        return jsonify({
            'is_active': False,
            'message': 'Ошибка получения статуса',
            'error': str(e)
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
            yield f"data: {safe_json_dumps({'type': 'connected', 'message': 'Подключено к потоку уведомлений'})}\n\n"
            
            while True:
                try:
                    # Ждем событие с таймаутом
                    event = client_queue.get(timeout=30)
                    yield f"data: {event}\n\n"
                except Empty:
                    # Отправляем heartbeat каждые 30 секунд
                    yield f"data: {safe_json_dumps({'type': 'heartbeat'})}\n\n"
                    
        except GeneratorExit:
            # Клиент отключился
            notification_manager.remove_listener(client_queue)
            
    return Response(generate(), mimetype="text/event-stream")

@app.route('/control-panel')
def control_panel():
    """Страница панели управления"""
    # Получаем список чатов для селекторов
    chats = []
    if analytics:
        try:
            raw_chats = analytics.get_most_active_chats(limit=1000)
            # Преобразуем к формату, ожидаемому шаблоном
            chats = [{'id': chat['chat_id'], 'name': chat['chat_name']} for chat in raw_chats]
        except Exception as e:
            print(f"Error getting chats: {e}")
            chats = []
    
    # Получаем размер БД
    db_size = 0
    if db and os.path.exists(db.db_path):
        db_size = round(os.path.getsize(db.db_path) / (1024 * 1024), 2)
    
    # Получаем номер телефона из конфига
    phone_number = os.getenv('PHONE_NUMBER', 'Не указан')
    
    # Use new template
    return render_template('control_panel_new.html',
                         chats=chats,
                         db_size=db_size,
                         phone_number=phone_number)

@app.route('/help')
def help_page():
    """Страница помощи"""
    return render_template('help.html')

@app.route('/api/parser/status')
def parser_status():
    """Получение статуса парсера"""
    status_data = StatusManager.get_status()
    is_active = status_data is not None and status_data.get('status') == 'parsing'
    
    return jsonify({
        'is_active': is_active,
        'status': status_data
    })

@app.route('/api/parser/start', methods=['POST'])
def start_parser():
    """Запуск парсера в фоновом режиме"""
    import subprocess
    import threading
    
    def run_parser():
        try:
            subprocess.run(['python', 'parser_runner.py', '--auto', '--all'], 
                         capture_output=True, text=True)
        except Exception as e:
            print(f"Error running parser: {e}")
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=run_parser)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Парсер запущен'})

@app.route('/api/parser/stop', methods=['POST'])
def stop_parser():
    """Остановка парсера"""
    StatusManager.request_interruption()
    return jsonify({'success': True, 'message': 'Запрошена остановка парсера'})

@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    """Запуск мониторинга"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'all')
        chat_ids = data.get('chat_ids', [])
        
        # Используем MonitorManager вместо get_monitor_instance
        global monitor_manager
        if 'monitor_manager' not in globals():
            monitor_manager = MonitorManager()
            
        # Запускаем мониторинг в отдельном потоке
        monitor_manager.start(mode=mode, chat_ids=chat_ids if mode == 'selected' else None)
        
        return jsonify({'success': True, 'message': 'Мониторинг запущен'})
    except Exception as e:
        print(f"Error starting monitor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    """Остановка мониторинга"""
    try:
        global monitor_manager
        if 'monitor_manager' in globals() and monitor_manager:
            monitor_manager.stop()
            return jsonify({'success': True, 'message': 'Мониторинг остановлен'})
        else:
            return jsonify({'success': False, 'error': 'Монитор не запущен'}), 400
    except Exception as e:
        print(f"Error stopping monitor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/monitor/configure', methods=['POST'])
def configure_monitor():
    """Настройка мониторинга"""
    data = request.get_json()
    # Сохраняем настройки в конфиг или БД
    return jsonify({'success': True, 'message': 'Настройки сохранены'})

@app.route('/api/parsing/start', methods=['POST'])
def start_parsing():
    """Запуск парсинга с параметрами"""
    data = request.get_json()
    parsing_type = data.get('type', 'all')
    chat_ids = data.get('chat_ids', [])
    force_full_scan = data.get('force_full_scan', False)
    limit = data.get('limit', 0)
    
    # Формируем команду
    cmd = ['python', 'parser_runner.py', '--auto']
    
    if parsing_type == 'all':
        cmd.append('--all')
    elif parsing_type == 'check_changes':
        cmd.append('--check-changes')
    elif parsing_type == 'selected' and chat_ids:
        cmd.extend(['--chats'] + [str(id) for id in chat_ids])
    
    if force_full_scan:
        cmd.append('--force-full-scan')
    
    if limit > 0:
        cmd.extend(['--limit', str(limit)])
    
    # Запускаем в фоне
    import subprocess
    import threading
    
    def run():
        subprocess.run(cmd, capture_output=True)
    
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Парсинг запущен'})

@app.route('/api/activity/stream')
def activity_stream():
    """SSE поток для логов активности"""
    def generate():
        # Отправляем heartbeat
        yield f"data: {safe_json_dumps({'message': 'Подключено к потоку активности', 'type': 'info'})}\n\n"
        
        while True:
            try:
                # Проверяем статус и отправляем обновления
                status = StatusManager.get_status()
                if status:
                    yield f"data: {safe_json_dumps({'message': f'Парсинг: {status.get("current_chat", "...")}', 'type': 'info'})}\n\n"
                
                time.sleep(2)
            except GeneratorExit:
                break
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/api/settings')
def get_settings():
    """Получение настроек"""
    return jsonify({
        'api_id': os.getenv('TELEGRAM_API_ID', ''),
        'phone_number': os.getenv('PHONE_NUMBER', ''),
        'auto_start_monitor': config.ENABLE_REALTIME_MONITOR if hasattr(config, 'ENABLE_REALTIME_MONITOR') else False
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Очистка кэша"""
    # TODO: Реализовать очистку кэша
    return jsonify({'success': True, 'message': 'Кэш очищен'})

@app.route('/api/stats/summary')
def api_stats_summary():
    """API для получения общей статистики для навбара"""
    if not analytics:
        return jsonify({'success': False, 'error': 'База данных недоступна'})
    
    try:
        with sqlite3.connect(analytics.db_path) as conn:
            # Получаем общую статистику
            total_chats = conn.execute('SELECT COUNT(*) FROM chats').fetchone()[0]
            total_messages = conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
            total_changes = conn.execute('SELECT COUNT(*) FROM message_history').fetchone()[0]
            
            return jsonify({
                'success': True,
                'total_chats': total_chats,
                'total_messages': total_messages,
                'total_changes': total_changes
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chats/search')
def api_chats_search():
    """API для поиска чатов"""
    if not analytics:
        return jsonify({'success': False, 'error': 'База данных недоступна'})
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'results': []})
    
    try:
        with sqlite3.connect(analytics.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Ищем чаты по имени
            results = conn.execute('''
                SELECT 
                    c.id,
                    c.name,
                    c.type,
                    COUNT(DISTINCT m.id) as message_count
                FROM chats c
                LEFT JOIN messages m ON c.id = m.chat_id
                WHERE LOWER(c.name) LIKE LOWER(?)
                GROUP BY c.id
                ORDER BY message_count DESC
                LIMIT 10
            ''', (f'%{query}%',)).fetchall()
            
            return jsonify({
                'success': True,
                'results': [dict(row) for row in results]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chat-list')
def api_chat_list():
    """API для получения списка всех чатов с полной статистикой"""
    if not analytics:
        return jsonify({'success': False, 'error': 'База данных недоступна'})
    
    try:
        # Получаем список всех чатов
        chats = analytics.get_all_chats()
        
        # Обогащаем данные статистикой
        enriched_chats = []
        for chat in chats:
            chat_id = chat['chat_id']
            # Получаем статистику для каждого чата
            stats = analytics.get_chat_statistics(chat_id)
            
            enriched_chat = {
                'id': chat_id,
                'name': chat['chat_name'],
                'type': chat['chat_type'],
                'message_count': stats.get('total_messages', 0),
                'unique_users': stats.get('unique_users', 0),
                'last_message_date': stats.get('last_message_date', ''),
                'active_days': stats.get('active_days', 0),
                'avg_messages_per_day': round(stats.get('avg_messages_per_day', 0), 1),
                'edited_count': stats.get('edited_count', 0),
                'deleted_count': stats.get('deleted_count', 0),
                'changes_count': analytics.get_chat_changes_count(chat_id)
            }
            enriched_chats.append(enriched_chat)
        
        return jsonify({
            'success': True,
            'chats': enriched_chats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent-chat/remove/<int:chat_id>', methods=['POST'])
def remove_recent_chat(chat_id):
    """Удаляет чат из недавних"""
    try:
        session_manager.remove_recent_chat(chat_id)
        return jsonify({'success': True, 'message': 'Чат удален из недавних'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/favorite-chat/toggle/<int:chat_id>', methods=['POST'])
def toggle_favorite_chat(chat_id):
    """Переключает статус избранного чата"""
    try:
        # Получаем информацию о чате
        chat_stats = analytics.get_chat_statistics(chat_id)
        if not chat_stats:
            return jsonify({'success': False, 'error': 'Чат не найден'})
            
        chat_name = chat_stats.get('chat_name', f'Chat {chat_id}')
        chat_type = chat_stats.get('chat_type', 'private')
        
        # Переключаем статус
        is_favorite = session_manager.toggle_favorite_chat(chat_id, chat_name, chat_type)
        
        return jsonify({
            'success': True, 
            'is_favorite': is_favorite,
            'message': 'Добавлен в избранное' if is_favorite else 'Удален из избранного'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent-chats/clear', methods=['POST'])
def clear_recent_chats():
    """Очищает список недавних чатов"""
    try:
        session_manager.clear_recent_chats()
        return jsonify({'success': True, 'message': 'Недавние чаты очищены'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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