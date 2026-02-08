import threading
import serial
from serial.tools import list_ports
import time
from src.utils.debug_logger import log_click, log_press, log_release

makcu = None
makcu_lock = threading.Lock()
button_states = {i: False for i in range(5)}
button_states_lock = threading.Lock()
is_connected = False
last_value = 0
_listener_thread = None  # Global listener thread reference

SUPPORTED_DEVICES = [
    ("1A86:55D3", "MAKCU"),
    ("1A86:5523", "CH343"),
    ("1A86:7523", "CH340"),
    ("1A86:5740", "CH347"),
    ("10C4:EA60", "CP2102"),
]
BAUD_RATES = [4_000_000, 2_000_000, 115_200]
BAUD_CHANGE_COMMAND = bytearray([0xDE, 0xAD, 0x05, 0x00, 0xA5, 0x00, 0x09, 0x3D, 0x00])

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
        print(f"[WARN] km_version_ok: {e}")
        return False

def connect_to_makcu():
    global makcu, is_connected
    ports = find_com_ports()
    if not ports:
        print("[ERROR] No supported serial devices found.")
        return False

    for port_name, dev_name in ports:
        if dev_name == "MAKCU":
            for baud in BAUD_RATES:
                print(f"[INFO] Probing MAKCU {port_name} @ {baud} with km.version()...")
                ser = None
                try:
                    ser = serial.Serial(port_name, baud, timeout=0.3)
                    time.sleep(0.1)
                    if km_version_ok(ser):
                        print(f"[INFO] MAKCU responded at {baud}, using it.")
                        ser.close()
                        time.sleep(0.1)
                        makcu = serial.Serial(port_name, baud, timeout=0.1)
                        with makcu_lock:
                            makcu.write(b"km.buttons(1)\r")
                            makcu.flush()
                        is_connected = True
                        # Start listener thread if not already running
                        _start_listener_thread()
                        return True
                    ser.close()
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[WARN] Failed MAKCU@{baud}: {e}")
                    if ser:
                        try:
                            ser.close()
                        except:
                            pass
                        time.sleep(0.1)
                    if makcu and makcu.is_open:
                        makcu.close()
                    makcu = None
                    is_connected = False
        else:
            for baud in BAUD_RATES:
                print(f"[INFO] Trying {dev_name} {port_name} @ {baud} ...")
                ser = None
                try:
                    ser = serial.Serial(port_name, baud, timeout=0.1)
                    with makcu_lock:
                        ser.write(b"km.buttons(1)\r")
                        ser.flush()
                    ser.close()
                    time.sleep(0.1)
                    makcu = serial.Serial(port_name, baud, timeout=0.1)
                    is_connected = True
                    print(f"[INFO] Connected to {dev_name} on {port_name} at {baud} baud.")
                    # Start listener thread if not already running
                    _start_listener_thread()
                    return True
                except Exception as e:
                    print(f"[WARN] Failed {dev_name}@{baud}: {e}")
                    if ser:
                        try:
                            ser.close()
                        except:
                            pass
                        time.sleep(0.1)
                    if makcu and makcu.is_open:
                        makcu.close()
                    makcu = None
                    is_connected = False

    print("[ERROR] Could not connect to any supported device.")
    return False


def count_bits(n: int) -> int:
    return bin(n).count("1")

def _start_listener_thread():
    """Start the listener thread if not already running"""
    global _listener_thread
    if _listener_thread is None or not _listener_thread.is_alive():
        print("[INFO] Starting MAKCU listener thread...")
        _listener_thread = threading.Thread(target=listen_makcu, daemon=True)
        _listener_thread.start()
        # Also update Mouse class reference if it exists
        try:
            Mouse._listener = _listener_thread
        except NameError:
            pass  # Mouse class not defined yet, that's okay
        print("[INFO] MAKCU listener thread started.")

def listen_makcu():
    global last_value
    # start from a clean state
    last_value = 0
    with button_states_lock:
        for i in range(5):
            button_states[i] = False

    while is_connected:
        try:
            b = makcu.read(1)  # blocking read (uses port timeout)
            if not b:
                continue

            v = b[0]

            # Ignore echoed ASCII (including CR/LF). Only 0..31 are valid masks.
            if v in (0x0A, 0x0D) or v > 31:
                continue

            # v is a 5-bit mask (bit0..bit4). Update only changed bits.
            changed = last_value ^ v
            if changed:
                with button_states_lock:
                    for i in range(5):
                        m = 1 << i
                        if changed & m:
                            button_states[i] = bool(v & m)
                last_value = v

        except serial.SerialException as e:
            print(f"[ERROR] Listener serial exception: {e}")
            break
        except Exception as e:
            # swallow transient errors but keep running
            print(f"[WARN] Listener error: {e}")
            time.sleep(0.001)

    # ensure clean state on exit
    with button_states_lock:
        for i in range(5):
            button_states[i] = False
    last_value = 0

def is_button_pressed(idx: int) -> bool:
    with button_states_lock:
        return button_states.get(idx, False)

def switch_to_4m():
    """
    Manually switch MAKCU device to 4M baud rate.
    Requires device to be connected at 115200 baud first.
    
    Returns:
        bool: True if switch successful, False otherwise
    """
    global makcu, is_connected
    
    if not is_connected or not makcu or not makcu.is_open:
        print("[ERROR] Device not connected. Please connect first.")
        return False
    
    # Get current port name
    port_name = makcu.port
    
    try:
        # Check if currently at 115200
        current_baud = makcu.baudrate
        if current_baud == 4_000_000:
            print("[INFO] Device already at 4M baud rate.")
            return True
        
        if current_baud != 115_200:
            print(f"[WARN] Current baud rate is {current_baud}, not 115200. Cannot switch to 4M.")
            return False
        
        print("[INFO] Sending 4M handshake command...")
        # Send baud change command
        with makcu_lock:
            makcu.write(BAUD_CHANGE_COMMAND)
            makcu.flush()
        
        # Close current connection
        makcu.close()
        time.sleep(0.15)
        
        # Try to open at 4M
        print("[INFO] Attempting to connect at 4M baud rate...")
        ser4m = serial.Serial(port_name, 4_000_000, timeout=0.3)
        time.sleep(0.1)
        
        if km_version_ok(ser4m):
            print(f"[INFO] Successfully switched to 4M on {port_name}.")
            ser4m.close()
            time.sleep(0.1)
            makcu = serial.Serial(port_name, 4_000_000, timeout=0.1)
            with makcu_lock:
                makcu.write(b"km.buttons(1)\r")
                makcu.flush()
            is_connected = True
            # Restart listener thread after reconnection
            _start_listener_thread()
            return True
        else:
            print("[WARN] 4M handshake failed, reconnecting at 115200...")
            ser4m.close()
            time.sleep(0.1)
            makcu = serial.Serial(port_name, 115_200, timeout=0.1)
            with makcu_lock:
                makcu.write(b"km.buttons(1)\r")
                makcu.flush()
            is_connected = True
            # Restart listener thread after reconnection
            _start_listener_thread()
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to switch to 4M: {e}")
        # Try to reconnect at original baud rate
        try:
            if makcu and makcu.is_open:
                makcu.close()
            time.sleep(0.1)
            makcu = serial.Serial(port_name, 115_200, timeout=0.1)
            with makcu_lock:
                makcu.write(b"km.buttons(1)\r")
                makcu.flush()
            is_connected = True
            # Restart listener thread after reconnection
            _start_listener_thread()
        except:
            is_connected = False
            makcu = None
        return False

def test_move():
    if is_connected:
        with makcu_lock:
            makcu.write(b"km.move(100,100)\r")
            makcu.flush()

# --------------------------------------------------------------------
# Button Lock / Masking helpers
# --------------------------------------------------------------------

# Index mapping: 0=L, 1=R, 2=M, 3=S4, 4=S5
_LOCK_CMD_BY_IDX = {
    0: "lock_ml",
    1: "lock_mr",
    2: "lock_mm",
    3: "lock_ms1",
    4: "lock_ms2",
}

# State tracked by mask manager (so we only send lock/unlock when needed)
_mask_applied_idx = None

# --------------------------------------------------------------------
# Mouse Movement Lock helpers (for blocking physical mouse input)
# --------------------------------------------------------------------

# Movement lock state tracking
_movement_lock_state = {
    "lock_x": False,  # X 軸鎖定狀態
    "lock_y": False,  # Y 軸鎖定狀態
    "main_aimbot_locked": False,  # Main Aimbot 是否正在鎖定
    "sec_aimbot_locked": False,  # Sec Aimbot 是否正在鎖定
    "last_main_move_time": 0.0,  # Main Aimbot 最後移動時間
    "last_sec_move_time": 0.0,  # Sec Aimbot 最後移動時間
    "lock": threading.Lock()  # 線程鎖
}

# 鎖定超時時間（秒）- 如果 aimbot 超過這個時間沒有移動，自動解鎖
_MOVEMENT_LOCK_TIMEOUT = 0.1

def _send_cmd_no_wait(cmd: str):
    """Send 'km.<cmd>\\r' without waiting for response (listener ignores ASCII)."""
    if not is_connected:
        return
    with makcu_lock:
        makcu.write(f"km.{cmd}\r".encode("ascii", "ignore"))
        makcu.flush()

def lock_button_idx(idx: int):
    """Lock a single button by index (0..4)."""
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(1)")

def unlock_button_idx(idx: int):
    """Unlock a single button by index (0..4)."""
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(0)")

def unlock_all_locks():
    """Best-effort unlock of all lockable buttons."""
    for i in range(5):
        unlock_button_idx(i)

def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    """鎖定或解鎖 X 軸物理鼠標移動
    
    Args:
        lock: 是否鎖定
        skip_lock: 如果為 True，跳過獲取鎖（用於已經持有鎖的情況）
    """
    global _movement_lock_state
    if not is_connected:
        return
    
    try:
        if skip_lock:
            # 已經持有鎖，直接執行
            if _movement_lock_state["lock_x"] != lock:
                _send_cmd_no_wait(f"lock_mx({1 if lock else 0})")
                _movement_lock_state["lock_x"] = lock
        else:
            with _movement_lock_state["lock"]:
                if _movement_lock_state["lock_x"] != lock:
                    _send_cmd_no_wait(f"lock_mx({1 if lock else 0})")
                    _movement_lock_state["lock_x"] = lock
    except Exception as e:
        print(f"[Mouse Lock] Error in lock_movement_x: {e}")

def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    """鎖定或解鎖 Y 軸物理鼠標移動
    
    Args:
        lock: 是否鎖定
        skip_lock: 如果為 True，跳過獲取鎖（用於已經持有鎖的情況）
    """
    global _movement_lock_state
    if not is_connected:
        return
    
    try:
        if skip_lock:
            # 已經持有鎖，直接執行
            if _movement_lock_state["lock_y"] != lock:
                _send_cmd_no_wait(f"lock_my({1 if lock else 0})")
                _movement_lock_state["lock_y"] = lock
        else:
            with _movement_lock_state["lock"]:
                if _movement_lock_state["lock_y"] != lock:
                    _send_cmd_no_wait(f"lock_my({1 if lock else 0})")
                    _movement_lock_state["lock_y"] = lock
    except Exception as e:
        print(f"[Mouse Lock] Error in lock_movement_y: {e}")

def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    """
    更新移動鎖定狀態（僅更新狀態，實際鎖定由 tick_movement_lock_manager 處理）
    
    Args:
        lock_x: 是否鎖定 X 軸
        lock_y: 是否鎖定 Y 軸
        is_main: 是否為 Main Aimbot（False 為 Sec Aimbot）
    """
    global _movement_lock_state
    import time
    
    if not is_connected:
        return
    
    try:
        current_time = time.time()
        
        # 使用超時鎖定，避免死鎖
        lock_acquired = False
        try:
            lock_acquired = _movement_lock_state["lock"].acquire(timeout=0.01)
            if not lock_acquired:
                # 無法獲取鎖，跳過本次更新
                return
            
            if is_main:
                _movement_lock_state["main_aimbot_locked"] = lock_x or lock_y
                if lock_x or lock_y:
                    _movement_lock_state["last_main_move_time"] = current_time
            else:
                _movement_lock_state["sec_aimbot_locked"] = lock_x or lock_y
                if lock_x or lock_y:
                    _movement_lock_state["last_sec_move_time"] = current_time
        finally:
            if lock_acquired:
                _movement_lock_state["lock"].release()
    except Exception as e:
        # 捕獲所有異常，避免崩潰
        print(f"[Mouse Lock] Error in update_movement_lock: {e}")

def tick_movement_lock_manager():
    """
    移動鎖定管理器 tick 函數
    檢查 aimbot 是否還在移動，如果超時則自動解鎖
    """
    global _movement_lock_state
    import time
    
    if not is_connected:
        return
    
    try:
        current_time = time.time()
        
        # 使用超時鎖定，避免死鎖
        lock_acquired = False
        try:
            lock_acquired = _movement_lock_state["lock"].acquire(timeout=0.01)
            if not lock_acquired:
                # 無法獲取鎖，跳過本次 tick
                return
            
            # 檢查 Main Aimbot 鎖定超時
            if _movement_lock_state["main_aimbot_locked"]:
                if current_time - _movement_lock_state["last_main_move_time"] > _MOVEMENT_LOCK_TIMEOUT:
                    _movement_lock_state["main_aimbot_locked"] = False
            
            # 檢查 Sec Aimbot 鎖定超時
            if _movement_lock_state["sec_aimbot_locked"]:
                if current_time - _movement_lock_state["last_sec_move_time"] > _MOVEMENT_LOCK_TIMEOUT:
                    _movement_lock_state["sec_aimbot_locked"] = False
            
            # 檢查是否需要解鎖
            # 從 config 讀取設置
            try:
                from src.utils.config import config
                main_lock_x = getattr(config, "mouse_lock_main_x", False)
                main_lock_y = getattr(config, "mouse_lock_main_y", False)
                sec_lock_x = getattr(config, "mouse_lock_sec_x", False)
                sec_lock_y = getattr(config, "mouse_lock_sec_y", False)
            except Exception as e:
                # 配置讀取失敗，使用默認值
                main_lock_x = False
                main_lock_y = False
                sec_lock_x = False
                sec_lock_y = False
            
            # 計算最終鎖定狀態（main 或 sec 任一鎖定即鎖定）
            should_lock_x = (
                (main_lock_x and _movement_lock_state["main_aimbot_locked"]) or
                (sec_lock_x and _movement_lock_state["sec_aimbot_locked"])
            )
            should_lock_y = (
                (main_lock_y and _movement_lock_state["main_aimbot_locked"]) or
                (sec_lock_y and _movement_lock_state["sec_aimbot_locked"])
            )
            
            # 更新實際鎖定狀態（已經持有鎖，使用 skip_lock=True）
            try:
                if _movement_lock_state["lock_x"] != should_lock_x:
                    lock_movement_x(should_lock_x, skip_lock=True)
                if _movement_lock_state["lock_y"] != should_lock_y:
                    lock_movement_y(should_lock_y, skip_lock=True)
            except Exception as e:
                print(f"[Mouse Lock] Error updating lock state: {e}")
        finally:
            if lock_acquired:
                _movement_lock_state["lock"].release()
    except Exception as e:
        # 捕獲所有異常，避免崩潰
        print(f"[Mouse Lock] Error in tick_movement_lock_manager: {e}")
        import traceback
        traceback.print_exc()

def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    """Manage button locks based on selected_idx and aimbot_running state."""
    
    global _mask_applied_idx

    if not is_connected:
        _mask_applied_idx = None
        return

    # clamp invalid index
    if not isinstance(selected_idx, int) or not (0 <= selected_idx <= 4):
        selected_idx = None

    if not aimbot_running:
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
            _mask_applied_idx = None
        return

    # running: apply lock for selected_idx
    if selected_idx is None:
        # nothing selected -> make sure nothing is locked
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
            _mask_applied_idx = None
        return

    if _mask_applied_idx != selected_idx:
        # switch lock to a new button
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
        lock_button_idx(selected_idx)
        _mask_applied_idx = selected_idx

class Mouse:
    _instance = None
    _listener = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_inited"):
            if not connect_to_makcu():
                print("[ERROR] Mouse init failed to connect.")
            else:
                # Listener thread will be started by connect_to_makcu()
                # Sync the class variable with global reference
                global _listener_thread
                Mouse._listener = _listener_thread
            self._inited = True

    def move(self, x: float, y: float):
        """
        Move mouse relative to current position.
        
        Args:
            x: Relative movement in X direction (positive = right, negative = left)
            y: Relative movement in Y direction (positive = down, negative = up)
        """
        if not is_connected:
            return
        dx, dy = int(x), int(y)
        with makcu_lock:
            # Send relative movement command to MAKCU device
            makcu.write(f"km.move({dx},{dy})\r".encode())
            makcu.flush()

    def move_bezier(self, x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
        if not is_connected:
            return
        with makcu_lock:
            cmd = f"km.move({int(x)},{int(y)},{int(segments)},{int(ctrl_x)},{int(ctrl_y)})\r"
            makcu.write(cmd.encode())
            makcu.flush()

    def click(self):
        """Click left mouse button (press and release immediately)"""
        if not is_connected:
            return
        with makcu_lock:
            makcu.write(b"km.left(1)\r")
            makcu.flush()
            makcu.write(b"km.left(0)\r")
            makcu.flush()
        # 記錄點擊日誌
        log_click("Mouse.click()")
    
    def press(self):
        """Press left mouse button (without releasing)"""
        if not is_connected:
            return
        with makcu_lock:
            makcu.write(b"km.left(1)\r")
            makcu.flush()
        # 記錄按下日誌
        log_press("Mouse.press()")
    
    def release(self):
        """Release left mouse button"""
        if not is_connected:
            return
        with makcu_lock:
            makcu.write(b"km.left(0)\r")
            makcu.flush()
        # 記錄釋放日誌
        log_release("Mouse.release()")

    @staticmethod
    def mask_manager_tick(selected_idx: int, aimbot_running: bool):
        """Static wrapper so callers can do: Mouse.mask_manager_tick(idx, running)."""
        mask_manager_tick(selected_idx, aimbot_running)

    @staticmethod
    def cleanup():
        global is_connected, makcu, _mask_applied_idx, _listener_thread, _movement_lock_state
        # Always release any locks before closing port
        try:
            unlock_all_locks()
        except Exception:
            pass
        _mask_applied_idx = None
        
        # 解鎖所有移動鎖定
        try:
            with _movement_lock_state["lock"]:
                _movement_lock_state["lock_x"] = False
                _movement_lock_state["lock_y"] = False
                _movement_lock_state["main_aimbot_locked"] = False
                _movement_lock_state["sec_aimbot_locked"] = False
            if is_connected:
                lock_movement_x(False)
                lock_movement_y(False)
        except Exception:
            pass

        is_connected = False
        if makcu and makcu.is_open:
            makcu.close()
        Mouse._instance = None
        Mouse._listener = None
        _listener_thread = None
        print("[INFO] Mouse serial cleaned up.")

