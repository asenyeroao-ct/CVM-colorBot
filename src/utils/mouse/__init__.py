
from src.utils.debug_logger import log_click, log_press, log_release, log_print

from . import ArduinoAPI, DHZAPI, MakV2, NetAPI, SendInputAPI, SerialAPI, state

is_connected = False


def _sync_public_state():
    global is_connected
    is_connected = bool(state.is_connected)


def _normalize_api_name(mode: str) -> str:
    mode_norm = str(mode).strip().lower()
    if mode_norm == "net":
        return "Net"
    if mode_norm == "dhz":
        return "DHZ"
    if mode_norm in ("makv2", "mak_v2", "mak-v2"):
        return "MakV2"
    if mode_norm == "arduino":
        return "Arduino"
    if mode_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
        return "SendInput"
    return "Serial"


def _get_selected_backend_from_config() -> str:
    try:
        from src.utils.config import config

        return _normalize_api_name(getattr(config, "mouse_api", "Serial"))
    except Exception:
        return "Serial"


def _get_serial_settings(mode=None, port=None):
    cfg_mode, cfg_port = "Auto", ""
    try:
        from src.utils.config import config

        cfg_mode = str(getattr(config, "serial_port_mode", cfg_mode))
        cfg_port = str(getattr(config, "serial_port", cfg_port))
    except Exception:
        pass

    selected_mode = str(mode if mode is not None else cfg_mode).strip().lower()
    if selected_mode not in ("auto", "manual"):
        selected_mode = "auto"
    selected_port = str(port if port is not None else cfg_port).strip()
    return ("Manual" if selected_mode == "manual" else "Auto"), selected_port


def _get_net_settings(ip=None, port=None, uuid=None, mac=None):
    cfg_ip, cfg_port, cfg_uuid = "192.168.2.188", "6234", ""
    try:
        from src.utils.config import config

        cfg_ip = str(getattr(config, "net_ip", cfg_ip))
        cfg_port = str(getattr(config, "net_port", cfg_port))
        cfg_uuid = str(getattr(config, "net_uuid", getattr(config, "net_mac", cfg_uuid)))
    except Exception:
        pass

    selected_uuid = uuid if uuid is not None else mac
    return (
        str(ip if ip is not None else cfg_ip),
        str(port if port is not None else cfg_port),
        str(selected_uuid if selected_uuid is not None else cfg_uuid),
    )


def _get_makv2_settings(port=None, baud=None):
    cfg_port, cfg_baud = "", 4_000_000
    try:
        from src.utils.config import config

        cfg_port = str(getattr(config, "makv2_port", cfg_port))
        cfg_baud = int(getattr(config, "makv2_baud", cfg_baud))
    except Exception:
        pass

    selected_port = str(port if port is not None else cfg_port).strip()
    selected_baud = int(baud if baud is not None else cfg_baud)
    return selected_port, selected_baud


def _get_dhz_settings(ip=None, port=None, random_shift=None):
    cfg_ip, cfg_port, cfg_random = "192.168.2.188", "5000", 0
    try:
        from src.utils.config import config

        cfg_ip = str(getattr(config, "dhz_ip", cfg_ip))
        cfg_port = str(getattr(config, "dhz_port", cfg_port))
        cfg_random = int(getattr(config, "dhz_random", cfg_random))
    except Exception:
        pass

    selected_ip = str(ip if ip is not None else cfg_ip).strip()
    selected_port = str(port if port is not None else cfg_port).strip()
    selected_random = int(random_shift if random_shift is not None else cfg_random)
    return selected_ip, selected_port, selected_random


def _get_arduino_settings(port=None, baud=None):
    cfg_port, cfg_baud = "", 115200
    try:
        from src.utils.config import config

        cfg_port = str(getattr(config, "arduino_port", cfg_port))
        cfg_baud = int(getattr(config, "arduino_baud", cfg_baud))
    except Exception:
        pass

    selected_port = str(port if port is not None else cfg_port).strip()
    selected_baud = int(baud if baud is not None else cfg_baud)
    return selected_port, selected_baud


def _disconnect_all_backends():
    SerialAPI.disconnect()
    ArduinoAPI.disconnect()
    SendInputAPI.disconnect()
    NetAPI.disconnect()
    DHZAPI.disconnect()
    MakV2.disconnect()


def disconnect_all(selected_mode: str = None):
    _disconnect_all_backends()
    backend = _normalize_api_name(selected_mode) if selected_mode is not None else _get_selected_backend_from_config()
    state.set_connected(False, backend)
    _sync_public_state()


def get_active_backend() -> str:
    return state.active_backend


def get_last_connect_error() -> str:
    return state.last_connect_error


def get_expected_kmnet_dll_name() -> str:
    return NetAPI.get_expected_kmnet_dll_name()


def connect_to_serial(mode=None, port=None) -> bool:
    selected_mode, selected_port = _get_serial_settings(mode=mode, port=port)
    if selected_mode == "Manual" and not selected_port:
        state.last_connect_error = "Serial manual mode requires COM port."
        state.set_connected(False, "Serial")
        _sync_public_state()
        return False

    ok = SerialAPI.connect(port=selected_port if selected_mode == "Manual" else None)
    _sync_public_state()
    return ok


def connect_to_net(ip=None, port=None, uuid=None, mac=None) -> bool:
    ip, port, uuid = _get_net_settings(ip=ip, port=port, uuid=uuid, mac=mac)
    ok = NetAPI.connect(ip=ip, port=port, uuid=uuid)
    _sync_public_state()
    return ok


def connect_to_makv2(port=None, baud=None) -> bool:
    port, baud = _get_makv2_settings(port=port, baud=baud)
    ok = MakV2.connect(port=port if port else None, baud=baud)
    _sync_public_state()
    return ok


def connect_to_dhz(ip=None, port=None, random_shift=None) -> bool:
    ip, port, random_shift = _get_dhz_settings(ip=ip, port=port, random_shift=random_shift)
    ok = DHZAPI.connect(ip=ip, port=port, random_shift=random_shift)
    _sync_public_state()
    return ok


def connect_to_arduino(port=None, baud=None) -> bool:
    port, baud = _get_arduino_settings(port=port, baud=baud)
    ok = ArduinoAPI.connect(port=port if port else None, baud=baud)
    _sync_public_state()
    return ok


def connect_to_sendinput() -> bool:
    ok = SendInputAPI.connect()
    _sync_public_state()
    return ok


def connect_to_makcu():
    """
    Backward-compatible entry point.
    Connect to backend selected by config.mouse_api.
    """
    mode = _get_selected_backend_from_config()
    if mode == "Net":
        return connect_to_net()
    if mode == "DHZ":
        return connect_to_dhz()
    if mode == "MakV2":
        return connect_to_makv2()
    if mode == "Arduino":
        return connect_to_arduino()
    if mode == "SendInput":
        return connect_to_sendinput()
    return connect_to_serial()


def switch_backend(
    mode: str,
    serial_port_mode=None,
    serial_port=None,
    arduino_port=None,
    arduino_baud=None,
    ip=None,
    port=None,
    uuid=None,
    mac=None,
    makv2_port=None,
    makv2_baud=None,
    dhz_ip=None,
    dhz_port=None,
    dhz_random=None,
):
    target_mode = _normalize_api_name(mode)
    if uuid is None and mac is not None:
        uuid = mac

    try:
        from src.utils.config import config

        config.mouse_api = target_mode
        if serial_port_mode is not None:
            normalized_serial_mode = str(serial_port_mode).strip().lower()
            config.serial_port_mode = "Manual" if normalized_serial_mode == "manual" else "Auto"
        if serial_port is not None:
            config.serial_port = str(serial_port)
        if arduino_port is not None:
            config.arduino_port = str(arduino_port)
        if arduino_baud is not None:
            config.arduino_baud = int(arduino_baud)
        if ip is not None:
            config.net_ip = str(ip)
        if port is not None and target_mode == "Net":
            config.net_port = str(port)
        if uuid is not None:
            config.net_uuid = str(uuid)
            config.net_mac = str(uuid)
        if makv2_port is not None:
            config.makv2_port = str(makv2_port)
        if makv2_baud is not None:
            config.makv2_baud = int(makv2_baud)
        if dhz_ip is not None:
            config.dhz_ip = str(dhz_ip)
        if dhz_port is not None:
            config.dhz_port = str(dhz_port)
        if dhz_random is not None:
            config.dhz_random = int(dhz_random)
    except Exception:
        pass

    state.set_connected(False)
    _disconnect_all_backends()

    if target_mode == "Net":
        ok = connect_to_net(ip=ip, port=port, uuid=uuid, mac=mac)
        return ok, (None if ok else (state.last_connect_error or "Net backend connect failed"))

    if target_mode == "MakV2":
        ok = connect_to_makv2(port=makv2_port, baud=makv2_baud)
        return ok, (None if ok else (state.last_connect_error or "MakV2 backend connect failed"))

    if target_mode == "DHZ":
        ok = connect_to_dhz(ip=dhz_ip, port=dhz_port, random_shift=dhz_random)
        return ok, (None if ok else (state.last_connect_error or "DHZ backend connect failed"))

    if target_mode == "Arduino":
        ok = connect_to_arduino(port=arduino_port, baud=arduino_baud)
        return ok, (None if ok else (state.last_connect_error or "Arduino backend connect failed"))

    if target_mode == "SendInput":
        ok = connect_to_sendinput()
        return ok, (None if ok else (state.last_connect_error or "SendInput backend connect failed"))

    ok = connect_to_serial(mode=serial_port_mode, port=serial_port)
    return ok, (None if ok else (state.last_connect_error or "Serial backend connect failed"))


def count_bits(n: int) -> int:
    return bin(n).count("1")


def is_button_pressed(idx: int) -> bool:
    if not state.is_connected:
        _sync_public_state()
        return False

    if state.active_backend == "Net":
        return NetAPI.is_button_pressed(idx)
    if state.active_backend == "DHZ":
        return DHZAPI.is_button_pressed(idx)
    if state.active_backend == "MakV2":
        return MakV2.is_button_pressed(idx)
    if state.active_backend == "Arduino":
        return ArduinoAPI.is_button_pressed(idx)
    if state.active_backend == "SendInput":
        return SendInputAPI.is_button_pressed(idx)
    return SerialAPI.is_button_pressed(idx)


def switch_to_4m():
    result = SerialAPI.switch_to_4m()
    _sync_public_state()
    return result


def test_move():
    if state.active_backend == "Net":
        NetAPI.move(100, 100)
    elif state.active_backend == "DHZ":
        DHZAPI.move(100, 100)
    elif state.active_backend == "MakV2":
        MakV2.move(100, 100)
    elif state.active_backend == "Arduino":
        ArduinoAPI.move(100, 100)
    elif state.active_backend == "SendInput":
        SendInputAPI.move(100, 100)
    else:
        SerialAPI.test_move()


def lock_button_idx(idx: int):
    if not state.is_connected:
        return
    if state.active_backend == "MakV2":
        MakV2.lock_button_idx(idx)
    elif state.active_backend == "Serial":
        SerialAPI.lock_button_idx(idx)


def unlock_button_idx(idx: int):
    if not state.is_connected:
        return
    if state.active_backend == "MakV2":
        MakV2.unlock_button_idx(idx)
    elif state.active_backend == "Serial":
        SerialAPI.unlock_button_idx(idx)


def unlock_all_locks():
    if state.active_backend == "MakV2":
        MakV2.unlock_all_locks()
    elif state.active_backend == "Serial":
        SerialAPI.unlock_all_locks()


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    if state.active_backend == "MakV2":
        MakV2.lock_movement_x(lock=lock, skip_lock=skip_lock)
    elif state.active_backend == "Serial":
        SerialAPI.lock_movement_x(lock=lock, skip_lock=skip_lock)


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    if state.active_backend == "MakV2":
        MakV2.lock_movement_y(lock=lock, skip_lock=skip_lock)
    elif state.active_backend == "Serial":
        SerialAPI.lock_movement_y(lock=lock, skip_lock=skip_lock)


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    if state.active_backend == "MakV2":
        MakV2.update_movement_lock(lock_x=lock_x, lock_y=lock_y, is_main=is_main)
    elif state.active_backend == "Serial":
        SerialAPI.update_movement_lock(lock_x=lock_x, lock_y=lock_y, is_main=is_main)


def tick_movement_lock_manager():
    if state.active_backend == "MakV2":
        MakV2.tick_movement_lock_manager()
    elif state.active_backend == "Serial":
        SerialAPI.tick_movement_lock_manager()


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    if state.active_backend == "MakV2":
        MakV2.mask_manager_tick(selected_idx=selected_idx, aimbot_running=aimbot_running)
    elif state.active_backend == "Serial":
        SerialAPI.mask_manager_tick(selected_idx=selected_idx, aimbot_running=aimbot_running)


class Mouse:
    _instance = None
    _listener = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_inited"):
            return
        auto_connect = False
        try:
            from src.utils.config import config

            auto_connect = bool(getattr(config, "auto_connect_mouse_api", False))
        except Exception:
            auto_connect = False

        if auto_connect:
            if not connect_to_makcu():
                log_print(f"[ERROR] Mouse init failed to connect. reason={get_last_connect_error()}")
            else:
                Mouse._listener = state.listener_thread
        else:
            disconnect_all()
            log_print("[INFO] Mouse auto-connect disabled. Waiting for manual connect.")
        self._inited = True

    def move(self, x: float, y: float):
        if not state.is_connected:
            return
        if state.active_backend == "Net":
            NetAPI.move(x, y)
        elif state.active_backend == "DHZ":
            DHZAPI.move(x, y)
        elif state.active_backend == "MakV2":
            MakV2.move(x, y)
        elif state.active_backend == "Arduino":
            ArduinoAPI.move(x, y)
        elif state.active_backend == "SendInput":
            SendInputAPI.move(x, y)
        else:
            SerialAPI.move(x, y)

    def move_bezier(self, x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
        if not state.is_connected:
            return
        if state.active_backend == "Net":
            NetAPI.move_bezier(x, y, segments, ctrl_x, ctrl_y)
        elif state.active_backend == "DHZ":
            DHZAPI.move_bezier(x, y, segments, ctrl_x, ctrl_y)
        elif state.active_backend == "MakV2":
            MakV2.move_bezier(x, y, segments, ctrl_x, ctrl_y)
        elif state.active_backend == "Arduino":
            ArduinoAPI.move_bezier(x, y, segments, ctrl_x, ctrl_y)
        elif state.active_backend == "SendInput":
            SendInputAPI.move_bezier(x, y, segments, ctrl_x, ctrl_y)
        else:
            SerialAPI.move_bezier(x, y, segments, ctrl_x, ctrl_y)

    def click(self):
        if not state.is_connected:
            return
        if state.active_backend == "Net":
            NetAPI.left(1)
            NetAPI.left(0)
        elif state.active_backend == "DHZ":
            DHZAPI.left(1)
            DHZAPI.left(0)
        elif state.active_backend == "MakV2":
            MakV2.left(1)
            MakV2.left(0)
        elif state.active_backend == "Arduino":
            ArduinoAPI.left(1)
            ArduinoAPI.left(0)
        elif state.active_backend == "SendInput":
            SendInputAPI.left(1)
            SendInputAPI.left(0)
        else:
            SerialAPI.left(1)
            SerialAPI.left(0)
        log_click("Mouse.click()")

    def press(self):
        if not state.is_connected:
            return
        if state.active_backend == "Net":
            NetAPI.left(1)
        elif state.active_backend == "DHZ":
            DHZAPI.left(1)
        elif state.active_backend == "MakV2":
            MakV2.left(1)
        elif state.active_backend == "Arduino":
            ArduinoAPI.left(1)
        elif state.active_backend == "SendInput":
            SendInputAPI.left(1)
        else:
            SerialAPI.left(1)
        log_press("Mouse.press()")

    def release(self):
        if not state.is_connected:
            return
        if state.active_backend == "Net":
            NetAPI.left(0)
        elif state.active_backend == "DHZ":
            DHZAPI.left(0)
        elif state.active_backend == "MakV2":
            MakV2.left(0)
        elif state.active_backend == "Arduino":
            ArduinoAPI.left(0)
        elif state.active_backend == "SendInput":
            SendInputAPI.left(0)
        else:
            SerialAPI.left(0)
        log_release("Mouse.release()")

    @staticmethod
    def mask_manager_tick(selected_idx: int, aimbot_running: bool):
        mask_manager_tick(selected_idx, aimbot_running)

    @staticmethod
    def cleanup():
        try:
            unlock_all_locks()
        except Exception:
            pass

        try:
            with state.movement_lock_state["lock"]:
                state.movement_lock_state["lock_x"] = False
                state.movement_lock_state["lock_y"] = False
                state.movement_lock_state["main_aimbot_locked"] = False
                state.movement_lock_state["sec_aimbot_locked"] = False
            if state.is_connected and state.active_backend in ("Serial", "MakV2"):
                lock_movement_x(False)
                lock_movement_y(False)
        except Exception:
            pass

        state.set_connected(False)
        _disconnect_all_backends()
        _sync_public_state()

        Mouse._instance = None
        Mouse._listener = None
        state.listener_thread = None
        log_print("[INFO] Mouse backend cleaned up.")


_sync_public_state()
