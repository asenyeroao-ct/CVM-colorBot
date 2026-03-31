"""
Ferrum Keyboard and Mouse API Implementation

根據 Ferrum_API.md 文檔實現的 Ferrum 設備控制模組。
支持滑鼠移動、按鈕控制、鍵盤按鍵控制、狀態讀取和按鍵屏蔽功能。

Ferrum 設備通過串口通訊，支持 KM style commands。
參考：https://ferrumllc.github.io/software_api.html
"""
from src.utils.debug_logger import log_print
import threading
import time

import serial
from serial.tools import list_ports

from . import state
from .keycodes import to_hid_code

# Ferrum 按鈕代碼映射（根據 Ferrum_API.md）
# 1=左鍵, 2=右鍵, 4=中鍵, 8=側鍵1, 16=側鍵2
_FERRUM_BUTTON_BY_IDX = {
    0: 1,   # 左鍵
    1: 2,   # 右鍵
    2: 4,   # 中鍵
    3: 8,   # 側鍵1
    4: 16,  # 側鍵2
}

# 反向映射：Ferrum 按鈕代碼 -> 索引
_FERRUM_IDX_BY_BUTTON = {v: k for k, v in _FERRUM_BUTTON_BY_IDX.items()}

# Ferrum 設備連接對象（串口）
_ferrum_device = None
_ferrum_lock = threading.Lock()
_ferrum_keyboard_device = None
_ferrum_keyboard_lock = threading.Lock()

# 串口配置
DEFAULT_BAUD_RATE = 115200
SUPPORTED_BAUD_RATES = [115200, 9600, 38400, 57600]

# 按鈕狀態緩存
_button_states_cache = {i: False for i in range(5)}
_button_states_lock = threading.Lock()

# 鍵盤狀態緩存（如果支持）
_key_states_cache = {}
_key_states_lock = threading.Lock()


def _resolve_device_and_lock(role: str = "mouse"):
    if str(role).strip().lower() == "keyboard":
        return _ferrum_keyboard_device, _ferrum_keyboard_lock
    return _ferrum_device, _ferrum_lock


def _is_role_connected(role: str = "mouse") -> bool:
    if str(role).strip().lower() == "keyboard":
        return bool(getattr(state, "keyboard_is_connected", False) and getattr(state, "keyboard_active_backend", "") == "Ferrum")
    return bool(state.is_connected and state.active_backend == "Ferrum")


def _set_role_connected(role: str, connected: bool):
    if str(role).strip().lower() == "keyboard":
        state.set_keyboard_connected(bool(connected), "Ferrum")
    else:
        state.set_connected(bool(connected), "Ferrum")


def _set_role_error(role: str, message: str):
    if str(role).strip().lower() == "keyboard":
        state.keyboard_last_connect_error = str(message or "")
    else:
        state.last_connect_error = str(message or "")


def _send_cmd_no_wait(cmd: str, role: str = "mouse"):
    """
    通過串口發送命令（不等待響應）。
    
    Args:
        cmd: 命令字符串（不包含換行符，如果沒有 km. 前綴會自動添加）
    """
    device, device_lock = _resolve_device_and_lock(role)
    if not _is_role_connected(role) or device is None:
        return
    
    try:
        # 確保命令以 km. 開頭（Ferrum API 格式）
        if not cmd.startswith("km."):
            cmd = f"km.{cmd}"
        
        with device_lock:
            if device and device.is_open:
                command = f"{cmd}\r".encode("ascii", "ignore")
                device.write(command)
                device.flush()
    except Exception as e:
        log_print(f"[Ferrum] Send command failed: {cmd} - {e}")


def _send_cmd_with_response(cmd: str, timeout: float = 0.5, role: str = "mouse"):
    """
    通過串口發送命令並等待響應。
    
    Args:
        cmd: 命令字符串（不包含換行符）
        timeout: 超時時間（秒）
        
    Returns:
        str: 響應字符串，失敗返回 None
    """
    device, device_lock = _resolve_device_and_lock(role)
    if not _is_role_connected(role) or device is None:
        return None
    
    try:
        # 只在發送時使用鎖，讀取響應時釋放鎖以避免死鎖
        with device_lock:
            if not (device and device.is_open):
                return None
            
            device.reset_input_buffer()
            command = f"{cmd}\r".encode("ascii", "ignore")
            device.write(command)
            device.flush()
        
        # 在鎖外等待響應，避免阻塞監聽線程
        time.sleep(0.1)
        resp = b""
        start = time.time()
        while time.time() - start < timeout:
            # 使用短時間鎖來檢查和讀取數據
            with device_lock:
                if not (device and device.is_open):
                    return None
                if device.in_waiting:
                    resp += device.read(device.in_waiting)
            
            # 檢查是否收到完整響應（Ferrum 設備會回顯命令，然後返回結果）
            if resp:
                resp_str = resp.decode("ascii", errors="ignore")
                # 檢查是否包含命令回顯和響應（通常以 >>> 結尾）
                if b">>>" in resp or (b"\r" in resp and b"\n" in resp and len(resp) > len(cmd) + 5):
                    break
            time.sleep(0.01)
        
        if resp:
            resp_str = resp.decode("ascii", errors="ignore").strip()
            # 過濾掉命令回顯，只保留響應內容
            if cmd in resp_str:
                # 移除命令回顯部分
                resp_str = resp_str.replace(cmd, "").strip()
            return resp_str
        return None
    except Exception as e:
        log_print(f"[Ferrum] Send command with response failed: {cmd} - {e}")
        return None


def _start_listener_thread():
    """啟動按鈕狀態監聽線程（如果設備支持）"""
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting Ferrum listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] Ferrum listener thread started.")


def _listener_loop():
    """按鈕狀態監聽循環（通過串口讀取按鈕狀態）"""
    state.reset_button_states()
    
    while state.is_connected and state.active_backend == "Ferrum":
        try:
            if _ferrum_device is None or not _ferrum_device.is_open:
                time.sleep(0.01)
                continue
            
            # 讀取串口數據（Ferrum 設備可能主動發送按鈕狀態）
            # 使用短時間鎖來讀取，避免與命令發送衝突
            data = None
            with _ferrum_lock:
                if _ferrum_device and _ferrum_device.is_open and _ferrum_device.in_waiting:
                    try:
                        # 只讀取少量數據，避免讀取命令響應
                        available = min(_ferrum_device.in_waiting, 64)
                        if available > 0:
                            data = _ferrum_device.read(available)
                    except Exception:
                        pass
            
            # 在鎖外處理數據，避免長時間持有鎖
            if data and len(data) > 0:
                # 過濾掉文本響應（命令回顯、提示符等），只處理二進制按鈕狀態
                # Ferrum 設備的按鈕狀態通常是單字節且小於 32
                for byte in data:
                    v = byte
                    # 只處理可能是按鈕狀態的字節（小於 32，不是換行符）
                    if v < 32 and v not in (0x0A, 0x0D, 0x20):
                        # 可能是按鈕狀態字節
                        with state.button_states_lock:
                            for i in range(5):
                                m = 1 << i
                                state.button_states[i] = bool(v & m)
            
            time.sleep(0.01)  # 10ms 輪詢間隔
        except serial.SerialException as e:
            log_print(f"[ERROR] Ferrum listener serial exception: {e}")
            break
        except Exception as e:
            log_print(f"[WARN] Ferrum listener error: {e}")
            time.sleep(0.001)
    
    state.reset_button_states()


# Ferrum 設備支持的串口轉換器（與 Serial API 相同）
FERRUM_SUPPORTED_DEVICES = [
    ("1A86:55D3", "MAKCU"),
    ("1A86:5523", "CH343"),
    ("1A86:7523", "CH340"),  # CH340 常用於 Ferrum 設備
    ("1A86:5740", "CH347"),
    ("10C4:EA60", "CP2102"),
]


def find_ferrum_ports():
    """查找可能的 Ferrum 設備串口（優先顯示支持的設備）"""
    found = []
    for port in list_ports.comports():
        hwid = port.hwid.upper()
        desc = port.description.upper()
        device_name = "Unknown"
        
        # 檢查是否為支持的設備
        for vidpid, name in FERRUM_SUPPORTED_DEVICES:
            if vidpid in hwid or name.upper() in desc:
                device_name = name
                break
        
        found.append((port.device, device_name))
    
    # 優先排序：支持的設備在前
    def sort_key(item):
        port_name, dev_name = item
        for vidpid, name in FERRUM_SUPPORTED_DEVICES:
            if dev_name == name:
                return (0, port_name)  # 支持的設備優先
        return (1, port_name)  # 其他設備在後
    
    found.sort(key=sort_key)
    return found


def _test_ferrum_device(ser: serial.Serial, timeout: float = 0.5):
    """
    測試串口設備是否為 Ferrum 設備。
    
    使用獨立的測試連接發送 km.version() 命令來識別設備。
    響應應包含 "kmbox: Ferrum" 或 "Ferrum"。
    測試完成後會清空所有響應數據，避免影響後續連接。
    
    Args:
        ser: 已打開的串口對象（測試連接，測試完成後會關閉）
        timeout: 讀取響應的超時時間（秒）
        
    Returns:
        tuple[bool, str]: (是否為 Ferrum 設備, 響應內容)
    """
    try:
        ser.reset_input_buffer()
        # 發送 km.version() 命令（根據 Ferrum API 文檔）
        test_cmd = "km.version()\r"
        ser.write(test_cmd.encode("ascii", "ignore"))
        ser.flush()
        time.sleep(0.15)  # 等待設備響應
        
        # 讀取響應（Ferrum 設備會回顯命令，然後返回響應）
        resp = b""
        start = time.time()
        last_data_time = start
        found_ferrum = False
        
        # 第一階段：快速讀取，只要識別出是 Ferrum 設備就返回
        while time.time() - start < timeout:
            if ser.in_waiting:
                new_data = ser.read(ser.in_waiting)
                resp += new_data
                last_data_time = time.time()
                
                # 檢查是否包含 Ferrum 標識
                resp_str = resp.decode("ascii", errors="ignore")
                if "Ferrum" in resp_str or "kmbox: Ferrum" in resp_str:
                    found_ferrum = True
                    # 已經識別出是 Ferrum，繼續讀取直到收到提示符或超時
                    if ">>>" in resp_str:
                        # 收到完整響應，可以立即返回
                        break
                elif ">>>" in resp_str:
                    # 收到提示符但沒有 Ferrum 標識，不是 Ferrum 設備
                    break
            elif time.time() - last_data_time > 0.1:
                # 超過 100ms 沒有新數據
                if found_ferrum:
                    # 已經識別出是 Ferrum，即使沒有完整響應也可以返回
                    break
                # 沒有識別出 Ferrum，繼續等待
                last_data_time = time.time()
            time.sleep(0.01)
        
        # 第二階段：如果已經識別出是 Ferrum，繼續讀取直到收到提示符或超時
        if found_ferrum:
            while time.time() - start < timeout + 0.3:  # 額外給 0.3 秒
                if ser.in_waiting:
                    new_data = ser.read(ser.in_waiting)
                    resp += new_data
                    resp_str = resp.decode("ascii", errors="ignore")
                    if ">>>" in resp_str:
                        break
                elif time.time() - last_data_time > 0.15:
                    # 超過 150ms 沒有新數據，認為響應已完整
                    break
                time.sleep(0.01)
        
        # 清空所有殘留數據，確保測試連接不會影響後續使用
        try:
            # 讀取所有剩餘數據
            max_clear_attempts = 10
            for _ in range(max_clear_attempts):
                if ser.in_waiting:
                    ser.read(ser.in_waiting)
                    time.sleep(0.01)
                else:
                    break
            # 清空緩衝區
            ser.reset_input_buffer()
        except Exception:
            pass
        
        resp_str = resp.decode("ascii", errors="ignore").strip()
        
        # 檢查響應是否包含 "Ferrum" 或 "kmbox: Ferrum"
        # 根據文檔：https://ferrumllc.github.io/software_api/km_api/misc/version.html
        if found_ferrum or "Ferrum" in resp_str or "kmbox: Ferrum" in resp_str:
            return True, resp_str
        
        return False, resp_str
    except Exception as e:
        log_print(f"[WARN] Ferrum device test failed: {e}")
        return False, ""


def connect(device_path: str = None, connection_type: str = "auto"):
    """
    連接 Ferrum 設備（通過串口）。
    
    直接嘗試連接串口，不發送測試命令。
    支持 CH340、CH343、CH347、CP2102 等串口轉換器。
    
    Args:
        device_path: 串口路徑（如 "COM3" 或 "/dev/ttyUSB0"）
        connection_type: 連接類型（目前僅支持 "serial"，"auto" 會自動選擇串口）
        
    Returns:
        bool: 連接是否成功
    """
    global _ferrum_device
    
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "Ferrum")
    
    selected_port = str(device_path).strip() if device_path else ""
    
    # 如果沒有指定端口，嘗試自動檢測（優先嘗試支持的設備）
    if not selected_port:
        ports = find_ferrum_ports()
        if not ports:
            state.last_connect_error = "No serial ports found. Please specify a COM port."
            log_print(f"[ERROR] {state.last_connect_error}")
            return False
        
        # 優先嘗試支持的設備（CH340、CP2102 等）
        # 先嘗試支持的設備，再嘗試其他設備
        supported_ports = []
        other_ports = []
        for p in ports:
            port_name, dev_name = p
            is_supported = any(name in dev_name for _, name in FERRUM_SUPPORTED_DEVICES)
            if is_supported:
                supported_ports.append(p)
            else:
                other_ports.append(p)
        sorted_ports = supported_ports + other_ports
        
        # 嘗試所有端口，直到找到可連接的 Ferrum 設備
        for port_name, dev_name in sorted_ports:
            log_print(f"[INFO] Trying Ferrum device on {port_name} ({dev_name})...")
            for baud in SUPPORTED_BAUD_RATES:
                try:
                    # 直接嘗試連接，不發送 km.version() 命令
                    _ferrum_device = serial.Serial(port_name, baud, timeout=0.1)
                    time.sleep(0.1)
                    
                    # 清空緩衝區，確保沒有殘留數據
                    try:
                        _ferrum_device.reset_input_buffer()
                        _ferrum_device.reset_output_buffer()
                        # 讀取並丟棄任何殘留數據
                        if _ferrum_device.in_waiting:
                            _ferrum_device.read(_ferrum_device.in_waiting)
                    except Exception:
                        pass
                    
                    state.set_connected(True, "Ferrum")
                    _start_listener_thread()
                    log_print(f"[INFO] Connected to Ferrum device on {port_name} ({dev_name}) at {baud} baud.")
                    return True
                except Exception as e:
                    log_print(f"[WARN] Failed Ferrum@{port_name}@{baud}: {e}")
                    if _ferrum_device:
                        try:
                            _ferrum_device.close()
                            _ferrum_device = None
                        except Exception:
                            pass
        
        state.last_connect_error = "Could not connect to any Ferrum device on available serial ports."
        log_print(f"[ERROR] {state.last_connect_error}")
        return False
    
    # 如果指定了端口，嘗試連接該端口
    # 嘗試不同的波特率連接
    for baud in SUPPORTED_BAUD_RATES:
        try:
            log_print(f"[INFO] Trying Ferrum device on {selected_port} @ {baud} baud...")
            # 直接嘗試連接，不發送 km.version() 命令
            _ferrum_device = serial.Serial(selected_port, baud, timeout=0.1)
            time.sleep(0.1)
            
            # 清空緩衝區，確保沒有殘留數據
            try:
                _ferrum_device.reset_input_buffer()
                _ferrum_device.reset_output_buffer()
                # 讀取並丟棄任何殘留數據
                if _ferrum_device.in_waiting:
                    _ferrum_device.read(_ferrum_device.in_waiting)
            except Exception:
                pass
            
            state.set_connected(True, "Ferrum")
            _start_listener_thread()
            log_print(f"[INFO] Connected to Ferrum device on {selected_port} at {baud} baud.")
            return True
            
        except serial.SerialException as e:
            log_print(f"[WARN] Failed to connect at {baud} baud: {e}")
            if _ferrum_device:
                try:
                    _ferrum_device.close()
                    _ferrum_device = None
                except Exception:
                    pass
            continue
        except Exception as e:
            log_print(f"[WARN] Connection error at {baud} baud: {e}")
            if _ferrum_device:
                try:
                    _ferrum_device.close()
                    _ferrum_device = None
                except Exception:
                    pass
            continue
    
    if selected_port:
        state.last_connect_error = f"Could not connect to Ferrum device on {selected_port}. Tried baud rates: {SUPPORTED_BAUD_RATES}"
    else:
        state.last_connect_error = "Could not connect to any Ferrum device."
    log_print(f"[ERROR] {state.last_connect_error}")
    _ferrum_device = None
    return False


def disconnect():
    """斷開 Ferrum 設備連接"""
    global _ferrum_device
    
    state.set_connected(False, "Ferrum")
    
    try:
        if _ferrum_device is not None and _ferrum_device.is_open:
            _ferrum_device.close()
    except Exception:
        pass
    
    _ferrum_device = None
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()
    
    with _button_states_lock:
        _button_states_cache.clear()
        for i in range(5):
            _button_states_cache[i] = False


def _connect_role(device_path: str = None, role: str = "mouse"):
    global _ferrum_device, _ferrum_keyboard_device

    role_norm = str(role).strip().lower()
    if role_norm == "keyboard":
        state.keyboard_last_connect_error = ""
        disconnect_keyboard()
        state.set_keyboard_connected(False, "Ferrum")
    else:
        state.last_connect_error = ""
        disconnect()
        state.set_connected(False, "Ferrum")

    selected_port = str(device_path).strip() if device_path else ""
    if not selected_port:
        ports = find_ferrum_ports()
        if not ports:
            message = "No serial ports found. Please specify a COM port."
            if role_norm == "keyboard":
                state.keyboard_last_connect_error = message
            else:
                state.last_connect_error = message
            log_print(f"[ERROR] {message}")
            return False
        supported_ports = []
        other_ports = []
        for p in ports:
            port_name, dev_name = p
            is_supported = any(name in dev_name for _, name in FERRUM_SUPPORTED_DEVICES)
            if is_supported:
                supported_ports.append(p)
            else:
                other_ports.append(p)
        sorted_ports = supported_ports + other_ports
    else:
        sorted_ports = [(selected_port, "MANUAL")]

    for port_name, dev_name in sorted_ports:
        for baud in SUPPORTED_BAUD_RATES:
            candidate = None
            try:
                log_print(f"[INFO] Trying Ferrum {role_norm} on {port_name} ({dev_name}) @ {baud}...")
                candidate = serial.Serial(port_name, baud, timeout=0.1)
                time.sleep(0.1)
                try:
                    candidate.reset_input_buffer()
                    candidate.reset_output_buffer()
                    if candidate.in_waiting:
                        candidate.read(candidate.in_waiting)
                except Exception:
                    pass

                if role_norm == "keyboard":
                    _ferrum_keyboard_device = candidate
                    state.set_keyboard_connected(True, "Ferrum")
                    log_print(f"[INFO] Connected keyboard Ferrum on {port_name} at {baud} baud.")
                else:
                    _ferrum_device = candidate
                    state.set_connected(True, "Ferrum")
                    _start_listener_thread()
                    log_print(f"[INFO] Connected mouse Ferrum on {port_name} at {baud} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] Failed Ferrum {role_norm}@{port_name}@{baud}: {e}")
                if candidate is not None:
                    try:
                        candidate.close()
                    except Exception:
                        pass

    message = (
        f"Could not connect to Ferrum device on {selected_port}. Tried baud rates: {SUPPORTED_BAUD_RATES}"
        if selected_port
        else "Could not connect to any Ferrum device on available serial ports."
    )
    if role_norm == "keyboard":
        state.keyboard_last_connect_error = message
        _ferrum_keyboard_device = None
    else:
        state.last_connect_error = message
        _ferrum_device = None
    log_print(f"[ERROR] {message}")
    return False


def connect(device_path: str = None, connection_type: str = "auto"):
    return _connect_role(device_path=device_path, role="mouse")


def connect_keyboard(device_path: str = None, connection_type: str = "auto"):
    return _connect_role(device_path=device_path, role="keyboard")


def disconnect_keyboard():
    global _ferrum_keyboard_device

    state.set_keyboard_connected(False, "Ferrum")
    try:
        if _ferrum_keyboard_device is not None and _ferrum_keyboard_device.is_open:
            _ferrum_keyboard_device.close()
    except Exception:
        pass
    _ferrum_keyboard_device = None


def is_button_pressed(idx: int) -> bool:
    """
    檢查按鈕是否被按下。
    
    Args:
        idx: 按鈕索引 (0=左鍵, 1=右鍵, 2=中鍵, 3=側鍵1, 4=側鍵2)
        
    Returns:
        bool: 按鈕是否被按下
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return False
    
    # 優先使用緩存
    with _button_states_lock:
        if idx in _button_states_cache:
            return _button_states_cache[idx]
    
    # 如果緩存不可用，直接查詢設備
    button_code = _FERRUM_BUTTON_BY_IDX.get(idx)
    if button_code is None:
        return False
    
    # 通過串口查詢按鈕狀態
    # 注意：頻繁查詢可能影響性能，建議使用監聽線程緩存狀態
    response = _send_cmd_with_response(f"mouse_button_is_pressed({button_code})", timeout=0.1)
    if response:
        # 解析響應（根據實際協議調整）
        is_pressed = "true" in response.lower() or "1" in response
    else:
        # 如果查詢失敗，使用緩存
        with _button_states_lock:
            is_pressed = _button_states_cache.get(idx, False)
    
    with _button_states_lock:
        _button_states_cache[idx] = bool(is_pressed)
        state.button_states[idx] = bool(is_pressed)
    
    return bool(is_pressed)


def is_key_pressed(key) -> bool:
    """
    檢查鍵盤按鍵是否被按下。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
        
    Returns:
        bool: 按鍵是否被按下
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return False
    
    hid_code = to_hid_code(key)
    if hid_code is None:
        return False
    
    # 優先使用緩存
    with _key_states_lock:
        if hid_code in _key_states_cache:
            return _key_states_cache[hid_code]
    
    # 通過串口查詢按鍵狀態
    response = _send_cmd_with_response(f"key_is_pressed({hid_code})", timeout=0.1)
    if response:
        # 解析響應（根據實際協議調整）
        is_pressed = "true" in response.lower() or "1" in response
    else:
        # 如果查詢失敗，使用緩存
        with _key_states_lock:
            is_pressed = _key_states_cache.get(hid_code, False)
    
    with _key_states_lock:
        _key_states_cache[hid_code] = bool(is_pressed)
    
    return bool(is_pressed)


def move(x: float, y: float):
    """
    相對移動滑鼠。
    
    Args:
        x: X 軸相對位移 (-32768 ~ 32767)
        y: Y 軸相對位移 (-32768 ~ 32767)
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    dx = int(x)
    dy = int(y)
    
    # 限制範圍
    dx = max(-32768, min(32767, dx))
    dy = max(-32768, min(32767, dy))
    
    # 發送滑鼠移動命令（Ferrum API 格式：km.mouse_move(x, y)）
    _send_cmd_no_wait(f"mouse_move({dx},{dy})")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    """
    Bezier 曲線移動（如果設備支持，否則回退到普通移動）。
    
    Args:
        x: X 軸目標位移
        y: Y 軸目標位移
        segments: 分段數
        ctrl_x: 控制點 X
        ctrl_y: 控制點 Y
    """
    # Ferrum API 可能不支持 Bezier，回退到普通移動
    move(x, y)


def left(isdown: int):
    """
    按下或釋放左鍵。
    
    Args:
        isdown: 1=按下, 0=釋放
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    button_code = 1  # 左鍵
    if isdown:
        _send_cmd_no_wait(f"mouse_button_press({button_code})")
    else:
        _send_cmd_no_wait(f"mouse_button_release({button_code})")


def right(isdown: int):
    """
    按下或釋放右鍵。
    
    Args:
        isdown: 1=按下, 0=釋放
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    button_code = 2  # 右鍵
    if isdown:
        _send_cmd_no_wait(f"mouse_button_press({button_code})")
    else:
        _send_cmd_no_wait(f"mouse_button_release({button_code})")


def middle(isdown: int):
    """
    按下或釋放中鍵。
    
    Args:
        isdown: 1=按下, 0=釋放
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    button_code = 4  # 中鍵
    if isdown:
        _send_cmd_no_wait(f"mouse_button_press({button_code})")
    else:
        _send_cmd_no_wait(f"mouse_button_release({button_code})")


def _resolve_hid_key_code(key):
    """解析按鍵為 HID Code"""
    key_code = to_hid_code(key)
    if key_code is None:
        return None
    try:
        return int(key_code)
    except Exception:
        return None


def key_down(key):
    """
    按下鍵盤按鍵。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    
    _send_cmd_no_wait(f"key_press({hid_code})")


def key_up(key):
    """
    釋放鍵盤按鍵。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    
    _send_cmd_no_wait(f"key_release({hid_code})")


def key_press(key):
    """
    點擊鍵盤按鍵（按下後立即釋放）。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    
    # 點擊 = 按下後立即釋放
    _send_cmd_no_wait(f"key_click({hid_code})")


def mask_key(key):
    """
    屏蔽鍵盤按鍵（阻止按鍵發送到輸出電腦）。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    
    _send_cmd_no_wait(f"key_block({hid_code},1)")


def unmask_key(key):
    """
    解除鍵盤按鍵屏蔽。
    
    Args:
        key: 按鍵（HID Code、VK Code 或按鍵名稱）
    """
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    
    _send_cmd_no_wait(f"key_block({hid_code},0)")


def unmask_all_keys():
    """解除所有鍵盤按鍵屏蔽"""
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    
    # Ferrum API 可能沒有批量解除功能，需要逐個解除
    # 這裡只是一個示例，實際實現可能需要維護一個已屏蔽按鍵列表
    log_print("[Ferrum] unmask_all_keys - Not fully implemented")


def test_move():
    """測試滑鼠移動功能"""
    if state.is_connected and state.active_backend == "Ferrum":
        move(100, 100)


def _keyboard_session_ready() -> bool:
    return bool(
        getattr(state, "keyboard_is_connected", False)
        and getattr(state, "keyboard_active_backend", "") == "Ferrum"
        and _ferrum_keyboard_device is not None
    )


def _send_keyboard_cmd_no_wait(cmd: str):
    _send_cmd_no_wait(cmd, role="keyboard")


def _send_keyboard_cmd_with_response(cmd: str, timeout: float = 0.1):
    return _send_cmd_with_response(cmd, timeout=timeout, role="keyboard")


def is_key_pressed(key) -> bool:
    hid_code = to_hid_code(key)
    if hid_code is None:
        return False

    if _keyboard_session_ready():
        response = _send_keyboard_cmd_with_response(f"key_is_pressed({hid_code})", timeout=0.1)
        if response:
            is_pressed = "true" in response.lower() or "1" in response
        else:
            with _key_states_lock:
                is_pressed = _key_states_cache.get(hid_code, False)
        with _key_states_lock:
            _key_states_cache[hid_code] = bool(is_pressed)
        return bool(is_pressed)

    if not state.is_connected or state.active_backend != "Ferrum":
        return False

    response = _send_cmd_with_response(f"key_is_pressed({hid_code})", timeout=0.1)
    return bool(response and ("true" in response.lower() or "1" in response))


def key_down(key):
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    if _keyboard_session_ready():
        _send_keyboard_cmd_no_wait(f"key_press({hid_code})")
        return
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    _send_cmd_no_wait(f"key_press({hid_code})")


def key_up(key):
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    if _keyboard_session_ready():
        _send_keyboard_cmd_no_wait(f"key_release({hid_code})")
        return
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    _send_cmd_no_wait(f"key_release({hid_code})")


def key_press(key):
    hid_code = _resolve_hid_key_code(key)
    if hid_code is None:
        return
    if _keyboard_session_ready():
        _send_keyboard_cmd_no_wait(f"key_click({hid_code})")
        return
    if not state.is_connected or state.active_backend != "Ferrum":
        return
    _send_cmd_no_wait(f"key_click({hid_code})")
