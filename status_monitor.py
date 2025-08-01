#!/usr/bin/env python3
"""
Real-time Status Monitor for Telegram Parser
Monitors parsing progress and allows graceful interruption
"""
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional
import requests


class StatusMonitor:
    """Real-time status monitor for Telegram Parser operations"""

    def __init__(self, api_base_url: str = "http://localhost:5001"):
        self.api_base_url = api_base_url
        self.running = True
        self.last_status = None

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Получен сигнал {signum}. Отправляем запрос на прерывание...")
            self.request_interruption()
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def get_status(self) -> Optional[dict]:
        """Get current parsing status from API"""
        try:
            response = requests.get(f"{self.api_base_url}/api/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'api_error', 'message': f'HTTP {response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'status': 'connection_error', 'message': str(e)}

    def request_interruption(self) -> bool:
        """Request graceful interruption of parsing operation"""
        try:
            response = requests.post(f"{self.api_base_url}/api/status/interrupt", timeout=5)
            if response.status_code == 200:
                print("✅ Запрос на прерывание отправлен успешно")
                return True
            else:
                print(f"❌ Ошибка при запросе прерывания: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка соединения при запросе прерывания: {e}")
            return False

    def format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}с"
        elif seconds < 3600:
            return f"{seconds/60:.1f}м"
        else:
            return f"{seconds/3600:.1f}ч"

    def display_status(self, status_data: dict):
        """Display current status in a nice format"""
        # Clear screen for better display
        os.system('clear' if os.name == 'posix' else 'cls')

        print("🔍 TELEGRAM PARSER - МОНИТОРИНГ СТАТУСА")
        print("=" * 60)
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if status_data['status'] == 'no_active_parser':
            print("😴 Нет активных операций парсинга")
            print("💡 Запустите парсер для мониторинга статуса")
            return

        if status_data['status'] == 'connection_error':
            print(f"❌ Ошибка соединения: {status_data['message']}")
            print("💡 Убедитесь, что веб-интерфейс запущен на http://localhost:5001")
            return

        if status_data['status'] != 'success':
            print(f"❌ Ошибка: {status_data.get('message', 'Unknown error')}")
            return

        data = status_data['data']

        # Основная информация
        print(f"🔄 Операция: {data.get('current_operation', 'Неизвестно')}")
        print(f"📱 Активность: {'🟢 Активен' if data.get('is_active') else '🔴 Неактивен'}")

        if data.get('interruption_requested'):
            print("🛑 ЗАПРОШЕНО ПРЕРЫВАНИЕ - ждем завершения текущей операции...")

        # Информация о текущем чате
        current_chat = data.get('current_chat')
        if current_chat:
            print(f"💬 Текущий чат: {current_chat.get('name', 'Unknown')}")
            print(f"🏷️  Тип чата: {current_chat.get('type', 'Unknown')}")

        # Прогресс
        progress = data.get('progress', {})
        if progress.get('total_chats', 0) > 0:
            processed = progress.get('processed_chats', 0)
            total = progress.get('total_chats', 0)
            percentage = (processed / total) * 100 if total > 0 else 0

            print(f"\n📊 ПРОГРЕСС:")
            print(f"├─ Чаты: {processed}/{total} ({percentage:.1f}%)")

            # Progress bar
            bar_length = 40
            filled_length = int(bar_length * processed // total) if total > 0 else 0
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f"├─ [{bar}]")

            # Estimated time remaining
            eta = progress.get('estimated_time_remaining')
            if eta and eta > 0:
                print(f"├─ Осталось: ~{self.format_time(eta)}")

        # Статистика сессии
        session_stats = data.get('session_statistics', {})
        if session_stats:
            print(f"\n📈 СТАТИСТИКА СЕССИИ:")
            print(f"├─ Всего запросов: {session_stats.get('total_requests', 0)}")
            print(f"├─ FloodWait ошибок: {session_stats.get('flood_waits', 0)}")
            print(f"├─ Других ошибок: {session_stats.get('errors', 0)}")

            duration = session_stats.get('duration_seconds', 0)
            if duration > 0:
                print(f"├─ Длительность: {self.format_time(duration)}")

            rpm = session_stats.get('requests_per_minute', 0)
            if rpm > 0:
                print(f"├─ Запросов/мин: {rpm:.1f}")

            flood_rate = session_stats.get('flood_wait_rate', 0)
            if flood_rate > 0:
                print(f"└─ Процент FloodWait: {flood_rate:.1f}%")

        print(f"\n🔄 Последнее обновление: {data.get('last_update', 'Не указано')}")
        print("\n💡 Нажмите Ctrl+C для изящного прерывания операции")

    def run(self, refresh_interval: float = 2.0):
        """Run the status monitor"""
        print("🚀 Запуск монитора статуса Telegram Parser...")
        print("💡 Нажмите Ctrl+C для изящного прерывания операции")

        self.setup_signal_handlers()

        while self.running:
            try:
                status = self.get_status()
                if status:
                    self.display_status(status)
                    self.last_status = status

                # Wait for next refresh
                time.sleep(refresh_interval)

            except KeyboardInterrupt:
                print(f"\n🛑 Прерывание мониторинга...")
                self.request_interruption()
                break
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                time.sleep(refresh_interval)

        print("👋 Мониторинг завершен")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Telegram Parser Status Monitor')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='Base URL for Telegram Parser API (default: http://localhost:5001)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Refresh interval in seconds (default: 2.0)')

    args = parser.parse_args()

    monitor = StatusMonitor(api_base_url=args.url)
    monitor.run(refresh_interval=args.interval)


if __name__ == '__main__':
    main()