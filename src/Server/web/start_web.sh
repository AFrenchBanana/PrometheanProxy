#!/bin/bash

# PrometheanProxy Web Interface Startup Script
# This script helps you start the Django web interface with all required services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEB_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/venv"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

check_redis() {
    if redis-cli ping &> /dev/null; then
        print_success "Redis is running"
        return 0
    else
        print_warning "Redis is not running"
        return 1
    fi
}

start_redis() {
    print_info "Starting Redis..."
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
        sleep 2
        if check_redis; then
            print_success "Redis started successfully"
        else
            print_error "Failed to start Redis"
            return 1
        fi
    else
        print_error "Redis is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt-get install redis-server"
        echo "  macOS: brew install redis"
        return 1
    fi
}

check_venv() {
    if [ -d "$VENV_DIR" ]; then
        print_success "Virtual environment found"
        return 0
    else
        print_error "Virtual environment not found at $VENV_DIR"
        return 1
    fi
}

activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
    else
        print_error "Could not activate virtual environment"
        return 1
    fi
}

check_env_file() {
    if [ -f "$WEB_DIR/.env" ]; then
        print_success ".env file exists"
        return 0
    else
        print_warning ".env file not found"
        if [ -f "$WEB_DIR/.env.example" ]; then
            print_info "Creating .env from .env.example..."
            cp "$WEB_DIR/.env.example" "$WEB_DIR/.env"
            print_success ".env file created"
            print_warning "Please review and update $WEB_DIR/.env with your settings"
        else
            print_error ".env.example not found"
            return 1
        fi
    fi
}

check_migrations() {
    cd "$WEB_DIR"
    python manage.py showmigrations --plan | grep -q '\[ \]'
    if [ $? -eq 0 ]; then
        print_warning "Unapplied migrations detected"
        return 1
    else
        print_success "All migrations applied"
        return 0
    fi
}

run_migrations() {
    print_info "Running database migrations..."
    cd "$WEB_DIR"
    python manage.py migrate --noinput
    if [ $? -eq 0 ]; then
        print_success "Migrations completed successfully"
    else
        print_error "Migrations failed"
        return 1
    fi
}

collect_static() {
    print_info "Collecting static files..."
    cd "$WEB_DIR"
    python manage.py collectstatic --noinput --clear
    if [ $? -eq 0 ]; then
        print_success "Static files collected"
    else
        print_warning "Static file collection failed (non-critical)"
    fi
}

check_backend() {
    print_info "Checking PrometheanProxy backend connection..."
    cd "$WEB_DIR"
    python -c "
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promethean_web.settings')
import django
django.setup()
from api.services import get_api_client
try:
    client = get_api_client()
    result = client.ping()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f'Backend check failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_success "Backend is reachable"
        return 0
    else
        print_warning "Backend is not reachable (you can still start the web interface)"
        print_info "Make sure the PrometheanProxy server is running with multiplayer enabled"
        return 1
    fi
}

start_development_server() {
    print_header "Starting Development Server"
    cd "$WEB_DIR"

    print_info "Starting Django development server with Daphne (WebSocket support)..."
    print_info "Access the interface at: http://localhost:8000"
    print_info "Press Ctrl+C to stop the server"
    echo ""

    daphne -b 0.0.0.0 -p 8000 promethean_web.asgi:application
}

start_production_server() {
    print_header "Starting Production Server"
    cd "$WEB_DIR"

    print_info "Starting Gunicorn (HTTP) on port 8000..."
    gunicorn promethean_web.wsgi:application --bind 0.0.0.0:8000 --workers 4 --daemon --pid gunicorn.pid

    print_info "Starting Daphne (WebSocket) on port 8001..."
    daphne -b 0.0.0.0 -p 8001 promethean_web.asgi:application --pid daphne.pid &

    print_success "Production servers started"
    print_info "HTTP: http://localhost:8000"
    print_info "WebSocket: ws://localhost:8001"
    print_info "To stop: kill \$(cat gunicorn.pid) && kill \$(cat daphne.pid)"
}

show_help() {
    echo "PrometheanProxy Web Interface Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -c, --check         Check dependencies and configuration"
    echo "  -m, --migrate       Run database migrations"
    echo "  -s, --static        Collect static files"
    echo "  -p, --production    Start in production mode (Gunicorn + Daphne)"
    echo "  -d, --dev           Start in development mode (default)"
    echo "  --no-redis-check    Skip Redis check and startup"
    echo ""
    echo "Examples:"
    echo "  $0                  Start development server (with checks)"
    echo "  $0 --check          Only check dependencies"
    echo "  $0 --migrate        Run migrations only"
    echo "  $0 --production     Start production server"
}

# Main script
main() {
    print_header "PrometheanProxy Web Interface"

    MODE="dev"
    CHECK_ONLY=false
    MIGRATE_ONLY=false
    STATIC_ONLY=false
    SKIP_REDIS_CHECK=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--check)
                CHECK_ONLY=true
                shift
                ;;
            -m|--migrate)
                MIGRATE_ONLY=true
                shift
                ;;
            -s|--static)
                STATIC_ONLY=true
                shift
                ;;
            -p|--production)
                MODE="production"
                shift
                ;;
            -d|--dev)
                MODE="dev"
                shift
                ;;
            --no-redis-check)
                SKIP_REDIS_CHECK=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Check dependencies
    print_header "Checking Dependencies"

    check_command python3 || exit 1
    check_command redis-server || print_warning "Redis not found (required for WebSockets)"
    check_command redis-cli || print_warning "redis-cli not found"

    # Check and start Redis
    if [ "$SKIP_REDIS_CHECK" = false ]; then
        if ! check_redis; then
            read -p "Start Redis now? [Y/n] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                start_redis || print_warning "Continuing without Redis (WebSockets will not work)"
            fi
        fi
    fi

    # Check virtual environment
    check_venv || exit 1
    activate_venv || exit 1

    # Check Django installation
    python -c "import django" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_error "Django is not installed in the virtual environment"
        print_info "Run: pip install -r ../web_requirements.txt"
        exit 1
    fi

    # Check environment file
    check_env_file || exit 1

    if [ "$CHECK_ONLY" = true ]; then
        print_header "Configuration Check"
        check_migrations
        check_backend
        print_success "Dependency check complete"
        exit 0
    fi

    # Run migrations if needed
    if [ "$MIGRATE_ONLY" = true ]; then
        run_migrations
        exit 0
    fi

    # Collect static files if needed
    if [ "$STATIC_ONLY" = true ]; then
        collect_static
        exit 0
    fi

    # Check and run migrations
    if ! check_migrations; then
        read -p "Run migrations now? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            run_migrations || exit 1
        else
            print_warning "Continuing without running migrations"
        fi
    fi

    # Check backend connectivity
    check_backend

    echo ""

    # Start server
    if [ "$MODE" = "production" ]; then
        start_production_server
    else
        start_development_server
    fi
}

# Run main function
main "$@"
