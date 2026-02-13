from src.utils.debug_logger import log_print
import ctypes
from ctypes import wintypes

from . import state

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

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


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


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


def move(x: float, y: float):
    _send_mouse(MOUSEEVENTF_MOVE, dx=int(x), dy=int(y))


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    move(x, y)


def left(isdown: int):
    _send_mouse(MOUSEEVENTF_LEFTDOWN if isdown else MOUSEEVENTF_LEFTUP)


def test_move():
    move(100, 100)
