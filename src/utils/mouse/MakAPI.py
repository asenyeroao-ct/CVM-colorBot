"""
MAK_API serial backend.

Binary frames: DE AD | LEN:u16le | CMD | PAYLOAD
Protocol: https://github.com/terrafirma2021/mak-suite/blob/main/protocol/MAK_API.md
Ported from mak_actuator.cpp / mak_actuator.h (independent of km.* ASCII Serial/MakV2).
"""
from src.utils.debug_logger import log_print
import struct
import threading
import time

import serial
from serial.tools import list_ports

from . import state
from .keycodes import to_hid_code

CMD_DEVICE = 0x02
CMD_FIRMWARE_VERSION = 0x04
CMD_BUTTONS = 0x10
CMD_LEFT = 0x11  # LEFT..SIDE2 = 0x11..0x15
CMD_MOVE_MASK = 0x16
CMD_MOVE = 0x18
CMD_LEFT_MASK = 0x1A  # LEFT_MASK..SIDE2_MASK = 0x1A..0x1E
CMD_KEY_DOWN = 0x20
CMD_KEY_UP = 0x21
CMD_KEY_MASK = 0x29
CMD_KEY_KEYS = 0x2B
CMD_INPUT_CHANGE = 0x53

KIND_KEYBOARD = 0x02
STREAM_MOUSE = 1
STREAM_KEYBOARD = 2
REJECTED = 0xFF
MAX_PAYLOAD = 512
BAUD_CANDIDATES = (115200, 1_000_000, 4_000_000)
MAK_VID = 0x1A86
MAK_PIDS = {0x55D3, 0x7523}

_client = None
_client_lock = threading.Lock()
_axis_lock_x = False
_axis_lock_y = False
_axis_lock = threading.Lock()


def _normalize_serial_port_name(port_value: str) -> str:
    raw = str(port_value or "").strip()
    if not raw:
        return ""
    if raw.upper() == "AUTO":
        return ""
    if raw.upper().startswith("COM"):
        return raw.upper()
    if raw.isdigit():
        return f"COM{raw}"
    return raw


def find_mak_ports():
    """CH343 (PID 55D3) / CH340 (PID 7523), VID 1A86 — MAKCU and MAKXD USB-serial bridge."""
    found = []
    for port in list_ports.comports():
        vid = int(getattr(port, "vid", 0) or 0)
        pid = int(getattr(port, "pid", 0) or 0)
        hwid = str(getattr(port, "hwid", "") or "").upper()
        is_mak = (vid == MAK_VID and pid in MAK_PIDS) or (
            "VID_1A86" in hwid and ("PID_55D3" in hwid or "PID_7523" in hwid)
        )
        if is_mak:
            found.append(str(port.device))
    return found


def _i16_le(value: int) -> bytes:
    return struct.pack("<h", int(value))


class _PendingReply:
    def __init__(self, cmd: int):
        self.cmd = int(cmd)
        self.event = threading.Event()
        self.rejected = False
        self.payload = b""


class MakClient:
    def __init__(self):
        self.ser = None
        self.port = ""
        self.baud = 0
        self.kinds = 0
        self.firmware = 0
        self.open = False
        self.mouse_stream = False
        self.keyboard_stream = False
        self._write_lock = threading.Lock()
        self._reply_lock = threading.Lock()
        self._pending = []
        self._rx = bytearray()
        self._stop = threading.Event()
        self._reader = None
        self._mouse_resub = False
        self._keyboard_resub = False
        self._physical_buttons = 0
        self._physical_keys = set()
        self._keys_lock = threading.Lock()
        self._button_mask = [False] * 5
        self._masked_keys = set()

    def start_reader(self):
        self._stop.clear()
        self._reader = threading.Thread(target=self._reader_loop, daemon=True, name="MakAPIReader")
        self._reader.start()

    def close(self):
        self.open = False
        self._stop.set()
        ser = self.ser
        self.ser = None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
        if self._reader is not None and self._reader.is_alive() and threading.current_thread() is not self._reader:
            self._reader.join(timeout=0.6)
        with self._reply_lock:
            for pending in self._pending:
                pending.rejected = True
                pending.event.set()
            self._pending.clear()

    def send_frame(self, cmd: int, payload: bytes = b"") -> bool:
        payload = bytes(payload or b"")
        if len(payload) > MAX_PAYLOAD:
            return False
        frame = bytes([0xDE, 0xAD, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, int(cmd) & 0xFF]) + payload
        with self._write_lock:
            if self.ser is None or not getattr(self.ser, "is_open", False):
                return False
            try:
                self.ser.write(frame)
                self.ser.flush()
                return True
            except Exception as e:
                state.last_connect_error = f"MAK write failed: {e}"
                return False

    def query(self, cmd: int, payload: bytes = b"", timeout_ms: int = 300):
        pending = _PendingReply(cmd)
        with self._reply_lock:
            self._pending.append(pending)
        if not self.send_frame(cmd, payload):
            with self._reply_lock:
                if pending in self._pending:
                    self._pending.remove(pending)
            return None
        if not pending.event.wait(timeout_ms / 1000.0):
            with self._reply_lock:
                if pending in self._pending:
                    self._pending.remove(pending)
            return None
        with self._reply_lock:
            if pending in self._pending:
                self._pending.remove(pending)
        if pending.rejected:
            return None
        return pending.payload

    def _reader_loop(self):
        while not self._stop.is_set():
            if self._mouse_resub:
                self._mouse_resub = False
                self.send_frame(CMD_BUTTONS, bytes([1]))
            if self._keyboard_resub:
                self._keyboard_resub = False
                self.send_frame(CMD_KEY_KEYS, bytes([1]))
            ser = self.ser
            if ser is None or not getattr(ser, "is_open", False):
                time.sleep(0.02)
                continue
            try:
                waiting = ser.in_waiting
                chunk = ser.read(waiting if waiting else 1)
            except Exception as e:
                if not self._stop.is_set():
                    log_print(f"[MakAPI] Serial read failed: {e}")
                    state.last_connect_error = str(e)
                    self.open = False
                break
            if chunk:
                self._consume(chunk)

    def _consume(self, data: bytes):
        self._rx.extend(data)
        offset = 0
        while True:
            marker = offset
            buf = self._rx
            while marker + 1 < len(buf) and not (buf[marker] == 0xDE and buf[marker + 1] == 0xAD):
                marker += 1
            if marker + 1 >= len(buf):
                offset = (len(buf) - 1) if (buf and buf[-1] == 0xDE) else len(buf)
                break
            offset = marker
            if len(buf) - offset < 5:
                break
            payload_len = buf[offset + 2] | (buf[offset + 3] << 8)
            if payload_len == 0 or payload_len > MAX_PAYLOAD:
                offset += 1
                continue
            if len(buf) - offset < 5 + payload_len:
                break
            cmd = buf[offset + 4]
            payload = bytes(buf[offset + 5 : offset + 5 + payload_len])
            self._dispatch(cmd, payload)
            offset += 5 + payload_len
        if offset:
            del self._rx[:offset]

    def _dispatch(self, cmd: int, payload: bytes):
        if cmd == CMD_INPUT_CHANGE:
            self._handle_input_change(payload)
            return
        rejected = len(payload) == 1 and payload[0] == REJECTED and cmd != CMD_DEVICE
        matched = False
        with self._reply_lock:
            for pending in self._pending:
                if pending.cmd == cmd and not pending.event.is_set():
                    pending.rejected = rejected
                    pending.payload = payload
                    pending.event.set()
                    matched = True
                    break
        if not matched and rejected:
            state.last_connect_error = f"MAK device rejected command 0x{cmd:02X}"

    def _handle_input_change(self, payload: bytes):
        if len(payload) < 3:
            return
        kind = payload[0]
        ident = payload[1]
        overflow = len(payload) == 3 and ident == 0xFF and payload[2] == 0xFF
        if kind == STREAM_MOUSE:
            if overflow:
                self._physical_buttons = 0
                self._mouse_resub = True
                state.reset_button_states()
                return
            if ident >= 5:
                return
            pressed = payload[2] != 0
            bit = 1 << ident
            if pressed:
                self._physical_buttons |= bit
            else:
                self._physical_buttons &= ~bit
            with state.button_states_lock:
                state.button_states[int(ident)] = pressed
            return
        if kind == STREAM_KEYBOARD:
            with self._keys_lock:
                if overflow:
                    self._physical_keys.clear()
                    self._keyboard_resub = True
                    return
                if payload[2]:
                    self._physical_keys.add(int(ident))
                else:
                    self._physical_keys.discard(int(ident))


def _open_serial(port: str, baud: int):
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = int(baud)
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = 0.02
    ser.write_timeout = 0.25
    ser.dsrdtr = False
    ser.rtscts = False
    ser.xonxoff = False
    ser.open()
    try:
        ser.dtr = False
        ser.rts = False
    except Exception:
        pass
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    return ser


def _try_connect_candidate(port: str, baud: int):
    client = MakClient()
    try:
        client.ser = _open_serial(port, baud)
    except Exception as e:
        state.last_connect_error = f"cannot open {port}: {e}"
        return None
    client.start_reader()
    time.sleep(0.18)
    reply = client.query(CMD_DEVICE, b"", timeout_ms=750)
    if reply is None or len(reply) != 1:
        state.last_connect_error = f"no DEVICE reply from {port} @ {baud}"
        client.close()
        time.sleep(0.12)
        return None
    client.port = port
    client.baud = int(baud)
    client.kinds = int(reply[0])
    client.open = True
    return client


def _initialize_session(client: MakClient):
    reply = client.query(CMD_FIRMWARE_VERSION, b"", timeout_ms=300)
    if reply is not None and len(reply) == 4:
        client.firmware = int.from_bytes(reply, "little")

    state.reset_button_states()
    client._physical_buttons = 0
    mouse_ok = client.send_frame(CMD_BUTTONS, bytes([1]))
    confirm = client.query(CMD_BUTTONS, b"", timeout_ms=300) if mouse_ok else None
    client.mouse_stream = bool(confirm is not None and len(confirm) == 1 and confirm[0] == 1)
    if not client.mouse_stream:
        log_print("[MakAPI] Physical mouse button stream unavailable.")

    if client.kinds & KIND_KEYBOARD:
        with client._keys_lock:
            client._physical_keys.clear()
        key_ok = client.send_frame(CMD_KEY_KEYS, bytes([1]))
        confirm = client.query(CMD_KEY_KEYS, b"", timeout_ms=300) if key_ok else None
        client.keyboard_stream = bool(confirm is not None and len(confirm) == 1 and confirm[0] == 1)

    _release_everything(client)


def _release_everything(client: MakClient):
    for slot in range(5):
        client.send_frame(CMD_LEFT + slot, bytes([0]))
    client.send_frame(CMD_MOVE_MASK, bytes([0, 0, 0, 0]))
    for slot in range(5):
        client.send_frame(CMD_LEFT_MASK + slot, bytes([0]))
        client._button_mask[slot] = False
    keys = set(client._masked_keys)
    client._masked_keys.clear()
    for hid in keys:
        client.send_frame(CMD_KEY_MASK, bytes([int(hid) & 0xFF, 0]))


def connect(port=None, baud=None) -> bool:
    global _client, _axis_lock_x, _axis_lock_y
    disconnect()
    state.last_connect_error = ""

    selected_port = _normalize_serial_port_name(port)
    try:
        selected_baud = int(baud) if baud not in (None, "", "0", 0) else 0
    except Exception:
        selected_baud = 0

    candidates = [selected_port] if selected_port else find_mak_ports()
    if not candidates:
        state.last_connect_error = "MAK auto-detect found no CH343/CH340 (VID 1A86) serial port"
        state.set_connected(False, "MakAPI")
        log_print(f"[MakAPI] {state.last_connect_error}")
        return False

    bauds = [selected_baud] if selected_baud else list(BAUD_CANDIDATES)
    client = None
    for candidate in candidates:
        for rate in bauds:
            client = _try_connect_candidate(candidate, rate)
            if client is not None:
                break
        if client is not None:
            break

    if client is None:
        target = candidates[0] if len(candidates) == 1 else "every detected port"
        baud_text = f" @ {selected_baud}" if selected_baud else " at every supported baud"
        detail = str(state.last_connect_error or "").strip()
        suffix = f": {detail}" if detail else ""
        state.last_connect_error = f"MAK device identity probe failed on {target}{baud_text}{suffix}"
        state.set_connected(False, "MakAPI")
        log_print(f"[MakAPI] {state.last_connect_error}")
        return False

    _initialize_session(client)
    with _client_lock:
        _client = client
    with _axis_lock:
        _axis_lock_x = False
        _axis_lock_y = False
    state.set_connected(True, "MakAPI")
    state.listener_thread = client._reader
    log_print(
        f"[MakAPI] Connected {client.port} @ {client.baud}, "
        f"kinds=0x{client.kinds:02X}, firmware={client.firmware}"
    )
    return True


def disconnect():
    global _client
    with _client_lock:
        client = _client
        _client = None
    if client is not None:
        if client.open:
            try:
                _release_everything(client)
                client.send_frame(CMD_BUTTONS, bytes([0]))
                if client.keyboard_stream:
                    client.send_frame(CMD_KEY_KEYS, bytes([0]))
            except Exception:
                pass
        client.close()
    if state.active_backend == "MakAPI":
        state.set_connected(False, "MakAPI")
    state.reset_button_states()
    state.mask_applied_idx = None


def _require_client():
    if not state.is_connected or state.active_backend != "MakAPI":
        return None
    with _client_lock:
        client = _client
    if client is None or not client.open:
        return None
    return client


def is_button_pressed(idx: int) -> bool:
    try:
        idx = int(idx)
    except Exception:
        return False
    with state.button_states_lock:
        return bool(state.button_states.get(idx, False))


def is_key_pressed(key) -> bool:
    client = _require_client()
    hid = to_hid_code(key)
    if client is None or hid is None or not client.keyboard_stream:
        return False
    with client._keys_lock:
        return int(hid) in client._physical_keys


def move(x: float, y: float):
    client = _require_client()
    if client is None:
        return
    dx = int(round(float(x)))
    dy = int(round(float(y)))
    while dx != 0 or dy != 0:
        step_x = max(-32768, min(32767, dx))
        step_y = max(-32768, min(32767, dy))
        if not client.send_frame(CMD_MOVE, _i16_le(step_x) + _i16_le(step_y)):
            log_print("[MakAPI] move write failed")
            return
        dx -= step_x
        dy -= step_y


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    del ctrl_x, ctrl_y
    steps = max(1, int(segments or 1))
    if steps <= 1:
        move(x, y)
        return
    sent_x = 0.0
    sent_y = 0.0
    total_x = float(x)
    total_y = float(y)
    for i in range(1, steps + 1):
        target_x = total_x * i / steps
        target_y = total_y * i / steps
        move(target_x - sent_x, target_y - sent_y)
        sent_x = target_x
        sent_y = target_y


def left(isdown: int):
    client = _require_client()
    if client is None:
        return
    client.send_frame(CMD_LEFT, bytes([1 if int(isdown) else 0]))


def key_down(key):
    client = _require_client()
    hid = to_hid_code(key)
    if client is None or hid is None:
        return
    client.send_frame(CMD_KEY_DOWN, bytes([int(hid) & 0xFF]))


def key_up(key):
    client = _require_client()
    hid = to_hid_code(key)
    if client is None or hid is None:
        return
    client.send_frame(CMD_KEY_UP, bytes([int(hid) & 0xFF]))


def key_press(key):
    key_down(key)
    time.sleep(0.012)
    key_up(key)


def lock_button_idx(idx: int):
    client = _require_client()
    if client is None:
        return
    try:
        slot = int(idx)
    except Exception:
        return
    if slot < 0 or slot > 4:
        return
    if client.send_frame(CMD_LEFT_MASK + slot, bytes([1])):
        client._button_mask[slot] = True


def unlock_button_idx(idx: int):
    client = _require_client()
    if client is None:
        return
    try:
        slot = int(idx)
    except Exception:
        return
    if slot < 0 or slot > 4:
        return
    if client.send_frame(CMD_LEFT_MASK + slot, bytes([0])):
        client._button_mask[slot] = False


def unlock_all_locks():
    client = _require_client()
    if client is None:
        return
    for slot in range(5):
        client.send_frame(CMD_LEFT_MASK + slot, bytes([0]))
        client._button_mask[slot] = False
    client.send_frame(CMD_MOVE_MASK, bytes([0, 0, 0, 0]))
    with _axis_lock:
        global _axis_lock_x, _axis_lock_y
        _axis_lock_x = False
        _axis_lock_y = False


def _apply_move_mask(mask_x: bool, mask_y: bool):
    global _axis_lock_x, _axis_lock_y
    client = _require_client()
    if client is None:
        return
    x = 1 if mask_x else 0
    y = 1 if mask_y else 0
    if client.send_frame(CMD_MOVE_MASK, bytes([x, x, y, y])):
        with _axis_lock:
            _axis_lock_x = bool(mask_x)
            _axis_lock_y = bool(mask_y)


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    del skip_lock
    with _axis_lock:
        mask_y = _axis_lock_y
    _apply_move_mask(bool(lock), mask_y)


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    del skip_lock
    with _axis_lock:
        mask_x = _axis_lock_x
    _apply_move_mask(mask_x, bool(lock))


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    del is_main
    _apply_move_mask(bool(lock_x), bool(lock_y))


def tick_movement_lock_manager():
    return


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    if not state.is_connected or state.active_backend != "MakAPI":
        return
    try:
        from src.utils.config import config

        if not bool(getattr(config, "button_mask_enabled", False)):
            if state.mask_applied_idx is not None:
                unlock_button_idx(state.mask_applied_idx)
                state.mask_applied_idx = None
            return
    except Exception:
        return

    if aimbot_running:
        if state.mask_applied_idx != selected_idx:
            if state.mask_applied_idx is not None:
                unlock_button_idx(state.mask_applied_idx)
            lock_button_idx(selected_idx)
            state.mask_applied_idx = selected_idx
    elif state.mask_applied_idx is not None:
        unlock_button_idx(state.mask_applied_idx)
        state.mask_applied_idx = None


def mask_key(key):
    client = _require_client()
    hid = to_hid_code(key)
    if client is None or hid is None:
        return
    if client.send_frame(CMD_KEY_MASK, bytes([int(hid) & 0xFF, 1])):
        client._masked_keys.add(int(hid))


def unmask_key(key):
    client = _require_client()
    hid = to_hid_code(key)
    if client is None or hid is None:
        return
    if client.send_frame(CMD_KEY_MASK, bytes([int(hid) & 0xFF, 0])):
        client._masked_keys.discard(int(hid))


def unmask_all_keys():
    client = _require_client()
    if client is None:
        return
    keys = set(client._masked_keys)
    client._masked_keys.clear()
    for hid in keys:
        client.send_frame(CMD_KEY_MASK, bytes([int(hid) & 0xFF, 0]))


def test_move():
    move(100, 100)


def connection_info():
    with _client_lock:
        client = _client
    if client is None:
        return {}
    return {
        "port": client.port,
        "baud": client.baud,
        "kinds": client.kinds,
        "firmware": client.firmware,
        "mouse_stream": client.mouse_stream,
        "keyboard_stream": client.keyboard_stream,
    }
