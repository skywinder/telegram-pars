# Telegram Parser - Monitoring Guide

## 🚀 Quick Start

Run monitoring with a single command:
```bash
./start_monitoring.sh
```

This starts:
- Web interface at http://localhost:5001
- Console status monitor with real-time updates

## 📊 Components

### 1. Web Interface (`web_interface.py`)
- **Port**: 5001
- **Features**:
  - Dashboard with statistics
  - Chat list and details
  - Analytics and search
  - Real-time status page
  - Export functionality

### 2. Status Monitor (`status_monitor.py`)
- Real-time console monitoring
- Shows current parsing progress
- Allows graceful interruption (Ctrl+C)

### 3. Status API Endpoints
- `GET /api/status` - Current parser status
- `POST /api/status/interrupt` - Request graceful interruption

## 🔍 What to Check

### Status Page (http://localhost:5001/status)
Check for:
- **Parser State**: Active/Inactive indicator
- **Current Operation**: What the parser is doing
- **Progress Bar**: Shows completion percentage
- **Current Chat**: Which chat is being processed
- **Session Statistics**:
  - Total requests made
  - FloodWait errors count
  - Other errors count
  - Duration and request rate

### Console Monitor
Shows:
- Real-time status updates every 2 seconds
- Current chat being processed
- Progress with visual progress bar
- Session statistics
- Estimated time remaining

## 🛠️ Usage Workflow

1. **Start Parser** (in terminal 1):
   ```bash
   python main.py
   ```

2. **Start Monitoring** (in terminal 2):
   ```bash
   ./start_monitoring.sh
   ```

3. **Check Status**:
   - Open http://localhost:5001/status in browser
   - Watch console monitor for real-time updates

4. **Graceful Interruption**:
   - Press Ctrl+C in monitor console
   - Or click "Прервать Операцию" on web status page
   - Parser will finish current chat before stopping

## 🔧 Manual Start

If you prefer to start components separately:

```bash
# Terminal 1: Web Interface
python web_interface.py

# Terminal 2: Status Monitor
python status_monitor.py --interval 2.0
```

## 📝 Key Files

- `web_interface.py`: Flask web server (port 5001)
- `status_monitor.py`: Console monitoring tool
- `templates/status.html`: Web status page
- `start_monitoring.sh`: Combined startup script

## ⚠️ Important Notes

1. **Port Consistency**: Both components use port 5001
2. **Database Required**: Web interface needs existing database from parser
3. **Active Parser**: Status only works when parser is running
4. **Graceful Shutdown**: Always use Ctrl+C for clean shutdown

## 🐛 Troubleshooting

**No Status Data**:
- Ensure parser is running with `python main.py`
- Check that parser registered with `set_active_parser()`

**Connection Error**:
- Verify web interface is running on port 5001
- Check no other process is using port 5001

**No Database**:
- Run parser at least once to create database
- Check `data/telegram_data.db` exists