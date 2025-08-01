"""
Status Manager - Shared status tracking without Flask dependency
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import threading

class StatusManager:
    """Manages parser status in a file-based approach for cross-process communication"""
    
    STATUS_FILE = "data/parser_status.json"
    _lock = threading.Lock()
    
    @classmethod
    def ensure_data_dir(cls):
        """Ensure data directory exists"""
        os.makedirs("data", exist_ok=True)
    
    @classmethod
    def set_active_parser(cls, parser):
        """Register active parser and save initial status"""
        cls.ensure_data_dir()
        with cls._lock:
            status = {
                "is_active": True,
                "parser_id": id(parser),
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "current_operation": "Initializing",
                "interruption_requested": False
            }
            cls._save_status(status)
            # Store parser reference for direct status updates
            parser._status_manager = cls
    
    @classmethod
    def clear_active_parser(cls):
        """Clear active parser status"""
        with cls._lock:
            if os.path.exists(cls.STATUS_FILE):
                try:
                    os.remove(cls.STATUS_FILE)
                except:
                    pass
    
    @classmethod
    def update_status(cls, updates: Dict[str, Any]):
        """Update parser status"""
        with cls._lock:
            status = cls._load_status()
            if status:
                status.update(updates)
                status["last_update"] = datetime.now().isoformat()
                cls._save_status(status)
    
    @classmethod
    def get_status(cls) -> Optional[Dict[str, Any]]:
        """Get current parser status"""
        with cls._lock:
            return cls._load_status()
    
    @classmethod
    def request_interruption(cls):
        """Request parser interruption"""
        cls.update_status({"interruption_requested": True})
    
    @classmethod
    def _save_status(cls, status: Dict[str, Any]):
        """Save status to file"""
        try:
            with open(cls.STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving status: {e}")
    
    @classmethod
    def _load_status(cls) -> Optional[Dict[str, Any]]:
        """Load status from file"""
        try:
            if os.path.exists(cls.STATUS_FILE):
                with open(cls.STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading status: {e}")
        return None

# Global functions for backward compatibility
def set_active_parser(parser):
    """Set active parser for monitoring"""
    StatusManager.set_active_parser(parser)

def clear_active_parser():
    """Clear active parser"""
    StatusManager.clear_active_parser()