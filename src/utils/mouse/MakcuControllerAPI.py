import ctypes
import re
import threading
import time
from ctypes import wintypes

import serial
from serial.tools import list_ports

from src.utils.debug_logger import log_print

from . import state
from .keycodes import to_vk_code

DEFAULT_BAUD_RATES = [115_200, 230_400, 460_800, 921_600]
PORT_HINTS = [
    "MAK",
    "MAKCU",
    "CONTROLLER",
    "GAMEPAD",
    "USB",
    "SERIAL",
    "CH340",
    "CH343",
]
STATE_PATTERN = re.compile(r"ctl\.state\((\d+),(\d+),(\d+)\)", re.IGNORECASE)
AXIS_LIMIT = 32767
AXIS_SCALE = 256
STICK_CLEAR_DELAY_SEC = 0.018
STATE_POLL_INTERVAL_SEC = 0.08

_USER32 = ctypes.windll.user32
_USER32.SendInput.argtypes = (wintypes.UINT, ctypes.c_void_p, ctypes.c_int)
_USER32.SendInput.restype = wintypes.UINT
_USER32.GetAsyncKeyState.argtypes = (wintypes.INT,)
_USER32.GetAsyncKeyState.restype = wintypes.SHORT

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTUNION),
    ]


_VK_BY_IDX = {
    0: 0x01,
    1: 0x02,
    2: 0x04,
    3: 0x05,
    4: 0x06,
}

_clear_timer = None
_clear_timer_lock = threading.Lock()


def _score_port(port):
    text = f"{port.description} {port.hwid}".upper()
    score = 0
    for hint in PORT_HINTS:
        if hint in text:
            score += 1
    return score


def find_candidate_ports():
    ports = list(list_ports.comports())
    ports.sort(key=_score_port, reverse=True)
    return [p.device for p in ports]


def _send_line(line: str):
    if not state.is_connected or state.active_backend != "MakcuController" or state.makcu is None:
        return False
    try:
        with state.makcu_lock:
            state.makcu.write(f"{line}\n".encode("ascii", "ignore"))
            state.makcu.flush()
        return True
    except Exception as e:
        state.last_connect_error = f"MakcuController send failed: {e}"
        return False


def _read_state_response(timeout: float = 0.35):
    if state.makcu is None:
        return None

    deadline = time.time() + max(0.05, float(timeout))
    buffer = b""
    while time.time() < deadline:
        try:
            with state.makcu_lock:
                waiting = int(getattr(state.makcu, "in_waiting", 0) or 0)
                if waiting:
                    buffer += state.makcu.read(waiting)
        except Exception:
            time.sleep(0.01)
            continue

        if buffer:
            text = buffer.decode("ascii", "ignore")
            match = STATE_PATTERN.search(text)
            if match:
                buttons = int(match.group(1))
                lt = int(match.group(2))
                rt = int(match.group(3))
                state.makcu_controller_buttons = buttons
                state.makcu_controller_lt = lt
                state.makcu_controller_rt = rt
                return buttons, lt, rt

        time.sleep(0.01)

    return None


def _probe_state(ser) -> bool:
    try:
        ser.reset_input_buffer()
        ser.write(b"ctl.state()\n")
        ser.flush()

        deadline = time.time() + 0.35
        buffer = b""
        while time.time() < deadline:
            waiting = int(getattr(ser, "in_waiting", 0) or 0)
            if waiting:
                buffer += ser.read(waiting)
                text = buffer.decode("ascii", "ignore")
                if STATE_PATTERN.search(text):
                    return True
            time.sleep(0.01)
    except Exception:
        return False
    return False


def _schedule_clear():
    global _clear_timer
    with _clear_timer_lock:
        if _clear_timer is not None:
            try:
                _clear_timer.cancel()
            except Exception:
                pass
        _clear_timer = threading.Timer(STICK_CLEAR_DELAY_SEC, _clear_override)
        _clear_timer.daemon = True
        _clear_timer.start()


def _clear_override():
    global _clear_timer
    if state.is_connected and state.active_backend == "MakcuController":
        _send_line("ctl.clear()")
    with _clear_timer_lock:
        _clear_timer = None


def _cancel_clear_timer():
    global _clear_timer
    with _clear_timer_lock:
        if _clear_timer is not None:
            try:
                _clear_timer.cancel()
            except Exception:
                pass
        _clear_timer = None


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting MakcuController listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] MakcuController listener thread started.")


def _listener_loop():
    while state.is_connected and state.active_backend == "MakcuController":
        try:
            _send_line("ctl.state()")
            _read_state_response(timeout=0.20)
        except Exception:
            pass
        time.sleep(STATE_POLL_INTERVAL_SEC)


def _safe_close_port():
    try:
        if state.makcu and state.makcu.is_open:
            state.makcu.close()
    except Exception:
        pass
    state.makcu = None


def connect(port: str = None, baud: int = None):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "MakcuController")

    ports = [str(port).strip()] if port and str(port).strip() else find_candidate_ports()
    if not ports:
        state.last_connect_error = "No COM port available for MakcuController."
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    baud_list = [int(baud)] if baud else list(DEFAULT_BAUD_RATES)

    for port_name in ports:
        for baud_value in baud_list:
            ser = None
            try:
                log_print(f"[INFO] Probing MakcuController {port_name} @ {baud_value}...")
                ser = serial.Serial(port_name, baud_value, timeout=0.12, write_timeout=0.12)
                time.sleep(0.08)
                if not _probe_state(ser):
                    ser.close()
                    time.sleep(0.03)
                    continue

                ser.close()
                time.sleep(0.03)
                state.makcu = serial.Serial(port_name, baud_value, timeout=0.12, write_timeout=0.12)
                state.set_connected(True, "MakcuController")
                _start_listener_thread()
                log_print(f"[INFO] Connected to MakcuController on {port_name} at {baud_value} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] MakcuController failed on {port_name}@{baud_value}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                _safe_close_port()

    state.last_connect_error = "Could not connect to MakcuController device."
    log_print(f"[ERROR] {state.last_connect_error}")
    return False


def disconnect():
    _cancel_clear_timer()
    try:
        if state.is_connected and state.active_backend == "MakcuController":
            _send_line("ctl.clear()")
    except Exception:
        pass
    state.set_connected(False, "MakcuController")
    _safe_close_port()
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def _send_input(packet):
    try:
        _USER32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT))
    except Exception as e:
        state.last_connect_error = f"MakcuController SendInput fallback failed: {e}"


def is_button_pressed(idx: int) -> bool:
    try:
        vk = _VK_BY_IDX.get(int(idx))
    except Exception:
        return False
    if vk is None:
        return False
    try:
        return bool(_USER32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def is_key_pressed(key) -> bool:
    vk = to_vk_code(key)
    if vk is None:
        return False
    try:
        return bool(_USER32.GetAsyncKeyState(int(vk)) & 0x8000)
    except Exception:
        return False


def _clamp_axis(value: float) -> int:
    try:
        raw = int(round(float(value) * AXIS_SCALE))
    except Exception:
        raw = 0
    return max(-AXIS_LIMIT, min(AXIS_LIMIT, raw))


def move(x: float, y: float):
    if not state.is_connected or state.active_backend != "MakcuController":
        return
    rx = _clamp_axis(x)
    ry = _clamp_axis(y)
    if _send_line(f"ctl.stick({rx},{ry})"):
        _schedule_clear()


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    # 文件只提供 ctl.stick/clear/state, 所以 bezier fallback 為 single pulse move.
    _ = segments, ctrl_x, ctrl_y
    move(x, y)


def left(isdown: int):
    packet = INPUT(
        type=INPUT_MOUSE,
        mi=MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=MOUSEEVENTF_LEFTDOWN if isdown else MOUSEEVENTF_LEFTUP,
            time=0,
            dwExtraInfo=0,
        ),
    )
    _send_input(packet)


def key_down(key):
    vk = to_vk_code(key)
    if vk is None:
        return
    packet = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(wVk=int(vk), wScan=0, dwFlags=0, time=0, dwExtraInfo=0),
    )
    _send_input(packet)


def key_up(key):
    vk = to_vk_code(key)
    if vk is None:
        return
    packet = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(wVk=int(vk), wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0),
    )
    _send_input(packet)


def key_press(key):
    key_down(key)
    key_up(key)


def test_move():
    move(48, 48)
