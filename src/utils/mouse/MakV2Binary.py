from src.utils.debug_logger import log_print
import threading
import time
import struct

import serial
from serial.tools import list_ports

from . import state
from .keycodes import to_hid_code

SUPPORTED_DEVICES = [
    ("1A86:55D3", "MAKCU"),
    ("1A86:5523", "CH343"),
    ("1A86:7523", "CH340"),
    ("1A86:5740", "CH347"),
    ("10C4:EA60", "CP2102"),
]

DEFAULT_BAUD_RATES = [4_000_000, 2_000_000, 1_000_000, 115_200]
ACTIVE_BACKENDS = ("MakV2Binary", "MakxdMakAPI")

# V2 API Binary Command Codes
# 根據 MAKCU API 3.9 文檔
CMD_MOVE = 0x0D
CMD_MOVETO = 0x0E
CMD_LEFT = 0x08
CMD_RIGHT = 0x11
CMD_MIDDLE = 0x12
CMD_BUTTONS = 0x02
CMD_VERSION = 0xBF
# Lock 命令（根據文檔，可能需要使用 ASCII 或不同的二進制代碼）
# 暫時使用 ASCII 格式的 lock 命令，因為二進制格式的 lock 命令代碼未在文檔中明確說明
# 如果需要純二進制，需要查閱完整的 API 文檔
CMD_LOCK_ML = None  # 將使用 ASCII 格式
CMD_LOCK_MR = None
CMD_LOCK_MM = None
CMD_LOCK_MS1 = None
CMD_LOCK_MS2 = None
CMD_LOCK_MX = None
CMD_LOCK_MY = None

# Binary frame header
FRAME_HEADER = 0x50

# Index mapping: 0=L, 1=R, 2=M, 3=S4, 4=S5
# Lock 命令使用 ASCII 格式（因為二進制格式的 lock 命令代碼未在文檔中明確說明）
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


def _version_ok_binary(ser):
    """使用二進制格式檢查版本"""
    try:
        ser.reset_input_buffer()
        # 發送二進制版本查詢命令
        # CMD_VERSION (0xBF) 無參數，長度為 0
        cmd = bytearray([FRAME_HEADER, CMD_VERSION, 0x00, 0x00])
        ser.write(cmd)
        ser.flush()
        time.sleep(0.1)
        
        resp = b""
        start = time.time()
        while time.time() - start < 0.3:
            if ser.in_waiting:
                resp += ser.read(ser.in_waiting)
                # 檢查是否收到有效的二進制響應或 ASCII 響應（兼容性）
                if len(resp) >= 2 and (resp[0] == CMD_VERSION or b"MAKCU" in resp or b"km." in resp):
                    return True
            time.sleep(0.01)
        return False
    except Exception as e:
        log_print(f"[WARN] _version_ok_binary: {e}")
        return False


def _send_binary_command(cmd_code: int, payload: bytes = b""):
    """發送二進制格式命令
    
    Args:
        cmd_code: 命令代碼
        payload: 命令負載（可選）
    
    Returns:
        構建好的二進制命令字節數組
    """
    payload_len = len(payload)
    # Little-Endian 長度
    len_lo = payload_len & 0xFF
    len_hi = (payload_len >> 8) & 0xFF
    
    frame = bytearray([FRAME_HEADER, cmd_code, len_lo, len_hi])
    frame.extend(payload)
    return frame


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting MakV2Binary listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] MakV2Binary listener thread started.")


def _listener_loop():
    state.reset_button_states()

    while state.is_connected and state.active_backend in ACTIVE_BACKENDS:
        try:
            if state.makcu is None:
                time.sleep(0.01)
                continue

            b = state.makcu.read(1)
            if not b:
                continue

            v = b[0]
            # 處理按鈕狀態響應（二進制格式的 buttons 響應）
            if v == CMD_BUTTONS:
                # 讀取按鈕掩碼
                mask_byte = state.makcu.read(1)
                if mask_byte:
                    v = mask_byte[0]
                else:
                    continue
            elif v in (0x0A, 0x0D) or v > 31:
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
            log_print(f"[ERROR] MakV2Binary listener exception: {e}")
            break
        except Exception as e:
            log_print(f"[WARN] MakV2Binary listener error: {e}")
            time.sleep(0.001)

    state.reset_button_states()


def _safe_close_port():
    try:
        if state.makcu and state.makcu.is_open:
            state.makcu.close()
    except Exception:
        pass
    state.makcu = None


def connect(port: str = None, baud: int = None, backend_name: str = "MakV2Binary", log_name: str = "MakV2Binary"):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, backend_name)

    selected_port = str(port).strip() if port is not None else ""
    if selected_port:
        ports = [(selected_port, "MANUAL")]
    else:
        ports = find_com_ports()
        if not ports:
            state.last_connect_error = f"No supported serial devices found for {log_name}."
            log_print(f"[ERROR] {state.last_connect_error}")
            return False

    baud_list = [int(baud)] if baud else list(DEFAULT_BAUD_RATES)

    for port_name, dev_name in ports:
        for baud_value in baud_list:
            ser = None
            try:
                label = "MANUAL" if dev_name == "MANUAL" else dev_name
                log_print(f"[INFO] Probing {log_name} {label} {port_name} @ {baud_value}...")
                ser = serial.Serial(port_name, baud_value, timeout=0.3)
                time.sleep(0.1)
                
                # 嘗試二進制版本檢查
                if not _version_ok_binary(ser):
                    ser.close()
                    time.sleep(0.1)
                    continue
                
                log_print(f"[INFO] {label} responded at {baud_value}, using binary API.")
                ser.close()
                time.sleep(0.1)
                state.makcu = serial.Serial(port_name, baud_value, timeout=0.1)
                
                # 啟用按鈕狀態監聽（二進制格式）
                with state.makcu_lock:
                    cmd = _send_binary_command(CMD_BUTTONS, struct.pack("<B", 1))
                    state.makcu.write(cmd)
                    state.makcu.flush()

                state.set_connected(True, backend_name)
                _start_listener_thread()
                log_print(f"[INFO] Connected to {log_name} on {port_name} at {baud_value} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] {log_name} failed {dev_name}@{baud_value}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                _safe_close_port()

    if selected_port:
        state.last_connect_error = f"Could not connect to manual serial port: {selected_port}."
    else:
        state.last_connect_error = f"Could not connect to any supported serial device for {log_name}."
    log_print(f"[ERROR] {state.last_connect_error}")
    return False


def disconnect():
    backend = state.active_backend if state.active_backend in ACTIVE_BACKENDS else "MakV2Binary"
    state.set_connected(False, backend)
    _safe_close_port()
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def is_button_pressed(idx: int) -> bool:
    with state.button_states_lock:
        return state.button_states.get(idx, False)


def _send_cmd_no_wait_binary(cmd_code: int, payload: bytes = b""):
    """發送二進制命令（非阻塞）"""
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS or state.makcu is None:
        return
    try:
        with state.makcu_lock:
            cmd = _send_binary_command(cmd_code, payload)
            state.makcu.write(cmd)
            state.makcu.flush()
    except Exception as e:
        log_print(f"[WARN] MakV2Binary send command error: {e}")


def _send_cmd_ascii(cmd: str):
    """發送 ASCII 命令（用於 lock 等命令）"""
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS or state.makcu is None:
        return
    try:
        with state.makcu_lock:
            state.makcu.write(f"km.{cmd}\r".encode("ascii", "ignore"))
            state.makcu.flush()
    except Exception as e:
        log_print(f"[WARN] MakV2Binary send ASCII command error: {e}")


def move(x: float, y: float):
    if not state.is_connected or state.makcu is None:
        return
    dx, dy = int(x), int(y)
    # move 命令：dx:i16, dy:i16
    payload = struct.pack("<hh", dx, dy)
    _send_cmd_no_wait_binary(CMD_MOVE, payload)


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    if not state.is_connected or state.makcu is None:
        return
    dx, dy = int(x), int(y)
    seg = max(1, min(512, int(segments)))
    cx1, cy1 = int(ctrl_x), int(ctrl_y)
    # move 命令帶貝塞爾參數：dx:i16, dy:i16, segments:u8, cx1:i8, cy1:i8
    payload = struct.pack("<hhBbb", dx, dy, seg, cx1, cy1)
    _send_cmd_no_wait_binary(CMD_MOVE, payload)


def left(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    # left 命令：state:u8 (0=釋放, 1=按下, 2=靜默釋放)
    payload = struct.pack("<B", 1 if isdown else 0)
    _send_cmd_no_wait_binary(CMD_LEFT, payload)


def right(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    payload = struct.pack("<B", 1 if isdown else 0)
    _send_cmd_no_wait_binary(CMD_RIGHT, payload)


def middle(isdown: int):
    if not state.is_connected or state.makcu is None:
        return
    payload = struct.pack("<B", 1 if isdown else 0)
    _send_cmd_no_wait_binary(CMD_MIDDLE, payload)


def _resolve_hid_key_code(key):
    key_code = to_hid_code(key)
    if key_code is None:
        return None
    try:
        return int(key_code)
    except Exception:
        return None


def key_down(key):
    key_code = _resolve_hid_key_code(key)
    if key_code is None:
        return
    _send_cmd_ascii(f"down({key_code})")


def key_up(key):
    key_code = _resolve_hid_key_code(key)
    if key_code is None:
        return
    _send_cmd_ascii(f"up({key_code})")


def key_press(key):
    key_code = _resolve_hid_key_code(key)
    if key_code is None:
        return
    _send_cmd_ascii(f"press({key_code})")


def is_key_pressed(key) -> bool:
    # MakV2Binary listener currently tracks mouse buttons only.
    _ = key
    return False


def lock_button_idx(idx: int):
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    # 使用 ASCII 格式發送 lock 命令（因為二進制格式的 lock 命令代碼未在文檔中明確說明）
    _send_cmd_ascii(f"{cmd}(1)")


def unlock_button_idx(idx: int):
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    # 使用 ASCII 格式發送 unlock 命令
    _send_cmd_ascii(f"{cmd}(0)")


def unlock_all_locks():
    for i in range(5):
        unlock_button_idx(i)


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS:
        return

    try:
        if skip_lock:
            if state.movement_lock_state["lock_x"] != lock:
                # 使用 ASCII 格式發送 lock 命令
                _send_cmd_ascii(f"lock_mx({1 if lock else 0})")
                state.movement_lock_state["lock_x"] = lock
        else:
            with state.movement_lock_state["lock"]:
                if state.movement_lock_state["lock_x"] != lock:
                    _send_cmd_ascii(f"lock_mx({1 if lock else 0})")
                    state.movement_lock_state["lock_x"] = lock
    except Exception as e:
        log_print(f"[Mouse Lock] Error in lock_movement_x: {e}")


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS:
        return

    try:
        if skip_lock:
            if state.movement_lock_state["lock_y"] != lock:
                # 使用 ASCII 格式發送 lock 命令
                _send_cmd_ascii(f"lock_my({1 if lock else 0})")
                state.movement_lock_state["lock_y"] = lock
        else:
            with state.movement_lock_state["lock"]:
                if state.movement_lock_state["lock_y"] != lock:
                    _send_cmd_ascii(f"lock_my({1 if lock else 0})")
                    state.movement_lock_state["lock_y"] = lock
    except Exception as e:
        log_print(f"[Mouse Lock] Error in lock_movement_y: {e}")


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS:
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
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS:
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
    if not state.is_connected or state.active_backend not in ACTIVE_BACKENDS:
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
