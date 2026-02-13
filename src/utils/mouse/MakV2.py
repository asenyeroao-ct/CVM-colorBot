from src.utils.debug_logger import log_print
import threading
import time

import serial
from serial.tools import list_ports

from . import state

DEFAULT_BAUD_RATES = [4_000_000, 2_000_000, 1_000_000, 115_200]

PORT_HINTS = [
    "MAK",
    "MAKXD",
    "V2",
    "CH343",
    "CH340",
    "USB",
    "SERIAL",
]

# Assume makxd v2 keeps same lock command names as MAKCU firmware.
_LOCK_CMD_BY_IDX = {
    0: "lock_ml",
    1: "lock_mr",
    2: "lock_mm",
    3: "lock_ms1",
    4: "lock_ms2",
}

_MOVEMENT_LOCK_TIMEOUT = 0.1


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


def _version_ok(ser):
    try:
        ser.reset_input_buffer()
        ser.write(b"km.version()\r")
        ser.flush()
        time.sleep(0.08)

        resp = b""
        start = time.time()
        while time.time() - start < 0.35:
            waiting = getattr(ser, "in_waiting", 0)
            if waiting:
                resp += ser.read(waiting)
                text = resp.upper()
                if b"MAK" in text or b"V2" in text or b"KM." in text:
                    return True
            time.sleep(0.01)

        # Some firmware may not return version text reliably; any payload is acceptable.
        return len(resp) > 0
    except Exception:
        return False


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting MakV2 listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] MakV2 listener thread started.")


def _listener_loop():
    state.reset_button_states()

    while state.is_connected and state.active_backend == "MakV2":
        try:
            if state.makcu is None:
                time.sleep(0.01)
                continue

            b = state.makcu.read(1)
            if not b:
                continue

            v = b[0]
            if v in (0x0A, 0x0D) or v > 31:
                continue

            changed = state.last_button_mask ^ v
            if changed:
                with state.button_states_lock:
                    for i in range(5):
                        m = 1 << i
                        if changed & m:
                            state.button_states[i] = bool(v & m)
                state.last_button_mask = v
        except Exception:
            time.sleep(0.001)

    state.reset_button_states()


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
    state.set_connected(False, "MakV2")

    if port:
        ports = [port]
    else:
        ports = find_candidate_ports()

    if not ports:
        state.last_connect_error = "No COM port available for MakV2."
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    baud_list = [int(baud)] if baud else list(DEFAULT_BAUD_RATES)

    for port_name in ports:
        for baud_value in baud_list:
            ser = None
            try:
                log_print(f"[INFO] Probing MakV2 {port_name} @ {baud_value}...")
                ser = serial.Serial(port_name, baud_value, timeout=0.25)
                time.sleep(0.08)
                if not _version_ok(ser):
                    ser.close()
                    time.sleep(0.05)
                    continue

                ser.close()
                time.sleep(0.05)
                state.makcu = serial.Serial(port_name, baud_value, timeout=0.1)
                with state.makcu_lock:
                    state.makcu.write(b"km.buttons(1)\r")
                    state.makcu.flush()

                state.set_connected(True, "MakV2")
                _start_listener_thread()
                log_print(f"[INFO] Connected to MakV2 on {port_name} at {baud_value} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] MakV2 failed on {port_name}@{baud_value}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                _safe_close_port()

    state.last_connect_error = "Could not connect to MakV2 device."
    log_print(f"[ERROR] {state.last_connect_error}")
    return False


def disconnect():
    state.set_connected(False, "MakV2")
    _safe_close_port()
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def is_button_pressed(idx: int) -> bool:
    with state.button_states_lock:
        return state.button_states.get(idx, False)


def _send_cmd_no_wait(cmd: str):
    if not state.is_connected or state.active_backend != "MakV2" or state.makcu is None:
        return
    try:
        with state.makcu_lock:
            state.makcu.write(f"km.{cmd}\r".encode("ascii", "ignore"))
            state.makcu.flush()
    except Exception:
        pass


def move(x: float, y: float):
    _send_cmd_no_wait(f"move({int(x)},{int(y)})")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    _send_cmd_no_wait(f"move({int(x)},{int(y)},{int(segments)},{int(ctrl_x)},{int(ctrl_y)})")


def left(isdown: int):
    _send_cmd_no_wait(f"left({1 if isdown else 0})")


def lock_button_idx(idx: int):
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(1)")


def unlock_button_idx(idx: int):
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(0)")


def unlock_all_locks():
    for i in range(5):
        unlock_button_idx(i)


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    if not state.is_connected or state.active_backend != "MakV2":
        return

    try:
        if skip_lock:
            if state.movement_lock_state["lock_x"] != lock:
                _send_cmd_no_wait(f"lock_mx({1 if lock else 0})")
                state.movement_lock_state["lock_x"] = lock
        else:
            with state.movement_lock_state["lock"]:
                if state.movement_lock_state["lock_x"] != lock:
                    _send_cmd_no_wait(f"lock_mx({1 if lock else 0})")
                    state.movement_lock_state["lock_x"] = lock
    except Exception:
        pass


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    if not state.is_connected or state.active_backend != "MakV2":
        return

    try:
        if skip_lock:
            if state.movement_lock_state["lock_y"] != lock:
                _send_cmd_no_wait(f"lock_my({1 if lock else 0})")
                state.movement_lock_state["lock_y"] = lock
        else:
            with state.movement_lock_state["lock"]:
                if state.movement_lock_state["lock_y"] != lock:
                    _send_cmd_no_wait(f"lock_my({1 if lock else 0})")
                    state.movement_lock_state["lock_y"] = lock
    except Exception:
        pass


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    if not state.is_connected or state.active_backend != "MakV2":
        return

    try:
        current_time = time.time()
        lock_acquired = state.movement_lock_state["lock"].acquire(timeout=0.01)
        if not lock_acquired:
            return
        try:
            if is_main:
                state.movement_lock_state["main_aimbot_locked"] = lock_x or lock_y
                if lock_x or lock_y:
                    state.movement_lock_state["last_main_move_time"] = current_time
            else:
                state.movement_lock_state["sec_aimbot_locked"] = lock_x or lock_y
                if lock_x or lock_y:
                    state.movement_lock_state["last_sec_move_time"] = current_time
        finally:
            state.movement_lock_state["lock"].release()
    except Exception:
        pass


def tick_movement_lock_manager():
    if not state.is_connected or state.active_backend != "MakV2":
        return

    try:
        current_time = time.time()
        lock_acquired = state.movement_lock_state["lock"].acquire(timeout=0.01)
        if not lock_acquired:
            return
        try:
            if state.movement_lock_state["main_aimbot_locked"]:
                if current_time - state.movement_lock_state["last_main_move_time"] > _MOVEMENT_LOCK_TIMEOUT:
                    state.movement_lock_state["main_aimbot_locked"] = False

            if state.movement_lock_state["sec_aimbot_locked"]:
                if current_time - state.movement_lock_state["last_sec_move_time"] > _MOVEMENT_LOCK_TIMEOUT:
                    state.movement_lock_state["sec_aimbot_locked"] = False

            try:
                from src.utils.config import config

                main_lock_x = getattr(config, "mouse_lock_main_x", False)
                main_lock_y = getattr(config, "mouse_lock_main_y", False)
                sec_lock_x = getattr(config, "mouse_lock_sec_x", False)
                sec_lock_y = getattr(config, "mouse_lock_sec_y", False)
            except Exception:
                main_lock_x = False
                main_lock_y = False
                sec_lock_x = False
                sec_lock_y = False

            should_lock_x = (
                (main_lock_x and state.movement_lock_state["main_aimbot_locked"])
                or (sec_lock_x and state.movement_lock_state["sec_aimbot_locked"])
            )
            should_lock_y = (
                (main_lock_y and state.movement_lock_state["main_aimbot_locked"])
                or (sec_lock_y and state.movement_lock_state["sec_aimbot_locked"])
            )

            if state.movement_lock_state["lock_x"] != should_lock_x:
                lock_movement_x(should_lock_x, skip_lock=True)
            if state.movement_lock_state["lock_y"] != should_lock_y:
                lock_movement_y(should_lock_y, skip_lock=True)
        finally:
            state.movement_lock_state["lock"].release()
    except Exception:
        pass


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    if not state.is_connected or state.active_backend != "MakV2":
        state.mask_applied_idx = None
        return

    if not isinstance(selected_idx, int) or not (0 <= selected_idx <= 4):
        selected_idx = None

    if not aimbot_running:
        if state.mask_applied_idx is not None:
            unlock_button_idx(state.mask_applied_idx)
            state.mask_applied_idx = None
        return

    if selected_idx is None:
        if state.mask_applied_idx is not None:
            unlock_button_idx(state.mask_applied_idx)
            state.mask_applied_idx = None
        return

    if state.mask_applied_idx != selected_idx:
        if state.mask_applied_idx is not None:
            unlock_button_idx(state.mask_applied_idx)
        lock_button_idx(selected_idx)
        state.mask_applied_idx = selected_idx
