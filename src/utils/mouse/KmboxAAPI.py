from src.utils.debug_logger import log_print
import ctypes
import glob
import importlib.util
import os
import sys
from ctypes import wintypes

from . import state

_loaded_module_path = None
_USER32 = ctypes.windll.user32
_USER32.GetAsyncKeyState.argtypes = (wintypes.INT,)
_USER32.GetAsyncKeyState.restype = wintypes.SHORT

_VK_BY_IDX = {
    0: 0x01,  # VK_LBUTTON
    1: 0x02,  # VK_RBUTTON
    2: 0x04,  # VK_MBUTTON
    3: 0x05,  # VK_XBUTTON1
    4: 0x06,  # VK_XBUTTON2
}


def get_expected_kmboxa_dll_name() -> str:
    return f"kmA.cp{sys.version_info.major}{sys.version_info.minor}-win_amd64.pyd"


def get_compat_kmboxa_dll_name() -> str:
    return f"kmA{sys.version_info.major}{sys.version_info.minor}.pyd"


def _get_kmboxa_dll_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "API", "kmboxA", "pyd")


def _load_module():
    global _loaded_module_path
    if state.kmboxa_module is not None:
        return state.kmboxa_module

    dll_dir = _get_kmboxa_dll_dir()
    expected = os.path.join(dll_dir, get_expected_kmboxa_dll_name())
    compat_name = os.path.join(dll_dir, get_compat_kmboxa_dll_name())

    candidates = []
    if os.path.exists(expected):
        candidates.append(expected)
    if os.path.exists(compat_name):
        candidates.append(compat_name)
    candidates.extend(sorted(glob.glob(os.path.join(dll_dir, "kmA*.pyd"))))

    if not candidates:
        state.last_connect_error = f"kmboxA pyd not found in: {dll_dir}"
        return None

    seen = set()
    for pyd_path in candidates:
        if pyd_path in seen:
            continue
        seen.add(pyd_path)
        try:
            spec = importlib.util.spec_from_file_location("kmA", pyd_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["kmA"] = module
            state.kmboxa_module = module
            _loaded_module_path = pyd_path
            log_print(f"[INFO] kmboxA module loaded from: {pyd_path}")
            return state.kmboxa_module
        except Exception as e:
            state.last_connect_error = f"Failed loading {os.path.basename(pyd_path)}: {e}"

    return None


def connect(vid: int, pid: int):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "KmboxA")

    try:
        selected_vid = int(vid)
        selected_pid = int(pid)
    except Exception:
        state.last_connect_error = f"Invalid kmboxA VID/PID: vid={vid!r}, pid={pid!r}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    module = _load_module()
    if module is None:
        if not state.last_connect_error:
            state.last_connect_error = "kmboxA module load failed"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    if not hasattr(module, "init"):
        state.last_connect_error = "kmboxA init not found"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    try:
        ret = int(module.init(selected_vid, selected_pid))
        if ret != 0:
            state.last_connect_error = f"kmboxA init failed (code={ret})"
            log_print(f"[ERROR] {state.last_connect_error}")
            return False
    except Exception as e:
        state.last_connect_error = f"kmboxA init error: {e}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    state.set_connected(True, "KmboxA")
    log_print(f"[INFO] Connected to kmboxA (VID={selected_vid}, PID={selected_pid})")
    return True


def disconnect():
    state.set_connected(False, "KmboxA")
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


def move(x: float, y: float):
    if state.kmboxa_module is None:
        return
    try:
        state.kmboxa_module.move(int(x), int(y))
    except Exception as e:
        log_print(f"[Mouse-kmboxA] move failed: {e}")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    move(x, y)


def left(isdown: int):
    if state.kmboxa_module is None:
        return
    try:
        state.kmboxa_module.left(1 if isdown else 0)
    except Exception as e:
        log_print(f"[Mouse-kmboxA] left failed: {e}")
