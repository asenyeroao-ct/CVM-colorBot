"""
Shared strafe-helper logic for trigger modules.
"""
import ctypes
import time

from src.utils.config import config
from src.utils.mouse import is_key_pressed as backend_is_key_pressed
from src.utils.mouse import key_down, key_up
from src.utils.mouse import supports_trigger_strafe_ui
from src.utils.mouse.keycodes import to_vk_code


STRAFE_MODE_OFF = "off"
STRAFE_MODE_AUTO = "auto"
STRAFE_MODE_MANUAL_WAIT = "manual_wait"
_STRAFE_MODES = {STRAFE_MODE_OFF, STRAFE_MODE_AUTO, STRAFE_MODE_MANUAL_WAIT}

_MOVEMENT_KEYS = ("W", "A", "S", "D")

try:
    _USER32 = ctypes.windll.user32
except Exception:
    _USER32 = None


def normalize_strafe_mode(value) -> str:
    mode = str(value).strip().lower()
    if mode not in _STRAFE_MODES:
        return STRAFE_MODE_OFF
    return mode


def get_strafe_mode() -> str:
    if not supports_trigger_strafe_ui(getattr(config, "mouse_api", "Serial")):
        return STRAFE_MODE_OFF
    return normalize_strafe_mode(getattr(config, "trigger_strafe_mode", STRAFE_MODE_OFF))


def reset_strafe_runtime_state(state_dict):
    state_dict["strafe_manual_neutral_since"] = None


def _read_local_key_state(key: str) -> bool:
    if _USER32 is None:
        return False
    vk = to_vk_code(key)
    if vk is None:
        return False
    try:
        return bool(_USER32.GetAsyncKeyState(int(vk)) & 0x8000)
    except Exception:
        return False


def _is_pressed(key: str) -> bool:
    try:
        if bool(backend_is_key_pressed(key)):
            return True
    except Exception:
        pass
    return _read_local_key_state(key)


def _sample_movement_snapshot() -> dict:
    return {key: bool(_is_pressed(key)) for key in _MOVEMENT_KEYS}


def _is_axis_neutral(negative_key: str, positive_key: str, snapshot: dict) -> bool:
    return bool(snapshot.get(negative_key, False)) == bool(snapshot.get(positive_key, False))


def _is_movement_neutral(snapshot: dict) -> bool:
    horizontal_neutral = _is_axis_neutral("A", "D", snapshot)
    vertical_neutral = _is_axis_neutral("W", "S", snapshot)
    return horizontal_neutral and vertical_neutral


def apply_manual_wait_gate(state_dict):
    mode = get_strafe_mode()
    if mode != STRAFE_MODE_MANUAL_WAIT:
        state_dict["strafe_manual_neutral_since"] = None
        return True, None

    snapshot = _sample_movement_snapshot()
    if not _is_movement_neutral(snapshot):
        state_dict["strafe_manual_neutral_since"] = None
        return False, "STRAFE_WAIT_MOVEMENT"

    required_ms = max(0, int(getattr(config, "trigger_strafe_manual_neutral_ms", 0)))
    if required_ms <= 0:
        return True, None

    now = time.time()
    neutral_since = state_dict.get("strafe_manual_neutral_since")
    if neutral_since is None:
        state_dict["strafe_manual_neutral_since"] = now
        neutral_since = now

    elapsed_ms = int((now - float(neutral_since)) * 1000.0)
    if elapsed_ms >= required_ms:
        return True, None
    return False, f"STRAFE_WAIT_NEUTRAL ({elapsed_ms}/{required_ms}ms)"


def _resolve_auto_opposing_keys() -> list:
    snapshot = _sample_movement_snapshot()
    result = []

    a_pressed = bool(snapshot.get("A", False))
    d_pressed = bool(snapshot.get("D", False))
    if a_pressed and not d_pressed:
        result.append("D")
    elif d_pressed and not a_pressed:
        result.append("A")

    w_pressed = bool(snapshot.get("W", False))
    s_pressed = bool(snapshot.get("S", False))
    if w_pressed and not s_pressed:
        result.append("S")
    elif s_pressed and not w_pressed:
        result.append("W")

    return result


def _safe_key_down(key: str):
    try:
        key_down(key)
    except Exception:
        pass


def _safe_key_up(key: str):
    try:
        key_up(key)
    except Exception:
        pass


def run_with_auto_strafe(shot_func):
    mode = get_strafe_mode()
    if mode != STRAFE_MODE_AUTO:
        return shot_func()

    opposing_keys = _resolve_auto_opposing_keys()
    if not opposing_keys:
        return shot_func()

    for key in opposing_keys:
        _safe_key_down(key)

    lead_ms = max(0, int(getattr(config, "trigger_strafe_auto_lead_ms", 8)))
    try:
        if lead_ms > 0:
            time.sleep(float(lead_ms) / 1000.0)
        return shot_func()
    finally:
        for key in reversed(opposing_keys):
            _safe_key_up(key)
