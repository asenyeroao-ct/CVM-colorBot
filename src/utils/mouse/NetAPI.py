from src.utils.debug_logger import log_print
import glob
import importlib.util
import os
import sys
import multiprocessing as mp

from . import state

_loaded_module_path = None


def get_expected_kmnet_dll_name() -> str:
    return f"kmNet.cp{sys.version_info.major}{sys.version_info.minor}-win_amd64.pyd"


def _get_kmnet_dll_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "API", "Net", "dll")


def _load_module():
    global _loaded_module_path
    if state.kmnet_module is not None:
        return state.kmnet_module

    dll_dir = _get_kmnet_dll_dir()
    expected = os.path.join(dll_dir, get_expected_kmnet_dll_name())

    candidates = []
    if os.path.exists(expected):
        candidates.append(expected)
    candidates.extend(sorted(glob.glob(os.path.join(dll_dir, "kmNet*.pyd"))))

    if not candidates:
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
