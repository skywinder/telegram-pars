"""
Telegram Parser - основная логика парсинга чатов с продвинутым управлением ограничениями
"""
import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telethon import TelegramClient
from telethon.tl.types import Message, User, Chat, Channel
from telethon.errors import FloodWaitError, AuthKeyUnregisteredError, UserRestrictedError
from telethon.tl.functions.account import GetAuthorizationsRequest
from database import TelegramDatabase
import config
from realtime_monitor import RealtimeMonitor, set_monitor_instance

class TelegramParser:
    """
    Класс для парсинга чатов Telegram
    """

    def __init__(self):
        """Инициализация парсера"""
        self.client = None
        self.session_name = 'telegram_parser_session'
        self.db = None
        self.monitor = None  # Экземпляр монитора изменений
        if config.ENABLE_HISTORY_TRACKING:
            db_path = os.path.join(config.OUTPUT_DIR, config.DB_FILENAME)
            self.db = TelegramDatabase(db_path)

        # Настройки ограничений
        self.rate_limits = config.RATE_LIMITING
        self.last_request_time = 0
        self.flood_wait_count = 0
        self.account_restricted = False

        # Статистика для мониторинга
        self.session_stats = {
            'total_requests': 0,
            'flood_waits': 0,
            'errors': 0,
            'start_time': None
        }

        # Расширенное отслеживание статуса
        self.current_status = {
            'is_active': False,
            'current_operation': None,
            'current_chat': None,
            'progress': {
                'total_chats': 0,
                'processed_chats': 0,
                'current_chat_progress': 0,
                'estimated_time_remaining': None
            },
            'last_update': None,
            'interruption_requested': False
        }

    async def initialize(self):
        """
        Подключение к Telegram
        """
        print("🔗 Подключаемся к Telegram...")
        self.session_stats['start_time'] = datetime.now()

        # Создаем клиента Telegram
        self.client = TelegramClient(
            self.session_name,
            config.API_ID,
            config.API_HASH
        )

        # Подключаемся
        await self.client.start(phone=config.PHONE_NUMBER)
        print("✅ Успешно подключились к Telegram!")

        # Проверяем ограничения аккаунта если включено
        if self.rate_limits.get('check_account_restrictions', True):
            await self._check_account_restrictions()
        
        # Инициализируем монитор изменений если включен
        await self._init_realtime_monitor()

    async def _check_account_restrictions(self):
        """Проверяет ограничения аккаунта"""
        try:
            print("🔍 Проверяем ограничения аккаунта...")

            # Проверяем авторизацию
            me = await self.client.get_me()
            if not me:
                print("⚠️ Не удалось получить информацию о пользователе")
                self.account_restricted = True
                return

            # Проверяем активные сессии
            try:
                await self._safe_request(self.client(GetAuthorizationsRequest()))
                print("✅ Аккаунт работает нормально")
            except Exception as e:
                print(f"⚠️ Возможные ограничения аккаунта: {e}")
                self.account_restricted = True

        except (AuthKeyUnregisteredError, UserRestrictedError) as e:
            print(f"🚫 Аккаунт заблокирован или ограничен: {e}")
            self.account_restricted = True
        except Exception as e:
            print(f"⚠️ Ошибка при проверке аккаунта: {e}")
    
    async def _init_realtime_monitor(self):
        """Инициализирует монитор изменений"""
        if not self.db:
            return
            
        try:
            # Проверяем настройку в конфиге
            if hasattr(config, 'ENABLE_REALTIME_MONITOR') and config.ENABLE_REALTIME_MONITOR:
                print("🔍 Инициализация монитора изменений...")
                self.monitor = RealtimeMonitor(self.client, self.db)
                set_monitor_instance(self.monitor)
                print("✅ Монитор изменений готов к работе")
            else:
                print("ℹ️ Монитор изменений отключен в настройках")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации монитора: {e}")

    async def _safe_request(self, request, max_retries: int = 3):
        """Безопасное выполнение запроса с обработкой ограничений"""
        for attempt in range(max_retries):
            try:
                # Добавляем задержку между запросами
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                delay_needed = self.rate_limits.get('delay_between_requests', 0.5)

                if time_since_last < delay_needed:
                    sleep_time = delay_needed - time_since_last
                    await asyncio.sleep(sleep_time)

                self.last_request_time = time.time()
                self.session_stats['total_requests'] += 1

                result = await request

                # Сбрасываем счетчик flood wait при успешном запросе
                self.flood_wait_count = 0
                return result

            except FloodWaitError as e:
                self.session_stats['flood_waits'] += 1
                self.flood_wait_count += 1

                wait_time = e.seconds
                max_wait = self.rate_limits.get('max_flood_wait', 300)

                if wait_time > max_wait:
                    print(f"🚫 Слишком долгое ожидание ({wait_time}s), пропускаем запрос")
                    raise

                backoff = self.rate_limits.get('backoff_multiplier', 1.5) ** (attempt + 1)
                actual_wait = min(wait_time * backoff, max_wait)

                print(f"⏳ FloodWait: ждем {actual_wait:.1f}s (попытка {attempt + 1}/{max_retries})")
                await asyncio.sleep(actual_wait)

                if attempt == max_retries - 1:
                    print(f"🚫 Превышено максимальное количество попыток для запроса")
                    raise

            except Exception as e:
                self.session_stats['errors'] += 1
                if attempt == max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # Экспоненциальная задержка
                print(f"⚠️ Ошибка запроса (попытка {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(wait_time)

    def _should_skip_chat(self, chat_info: Dict) -> bool:
        """Определяет, нужно ли пропустить чат при парсинге"""
        if self.account_restricted:
            return True

        # Проверяем кэшированные сообщения
        if self.db:
            cached_count = self.db.get_cached_message_count(chat_info['id'])
            if cached_count > 0:
                print(f"📦 Чат '{chat_info['name']}' уже содержит {cached_count} кэшированных сообщений")
                return True

        return False

    def get_session_statistics(self) -> Dict:
        """Возвращает статистику текущей сессии"""
        current_time = datetime.now()
        duration = (current_time - self.session_stats['start_time']).total_seconds() if self.session_stats['start_time'] else 0

        return {
            **self.session_stats,
            'duration_seconds': duration,
            'requests_per_minute': (self.session_stats['total_requests'] / duration * 60) if duration > 0 else 0,
            'flood_wait_rate': (self.session_stats['flood_waits'] / self.session_stats['total_requests'] * 100) if self.session_stats['total_requests'] > 0 else 0,
            'account_restricted': self.account_restricted
        }

    def update_status(self, operation: str = None, chat_info: Dict = None, progress_update: Dict = None):
        """Обновляет текущий статус операции"""
        self.current_status['last_update'] = datetime.now().isoformat()

        if operation:
            self.current_status['current_operation'] = operation
            self.current_status['is_active'] = operation != 'idle'

        if chat_info:
            self.current_status['current_chat'] = chat_info

        if progress_update:
            self.current_status['progress'].update(progress_update)

            # Вычисляем оставшееся время
            if (self.current_status['progress']['processed_chats'] > 0 and
                self.session_stats['start_time']):
                elapsed = (datetime.now() - self.session_stats['start_time']).total_seconds()
                avg_time_per_chat = elapsed / self.current_status['progress']['processed_chats']
                remaining_chats = (self.current_status['progress']['total_chats'] -
                                 self.current_status['progress']['processed_chats'])
                self.current_status['progress']['estimated_time_remaining'] = avg_time_per_chat * remaining_chats

    def get_current_status(self) -> Dict:
        """Возвращает полный текущий статус"""
        return {
            **self.current_status,
            'session_statistics': self.get_session_statistics()
        }

    def request_interruption(self):
        """Запрашивает изящное прерывание операции"""
        self.current_status['interruption_requested'] = True
        print("🛑 Запрошено прерывание операции. Завершение после текущего чата...")

    def check_interruption_requested(self) -> bool:
        """Проверяет, было ли запрошено прерывание"""
        return self.current_status['interruption_requested']

    async def get_chats_list(self) -> List[Dict]:
        """
        Получаем список всех доступных чатов
        """
        print("📋 Получаем список чатов...")
        chats = []

        try:
            async for dialog in self.client.iter_dialogs():
                chat_info = {
                    'id': dialog.id,
                    'name': dialog.name,
                    'type': type(dialog.entity).__name__,
                    'unread_count': dialog.unread_count
                }
                chats.append(chat_info)

                # Сохраняем информацию о чате в БД
                if self.db:
                    self.db.save_chat(chat_info)

                # Добавляем небольшую задержку между чатами
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"❌ Ошибка при получении списка чатов: {e}")
            self.session_stats['errors'] += 1

        print(f"📁 Найдено {len(chats)} чатов")
        return chats

    async def parse_chat_messages(self, chat_id: int, limit: int = None, session_id: str = None, force_full_scan: bool = False) -> List[Dict]:
        """
        Парсим сообщения из конкретного чата с умным кэшированием

        Args:
            chat_id: ID чата
            limit: Максимальное количество сообщений (None = все доступные)
            session_id: ID сессии парсинга для трекинга изменений
            force_full_scan: Принудительно парсить все сообщения
        """
        # Проверяем ограничения аккаунта
        if self.account_restricted:
            print(f"🚫 Пропускаем чат {chat_id} - аккаунт ограничен")
            return []

        # Используем умное кэширование если не принудительное сканирование
        if not force_full_scan and self.db:
            cached_count = self.db.get_cached_message_count(chat_id)
            last_message_date = self.db.get_last_message_date(chat_id)

            if cached_count > 0:
                print(f"📦 Чат {chat_id} содержит {cached_count} кэшированных сообщений")
                print(f"📅 Последнее сообщение: {last_message_date}")

                # Парсим только новые сообщения с последней даты
                if last_message_date:
                    try:
                        last_date = datetime.fromisoformat(last_message_date.replace('Z', '+00:00'))
                        return await self._parse_new_messages_since(chat_id, last_date, session_id)
                    except ValueError:
                        print("⚠️ Ошибка парсинга даты, выполняем полное сканирование")

        # Полное сканирование
        return await self._parse_all_messages(chat_id, limit, session_id)

    async def _parse_new_messages_since(self, chat_id: int, since_date: datetime, session_id: str = None) -> List[Dict]:
        """Парсит только новые сообщения с указанной даты"""
        print(f"🔄 Парсим новые сообщения с {since_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Обновляем статус с детальной информацией
        self.update_status(
            operation='parsing_new_messages',
            progress_update={
                'current_chat_messages': 0,
                'current_chat_messages_processed': 0,
                'parsing_phase': 'Поиск новых сообщений'
            }
        )

        messages = []
        current_message_ids = []
        new_count = 0
        total_checked = 0

        try:
            async for message in self.client.iter_messages(chat_id, offset_date=since_date):
                if isinstance(message, Message):
                    total_checked += 1
                    
                    # Обновляем статус каждые 10 сообщений
                    if total_checked % 10 == 0:
                        self.update_status(
                            progress_update={
                                'current_chat_messages_processed': total_checked,
                                'new_messages_found': new_count,
                                'parsing_phase': f'Проверено {total_checked} сообщений, найдено {new_count} новых'
                            }
                        )
                    
                    # Добавляем задержку для соблюдения лимитов
                    await asyncio.sleep(self.rate_limits.get('delay_between_requests', 0.5))

                    # Сохраняем информацию об отправителе
                    if message.sender and self.db:
                        await self._save_user_info(message.sender)

                    message_data = {
                        'id': message.id,
                        'date': message.date.isoformat() if message.date else None,
                        'text': message.text or '',
                        'sender_id': message.sender_id,
                        'chat_id': chat_id,
                        'reply_to': message.reply_to_msg_id if message.reply_to else None,
                        'media_type': type(message.media).__name__ if message.media else None,
                        'views': getattr(message, 'views', 0),
                        'forwards': getattr(message, 'forwards', 0)
                    }

                    messages.append(message_data)
                    current_message_ids.append(message.id)
                    new_count += 1

                    # Сохраняем в БД с отслеживанием изменений
                    if self.db and session_id:
                        self.db.save_message_with_history(message_data, session_id)

        except Exception as e:
            print(f"❌ Ошибка при парсинге новых сообщений: {e}")
            self.session_stats['errors'] += 1

        print(f"✅ Найдено {new_count} новых сообщений из {total_checked} проверенных")
        
        # Финальное обновление статуса
        self.update_status(
            progress_update={
                'parsing_phase': f'Завершено: {new_count} новых из {total_checked} проверенных',
                'messages_saved': self.session_stats.get('messages_saved', 0) + new_count
            }
        )
        
        return messages

    async def _parse_all_messages(self, chat_id: int, limit: int = None, session_id: str = None) -> List[Dict]:
        """Полное сканирование всех сообщений чата"""
        if limit is None:
            limit = config.MAX_MESSAGES

        print(f"💬 Полное сканирование чата {chat_id} (лимит: {limit or 'все'})")
        
        # Обновляем статус
        self.update_status(
            operation='parsing_full_chat',
            progress_update={
                'current_chat_messages': limit or 'all',
                'current_chat_messages_processed': 0,
                'parsing_phase': 'Начало полного сканирования'
            }
        )

        messages = []
        current_message_ids = []

        try:
            message_count = 0
            async for message in self.client.iter_messages(chat_id, limit=limit):
                if isinstance(message, Message):
                    message_count += 1
                    
                    # Обновляем статус каждые 10 сообщений
                    if message_count % 10 == 0:
                        self.update_status(
                            progress_update={
                                'current_chat_messages_processed': message_count,
                                'parsing_phase': f'Обработано {message_count} сообщений'
                            }
                        )
                    
                    # Добавляем задержку для соблюдения лимитов
                    await asyncio.sleep(self.rate_limits.get('delay_between_requests', 0.5))

                    # Сохраняем информацию об отправителе
                    if message.sender and self.db:
                        await self._save_user_info(message.sender)

                    message_data = {
                        'id': message.id,
                        'date': message.date.isoformat() if message.date else None,
                        'text': message.text or '',
                        'sender_id': message.sender_id,
                        'chat_id': chat_id,
                        'reply_to': message.reply_to_msg_id if message.reply_to else None,
                        'media_type': type(message.media).__name__ if message.media else None,
                        'views': getattr(message, 'views', 0),
                        'forwards': getattr(message, 'forwards', 0)
                    }

                    messages.append(message_data)
                    current_message_ids.append(message.id)

                    # Сохраняем в БД с отслеживанием изменений
                    if self.db and session_id:
                        self.db.save_message_with_history(message_data, session_id)
                        
                    # Обновляем статистику сессии
                    self.session_stats['messages_saved'] = self.session_stats.get('messages_saved', 0) + 1

            # Помечаем удаленные сообщения
            if self.db and session_id:
                deleted_count = self.db.mark_deleted_messages(chat_id, current_message_ids, session_id)
                if deleted_count > 0:
                    print(f"🗑️ Обнаружено {deleted_count} удаленных сообщений")

        except Exception as e:
            print(f"❌ Ошибка при полном сканировании: {e}")
            self.session_stats['errors'] += 1

        print(f"✅ Спарсили {len(messages)} сообщений")
        return messages

    async def check_for_changes(self, chat_id: int = None, hours_threshold: int = 24) -> Dict[str, Any]:
        """
        Отдельный метод для проверки изменений (редактирование/удаление сообщений)

        Args:
            chat_id: ID конкретного чата (None = все чаты)
            hours_threshold: Проверять изменения за последние N часов
        """
        print(f"🔍 Проверяем изменения за последние {hours_threshold} часов...")

        if self.account_restricted:
            print("🚫 Аккаунт ограничен - проверка изменений невозможна")
            return {'error': 'Account restricted'}

        # Создаем сессию для отслеживания изменений
        session_id = None
        if self.db:
            session_id = self.db.create_scan_session()

        changes_found = {
            'total_changes': 0,
            'edited_messages': 0,
            'deleted_messages': 0,
            'chats_checked': 0,
            'session_id': session_id
        }

        try:
            if chat_id:
                # Проверяем конкретный чат
                chats_to_check = [{'id': chat_id, 'name': f'Chat {chat_id}'}]
            else:
                # Получаем все чаты
                chats_to_check = await self.get_chats_list()

            for chat in chats_to_check:
                chat_id = chat['id']

                # Проверяем нужно ли проверять этот чат
                if self.db and not self.db.should_check_for_changes(chat_id, hours_threshold):
                    print(f"⏭️ Чат '{chat['name']}' недавно проверялся, пропускаем")
                    continue

                print(f"🔄 Проверяем изменения в '{chat['name']}'...")

                try:
                    # Принудительно парсим чат для обнаружения изменений
                    await self.parse_chat_messages(chat_id, session_id=session_id, force_full_scan=True)
                    changes_found['chats_checked'] += 1

                    # Добавляем задержку между чатами
                    delay = self.rate_limits.get('delay_between_chats', 2)
                    await asyncio.sleep(delay)

                except Exception as e:
                    print(f"❌ Ошибка при проверке чата '{chat['name']}': {e}")
                    self.session_stats['errors'] += 1
                    continue

            # Получаем статистику изменений
            if self.db and session_id:
                changes_summary = self.db.get_changes_summary(hours_threshold // 24 or 1)
                changes_found.update(changes_summary)

                stats = {
                    'total_chats': changes_found['chats_checked'],
                    'total_messages': 0,  # Подсчитывается в БД
                    'changes_detected': changes_found['total_changes']
                }
                self.db.close_scan_session(session_id, stats)

        except Exception as e:
            print(f"❌ Ошибка при проверке изменений: {e}")
            self.session_stats['errors'] += 1

        print(f"✅ Проверка изменений завершена. Найдено {changes_found['total_changes']} изменений")
        return changes_found

    async def parse_all_chats(self, force_full_scan: bool = False) -> Dict[str, Any]:
        """
        Парсим все доступные чаты с умным кэшированием и обработкой ограничений

        Args:
            force_full_scan: Принудительно парсить все сообщения (игнорировать кэш)
        """
        print("🚀 Начинаем парсинг всех чатов...")

        # Проверяем ограничения аккаунта
        if self.account_restricted:
            print("🚫 Парсинг невозможен - аккаунт ограничен")
            return {'error': 'Account restricted', 'session_statistics': self.get_session_statistics()}

        # Инициализируем статус операции
        self.update_status(operation='parsing_all_chats')

        # Создаем сессию парсинга
        session_id = None
        if self.db:
            session_id = self.db.create_scan_session()

        # Получаем список чатов
        chats = await self.get_chats_list()

        # Обновляем прогресс
        self.update_status(progress_update={
            'total_chats': len(chats),
            'processed_chats': 0
        })

        all_data = {
            'timestamp': datetime.now().isoformat(),
            'total_chats': len(chats),
            'chats': {},
            'session_id': session_id,
            'parsing_mode': 'full_scan' if force_full_scan else 'smart_cache'
        }

        total_messages = 0
        chats_parsed = 0
        chats_skipped = 0

        # Парсим каждый чат
        for i, chat in enumerate(chats, 1):
            # Проверяем прерывание
            if self.check_interruption_requested():
                print(f"\n🛑 Прерывание запрошено. Остановка после {i-1}/{len(chats)} чатов")
                break

            # Обновляем статус текущего чата
            self.update_status(
                chat_info={
                    'id': chat['id'],
                    'name': chat['name'],
                    'type': chat['type']
                },
                progress_update={
                    'processed_chats': i - 1,
                    'current_chat_number': i,
                    'parsing_phase': f'Парсинг чата {i}/{len(chats)}: {chat["name"]}'
                }
            )

            print(f"\n📊 Прогресс: {i}/{len(chats)} - Обрабатываем '{chat['name']}'")

            # Показываем расширенную статистику
            if i > 1 and self.current_status['progress']['estimated_time_remaining']:
                remaining_time = self.current_status['progress']['estimated_time_remaining']
                print(f"⏱️ Примерно осталось: {remaining_time/60:.1f} минут")

            try:
                # Проверяем нужно ли парсить чат
                if not force_full_scan and self._should_skip_chat(chat):
                    all_data['chats'][str(chat['id'])] = {
                        'info': chat,
                        'messages': [],
                        'total_messages': 0,
                        'status': 'skipped - already cached'
                    }
                    chats_skipped += 1
                    continue

                messages = await self.parse_chat_messages(
                    chat['id'],
                    session_id=session_id,
                    force_full_scan=force_full_scan
                )

                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'messages': messages,
                    'total_messages': len(messages),
                    'status': 'parsed'
                }
                total_messages += len(messages)
                chats_parsed += 1

                # Добавляем задержку между чатами
                delay = self.rate_limits.get('delay_between_chats', 2)
                print(f"⏸️ Ждем {delay}s перед следующим чатом...")
                await asyncio.sleep(delay)

            except FloodWaitError as e:
                print(f"🚫 FloodWait для чата '{chat['name']}': {e.seconds}s")
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'error': f'FloodWait: {e.seconds}s',
                    'messages': [],
                    'total_messages': 0,
                    'status': 'flood_wait_error'
                }

                # Если слишком долгое ожидание, прерываем
                if e.seconds > self.rate_limits.get('max_flood_wait', 300):
                    print(f"🚫 Прерываем парсинг - слишком долгое ожидание")
                    break

            except Exception as e:
                print(f"❌ Ошибка при парсинге чата '{chat['name']}': {e}")
                all_data['chats'][str(chat['id'])] = {
                    'info': chat,
                    'error': str(e),
                    'messages': [],
                    'total_messages': 0,
                    'status': 'error'
                }
                self.session_stats['errors'] += 1

        # Добавляем статистику парсинга
        all_data['parsing_statistics'] = {
            'chats_parsed': chats_parsed,
            'chats_skipped': chats_skipped,
            'total_messages': total_messages,
            'session_statistics': self.get_session_statistics()
        }

        # Закрываем сессию парсинга
        if self.db and session_id:
            stats = {
                'total_chats': chats_parsed,
                'total_messages': total_messages,
                'changes_detected': 0  # Подсчитывается в БД
            }
            self.db.close_scan_session(session_id, stats)

            # Получаем сводку изменений
            changes_summary = self.db.get_changes_summary()
            all_data['changes_summary'] = changes_summary

            # Добавляем общую статистику парсинга
            all_data['database_statistics'] = self.db.get_parsing_statistics()

        # Завершаем операцию
        self.update_status(operation='idle')

        print(f"\n✅ Парсинг завершен!")
        print(f"📊 Обработано чатов: {chats_parsed}")
        print(f"⏭️ Пропущено чатов: {chats_skipped}")
        print(f"💬 Всего сообщений: {total_messages}")

        return all_data

    async def _save_user_info(self, user):
        """Сохраняет информацию о пользователе"""
        if not isinstance(user, User) or not self.db:
            return

        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute('''
                INSERT OR IGNORE INTO users (id, username, first_name, last_name, phone)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user.id,
                getattr(user, 'username', None),
                getattr(user, 'first_name', None),
                getattr(user, 'last_name', None),
                getattr(user, 'phone', None)
            ))

    async def close(self):
        """Закрываем соединение с выводом статистики"""
        # Останавливаем монитор если он активен
        if self.monitor and self.monitor.is_running:
            self.monitor.stop_monitoring()
            print("🛑 Остановлен монитор изменений")
            
        if self.client:
            await self.client.disconnect()
            print("👋 Отключились от Telegram")

        # Выводим финальную статистику сессии
        stats = self.get_session_statistics()
        print(f"\n📊 Статистика сессии:")
        print(f"⏱️ Длительность: {stats['duration_seconds']:.1f}s")
        print(f"📡 Всего запросов: {stats['total_requests']}")
    
    async def start_realtime_monitor(self, chat_ids: Optional[List[int]] = None):
        """Запускает мониторинг изменений в реальном времени"""
        if not self.monitor:
            print("❌ Монитор не инициализирован. Включите ENABLE_REALTIME_MONITOR в config.py")
            return False
            
        try:
            await self.monitor.start_monitoring(chat_ids)
            print(f"✅ Мониторинг изменений запущен для {len(chat_ids) if chat_ids else 'всех'} чатов")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска мониторинга: {e}")
            return False
    
    def stop_realtime_monitor(self):
        """Останавливает мониторинг изменений"""
        if self.monitor and self.monitor.is_running:
            self.monitor.stop_monitoring()
            print("🛑 Мониторинг изменений остановлен")
            return True
        return False