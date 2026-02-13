from src.utils.debug_logger import log_print
import threading
import time

import serial
from serial.tools import list_ports

from . import state

DEFAULT_BAUD_RATES = [115200, 9600]
PORT_HINTS = [
    "ARDUINO",
    "CH340",
    "CH341",
    "USB SERIAL",
    "CP210",
]


def _score_port(port):
    text = f"{port.device} {port.description} {port.hwid}".upper()
    score = 0
    for hint in PORT_HINTS:
        if hint in text:
            score += 1
    return score


def find_candidate_ports():
    ports = list(list_ports.comports())
    ports.sort(key=_score_port, reverse=True)
    return [p.device for p in ports]


def _safe_close_port():
    try:
        if state.makcu and state.makcu.is_open:
            state.makcu.close()
    except Exception:
        pass
    state.makcu = None


def _normalize_button_idx(value):
    try:
        raw_idx = int(str(value).strip())
    except Exception:
        return None

    if raw_idx == 0:
        return raw_idx
    if 1 <= raw_idx <= 5:
        return raw_idx - 1
    return None


def _handle_incoming_line(line: str):
    if not line:
        return

    parts = str(line).strip().split(":", 1)
    if len(parts) != 2:
        return

    event = parts[0].strip().upper()
    idx = _normalize_button_idx(parts[1])
    if idx is None or event not in ("BD", "BU"):
        return

    with state.button_states_lock:
        state.button_states[idx] = event == "BD"


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting Arduino listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] Arduino listener thread started.")


def _listener_loop():
    state.reset_button_states()

    while state.is_connected and state.active_backend == "Arduino":
        try:
            if state.makcu is None:
                time.sleep(0.01)
                continue

            raw = state.makcu.readline()
            if not raw:
                continue

            line = raw.decode("ascii", errors="ignore").strip()
            _handle_incoming_line(line)
        except serial.SerialException as e:
            log_print(f"[ERROR] Arduino listener exception: {e}")
            break
        except Exception as e:
            log_print(f"[WARN] Arduino listener error: {e}")
            time.sleep(0.005)

    state.reset_button_states()


def connect(port: str = None, baud: int = None):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "Arduino")

    selected_port = str(port).strip() if port is not None else ""
    if selected_port:
        ports = [selected_port]
    else:
        ports = find_candidate_ports()

    if not ports:
        state.last_connect_error = "No COM port available for Arduino."
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    baud_list = []
    if baud is not None:
        try:
            baud_list.append(int(baud))
        except Exception:
            pass
    for default_baud in DEFAULT_BAUD_RATES:
        if default_baud not in baud_list:
            baud_list.append(default_baud)

    for port_name in ports:
        for baud_value in baud_list:
            ser = None
            try:
                log_print(f"[INFO] Probing Arduino {port_name} @ {baud_value}...")
                ser = serial.Serial(port_name, int(baud_value), timeout=0.05, write_timeout=0.2)
                time.sleep(0.1)
                ser.reset_input_buffer()

                state.makcu = ser
                state.set_connected(True, "Arduino")
                _start_listener_thread()
                log_print(f"[INFO] Connected to Arduino on {port_name} at {baud_value} baud.")
                return True
            except Exception as e:
                log_print(f"[WARN] Arduino failed on {port_name}@{baud_value}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
                _safe_close_port()

    state.last_connect_error = (
        f"Could not connect to Arduino on manual port: {selected_port}."
        if selected_port
        else "Could not connect to Arduino on any detected COM port."
    )
    log_print(f"[ERROR] {state.last_connect_error}")
    return False


def disconnect():
    state.set_connected(False, "Arduino")
    _safe_close_port()
    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def is_button_pressed(idx: int) -> bool:
    with state.button_states_lock:
        return state.button_states.get(idx, False)


def _send_line(payload: str):
    if not state.is_connected or state.active_backend != "Arduino" or state.makcu is None:
        return
    try:
        with state.makcu_lock:
            state.makcu.write(f"{payload}\n".encode("ascii", "ignore"))
            state.makcu.flush()
    except Exception as e:
        log_print(f"[Mouse-Arduino] command failed: {payload} ({e})")


def _split_axis(delta: int):
    remaining = int(delta)
    chunks = []

    while remaining > 127:
        chunks.append(127)
        remaining -= 127

    while remaining < -127:
        chunks.append(-127)
        remaining += 127

    chunks.append(remaining)
    return chunks


def _iter_segmented_moves(dx: int, dy: int):
    x_chunks = _split_axis(dx)
    y_chunks = _split_axis(dy)
    chunk_count = max(len(x_chunks), len(y_chunks))

    for i in range(chunk_count):
        yield (
            x_chunks[i] if i < len(x_chunks) else 0,
            y_chunks[i] if i < len(y_chunks) else 0,
        )


def move(x: float, y: float):
    dx, dy = int(x), int(y)
    use_16_bit = True
    try:
        from src.utils.config import config

        use_16_bit = bool(getattr(config, "arduino_16_bit_mouse", True))
    except Exception:
        pass

    if use_16_bit:
        _send_line(f"m{dx},{dy}")
        return

    for chunk_x, chunk_y in _iter_segmented_moves(dx, dy):
        if chunk_x == 0 and chunk_y == 0:
            continue
        _send_line(f"m{chunk_x},{chunk_y}")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    move(x, y)


def left(isdown: int):
    _send_line("p" if isdown else "r")


def click():
    _send_line("c")


def test_move():
    move(100, 100)
