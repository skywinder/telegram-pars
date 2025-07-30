"""
Модуль для транскрибации голосовых и видеосообщений из Telegram
"""
import os
import asyncio
from typing import Dict, List, Optional
import whisper
import speech_recognition as sr
from pydub import AudioSegment
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
import config

class VoiceTranscriber:
    """
    Класс для транскрибации голосовых сообщений
    """
    
    def __init__(self, use_whisper: bool = True):
        """
        Инициализация транскрибера
        
        Args:
            use_whisper: Использовать Whisper AI (более точно) или SpeechRecognition
        """
        self.use_whisper = use_whisper
        self.whisper_model = None
        self.recognizer = None
        
        # Создаем папку для временных файлов
        self.temp_dir = os.path.join(config.OUTPUT_DIR, 'voice_temp')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def initialize(self):
        """Инициализация модели распознавания"""
        if self.use_whisper:
            print("🔊 Загружаем модель Whisper AI...")
            # Загружаем модель Whisper (можно выбрать размер: tiny, base, small, medium, large)
            self.whisper_model = whisper.load_model("base")  # Компромисс скорость/качество
            print("✅ Whisper готов к работе")
        else:
            print("🔊 Инициализируем SpeechRecognition...")
            self.recognizer = sr.Recognizer()
            print("✅ SpeechRecognition готов")
    
    async def download_voice_message(self, client, message) -> Optional[str]:
        """
        Скачивает голосовое сообщение во временный файл
        
        Args:
            client: Telegram клиент
            message: Сообщение с голосовкой
            
        Returns:
            Путь к скаченному файлу или None
        """
        if not message.media:
            return None
        
        # Проверяем тип медиа
        if hasattr(message.media, 'document'):
            document = message.media.document
            
            # Проверяем MIME тип
            if document.mime_type not in ['audio/ogg', 'audio/mpeg', 'video/mp4', 'audio/wav']:
                return None
            
            # Определяем расширение файла
            if 'ogg' in document.mime_type:
                ext = '.ogg'
            elif 'mp4' in document.mime_type:
                ext = '.mp4'
            elif 'wav' in document.mime_type:
                ext = '.wav'
            else:
                ext = '.mp3'
            
            # Создаем уникальное имя файла
            filename = f"voice_{message.id}_{message.date.strftime('%Y%m%d_%H%M%S')}{ext}"
            filepath = os.path.join(self.temp_dir, filename)
            
            try:
                # Скачиваем файл
                await client.download_media(message.media, filepath)
                print(f"📥 Скачан: {filename}")
                return filepath
            except Exception as e:
                print(f"❌ Ошибка скачивания {filename}: {e}")
                return None
        
        return None
    
    def convert_to_wav(self, input_file: str) -> Optional[str]:
        """
        Конвертирует аудио в WAV формат для распознавания
        
        Args:
            input_file: Путь к исходному файлу
            
        Returns:
            Путь к WAV файлу или None
        """
        try:
            # Определяем выходной файл
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}.wav"
            
            # Конвертируем с помощью pydub
            if input_file.endswith('.ogg'):
                audio = AudioSegment.from_ogg(input_file)
            elif input_file.endswith('.mp4'):
                audio = AudioSegment.from_file(input_file, format="mp4")
            elif input_file.endswith('.mp3'):
                audio = AudioSegment.from_mp3(input_file)
            else:
                # Уже WAV
                return input_file
            
            # Экспортируем в WAV с оптимальными настройками для распознавания
            audio = audio.set_frame_rate(16000).set_channels(1)  # Моно, 16kHz
            audio.export(output_file, format="wav")
            
            print(f"🔄 Конвертирован в WAV: {os.path.basename(output_file)}")
            return output_file
            
        except Exception as e:
            print(f"❌ Ошибка конвертации {input_file}: {e}")
            return None
    
    def transcribe_with_whisper(self, wav_file: str) -> Optional[Dict]:
        """
        Транскрибация с помощью Whisper AI
        
        Args:
            wav_file: Путь к WAV файлу
            
        Returns:
            Результат транскрибации
        """
        try:
            if not self.whisper_model:
                self.initialize()
            
            print(f"🤖 Whisper анализирует: {os.path.basename(wav_file)}")
            result = self.whisper_model.transcribe(wav_file)
            
            return {
                'method': 'whisper',
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'confidence': 'high',  # Whisper обычно очень точный
                'segments': result.get('segments', [])
            }
            
        except Exception as e:
            print(f"❌ Ошибка Whisper: {e}")
            return None
    
    def transcribe_with_speech_recognition(self, wav_file: str) -> Optional[Dict]:
        """
        Транскрибация с помощью SpeechRecognition
        
        Args:
            wav_file: Путь к WAV файлу
            
        Returns:
            Результат транскрибации
        """
        try:
            if not self.recognizer:
                self.initialize()
            
            print(f"🎤 SpeechRecognition анализирует: {os.path.basename(wav_file)}")
            
            with sr.AudioFile(wav_file) as source:
                audio = self.recognizer.record(source)
            
            # Пробуем разные движки
            results = []
            
            # Google Speech Recognition (требует интернет)
            try:
                text = self.recognizer.recognize_google(audio, language='ru-RU')
                results.append({
                    'engine': 'google',
                    'text': text,
                    'confidence': 'medium'
                })
            except:
                pass
            
            # Offline Sphinx (менее точный, но работает без интернета)
            try:
                text = self.recognizer.recognize_sphinx(audio, language='ru-RU')
                results.append({
                    'engine': 'sphinx',
                    'text': text,
                    'confidence': 'low'
                })
            except:
                pass
            
            if results:
                # Возвращаем лучший результат (Google предпочтительнее)
                best_result = results[0]
                return {
                    'method': 'speech_recognition',
                    'text': best_result['text'],
                    'engine': best_result['engine'],
                    'confidence': best_result['confidence'],
                    'alternatives': results[1:] if len(results) > 1 else []
                }
            else:
                return None
                
        except Exception as e:
            print(f"❌ Ошибка SpeechRecognition: {e}")
            return None
    
    def transcribe_audio_file(self, audio_file: str) -> Optional[Dict]:
        """
        Основной метод транскрибации
        
        Args:
            audio_file: Путь к аудио файлу
            
        Returns:
            Результат транскрибации
        """
        # Конвертируем в WAV если нужно
        wav_file = self.convert_to_wav(audio_file)
        if not wav_file:
            return None
        
        # Выбираем метод транскрибации
        if self.use_whisper:
            result = self.transcribe_with_whisper(wav_file)
        else:
            result = self.transcribe_with_speech_recognition(wav_file)
        
        # Удаляем временные файлы
        try:
            if wav_file != audio_file:  # Не удаляем оригинал если он уже WAV
                os.remove(wav_file)
            os.remove(audio_file)
        except:
            pass
        
        return result
    
    async def transcribe_voice_messages(self, client, messages: List) -> Dict:
        """
        Транскрибирует все голосовые сообщения из списка
        
        Args:
            client: Telegram клиент
            messages: Список сообщений
            
        Returns:
            Словарь с результатами транскрибации
        """
        results = {
            'total_voice_messages': 0,
            'successfully_transcribed': 0,
            'failed_transcriptions': 0,
            'transcriptions': {}
        }
        
        for message in messages:
            # Проверяем есть ли голосовое/видео сообщение
            if not message.media:
                continue
                
            if hasattr(message.media, 'document'):
                doc = message.media.document
                if not doc.mime_type or not any(t in doc.mime_type for t in ['audio', 'video']):
                    continue
                
                results['total_voice_messages'] += 1
                print(f"\n🎤 Обрабатываем голосовое сообщение {message.id}...")
                
                # Скачиваем файл
                audio_file = await self.download_voice_message(client, message)
                if not audio_file:
                    results['failed_transcriptions'] += 1
                    continue
                
                # Транскрибируем
                transcription = self.transcribe_audio_file(audio_file)
                if transcription:
                    results['transcriptions'][message.id] = {
                        'message_id': message.id,
                        'date': message.date.isoformat(),
                        'sender_id': message.sender_id,
                        'transcription': transcription,
                        'original_duration': getattr(message.media.document, 'duration', 0)
                    }
                    results['successfully_transcribed'] += 1
                    print(f"✅ Транскрибировано: '{transcription['text'][:50]}...'")
                else:
                    results['failed_transcriptions'] += 1
                    print(f"❌ Не удалось транскрибировать сообщение {message.id}")
        
        return results
    
    def cleanup_temp_files(self):
        """Очищает временные файлы"""
        try:
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                os.remove(file_path)
            print("🧹 Временные файлы очищены")
        except Exception as e:
            print(f"⚠️ Ошибка очистки: {e}")

# Пример использования в main_advanced.py
async def transcribe_voice_messages_menu(parser, transcriber):
    """
    Меню для транскрибации голосовых сообщений
    """
    print("\n🎤 ТРАНСКРИБАЦИЯ ГОЛОСОВЫХ СООБЩЕНИЙ")
    print("⚠️ Это экспериментальная функция!")
    
    # Выбор чата
    chats = await parser.get_chats_list()
    print("\n📋 Доступные чаты:")
    for i, chat in enumerate(chats[:10], 1):
        print(f"{i}. {chat['name']}")
    
    try:
        choice = int(input(f"\nВыбери чат (1-{min(10, len(chats))}): "))
        if 1 <= choice <= min(10, len(chats)):
            selected_chat = chats[choice - 1]
            
            # Получаем сообщения
            limit = int(input("Сколько последних сообщений проверить? (по умолчанию 50): ") or "50")
            messages = await parser.parse_chat_messages(selected_chat['id'], limit)
            
            # Фильтруем только голосовые
            voice_messages = []
            for msg_data in messages:
                # Здесь нужно получить оригинальный объект сообщения
                # Это требует модификации парсера для сохранения медиа-объектов
                pass
            
            print(f"🎤 Найдено голосовых сообщений: {len(voice_messages)}")
            
            if voice_messages:
                confirm = input("Начать транскрибацию? (y/N): ").strip().lower()
                if confirm in ['y', 'yes', 'да']:
                    results = await transcriber.transcribe_voice_messages(parser.client, voice_messages)
                    
                    print(f"\n📊 РЕЗУЛЬТАТЫ:")
                    print(f"🎤 Всего голосовых: {results['total_voice_messages']}")
                    print(f"✅ Успешно: {results['successfully_transcribed']}")
                    print(f"❌ Ошибок: {results['failed_transcriptions']}")
                    
                    # Сохраняем результаты
                    import json
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"voice_transcriptions_{timestamp}.json"
                    filepath = os.path.join(config.OUTPUT_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    
                    print(f"💾 Результаты сохранены: {filename}")
            else:
                print("📭 Голосовых сообщений не найдено")
                
    except ValueError:
        print("❌ Неверный выбор")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        transcriber.cleanup_temp_files()