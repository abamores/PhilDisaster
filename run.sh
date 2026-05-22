#!/bin/bash
# Philippine Disaster Monitor - Launcher

cd "$(dirname "$0")"

PYTHON=/Users/a2519/.pyenv/shims/python3

echo "=========================================="
echo "  🌏 Philippine Disaster Monitor"
echo "=========================================="

# Parse arguments
case "${1:-all}" in
    all)
        echo "Starting all components..."
        $PYTHON launcher.py
        ;;
    dashboard)
        echo "Starting Dashboard only..."
        $PYTHON -m streamlit run dashboard.py --server.port 8501
        ;;
    bot)
        echo "Starting Telegram Bot Handler..."
        export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM}"
        $PYTHON bot_handler.py $TELEGRAM_BOT_TOKEN
        ;;
    monitor|monitoring)
        echo "Starting Disaster Monitor..."
        $PYTHON monitor.py --once
        ;;
    continuous|scheduler)
        echo "Starting Continuous Monitor..."
        $PYTHON monitor.py --interval ${2:-15}
        ;;
    help|--help|-h)
        echo "Usage: ./run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  all           Start all components (default)"
        echo "  dashboard     Dashboard only"
        echo "  bot          Telegram bot handler only"
        echo "  monitor      Single monitoring check"
        echo "  continuous   Continuous monitoring (default 15 min)"
        echo "  help         Show this help"
        echo ""
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run ./run.sh help for usage"
        ;;
esac