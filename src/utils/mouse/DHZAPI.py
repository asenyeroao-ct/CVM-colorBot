from src.utils.debug_logger import log_print
import re
import socket
import threading
import time

from . import state

_POLL_INTERVAL_SEC = 0.03
_SOCKET_TIMEOUT_SEC = 0.02
_RETRY_COUNT = 1

_BUTTON_QUERY_BY_IDX = {
    0: "isdown_left()",
    1: "isdown_right()",
    2: "isdown_middle()",
    3: "isdown_side1()",
    4: "isdown_side2()",
}


class DHZClient:
    def __init__(self, ip: str, port: int, random_shift: int):
        self.addr = (str(ip), int(port))
        self.random_shift = int(random_shift) % 26
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(_SOCKET_TIMEOUT_SEC)
        self.lock = threading.Lock()

    @staticmethod
    def _caesar_shift(text: str, shift: int) -> str:
        shift = int(shift) % 26
        out = []
        for ch in str(text):
            code = ord(ch)
            if 65 <= code <= 90:
                out.append(chr((code - 65 + shift) % 26 + 65))
            elif 97 <= code <= 122:
                out.append(chr((code - 97 + shift) % 26 + 97))
            else:
                out.append(ch)
        return "".join(out)

    @staticmethod
    def _parse_bool(text: str):
        normalized = str(text).strip().lower()
        if normalized in ("1", "true", "yes", "down", "pressed"):
            return True
        if normalized in ("0", "false", "no", "up", "released"):
            return False

        for token in re.split(r"[^a-z0-9]+", normalized):
            if token in ("1", "true", "yes", "down", "pressed"):
                return True
            if token in ("0", "false", "no", "up", "released"):
                return False
        return None

    def send(self, command: str, expect_response: bool = False, timeout: float = None, retries: int = None):
        timeout_value = _SOCKET_TIMEOUT_SEC if timeout is None else max(0.001, float(timeout))
        retry_count = _RETRY_COUNT if retries is None else max(0, int(retries))
        payload = self._caesar_shift(str(command), self.random_shift).encode("ascii", "ignore")
        last_error = "no response"

        for _ in range(retry_count + 1):
            try:
                with self.lock:
                    self.socket.settimeout(timeout_value)
                    self.socket.sendto(payload, self.addr)
                    if not expect_response:
                        return True, ""
                    data, _ = self.socket.recvfrom(1024)
                raw = data.decode("ascii", errors="ignore")
                decrypted = self._caesar_shift(raw, -self.random_shift)
                return True, (decrypted or raw)
            except socket.timeout:
                last_error = f"timeout after {timeout_value:.3f}s"
            except OSError as e:
                last_error = str(e)
                break
            except Exception as e:
                last_error = str(e)
                break

        return False, last_error

    def query_bool(self, command: str, timeout: float = None, retries: int = None):
        ok, response = self.send(command, expect_response=True, timeout=timeout, retries=retries)
        if not ok:
            return False, False, response

        candidates = [
            str(response),
            self._caesar_shift(str(response), self.random_shift),
            self._caesar_shift(str(response), -self.random_shift),
        ]
        for text in candidates:
            value = self._parse_bool(text)
            if value is not None:
                return True, value, ""
        return False, False, f"invalid bool response: {response!r}"

    def close(self):
        try:
            self.socket.close()
        except Exception:
            pass


def _start_listener_thread():
    if state.listener_thread is None or not state.listener_thread.is_alive():
        log_print("[INFO] Starting DHZ listener thread...")
        state.listener_thread = threading.Thread(target=_listener_loop, daemon=True)
        state.listener_thread.start()
        log_print("[INFO] DHZ listener thread started.")


def _listener_loop():
    state.reset_button_states()

    while state.is_connected and state.active_backend == "DHZ":
        client = state.dhz_client
        if client is None:
            time.sleep(_POLL_INTERVAL_SEC)
            continue

        updates = {}
        for idx, cmd in _BUTTON_QUERY_BY_IDX.items():
            ok, pressed, _ = client.query_bool(cmd, timeout=_SOCKET_TIMEOUT_SEC, retries=0)
            if ok:
                updates[idx] = bool(pressed)

        if not updates:
            time.sleep(_POLL_INTERVAL_SEC)
            continue

        with state.button_states_lock:
            for idx, pressed in updates.items():
                state.button_states[idx] = pressed
        time.sleep(_POLL_INTERVAL_SEC)

    state.reset_button_states()


def connect(ip: str, port: str, random_shift=0):
    state.last_connect_error = ""
    disconnect()
    state.set_connected(False, "DHZ")

    try:
        selected_port = int(str(port).strip())
    except Exception:
        state.last_connect_error = f"Invalid DHZ port: {port!r}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    try:
        selected_shift = int(str(random_shift).strip())
    except Exception:
        state.last_connect_error = f"Invalid DHZ random shift: {random_shift!r}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    selected_ip = str(ip).strip()
    if not selected_ip:
        state.last_connect_error = "Invalid DHZ IP: empty"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    try:
        client = DHZClient(selected_ip, selected_port, selected_shift)
    except Exception as e:
        state.last_connect_error = f"DHZ socket init failed: {e}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    ok, _, err = client.query_bool("isdown_left()", timeout=0.1, retries=0)
    if not ok:
        client.close()
        state.last_connect_error = f"DHZ probe failed: {err}"
        log_print(f"[ERROR] {state.last_connect_error}")
        return False

    state.dhz_client = client
    state.set_connected(True, "DHZ")
    _start_listener_thread()
    log_print(f"[INFO] Connected to DHZ at {selected_ip}:{selected_port} (RANDOM={selected_shift}).")
    return True


def disconnect():
    state.set_connected(False, "DHZ")
    client = state.dhz_client
    state.dhz_client = None

    if client is not None:
        try:
            client.send("monitor(0)", expect_response=False, timeout=0.02, retries=0)
        except Exception:
            pass
        client.close()

    state.listener_thread = None
    state.mask_applied_idx = None
    state.reset_button_states()


def is_button_pressed(idx: int) -> bool:
    with state.button_states_lock:
        return state.button_states.get(idx, False)


def _send_no_wait(command: str):
    if not state.is_connected or state.active_backend != "DHZ" or state.dhz_client is None:
        return
    ok, err = state.dhz_client.send(command, expect_response=False, timeout=0.02, retries=0)
    if not ok:
        log_print(f"[Mouse-DHZ] command failed: {command} ({err})")


def move(x: float, y: float):
    _send_no_wait(f"move({int(x)},{int(y)})")


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    # DHZ API does not expose a bezier move signature in the current docs.
    move(x, y)


def left(isdown: int):
    _send_no_wait(f"left({1 if isdown else 0})")


def right(isdown: int):
    _send_no_wait(f"right({1 if isdown else 0})")


def middle(isdown: int):
    _send_no_wait(f"middle({1 if isdown else 0})")


def side1(isdown: int):
    _send_no_wait(f"side1({1 if isdown else 0})")


def side2(isdown: int):
    _send_no_wait(f"side2({1 if isdown else 0})")


def wheel(delta: int):
    _send_no_wait(f"wheel({int(delta)})")
