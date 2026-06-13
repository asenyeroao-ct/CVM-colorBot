from src.utils.debug_logger import log_print
import glob
import importlib.util
import os
import sys
import multiprocessing as mp

from . import state
from .keycodes import to_hid_code, to_vk_code

_loaded_module_path = None
_WARNED_KEYBOARD_NOT_SUPPORTED = False


def get_expected_kmnet_dll_name() -> str:
    return f"kmNet.cp{sys.version_info.major}{sys.version_info.minor}-win_amd64.pyd"


def _get_kmnet_dll_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "API", "Net", "dll")


def _get_compatible_kmnet_candidates(dll_dir: str):
    expected_name = get_expected_kmnet_dll_name()
    expected_path = os.path.join(dll_dir, expected_name)
    if os.path.exists(expected_path):
        return [expected_path]

    legacy_name = f"kmNet{sys.version_info.major}_{sys.version_info.minor}.pyd"
    legacy_path = os.path.join(dll_dir, legacy_name)
    if os.path.exists(legacy_path):
        return [legacy_path]

    return []


def _load_module():
    global _loaded_module_path
    if state.kmnet_module is not None:
        return state.kmnet_module

    dll_dir = _get_kmnet_dll_dir()
    candidates = _get_compatible_kmnet_candidates(dll_dir)

    if not candidates:
        available = sorted(os.path.basename(p) for p in glob.glob(os.path.join(dll_dir, "kmNet*.pyd")))
        expected_name = get_expected_kmnet_dll_name()
        legacy_name = f"kmNet{sys.version_info.major}_{sys.version_info.minor}.pyd"
        if available:
            state.last_connect_error = (
                f"No compatible kmNet module for Python {sys.version_info.major}.{sys.version_info.minor}. "
                f"Expected {expected_name} or {legacy_name}. Available: {', '.join(available)}"
            )
        else:
            state.last_connect_error = f"kmNet dll not found in: {dll_dir}"
        return None

    seen = set()
    for pyd_path in candidates:
        if pyd_path in seen:
            continue
        seen.add(pyd_path)
        try:
            spec = importlib.util.spec_from_file_location("kmNet", pyd_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["kmNet"] = module
            state.kmnet_module = module
            _loaded_module_path = pyd_path
            log_print(f"[INFO] kmNet loaded from: {pyd_path}")
            return state.kmnet_module
        except Exception as e:
            state.last_connect_error = f"Failed loading {os.path.basename(pyd_path)}: {e}"

    return None


def _init_probe_worker(pyd_path: str, ip: str, port: str, uuid: str, out_q):
    try:
        spec = importlib.util.spec_from_file_location("kmNet", pyd_path)
        if spec is None or spec.loader is None:
            out_q.put(("error", "invalid kmNet module spec"))
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ret = int(module.init(str(ip), str(port), str(uuid)))
        out_q.put(("ok", ret))
    except Exception as e:
        out_q.put(("error", str(e)))


def _preflight_init(ip: str, port: str, uuid: str, timeout_sec: float = 3.0):
    if not _loaded_module_path:
        return False, "kmNet module path unavailable"

    ctx = mp.get_context("spawn")
    out_q = ctx.Queue()
    proc = ctx.Process(
        target=_init_probe_worker,
        args=(_loaded_module_path, ip, port, uuid, out_q),
        daemon=True,
    )
    proc.start()
    proc.join(timeout_sec)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=1.0)
        return False, f"kmNet.init timeout ({timeout_sec:.1f}s)"

    try:
        status, payload = out_q.get_nowait()
    except Exception:
        return False, "kmNet.init probe returned no result"

    if status == "error":
        return False, payload
    if int(payload) != 0:
        return False, f"kmNet.init probe failed (code={int(payload)})"
    return True, None


def connect(ip: str, port: str, uuid: str):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "Net")

    module = _load_module()
    if module is None:
        if not state.last_connect_error:
            state.last_connect_error = "kmNet module load failed"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    if not hasattr(module, "init"):
        state.last_connect_error = "kmNet.init not found"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    # Run init preflight in a child process.
    # Some kmNet builds can block and freeze UI if called with bad params.
    ok_probe, probe_error = _preflight_init(str(ip), str(port), str(uuid), timeout_sec=3.0)
    if not ok_probe:
        state.last_connect_error = f"{probe_error}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    try:
        ret = int(module.init(str(ip), str(port), str(uuid)))
        if ret != 0:
            state.last_connect_error = f"kmNet.init failed (code={ret})"
            log_print(f"[ERROR] {state.last_connect_error}")
            return False

        try:
            if hasattr(module, "monitor"):
                module.monitor(30000)
        except Exception as mon_err:
            log_print(f"[WARN] kmNet.monitor failed: {mon_err}")

        state.set_connected(True, "Net")
        log_print(f"[INFO] Connected to kmNet at {ip}:{port} (UUID: {uuid})")
        return True
    except Exception as e:
        state.last_connect_error = f"kmNet connection error: {e}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False


def disconnect():
    if state.kmnet_module is None:
        return
    try:
        if hasattr(state.kmnet_module, "monitor"):
            state.kmnet_module.monitor(0)
    except Exception:
        pass


def _call_kmnet(candidates, *args):
    module = state.kmnet_module
    if module is None:
        return False, None

    for fn_name in candidates:
        fn = getattr(module, fn_name, None)
        if fn is None:
            continue
        try:
            return True, fn(*args)
        except Exception as e:
            log_print(f"[Mouse-Net] {fn_name} failed: {e}")
            continue
    return False, None


def _warn_keyboard_not_supported():
    global _WARNED_KEYBOARD_NOT_SUPPORTED
    if _WARNED_KEYBOARD_NOT_SUPPORTED:
        return
    _WARNED_KEYBOARD_NOT_SUPPORTED = True
    log_print("[WARN] kmNet keyboard functions are not available in this module build.")


def is_button_pressed(idx: int) -> bool:
    if state.kmnet_module is None:
        return False

    fn_name_by_idx = {
        0: "isdown_left",
        1: "isdown_right",
        2: "isdown_middle",
        3: "isdown_side1",
        4: "isdown_side2",
    }
    fn_name = fn_name_by_idx.get(idx)
    if not fn_name:
        return False

    fn = getattr(state.kmnet_module, fn_name, None)
    if fn is None:
        return False

    try:
        return bool(fn())
    except Exception:
        return False


def is_key_pressed(key) -> bool:
    vk_code = to_vk_code(key)
    hid_code = to_hid_code(key)
    tried = set()

    for code in (vk_code, hid_code):
        if code is None:
            continue
        code = int(code)
        if code in tried:
            continue
        tried.add(code)

        found, value = _call_kmnet(("isdown_keyboard", "isdown_key", "isdown2"), code)
        if found:
            try:
                return bool(value)
            except Exception:
                return False

    return False


def move(x: float, y: float):
    if state.kmnet_module is None:
        return
    try:
        state.kmnet_module.move(int(x), int(y))
    except Exception as e:
        log_print(f"[Mouse-Net] move failed: {e}")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    # kmNet Bezier signature differs from Serial API; fallback to basic move.
    move(x, y)


def left(isdown: int):
    if state.kmnet_module is None:
        return
    try:
        state.kmnet_module.left(1 if isdown else 0)
    except Exception as e:
        log_print(f"[Mouse-Net] left failed: {e}")


def _resolve_net_key_code(key):
    vk_code = to_vk_code(key)
    if vk_code is not None:
        return int(vk_code)
    hid_code = to_hid_code(key)
    if hid_code is not None:
        return int(hid_code)
    return None


def key_down(key):
    key_code = _resolve_net_key_code(key)
    if key_code is None:
        return
    found, _ = _call_kmnet(("keydown", "key_down", "enc_keydown"), int(key_code))
    if not found:
        _warn_keyboard_not_supported()


def key_up(key):
    key_code = _resolve_net_key_code(key)
    if key_code is None:
        return
    found, _ = _call_kmnet(("keyup", "key_up", "enc_keyup"), int(key_code))
    if not found:
        _warn_keyboard_not_supported()


def key_press(key):
    key_code = _resolve_net_key_code(key)
    if key_code is None:
        return

    found, _ = _call_kmnet(("keypress", "key_press", "press"), int(key_code))
    if found:
        return

    found_down, _ = _call_kmnet(("keydown", "key_down", "enc_keydown"), int(key_code))
    found_up, _ = _call_kmnet(("keyup", "key_up", "enc_keyup"), int(key_code))
    if not (found_down or found_up):
        _warn_keyboard_not_supported()


def mask_key(key):
    key_code = _resolve_net_key_code(key)
    if key_code is None:
        return
    found, _ = _call_kmnet(("mask_keyboard", "mask_key"), int(key_code))
    if not found:
        _warn_keyboard_not_supported()


def unmask_key(key):
    key_code = _resolve_net_key_code(key)
    if key_code is None:
        return
    found, _ = _call_kmnet(("dismask_keyboard", "unmask_key"), int(key_code))
    if not found:
        _warn_keyboard_not_supported()


def unmask_all_keys():
    found, _ = _call_kmnet(("dismask_keyboard_all", "unmask_all_keys"))
    if not found:
        _warn_keyboard_not_supported()
