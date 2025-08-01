#!/bin/bash
# Telegram Parser - Monitoring Suite Startup Script
# This script starts both the web interface and status monitor

echo "🚀 Starting Telegram Parser Monitoring Suite..."
echo "================================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down monitoring suite..."
    kill $WEB_PID 2>/dev/null
    kill $MONITOR_PID 2>/dev/null
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup INT TERM

# Start web interface in background
echo "🌐 Starting web interface on http://localhost:5001..."
python3 web_interface.py &
WEB_PID=$!

# Wait a bit for web interface to start
sleep 2

# Check if web interface started successfully
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "❌ Failed to start web interface!"
    exit 1
fi

echo "✅ Web interface started (PID: $WEB_PID)"
echo ""

# Start status monitor
echo "📊 Starting status monitor..."
echo "💡 Press Ctrl+C to stop monitoring and web interface"
echo ""

python3 status_monitor.py --interval 2.0

# If monitor exits, cleanup
cleanup