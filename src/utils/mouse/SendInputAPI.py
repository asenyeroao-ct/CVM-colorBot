from src.utils.debug_logger import log_print
import ctypes
from ctypes import wintypes

from . import state
from .keycodes import to_vk_code

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
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


_USER32 = ctypes.windll.user32
_USER32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_USER32.SendInput.restype = wintypes.UINT
_USER32.GetAsyncKeyState.argtypes = (wintypes.INT,)
_USER32.GetAsyncKeyState.restype = wintypes.SHORT

_VK_BY_IDX = {
    0: 0x01,  # VK_LBUTTON
    1: 0x02,  # VK_RBUTTON
    2: 0x04,  # VK_MBUTTON
    3: 0x05,  # VK_XBUTTON1
    4: 0x06,  # VK_XBUTTON2
}


def connect():
    state.last_connect_error = ""
    disconnect()
    state.set_connected(True, "SendInput")
    state.reset_button_states()
    log_print("[INFO] SendInput backend ready.")
    return True


def disconnect():
    state.set_connected(False, "SendInput")
    state.mask_applied_idx = None
    state.reset_button_states()


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


def _send_mouse(flags: int, dx: int = 0, dy: int = 0, data: int = 0):
    if not state.is_connected or state.active_backend != "SendInput":
        return

    mouse_input = MOUSEINPUT(
        dx=int(dx),
        dy=int(dy),
        mouseData=int(data),
        dwFlags=int(flags),
        time=0,
        dwExtraInfo=0,
    )
    packet = INPUT(type=INPUT_MOUSE, mi=mouse_input)

    sent = int(_USER32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT)))
    if sent != 1:
        err = ctypes.get_last_error()
        if err:
            state.last_connect_error = f"SendInput failed (winerr={err})"


def _send_keyboard(vk_code: int, key_up: bool = False):
    if not state.is_connected or state.active_backend != "SendInput":
        return

    key_input = KEYBDINPUT(
        wVk=int(vk_code),
        wScan=0,
        dwFlags=(KEYEVENTF_KEYUP if key_up else 0),
        time=0,
        dwExtraInfo=0,
    )
    packet = INPUT(type=INPUT_KEYBOARD, ki=key_input)

    sent = int(_USER32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT)))
    if sent != 1:
        err = ctypes.get_last_error()
        if err:
            state.last_connect_error = f"SendInput keyboard failed (winerr={err})"


def move(x: float, y: float):
    _send_mouse(MOUSEEVENTF_MOVE, dx=int(x), dy=int(y))


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    move(x, y)


def left(isdown: int):
    _send_mouse(MOUSEEVENTF_LEFTDOWN if isdown else MOUSEEVENTF_LEFTUP)


def key_down(key):
    vk = to_vk_code(key)
    if vk is None:
        return
    _send_keyboard(vk_code=vk, key_up=False)


def key_up(key):
    vk = to_vk_code(key)
    if vk is None:
        return
    _send_keyboard(vk_code=vk, key_up=True)


def key_press(key):
    vk = to_vk_code(key)
    if vk is None:
        return
    _send_keyboard(vk_code=vk, key_up=False)
    _send_keyboard(vk_code=vk, key_up=True)


def local_is_key_pressed(key) -> bool:
    """Local keyboard state query, 鐙珛浜巃ctive backend."""
    vk = to_vk_code(key)
    if vk is None:
        return False
    try:
        return bool(_USER32.GetAsyncKeyState(int(vk)) & 0x8000)
    except Exception:
        return False


def local_key_down(key):
    """Local keyboard down, 涓嶄緷璧?state.active_backend."""
    vk = to_vk_code(key)
    if vk is None:
        return
    key_input = KEYBDINPUT(wVk=int(vk), wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
    packet = INPUT(type=INPUT_KEYBOARD, ki=key_input)
    _USER32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT))


def local_key_up(key):
    """Local keyboard up, 涓嶄緷璧?state.active_backend."""
    vk = to_vk_code(key)
    if vk is None:
        return
    key_input = KEYBDINPUT(wVk=int(vk), wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
    packet = INPUT(type=INPUT_KEYBOARD, ki=key_input)
    _USER32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT))


def local_key_press(key):
    """Local keyboard click, 鐙珛 keyboard API 浣跨敤."""
    local_key_down(key)
    local_key_up(key)


def test_move():
    move(100, 100)
