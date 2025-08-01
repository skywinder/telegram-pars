# 🚀 Telegram Chat Parser - Расширенная версия

Мощный инструмент для парсинга, анализа и отслеживания истории изменений ваших Telegram чатов с поддержкой ИИ анализа.

> **📋 Требования**: Python 3.12+ | Последнее обновление: январь 2025

## ✨ Основные возможности:

### 📊 Парсинг и сбор данных:
- Извлечение сообщений из всех чатов
- Отслеживание истории изменений (редактирования, удаления)
- Сохранение информации о пользователях
- Экспорт в JSON, CSV форматы

### 🔍 Аналитика:
- **Самые активные чаты** - статистика по сообщениям и пользователям
- **Анализ активности по времени** - паттерны активности по часам и дням
- **Анализ тем разговоров** - частотность слов и ключевые темы
- **Статистика пользователей** - кто больше всего пишет

### 🤖 ИИ анализ:
- Автоматическое создание файлов для загрузки в ChatGPT/Claude
- Оптимизированные форматы для ИИ анализа
- Готовые промпты для анализа стиля общения
- Анализ тем и эмоциональной окраски

### 📝 Трекинг изменений:
- Отслеживание редактирования сообщений
- Обнаружение удаленных сообщений
- История изменений с временными метками
- Сравнение между разными парсингами

### 📊 Мониторинг статуса (NEW!):
- **Real-time мониторинг** - отслеживание прогресса в реальном времени
- **Веб-интерфейс статуса** - визуальный мониторинг через браузер
- **CLI мониторинг** - терминальный интерфейс с прогресс-баром
- **Изящное прерывание** - безопасная остановка с сохранением данных
- **Статистика API** - мониторинг запросов и ошибок
- **Оценка времени** - расчет времени завершения операций

## 🗄️ База данных (SQLite):
- Локальное хранение без внешних серверов
- Эффективное отслеживание изменений
- Быстрый поиск и аналитика
- Автоматическое создание индексов

## 🎯 Для кого этот проект:
- **Исследователи** - анализ коммуникационных паттернов
- **Личное использование** - анализ своего стиля общения
- **Изучающие программирование** - практика работы с API и БД
- **Аналитики** - изучение социальных взаимодействий

## ⚡ Мгновенная установка:

### 🛠️ Автоматическая установка (рекомендуется):

#### macOS/Linux:
```bash
git clone <repository>
cd telegram-pars
./setup.sh
```

#### Windows:
```cmd
git clone <repository>
cd telegram-pars
setup.bat
```

**Готово!** Скрипт автоматически:
- ✅ Проверит/установит Python 3.12
- ✅ Создаст виртуальное окружение (с подтверждением при перезаписи)
- ✅ Установит все зависимости
- ✅ Создаст файл .env для настройки
- ✅ Создаст скрипт запуска

> **🔒 Безопасность**: Скрипты спросят подтверждение перед удалением существующих файлов

---

## 🚀 Ручная установка:

### 📋 Системные требования:
- **Python 3.12+** (рекомендуется последняя версия)
- **macOS**: Homebrew для установки Python
- **Linux**: `python3.12-dev` пакет
- **Windows**: Python 3.12 с официального сайта

### 1. 🐍 Установка Python 3.12:

#### macOS (с Homebrew):
```bash
# Установка Homebrew (если нет)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка Python 3.12
brew install python@3.12
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

#### Windows:
1. Скачайте Python 3.12 с https://python.org/downloads/
2. При установке отметьте "Add to PATH"

### 2. 📦 Клонирование и настройка проекта:
```bash
# Клонирование репозитория
git clone <repository>
cd telegram-pars

# Создание виртуального окружения
python3.12 -m venv telegram_env

# Активация окружения
# macOS/Linux:
source telegram_env/bin/activate

# Windows:
telegram_env\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
```

### 3. 🔑 Настройка Telegram API:
1. Перейдите на https://my.telegram.org
2. Войдите с вашим номером телефона
3. Перейдите в "API Development tools"
4. Создайте новое приложение:
   - **App title**: Telegram Parser
   - **Short name**: parser
   - **Platform**: Desktop
5. Создайте файл `.env` в корне проекта:
```env
# Настройки Telegram API
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
PHONE_NUMBER=+7XXXXXXXXXX
```

### 4. 🚀 Запуск:
```bash
# Убедитесь что виртуальное окружение активировано
source telegram_env/bin/activate  # macOS/Linux
# или
telegram_env\Scripts\activate     # Windows

# Полная версия с аналитикой (рекомендуется)
python main.py

# Простая версия (только парсинг)
python main_simple.py
```

### 5. 🔄 Повторный запуск:
```bash
# При следующем запуске достаточно:
cd telegram-pars
source telegram_env/bin/activate  # macOS/Linux
python main.py
```

### 6. 📊 Мониторинг статуса (NEW!):
```bash
# Веб-интерфейс с мониторингом статуса
python web_interface.py
# Открыть: http://localhost:5001/status

# CLI мониторинг в отдельном терминале
python status_monitor.py

# Мониторинг с настройками
python status_monitor.py --interval 1.0    # Обновление каждую секунду
python status_monitor.py --url http://192.168.1.100:5000  # Удаленный мониторинг
```

**Возможности мониторинга:**
- 📊 **Real-time прогресс** с визуальным прогресс-баром
- ⏰ **Оценка времени** завершения операций
- 🛑 **Безопасное прерывание** через Ctrl+C
- 📈 **Статистика API** запросов и ошибок
- 🌐 **Веб-интерфейс** + CLI мониторинг

## 📁 Структура проекта:
```
telegram-pars/
├── telegram_env/        # Виртуальное окружение Python (создается автоматически)
├── main.py              # Полная версия с аналитикой
├── main_simple.py       # Простая версия (только парсинг)
├── telegram_parser.py   # Логика парсинга с трекингом
├── database.py          # SQLite база для истории
├── analytics.py         # Модуль аналитики
├── ai_exporter.py      # Экспорт для ИИ анализа
├── data_exporter.py    # Стандартный экспорт
├── web_interface.py    # Веб-интерфейс с мониторингом
├── status_monitor.py   # CLI мониторинг статуса (NEW!)
├── config.py           # Настройки
├── requirements.txt     # Зависимости Python
├── .env                # API ключи (создается вручную)
└── parsed_data/        # Результаты (создается автоматически)
    ├── telegram_history.db  # База данных SQLite
    ├── ai_ready/           # Файлы для ИИ анализа
    └── exports/            # JSON/CSV файлы
```

## 💡 Примеры использования:

### Анализ стиля общения:
1. Спарсите чаты: `python main.py` → пункт 3
2. Создайте ИИ пакет: меню → пункт 5 → пункт 5
3. Загрузите файлы в ChatGPT/Claude
4. Спросите: "Проанализируй мой стиль общения"

### Отслеживание изменений:
1. Первый парсинг: `python main.py`
2. Через неделю повторный парсинг
3. Просмотр изменений: меню → пункт 6

### Поиск активных чатов:
1. Запустите аналитику: меню → пункт 4 → пункт 1
2. Выберите период анализа

## 🔒 Конфиденциальность:
- Все данные хранятся локально
- API ключи защищены в .env файле
- Нет передачи данных на внешние серверы
- Контроль над экспортом для ИИ

## 🔧 Устранение неполадок:

### Проблемы с установкой Python:

#### macOS - "Command not found: python3.12"
```bash
# Добавьте Python в PATH
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Или используйте полный путь
/usr/local/bin/python3.12 -m venv telegram_env
```

#### Linux - "python3.12: command not found"
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3.12-dev

# CentOS/RHEL
sudo dnf install python3.12 python3.12-pip python3.12-venv
```

#### Windows - "python3.12 is not recognized"
```cmd
# Используйте py launcher
py -3.12 -m venv telegram_env

# Или переустановите Python с галочкой "Add to PATH"
```

### Проблемы с зависимостями:

#### Ошибка "externally-managed-environment"
```bash
# Используйте виртуальное окружение (рекомендуется)
python3.12 -m venv telegram_env
source telegram_env/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

#### Ошибка при установке pandas/matplotlib
```bash
# macOS - установите Command Line Tools
xcode-select --install

# Linux - установите зависимости для сборки
sudo apt install build-essential python3.12-dev

# Windows - обновите pip и wheel
python -m pip install --upgrade pip wheel setuptools
```

### Проблемы с Telegram API:

#### "Invalid phone number"
- Используйте международный формат: `+7XXXXXXXXXX`
- Убедитесь что номер активен в Telegram

#### "API ID/Hash invalid"
- Проверьте что API ID состоит только из цифр
- API Hash должен быть строкой из букв и цифр
- Не должно быть лишних пробелов в .env файле

### Проблемы с запуском:

#### "ModuleNotFoundError: No module named..."
```bash
# Убедитесь что активировали виртуальное окружение
source telegram_env/bin/activate  # macOS/Linux
telegram_env\Scripts\activate     # Windows

# Переустановите зависимости
pip install -r requirements.txt
```

#### База данных заблокирована
```bash
# Закройте все экземпляры программы
# Удалите lock файлы если есть
rm parsed_data/*.lock
```

### 🆘 Получить помощь:
1. **Проверьте логи** - ошибки отображаются в консоли
2. **GitHub Issues** - опишите проблему с версией Python и ОС
3. **Telegram Support** - @your_support_channel

## 📚 Детальная документация:
- `VOICE_TRANSCRIPTION_GUIDE.md` - инструкция по работе с голосовыми сообщениями
- `SECURITY_GUIDE.md` - рекомендации по безопасности
- Встроенная справка в программе

## 📈 История изменений:
- **v2.0** (янв 2025) - Обновление до Python 3.12, новые зависимости
- **v1.5** - Анализ тем разговоров, улучшенная аналитика
- **v1.0** - Базовый функционал парсинга и экспорта