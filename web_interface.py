"""
Веб-интерфейс для Telegram Parser
Запуск: python web_interface.py
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from analytics import TelegramAnalytics
from ai_exporter import AIExporter
from database import TelegramDatabase
import config

# Создаем Flask приложение
app = Flask(__name__)
app.secret_key = 'telegram_parser_secret_key_2024'  # Для flash сообщений

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

@app.route('/')
def index():
    """Главная страница"""
    if not analytics:
        return render_template('no_data.html')

    try:
        # Получаем базовую статистику
        stats = analytics.get_chat_statistics()[:10]  # Топ 10 чатов

        # Общая статистика
        total_chats = len(analytics.get_chat_statistics())
        total_messages = sum(s['total_messages'] for s in analytics.get_chat_statistics())

        # Последние изменения
        changes_summary = analytics.get_changes_summary(days=7)

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
        chats_data = analytics.get_chat_statistics()
        return render_template('chats.html', chats=chats_data)
    except Exception as e:
        flash(f'Ошибка загрузки чатов: {e}', 'error')
        return render_template('chats.html', chats=[])

@app.route('/chat/<int:chat_id>')
def chat_detail(chat_id):
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
        active_chats = analytics.get_most_active_chats(limit=15)

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
        return render_template('analytics.html')

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

@app.route('/api/chat-stats/<int:chat_id>')
def api_chat_stats(chat_id):
    """API для получения статистики чата"""
    if not analytics:
        return jsonify({'error': 'Analytics недоступен'}), 500

    try:
        # Базовая статистика
        stats = analytics.get_chat_statistics()
        chat_stats = next((s for s in stats if s['id'] == chat_id), None)

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

@app.route('/api/status')
def api_get_status():
    """API для получения текущего статуса парсинга"""
    if not active_parser:
        return jsonify({
            'status': 'no_active_parser',
            'message': 'Нет активного парсера'
        })

    try:
        status = active_parser.get_current_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/status/interrupt', methods=['POST'])
def api_request_interrupt():
    """API для запроса прерывания парсинга"""
    if not active_parser:
        return jsonify({
            'status': 'error',
            'message': 'Нет активного парсера для прерывания'
        }), 400

    try:
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
        print("   python main_advanced.py")