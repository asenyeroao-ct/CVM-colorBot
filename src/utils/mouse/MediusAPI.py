"""
Medius box mouse/keyboard backend.

Uses the official Python bindings: https://medius.k4tech.net/bindings/python
The box sits inline between a mouse and the game PC; this process talks to
the control port and injects relative motion / buttons / keys.
"""
from src.utils.debug_logger import log_print
import threading
import time

from . import state
from .keycodes import to_hid_code

_medius_device = None
_medius_lock = threading.Lock()
_listener_stop = threading.Event()
_held_keys = set()
_held_keys_lock = threading.Lock()

_BUTTON_IDX_TO_SLOT = {
    0: 0,  # LEFT
    1: 1,  # RIGHT
    2: 2,  # MIDDLE
    3: 3,  # SIDE1
    4: 4,  # SIDE2
}


def _import_medius():
    try:
        import medius
        from medius import (
            Button,
            CatchFilter,
            Device,
            Direction,
            LockTarget,
            NotFoundError,
            Usage,
        )
        return {
            "medius": medius,
            "Button": Button,
            "CatchFilter": CatchFilter,
            "Device": Device,
            "Direction": Direction,
            "LockTarget": LockTarget,
            "NotFoundError": NotFoundError,
            "Usage": Usage,
        }
    except ImportError as e:
        raise ImportError(
            "medius package is not installed. Run: pip install medius"
        ) from e


def _normalize_serial_port_name(port_value: str) -> str:
    raw = str(port_value or "").strip()
    if not raw:
        return ""
    if raw.upper().startswith("COM"):
        return raw.upper()
    if raw.isdigit():
        return f"COM{raw}"
    return raw


def list_ports():
    """Return [{path, vid, pid, serial}, ...] for connected Medius boxes."""
    try:
        mods = _import_medius()
        ports = []
        for info in mods["medius"].find_ports():
            ports.append(
                {
                    "path": str(getattr(info, "path", "") or ""),
                    "vid": int(getattr(info, "vid", 0) or 0),
                    "pid": int(getattr(info, "pid", 0) or 0),
                    "serial": str(getattr(info, "serial", "") or ""),
                }
            )
        return ports
    except Exception as e:
        log_print(f"[Medius] list_ports failed: {e}")
        return []


def _button_usage(mods, idx: int):
    button = mods["Button"]
    usage = mods["Usage"]
    slot = _BUTTON_IDX_TO_SLOT.get(int(idx))
    if slot is None:
        return None
    mapping = {
        0: button.LEFT,
        1: button.RIGHT,
        2: button.MIDDLE,
        3: button.SIDE1,
        4: button.SIDE2,
    }
    member = mapping.get(slot)
    if member is None:
        return None
    return usage.button(member)


def _usage_matches_button(mods, usage, idx: int) -> bool:
    target = _button_usage(mods, idx)
    if usage is None or target is None:
        return False
    if usage == target:
        return True
    try:
        return int(usage) == int(target)
    except Exception:
        return False


def _apply_usage_snapshot(mods, snapshot):
    if snapshot is None:
        return
    cls_name = str(getattr(snapshot, "cls", "")).upper()
    is_buttons = "BUTTON" in cls_name or cls_name.endswith("BUTTONS")
    is_keys = "KEY" in cls_name or "KEYBOARD" in cls_name
    if not is_buttons and not is_keys:
        # Some builds leave cls empty; try both.
        is_buttons = True
        is_keys = True

    if is_buttons:
        with state.button_states_lock:
            for idx in range(5):
                target = _button_usage(mods, idx)
                held = False
                if target is not None:
                    try:
                        held = bool(snapshot.is_held(target))
                    except Exception:
                        held = False
                state.button_states[idx] = held

    if is_keys:
        held = set()
        usages = getattr(snapshot, "usages", None) or []
        for item in usages:
            try:
                held.add(int(item))
            except Exception:
                continue
        with _held_keys_lock:
            _held_keys.clear()
            _held_keys.update(held)


def _apply_input_event(mods, event):
    usage = getattr(event, "usage", None)
    is_press = bool(getattr(event, "is_press", False))
    is_release = bool(getattr(event, "is_release", False))
    if usage is None or not (is_press or is_release):
        return

    matched_button = False
    with state.button_states_lock:
        for idx in range(5):
            if _usage_matches_button(mods, usage, idx):
                state.button_states[idx] = is_press
                matched_button = True
                break
    if matched_button:
        return

    try:
        hid = int(usage)
    except Exception:
        return
    with _held_keys_lock:
        if is_press:
            _held_keys.add(hid)
        else:
            _held_keys.discard(hid)


def _listener_loop(device, mods):
    stream = None
    try:
        catch_filter = mods["CatchFilter"]
        if hasattr(device, "input_events"):
            stream = device.input_events(catch_filter.all_input())
        else:
            stream = device.catch_events(catch_filter.all_input())
    except Exception as e:
        log_print(f"[Medius] Failed to subscribe input events: {e}")
        return

    log_print("[Medius] Input listener started.")
    try:
        while not _listener_stop.is_set() and state.is_connected and state.active_backend == "Medius":
            try:
                event = stream.recv_timeout(80) if hasattr(stream, "recv_timeout") else stream.try_recv()
            except Exception:
                if _listener_stop.is_set():
                    break
                time.sleep(0.02)
                continue
            if event is None:
                continue
            try:
                if getattr(event, "usages", None) is not None:
                    _apply_usage_snapshot(mods, event.usages)
                elif hasattr(event, "is_press") or hasattr(event, "usage"):
                    _apply_input_event(mods, event)
            except Exception:
                continue
    finally:
        try:
            if stream is not None:
                stream.close()
        except Exception:
            pass
        log_print("[Medius] Input listener stopped.")


def _start_listener(device, mods):
    global state
    _listener_stop.clear()
    thread = threading.Thread(target=_listener_loop, args=(device, mods), daemon=True, name="MediusListener")
    state.listener_thread = thread
    thread.start()


def connect(port=None) -> bool:
    global _medius_device
    state.last_connect_error = ""
    disconnect()

    try:
        mods = _import_medius()
    except ImportError as e:
        state.last_connect_error = str(e)
        state.set_connected(False, "Medius")
        log_print(f"[Medius] {e}")
        return False

    selected_port = _normalize_serial_port_name(port)
    Device = mods["Device"]
    NotFoundError = mods["NotFoundError"]

    try:
        if selected_port:
            device = Device.open(selected_port)
        else:
            finder = getattr(Device, "find_mouse_box", None)
            if callable(finder):
                try:
                    device = finder()
                except NotFoundError:
                    device = Device.find()
            else:
                device = Device.find()
    except NotFoundError:
        state.last_connect_error = "No Medius box found. Check the control-port cable."
        state.set_connected(False, "Medius")
        log_print(f"[Medius] {state.last_connect_error}")
        return False
    except Exception as e:
        state.last_connect_error = str(e)
        state.set_connected(False, "Medius")
        log_print(f"[Medius] Connect failed: {e}")
        return False

    with _medius_lock:
        _medius_device = device

    state.reset_button_states()
    with _held_keys_lock:
        _held_keys.clear()
    state.set_connected(True, "Medius")
    _start_listener(device, mods)

    try:
        version = device.query_version()
        log_print(
            "[Medius] Connected: firmware "
            f"{version.fw_major}.{version.fw_minor}.{version.fw_patch}, proto {version.proto_ver}"
        )
    except Exception:
        log_print("[Medius] Connected.")
    return True


def disconnect():
    global _medius_device
    _listener_stop.set()
    device = None
    with _medius_lock:
        device = _medius_device
        _medius_device = None
    if device is not None:
        try:
            device.close()
        except Exception:
            pass
    if state.active_backend == "Medius":
        state.set_connected(False, "Medius")
    state.reset_button_states()
    with _held_keys_lock:
        _held_keys.clear()
    state.mask_applied_idx = None


def _require_device():
    if not state.is_connected or state.active_backend != "Medius":
        return None
    with _medius_lock:
        return _medius_device


def is_button_pressed(idx: int) -> bool:
    try:
        idx = int(idx)
    except Exception:
        return False
    with state.button_states_lock:
        return bool(state.button_states.get(idx, False))


def is_key_pressed(key) -> bool:
    hid = to_hid_code(key)
    if hid is None:
        return False
    with _held_keys_lock:
        return int(hid) in _held_keys


def move(x: float, y: float):
    device = _require_device()
    if device is None:
        return
    try:
        dx = max(-32768, min(32767, int(round(float(x)))))
        dy = max(-32768, min(32767, int(round(float(y)))))
        if dx == 0 and dy == 0:
            return
        device.move_rel(dx, dy)
    except Exception as e:
        log_print(f"[Medius] move failed: {e}")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    del ctrl_x, ctrl_y
    steps = max(1, int(segments or 1))
    if steps <= 1:
        move(x, y)
        return
    total_x = float(x)
    total_y = float(y)
    sent_x = 0.0
    sent_y = 0.0
    for i in range(1, steps + 1):
        target_x = total_x * i / steps
        target_y = total_y * i / steps
        move(target_x - sent_x, target_y - sent_y)
        sent_x = target_x
        sent_y = target_y


def left(isdown: int):
    device = _require_device()
    if device is None:
        return
    try:
        mods = _import_medius()
        usage = mods["Usage"].button(mods["Button"].LEFT)
        if int(isdown):
            device.press(usage)
        else:
            device.soft_release(usage)
    except Exception as e:
        log_print(f"[Medius] left failed: {e}")


def key_down(key):
    device = _require_device()
    hid = to_hid_code(key)
    if device is None or hid is None:
        return
    try:
        mods = _import_medius()
        device.press(mods["Usage"].key(int(hid)))
        with _held_keys_lock:
            _held_keys.add(int(hid))
    except Exception as e:
        log_print(f"[Medius] key_down failed: {e}")


def key_up(key):
    device = _require_device()
    hid = to_hid_code(key)
    if device is None or hid is None:
        return
    try:
        mods = _import_medius()
        device.soft_release(mods["Usage"].key(int(hid)))
        with _held_keys_lock:
            _held_keys.discard(int(hid))
    except Exception as e:
        log_print(f"[Medius] key_up failed: {e}")


def key_press(key):
    key_down(key)
    time.sleep(0.012)
    key_up(key)


def lock_button_idx(idx: int):
    device = _require_device()
    if device is None:
        return
    try:
        mods = _import_medius()
        usage = _button_usage(mods, idx)
        if usage is None:
            return
        device.lock(mods["LockTarget"].usage(usage), mods["Direction"].BOTH)
    except Exception as e:
        log_print(f"[Medius] lock_button failed: {e}")


def unlock_button_idx(idx: int):
    device = _require_device()
    if device is None:
        return
    try:
        mods = _import_medius()
        usage = _button_usage(mods, idx)
        if usage is None:
            return
        device.unlock(mods["LockTarget"].usage(usage), mods["Direction"].BOTH)
    except Exception as e:
        log_print(f"[Medius] unlock_button failed: {e}")


def unlock_all_locks():
    device = _require_device()
    if device is None:
        return
    try:
        device.reset()
    except Exception as e:
        log_print(f"[Medius] unlock_all failed: {e}")


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    del skip_lock
    device = _require_device()
    if device is None:
        return
    try:
        mods = _import_medius()
        target = mods["LockTarget"].x()
        if lock:
            device.lock(target, mods["Direction"].BOTH)
        else:
            device.unlock(target, mods["Direction"].BOTH)
    except Exception as e:
        log_print(f"[Medius] lock_movement_x failed: {e}")


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    del skip_lock
    device = _require_device()
    if device is None:
        return
    try:
        mods = _import_medius()
        target = mods["LockTarget"].y()
        if lock:
            device.lock(target, mods["Direction"].BOTH)
        else:
            device.unlock(target, mods["Direction"].BOTH)
    except Exception as e:
        log_print(f"[Medius] lock_movement_y failed: {e}")


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    del is_main
    lock_movement_x(bool(lock_x))
    lock_movement_y(bool(lock_y))


def tick_movement_lock_manager():
    return


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    if not state.is_connected or state.active_backend != "Medius":
        return
    try:
        from src.utils.config import config

        if not bool(getattr(config, "button_mask_enabled", False)):
            if state.mask_applied_idx is not None:
                unlock_button_idx(state.mask_applied_idx)
                state.mask_applied_idx = None
            return
    except Exception:
        return

    if aimbot_running:
        if state.mask_applied_idx != selected_idx:
            if state.mask_applied_idx is not None:
                unlock_button_idx(state.mask_applied_idx)
            lock_button_idx(selected_idx)
            state.mask_applied_idx = selected_idx
    elif state.mask_applied_idx is not None:
        unlock_button_idx(state.mask_applied_idx)
        state.mask_applied_idx = None


def test_move():
    move(100, 100)
