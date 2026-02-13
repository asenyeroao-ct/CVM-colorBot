"""
Unified debug logger used by app modules and Debug tab.
"""

import builtins
import datetime as _dt
import re
import time
import traceback
from collections import deque
from threading import Lock
from typing import Optional


LOG_TYPE_DEBUG = "DEBUG"
LOG_TYPE_INFO = "INFO"
LOG_TYPE_WARN = "WARN"
LOG_TYPE_ERROR = "ERROR"
LOG_TYPE_MOVE = "MOVE"
LOG_TYPE_CLICK = "CLICK"
LOG_TYPE_PRESS = "PRESS"
LOG_TYPE_RELEASE = "RELEASE"

_LEVEL_ORDER = {
    LOG_TYPE_DEBUG: 10,
    LOG_TYPE_INFO: 20,
    LOG_TYPE_WARN: 30,
    LOG_TYPE_ERROR: 40,
}

_log_buffer = deque(maxlen=5000)
_log_lock = Lock()

_console_enabled = True
_console_level = LOG_TYPE_INFO
_log_file_path = None

_PREFIX_LEVEL_RE = re.compile(r"^\[(DEBUG|INFO|WARN|WARNING|ERROR)\]\s*(.*)$", re.IGNORECASE)
_PREFIX_SOURCE_RE = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


def _normalize_level(level: str) -> str:
    level = str(level or LOG_TYPE_INFO).strip().upper()
    if level == "WARNING":
        return LOG_TYPE_WARN
    if level in _LEVEL_ORDER:
        return level
    return LOG_TYPE_INFO


def _should_echo(level: str) -> bool:
    if not _console_enabled:
        return False
    return _LEVEL_ORDER.get(level, 20) >= _LEVEL_ORDER.get(_console_level, 20)


def _append_entry(entry: dict):
    with _log_lock:
        _log_buffer.append(entry)


def _format_console_line(entry: dict) -> str:
    ts = _dt.datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
    return f"[{ts}] [{entry.get('level', LOG_TYPE_INFO)}] [{entry.get('source', 'App')}] {entry.get('message', '')}"


def _write_outputs(entry: dict):
    line = _format_console_line(entry)
    if _should_echo(entry.get("level", LOG_TYPE_INFO)):
        builtins.print(line)

    if _log_file_path:
        try:
            with open(_log_file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Logging should never raise to callers.
            pass


def _emit(level: str, message: str, source: str = "App", log_type: Optional[str] = None, **fields):
    entry = {
        "type": log_type or _normalize_level(level),
        "level": _normalize_level(level),
        "timestamp": time.time(),
        "source": source,
        "message": str(message),
    }
    if fields:
        entry.update(fields)

    _append_entry(entry)
    _write_outputs(entry)


def set_console_enabled(enabled: bool):
    global _console_enabled
    _console_enabled = bool(enabled)


def set_console_level(level: str):
    global _console_level
    _console_level = _normalize_level(level)


def set_log_file(path: Optional[str]):
    global _log_file_path
    _log_file_path = path if path else None


def debug(message: str, source: str = "App", **fields):
    _emit(LOG_TYPE_DEBUG, message, source=source, **fields)


def info(message: str, source: str = "App", **fields):
    _emit(LOG_TYPE_INFO, message, source=source, **fields)


def warn(message: str, source: str = "App", **fields):
    _emit(LOG_TYPE_WARN, message, source=source, **fields)


def error(message: str, source: str = "App", **fields):
    _emit(LOG_TYPE_ERROR, message, source=source, **fields)


def exception(message: str, exc: Optional[Exception] = None, source: str = "App", **fields):
    if exc is None:
        trace = traceback.format_exc()
    else:
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _emit(LOG_TYPE_ERROR, f"{message}\n{trace}", source=source, **fields)


def _infer_source_and_level(message: str):
    source = "App"
    level = None
    text = str(message)

    m = _PREFIX_LEVEL_RE.match(text)
    if m:
        level = _normalize_level(m.group(1))
        text = m.group(2)
        return source, level, text

    m = _PREFIX_SOURCE_RE.match(text)
    if m:
        tag = m.group(1).strip()
        text = m.group(2)
        tag_lower = tag.lower()

        if tag_lower in ("debug", "info", "warn", "warning", "error"):
            level = _normalize_level(tag)
        elif tag_lower.endswith(" error"):
            source = tag[:-6].strip() or "App"
            level = LOG_TYPE_ERROR
        elif tag_lower.endswith(" warning"):
            source = tag[:-8].strip() or "App"
            level = LOG_TYPE_WARN
        else:
            source = tag or "App"

    if level is None:
        lowered = text.lower()
        if "error" in lowered or "failed" in lowered or "exception" in lowered:
            level = LOG_TYPE_ERROR
        elif "warn" in lowered:
            level = LOG_TYPE_WARN
        elif "debug" in lowered:
            level = LOG_TYPE_DEBUG
        else:
            level = LOG_TYPE_INFO

    return source, level, text


def log_print(*args, sep: str = " ", end: str = "\n", file=None, flush: bool = False):
    """
    Drop-in replacement for print() that routes messages to debug logger.
    """
    message = sep.join(str(arg) for arg in args)
    if end and end != "\n":
        message += end
    message = message.rstrip("\r\n")

    source, level, text = _infer_source_and_level(message)
    _emit(level, text, source=source)

    # Keep compatibility with explicit `file=` prints.
    if file is not None:
        builtins.print(*args, sep=sep, end=end, file=file, flush=flush)


def log_move(dx: float, dy: float, source: str = "Aimbot"):
    _append_entry(
        {
            "type": LOG_TYPE_MOVE,
            "level": LOG_TYPE_DEBUG,
            "timestamp": time.time(),
            "dx": dx,
            "dy": dy,
            "source": source,
            "message": f"[{source}] Move: dx={dx:.2f}, dy={dy:.2f}",
        }
    )


def log_click(source: str = "Triggerbot"):
    _emit(LOG_TYPE_INFO, "Click (press + release)", source=source, log_type=LOG_TYPE_CLICK)


def log_press(source: str = "Triggerbot"):
    _emit(LOG_TYPE_INFO, "Press", source=source, log_type=LOG_TYPE_PRESS)


def log_release(source: str = "Triggerbot"):
    _emit(LOG_TYPE_INFO, "Release", source=source, log_type=LOG_TYPE_RELEASE)


def get_recent_logs(count: int = 100) -> list:
    with _log_lock:
        return list(_log_buffer)[-count:]


def clear_logs():
    with _log_lock:
        _log_buffer.clear()


def get_log_count() -> int:
    with _log_lock:
        return len(_log_buffer)
