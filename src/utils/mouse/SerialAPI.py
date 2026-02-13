from src.utils.debug_logger import log_print
import threading
import time

import serial
from serial.tools import list_ports

from . import state

SUPPORTED_DEVICES = [
    ("1A86:55D3", "MAKCU"),
    ("1A86:5523", "CH343"),
    ("1A86:7523", "CH340"),
    ("1A86:5740", "CH347"),
    ("10C4:EA60", "CP2102"),
]

BAUD_RATES = [4_000_000, 2_000_000, 115_200]
BAUD_CHANGE_COMMAND = bytearray([0xDE, 0xAD, 0x05, 0x00, 0xA5, 0x00, 0x09, 0x3D, 0x00])

# Index mapping: 0=L, 1=R, 2=M, 3=S4, 4=S5
_LOCK_CMD_BY_IDX = {
    0: "lock_ml",
    1: "lock_mr",
    2: "lock_mm",
    3: "lock_ms1",
    4: "lock_ms2",
}

_MOVEMENT_LOCK_TIMEOUT = 0.1


def find_com_ports():
    found = []
    for port in list_ports.comports():
        hwid = port.hwid.upper()
        desc = port.description.upper()
        for vidpid, name in SUPPORTED_DEVICES:
            if vidpid in hwid or name.upper() in desc:
                found.append((port.device, name))
                break
    return found


def km_version_ok(ser):
    try:
        ser.reset_input_buffer()
        ser.write(b"km.version()\r")
        ser.flush()
        time.sleep(0.1)
        resp = b""
        start = time.time()
        while time.time() - start < 0.3:
            if ser.in_waiting:
                resp += ser.read(ser.in_waiting)
                if b"km.MAKCU" in resp or b"MAKCU" in resp:
                    return True
            time.sleep(0.01)
        return False
    except Exception as e:
        log_print(f"[WARN] km_version_ok: {e}")
        return False


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting serial listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] Serial listener thread started.")


def _listener_loop():
    state.reset_button_states()

    while state.is_connected and state.active_backend == "Serial":
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

        except serial.SerialException as e:
            log_print(f"[ERROR] Serial listener exception: {e}")
            break
        except Exception as e:
            log_print(f"[WARN] Serial listener error: {e}")
            time.sleep(0.001)

    state.reset_button_states()


def connect(port: str = None):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "Serial")

    selected_port = str(port).strip() if port is not None else ""
    if selected_port:
        ports = [(selected_port, "MANUAL")]
    else:
        ports = find_com_ports()
        if not ports:
            state.last_connect_error = "No supported serial devices found."
            log_print(f"[ERROR] {state.last_connect_error}")
            return False

    for port_name, dev_name in ports:
        for baud in BAUD_RATES:
            ser = None
            try:
                if dev_name in ("MAKCU", "MANUAL"):
                    label = "MANUAL" if dev_name == "MANUAL" else "MAKCU"
                    log_print(f"[INFO] Probing {label} {port_name} @ {baud} with km.version()...")
                    ser = serial.Serial(port_name, baud, timeout=0.3)
                    time.sleep(0.1)
                    if not km_version_ok(ser):
                        ser.close()
                        time.sleep(0.1)
                        continue
                    log_print(f"[INFO] {label} responded at {baud}, using it.")
                    ser.close()
                    time.sleep(0.1)
                    state.makcu = serial.Serial(port_name, baud, timeout=0.1)
                else:
                    log_print(f"[INFO] Trying {dev_name} {port_name} @ {baud} ...")
                    ser = serial.Serial(port_name, baud, timeout=0.1)
                    with state.makcu_lock:
                        ser.write(b"km.buttons(1)\r")
                        ser.flush()
                    ser.close()
                    time.sleep(0.1)
                    state.makcu = serial.Serial(port_name, baud, timeout=0.1)

                with state.makcu_lock:
                    state.makcu.write(b"km.buttons(1)\r")
                    state.makcu.flush()

                state.set_connected(True, "Serial")
                _start_listener_thread()
                log_print(f"[INFO] Connected to {dev_name} on {port_name} at {baud} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] Failed {dev_name}@{baud}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                _safe_close_port()

    if selected_port:
        state.last_connect_error = f"Could not connect to manual serial port: {selected_port}."
    else:
        state.last_connect_error = "Could not connect to any supported serial device."
    log_print(f"[ERROR] {state.last_connect_error}")
    return False


def _safe_close_port():
    try:
        if state.makcu and state.makcu.is_open:
            state.makcu.close()
    except Exception:
        pass
    state.makcu = None


def disconnect():
    state.set_connected(False, "Serial")
    _safe_close_port()
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def is_button_pressed(idx: int) -> bool:
    with state.button_states_lock:
        return state.button_states.get(idx, False)


def _send_cmd_no_wait(cmd: str):
    if not state.is_connected or state.active_backend != "Serial" or state.makcu is None:
        return
    with state.makcu_lock:
        state.makcu.write(f"km.{cmd}\r".encode("ascii", "ignore"))
        state.makcu.flush()


def move(x: float, y: float):
    if not state.is_connected or state.makcu is None:
        return
    dx, dy = int(x), int(y)
    with state.makcu_lock:
        state.makcu.write(f"km.move({dx},{dy})\r".encode())
        state.makcu.flush()


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    if not state.is_connected or state.makcu is None:
        return
    with state.makcu_lock:
        cmd = f"km.move({int(x)},{int(y)},{int(segments)},{int(ctrl_x)},{int(ctrl_y)})\r"
        state.makcu.write(cmd.encode())
        state.makcu.flush()


def left(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    with state.makcu_lock:
        state.makcu.write(f"km.left({1 if isdown else 0})\r".encode())
        state.makcu.flush()


def right(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    with state.makcu_lock:
        state.makcu.write(f"km.right({1 if isdown else 0})\r".encode())
        state.makcu.flush()


def middle(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    with state.makcu_lock:
        state.makcu.write(f"km.middle({1 if isdown else 0})\r".encode())
        state.makcu.flush()


def test_move():
    if state.is_connected and state.makcu is not None:
        with state.makcu_lock:
            state.makcu.write(b"km.move(100,100)\r")
            state.makcu.flush()


def switch_to_4m():
    if state.active_backend != "Serial":
        log_print("[WARN] switch_to_4m is only supported in Serial mode.")
        return False

    if not state.is_connected or not state.makcu or not state.makcu.is_open:
        log_print("[ERROR] Device not connected. Please connect first.")
        return False

    port_name = state.makcu.port

    try:
        current_baud = state.makcu.baudrate
        if current_baud == 4_000_000:
            log_print("[INFO] Device already at 4M baud rate.")
            return True

        if current_baud != 115_200:
            log_print(f"[WARN] Current baud rate is {current_baud}, not 115200. Cannot switch to 4M.")
            return False

        log_print("[INFO] Sending 4M handshake command...")
        with state.makcu_lock:
            state.makcu.write(BAUD_CHANGE_COMMAND)
            state.makcu.flush()

        state.makcu.close()
        time.sleep(0.15)

        log_print("[INFO] Attempting to connect at 4M baud rate...")
        ser4m = serial.Serial(port_name, 4_000_000, timeout=0.3)
        time.sleep(0.1)

        if km_version_ok(ser4m):
            log_print(f"[INFO] Successfully switched to 4M on {port_name}.")
            ser4m.close()
            time.sleep(0.1)
            state.makcu = serial.Serial(port_name, 4_000_000, timeout=0.1)
            with state.makcu_lock:
                state.makcu.write(b"km.buttons(1)\r")
                state.makcu.flush()
            state.set_connected(True, "Serial")
            _start_listener_thread()
            return True

        log_print("[WARN] 4M handshake failed, reconnecting at 115200...")
        ser4m.close()
        time.sleep(0.1)
        state.makcu = serial.Serial(port_name, 115_200, timeout=0.1)
        with state.makcu_lock:
            state.makcu.write(b"km.buttons(1)\r")
            state.makcu.flush()
        state.set_connected(True, "Serial")
        _start_listener_thread()
        return False

    except Exception as e:
        log_print(f"[ERROR] Failed to switch to 4M: {e}")
        try:
            if state.makcu and state.makcu.is_open:
                state.makcu.close()
            time.sleep(0.1)
            state.makcu = serial.Serial(port_name, 115_200, timeout=0.1)
            with state.makcu_lock:
                state.makcu.write(b"km.buttons(1)\r")
                state.makcu.flush()
            state.set_connected(True, "Serial")
            _start_listener_thread()
        except Exception:
            state.set_connected(False, "Serial")
            state.makcu = None
        return False


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
    if not state.is_connected or state.active_backend != "Serial":
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
    except Exception as e:
        log_print(f"[Mouse Lock] Error in lock_movement_x: {e}")


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    if not state.is_connected or state.active_backend != "Serial":
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
    except Exception as e:
        log_print(f"[Mouse Lock] Error in lock_movement_y: {e}")


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    if not state.is_connected or state.active_backend != "Serial":
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
    except Exception as e:
        log_print(f"[Mouse Lock] Error in update_movement_lock: {e}")


def tick_movement_lock_manager():
    if not state.is_connected or state.active_backend != "Serial":
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
    except Exception as e:
        log_print(f"[Mouse Lock] Error in tick_movement_lock_manager: {e}")


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    if not state.is_connected or state.active_backend != "Serial":
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
