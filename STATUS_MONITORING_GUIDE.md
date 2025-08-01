# 📊 Status Monitoring & Progress Tracking Guide

This guide explains how to use the enhanced status monitoring and progress tracking features in Telegram Parser.

## 🆕 New Features

### ✅ Real-time Progress Tracking
- **Detailed progress info**: Chat progress, estimated time remaining, API request statistics
- **Enhanced status updates**: Current operation, chat being processed, completion percentage
- **Time estimation**: Smart calculation of remaining time based on processing speed

### ✅ Graceful Interruption Handling
- **Safe interruption**: Ctrl+C handling with proper cleanup
- **Session preservation**: Database sessions are properly closed even if interrupted
- **Progress saving**: All processed data is saved before interruption

### ✅ Real-time Status API
- **Web API endpoints**: `/api/status` and `/api/status/interrupt`
- **Status monitoring**: Real-time status checking via web interface
- **Remote interruption**: Gracefully interrupt operations remotely

## 🚀 How to Use

### 1. **Basic Progress Tracking** (Built-in)

When you run any parsing operation, you'll now see enhanced progress information:

```bash
python main_advanced.py
# Choose option 3 (Parse all chats)
```

**New Progress Display:**
```
📊 Прогресс: 5/20 - Обрабатываем 'Chat Name'
⏱️ Примерно осталось: 12.5 минут
📡 Всего запросов: 342
⚡ Процент FloodWait: 2.1%
```

### 2. **Real-time Status Monitor** (Separate Terminal)

Run the status monitor in a separate terminal for real-time tracking:

```bash
python status_monitor.py
```

**Features:**
- 🔄 Real-time updates every 2 seconds
- 📊 Visual progress bar
- ⏰ Time estimation
- 🛑 Graceful interruption with Ctrl+C

**Example Output:**
```
🔍 TELEGRAM PARSER - МОНИТОРИНГ СТАТУСА
============================================================
⏰ Время: 2024-01-15 14:30:45
🔄 Операция: parsing_all_chats
📱 Активность: 🟢 Активен
💬 Текущий чат: My Important Group
🏷️  Тип чата: Channel

📊 ПРОГРЕСС:
├─ Чаты: 8/25 (32.0%)
├─ [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░]
├─ Осталось: ~8.4м

📈 СТАТИСТИКА СЕССИИ:
├─ Всего запросов: 156
├─ FloodWait ошибок: 3
├─ Других ошибок: 0
├─ Длительность: 4.2м
├─ Запросов/мин: 37.1
└─ Процент FloodWait: 1.9%

💡 Нажмите Ctrl+C для изящного прерывания операции
```

### 3. **Web Interface Status** (Browser)

1. Start the web interface:
```bash
python web_interface.py
```

2. Open browser: `http://localhost:5000`

3. **New API Endpoints:**
   - **GET** `/api/status` - Get current parsing status
   - **POST** `/api/status/interrupt` - Request graceful interruption

### 4. **Interruption Handling**

#### ✅ **Safe Interruption Methods:**

1. **Terminal Ctrl+C** - Graceful interruption in main script
2. **Status Monitor Ctrl+C** - Remote graceful interruption
3. **Web API** - Programmatic interruption request

#### ✅ **What Happens on Interruption:**
- ✅ Current chat processing completes
- ✅ Database session is properly closed
- ✅ All processed data is saved
- ✅ Statistics are preserved
- ✅ Connection cleanup is performed

## 📊 API Reference

### Status Endpoint
```bash
curl http://localhost:5000/api/status
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "is_active": true,
    "current_operation": "parsing_all_chats",
    "current_chat": {
      "id": 12345,
      "name": "My Chat",
      "type": "Channel"
    },
    "progress": {
      "total_chats": 25,
      "processed_chats": 8,
      "estimated_time_remaining": 504.2
    },
    "session_statistics": {
      "total_requests": 156,
      "flood_waits": 3,
      "errors": 0,
      "duration_seconds": 252.1,
      "requests_per_minute": 37.1
    },
    "last_update": "2024-01-15T14:30:45.123456",
    "interruption_requested": false
  }
}
```

### Interrupt Endpoint
```bash
curl -X POST http://localhost:5000/api/status/interrupt
```

**Response:**
```json
{
  "status": "success",
  "message": "Запрошено изящное прерывание операции"
}
```

## 🔧 Configuration Options

### Status Monitor Options
```bash
python status_monitor.py --help
```

**Arguments:**
- `--url` - API base URL (default: http://localhost:5000)
- `--interval` - Refresh interval in seconds (default: 2.0)

**Examples:**
```bash
# Monitor with custom refresh rate
python status_monitor.py --interval 1.0

# Monitor remote parser
python status_monitor.py --url http://192.168.1.100:5000
```

## 🛡️ Error Handling

### ✅ **Robust Error Handling:**
- Network connection errors
- API timeout handling
- Graceful degradation if web interface is not running
- Database connection failure recovery

### ✅ **Interruption Safety:**
- No data loss on interruption
- Proper cleanup of resources
- Session state preservation
- Resume capability (existing cache is preserved)

## 💡 Best Practices

1. **Monitor Large Operations:**
   ```bash
   # Terminal 1: Run parser
   python main_advanced.py

   # Terminal 2: Monitor progress
   python status_monitor.py
   ```

2. **Safe Interruption:**
   - Always use Ctrl+C instead of killing the process
   - Wait for "Прерывание запрошено" message
   - Allow current chat to complete processing

3. **Resume Operations:**
   - Interrupted operations can be resumed
   - Cached data is preserved
   - Only new/changed messages are processed

## 🔍 Troubleshooting

### Status Monitor Not Working?
```bash
# Check if web interface is running
curl http://localhost:5000/api/status

# If not, start web interface
python web_interface.py
```

### No Progress Shown?
- Ensure you're using `main_advanced.py` (has status integration)
- Check that parsing operation is actually running
- Verify web interface is accessible

### Interruption Not Working?
- Make sure to use Ctrl+C, not Ctrl+Z
- Wait for current chat to complete
- Check that parser is registered for monitoring

## 🎯 Summary

The enhanced status monitoring provides:
- ✅ **Real-time progress tracking**
- ✅ **Graceful interruption handling**
- ✅ **Time estimation and statistics**
- ✅ **Remote monitoring capabilities**
- ✅ **Safe operation resumption**

This makes the Telegram Parser production-ready for large-scale operations with proper monitoring and control capabilities!