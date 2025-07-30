#!/bin/bash
# 🚀 Telegram Chat Parser - Setup Script
# Автоматическая настройка проекта для всех операционных систем

set -e  # Остановка при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_step() {
    echo -e "${BLUE}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка операционной системы
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        print_error "Неподдерживаемая операционная система: $OSTYPE"
        exit 1
    fi
    print_success "Операционная система: $OS"
}

# Проверка наличия Python 3.12
check_python() {
    print_step "Проверка Python 3.12..."
    
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
        print_success "Python 3.12 найден: $(python3.12 --version)"
    elif command -v python3 &> /dev/null && python3 --version | grep -q "3.12"; then
        PYTHON_CMD="python3"
        print_success "Python 3.12 найден: $(python3 --version)"
    elif command -v python &> /dev/null && python --version | grep -q "3.12"; then
        PYTHON_CMD="python"
        print_success "Python 3.12 найден: $(python --version)"
    else
        print_error "Python 3.12 не найден!"
        install_python
    fi
}

# Установка Python 3.12
install_python() {
    print_step "Установка Python 3.12..."
    
    case $OS in
        macos)
            if ! command -v brew &> /dev/null; then
                print_step "Установка Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            print_step "Установка Python 3.12 через Homebrew..."
            brew install python@3.12
            PYTHON_CMD="python3.12"
            ;;
            
        linux)
            if command -v apt &> /dev/null; then
                print_step "Установка Python 3.12 через apt..."
                sudo apt update
                sudo apt install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt install -y python3.12 python3.12-venv python3.12-dev python3.12-pip
            elif command -v dnf &> /dev/null; then
                print_step "Установка Python 3.12 через dnf..."
                sudo dnf install -y python3.12 python3.12-pip python3.12-venv
            else
                print_error "Неподдерживаемый пакетный менеджер. Установите Python 3.12 вручную."
                exit 1
            fi
            PYTHON_CMD="python3.12"
            ;;
            
        windows)
            print_error "Автоматическая установка Python на Windows не поддерживается."
            print_warning "Пожалуйста, скачайте Python 3.12 с https://python.org/downloads/"
            exit 1
            ;;
    esac
    
    print_success "Python 3.12 установлен!"
}

# Создание виртуального окружения
create_venv() {
    print_step "Создание виртуального окружения..."
    
    if [ -d "telegram_env" ]; then
        print_warning "Виртуальное окружение уже существует."
        echo -e "${YELLOW}Хотите пересоздать его? (y/N): ${NC}"
        read -r response
        case "$response" in
            [yY][eE][sS]|[yY])
                print_step "Удаление старого окружения..."
                rm -rf telegram_env
                ;;
            *)
                print_success "Используем существующее виртуальное окружение"
                return 0
                ;;
        esac
    fi
    
    $PYTHON_CMD -m venv telegram_env
    print_success "Виртуальное окружение создано!"
}

# Активация виртуального окружения и установка зависимостей
install_dependencies() {
    print_step "Активация окружения и установка зависимостей..."
    
    # Активация в зависимости от ОС
    if [[ "$OS" == "windows" ]]; then
        source telegram_env/Scripts/activate
    else
        source telegram_env/bin/activate
    fi
    
    # Обновление pip
    pip install --upgrade pip
    
    # Установка зависимостей
    pip install -r requirements.txt
    
    print_success "Все зависимости установлены!"
}

# Создание файла .env если его нет
create_env_file() {
    if [ ! -f ".env" ]; then
        print_step "Создание файла .env..."
        cat > .env << 'EOF'
# Настройки Telegram API
# Получите эти данные на https://my.telegram.org
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
PHONE_NUMBER=+7XXXXXXXXXX
EOF
        print_success "Файл .env создан!"
        print_warning "❗ ВАЖНО: Отредактируйте файл .env со своими API данными!"
    else
        print_success "Файл .env уже существует"
    fi
}

# Создание скрипта запуска
create_run_script() {
    print_step "Создание скрипта запуска..."
    
    if [[ "$OS" == "windows" ]]; then
        cat > run.bat << 'EOF'
@echo off
echo 🚀 Запуск Telegram Chat Parser...
call telegram_env\Scripts\activate
python main_advanced.py
pause
EOF
        print_success "Создан run.bat для запуска на Windows"
    else
        cat > run.sh << 'EOF'
#!/bin/bash
echo "🚀 Запуск Telegram Chat Parser..."
source telegram_env/bin/activate
python main_advanced.py
EOF
        chmod +x run.sh
        print_success "Создан run.sh для запуска на Unix системах"
    fi
}

# Финальные инструкции
print_final_instructions() {
    echo ""
    echo -e "${GREEN}🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!${NC}"
    echo ""
    echo -e "${BLUE}📋 Следующие шаги:${NC}"
    echo ""
    echo "1. 🔑 Настройте API ключи:"
    echo "   - Откройте файл .env"
    echo "   - Замените your_api_id_here на ваш API ID"
    echo "   - Замените your_api_hash_here на ваш API Hash"
    echo "   - Замените +7XXXXXXXXXX на ваш номер телефона"
    echo ""
    echo "2. 🚀 Запустите программу:"
    if [[ "$OS" == "windows" ]]; then
        echo "   run.bat"
    else
        echo "   ./run.sh"
        echo "   или:"
        echo "   source telegram_env/bin/activate && python main_advanced.py"
    fi
    echo ""
    echo -e "${YELLOW}📚 Получить API ключи:${NC}"
    echo "   https://my.telegram.org → API Development tools"
    echo ""
    echo -e "${GREEN}✨ Готово к использованию!${NC}"
}

# Основная функция
main() {
    echo -e "${BLUE}"
    echo "🚀 Telegram Chat Parser - Setup Script"
    echo "====================================="
    echo -e "${NC}"
    
    detect_os
    check_python
    create_venv
    install_dependencies
    create_env_file
    create_run_script
    print_final_instructions
}

# Запуск основной функции
main "$@"