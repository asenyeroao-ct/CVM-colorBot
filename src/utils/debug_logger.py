"""
調試日誌記錄器
用於記錄滑鼠移動和點擊事件，供 Debug tab 顯示
"""
import time
from collections import deque
from threading import Lock

# 全局日誌緩衝區（使用 deque 限制大小）
_log_buffer = deque(maxlen=1000)  # 最多保存 1000 條記錄
_log_lock = Lock()

# 日誌類型
LOG_TYPE_MOVE = "MOVE"
LOG_TYPE_CLICK = "CLICK"
LOG_TYPE_PRESS = "PRESS"
LOG_TYPE_RELEASE = "RELEASE"


def log_move(dx: float, dy: float, source: str = "Aimbot"):
    """
    記錄滑鼠移動事件
    
    Args:
        dx: X 方向移動量
        dy: Y 方向移動量
        source: 移動來源（例如 "Aimbot", "Sec Aimbot"）
    """
    with _log_lock:
        timestamp = time.time()
        _log_buffer.append({
            "type": LOG_TYPE_MOVE,
            "timestamp": timestamp,
            "dx": dx,
            "dy": dy,
            "source": source,
            "message": f"[{source}] Move: dx={dx:.2f}, dy={dy:.2f}"
        })


def log_click(source: str = "Triggerbot"):
    """
    記錄滑鼠點擊事件（按下並釋放）
    
    Args:
        source: 點擊來源（例如 "Triggerbot", "Manual"）
    """
    with _log_lock:
        timestamp = time.time()
        _log_buffer.append({
            "type": LOG_TYPE_CLICK,
            "timestamp": timestamp,
            "source": source,
            "message": f"[{source}] Click (press + release)"
        })


def log_press(source: str = "Triggerbot"):
    """
    記錄滑鼠按下事件
    
    Args:
        source: 按下來源
    """
    with _log_lock:
        timestamp = time.time()
        _log_buffer.append({
            "type": LOG_TYPE_PRESS,
            "timestamp": timestamp,
            "source": source,
            "message": f"[{source}] Press"
        })


def log_release(source: str = "Triggerbot"):
    """
    記錄滑鼠釋放事件
    
    Args:
        source: 釋放來源
    """
    with _log_lock:
        timestamp = time.time()
        _log_buffer.append({
            "type": LOG_TYPE_RELEASE,
            "timestamp": timestamp,
            "source": source,
            "message": f"[{source}] Release"
        })


def get_recent_logs(count: int = 100) -> list:
    """
    獲取最近的日誌記錄
    
    Args:
        count: 要獲取的記錄數量
        
    Returns:
        list: 日誌記錄列表（最新的在前）
    """
    with _log_lock:
        return list(_log_buffer)[-count:]


def clear_logs():
    """清空所有日誌"""
    with _log_lock:
        _log_buffer.clear()


def get_log_count() -> int:
    """獲取當前日誌數量"""
    with _log_lock:
        return len(_log_buffer)

