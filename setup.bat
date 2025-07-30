@echo off
REM 🚀 Telegram Chat Parser - Setup Script for Windows
REM Автоматическая настройка проекта для Windows

setlocal enabledelayedexpansion

echo.
echo 🚀 Telegram Chat Parser - Setup Script
echo =====================================
echo.

REM Проверка Python 3.12
echo 🔄 Проверка Python 3.12...

REM Пробуем разные команды Python
python --version 2>nul | findstr "3.12" >nul
if !errorlevel! equ 0 (
    set PYTHON_CMD=python
    goto :python_found
)

python3 --version 2>nul | findstr "3.12" >nul
if !errorlevel! equ 0 (
    set PYTHON_CMD=python3
    goto :python_found
)

py -3.12 --version 2>nul | findstr "3.12" >nul
if !errorlevel! equ 0 (
    set PYTHON_CMD=py -3.12
    goto :python_found
)

REM Python 3.12 не найден
echo ❌ Python 3.12 не найден!
echo.
echo 📥 Пожалуйста, установите Python 3.12:
echo    1. Перейдите на https://python.org/downloads/
echo    2. Скачайте Python 3.12 для Windows
echo    3. При установке отметьте "Add Python to PATH"
echo    4. Перезапустите командную строку
echo.
pause
exit /b 1

:python_found
echo ✅ Python найден: !PYTHON_CMD!
for /f "tokens=*" %%i in ('!PYTHON_CMD! --version') do echo    Версия: %%i

REM Создание виртуального окружения
echo.
echo 🔄 Создание виртуального окружения...

if exist telegram_env (
    echo ⚠️  Виртуальное окружение уже существует.
    set /p "response=Хотите пересоздать его? (y/N): "
    if /i "!response!"=="y" (
        echo 🔄 Удаление старого окружения...
        rmdir /s /q telegram_env
    ) else (
        echo ✅ Используем существующее виртуальное окружение
        goto :install_deps
    )
)

!PYTHON_CMD! -m venv telegram_env
if !errorlevel! neq 0 (
    echo ❌ Ошибка создания виртуального окружения!
    pause
    exit /b 1
)

echo ✅ Виртуальное окружение создано!

:install_deps
REM Активация и установка зависимостей
echo.
echo 🔄 Активация окружения и установка зависимостей...

call telegram_env\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo ❌ Ошибка активации виртуального окружения!
    pause
    exit /b 1
)

REM Обновление pip
python -m pip install --upgrade pip

REM Установка зависимостей
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo ❌ Ошибка установки зависимостей!
    echo.
    echo 💡 Возможные решения:
    echo    - Обновите pip: python -m pip install --upgrade pip
    echo    - Установите Visual Studio Build Tools
    echo    - Попробуйте запустить как администратор
    pause
    exit /b 1
)

echo ✅ Все зависимости установлены!

REM Создание файла .env
echo.
echo 🔄 Создание файла .env...

if not exist .env (
    (
        echo # Настройки Telegram API
        echo # Получите эти данные на https://my.telegram.org
        echo TELEGRAM_API_ID=your_api_id_here
        echo TELEGRAM_API_HASH=your_api_hash_here
        echo PHONE_NUMBER=+7XXXXXXXXXX
    ) > .env
    echo ✅ Файл .env создан!
) else (
    echo ✅ Файл .env уже существует
)

REM Создание скрипта запуска
echo.
echo 🔄 Создание скрипта запуска...

(
    echo @echo off
    echo echo 🚀 Запуск Telegram Chat Parser...
    echo call telegram_env\Scripts\activate.bat
    echo python main_advanced.py
    echo pause
) > run.bat

echo ✅ Создан run.bat для запуска

REM Финальные инструкции
echo.
echo 🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!
echo.
echo 📋 Следующие шаги:
echo.
echo 1. 🔑 Настройте API ключи:
echo    - Откройте файл .env в блокноте
echo    - Замените your_api_id_here на ваш API ID
echo    - Замените your_api_hash_here на ваш API Hash  
echo    - Замените +7XXXXXXXXXX на ваш номер телефона
echo.
echo 2. 🚀 Запустите программу:
echo    - Двойной клик на run.bat
echo    - Или в командной строке: run.bat
echo.
echo 📚 Получить API ключи:
echo    https://my.telegram.org → API Development tools
echo.
echo ✨ Готово к использованию!
echo.
pause