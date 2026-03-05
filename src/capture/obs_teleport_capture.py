"""OBS Teleport capture backend (Python implementation).

此模組提供 Python 版本的 OBS Teleport capture，包含:
- stream discovery (UDP multicast)
- TCP packet receive loop
- JPEG frame decode to OpenCV BGR image
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.utils.debug_logger import log_print


class OBSTeleportConnectionPhase:
    """Connection phase enum-like constants."""

    IDLE = "Idle"
    WAITING_FOR_DISCOVERY = "WaitingForDiscovery"
    WAITING_FOR_ENDPOINT = "WaitingForEndpoint"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    ERROR = "Error"


@dataclass
class OBSTeleportDiscoveredStream:
    key: str
    name: str
    address: str
    port: int
    audio_and_video: bool = False
    version: str = ""


@dataclass
class OBSTeleportConnectionSnapshot:
    phase: str = OBSTeleportConnectionPhase.IDLE
    discovery_running: bool = False
    discovered_count: int = 0
    endpoint: str = ""
    stream_key: str = ""
    stream_name: str = ""
    last_error: str = ""


_DISCOVERY_PORT = 9999
_DISCOVERY_GROUP = "239.255.255.250"
_DISCOVERY_TTL_SECONDS = 5.0

_connection_state_lock = threading.Lock()
_connection_state = OBSTeleportConnectionSnapshot()


def _set_connection_state(
    phase: str,
    endpoint: str = "",
    stream_key: str = "",
    stream_name: str = "",
    last_error: str = "",
) -> None:
    with _connection_state_lock:
        _connection_state.phase = phase
        _connection_state.endpoint = endpoint
        _connection_state.stream_key = stream_key
        _connection_state.stream_name = stream_name
        _connection_state.last_error = last_error


def _clear_connection_state() -> None:
    _set_connection_state(OBSTeleportConnectionPhase.IDLE, "", "", "", "")


class _DiscoveryManager:
    """OBS Teleport discovery manager.

    透過 UDP multicast 持續接收 OBS Teleport announce packets，
    並維護短生命週期的 discovered stream list.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streams: Dict[str, Tuple[OBSTeleportDiscoveredStream, float]] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = threading.Event()

    def ensure_running(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._thread_main, name="OBSTeleportDiscovery", daemon=True)
            self._thread.start()

    def is_running(self) -> bool:
        return self._running.is_set()

    def get_streams(self) -> List[OBSTeleportDiscoveredStream]:
        now = time.monotonic()
        with self._lock:
            self._prune_locked(now)
            streams = [entry[0] for entry in self._streams.values()]
        streams.sort(key=lambda s: (s.name, s.address, s.port))
        return streams

    def resolve(self, key: str) -> Optional[OBSTeleportDiscoveredStream]:
        now = time.monotonic()
        with self._lock:
            self._prune_locked(now)
            value = self._streams.get(key)
            if not value:
                return None
            return value[0]

    def _prune_locked(self, now_mono: float) -> None:
        expired = []
        for key, (_, last_seen) in self._streams.items():
            if (now_mono - last_seen) > _DISCOVERY_TTL_SECONDS:
                expired.append(key)
        for key in expired:
            self._streams.pop(key, None)

    def _thread_main(self) -> None:
        self._running.set()
        try:
            while not self._stop_event.is_set():
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(("", _DISCOVERY_PORT))
                    membership = struct.pack(
                        "4s4s",
                        socket.inet_aton(_DISCOVERY_GROUP),
                        socket.inet_aton("0.0.0.0"),
                    )
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                    sock.settimeout(1.0)
                except OSError as exc:
                    if sock:
                        sock.close()
                    log_print(f"[Teleport] Discovery socket init failed: {exc}")
                    time.sleep(1.0)
                    continue

                while not self._stop_event.is_set():
                    try:
                        payload, addr = sock.recvfrom(2048)
                    except socket.timeout:
                        with self._lock:
                            self._prune_locked(time.monotonic())
                        continue
                    except OSError:
                        break

                    try:
                        json_payload = payload.decode("utf-8", errors="ignore")
                        packet = json.loads(json_payload)
                    except Exception:
                        continue

                    name = str(packet.get("Name", "")).strip()
                    if not name:
                        continue

                    try:
                        port = int(packet.get("Port", 0))
                    except Exception:
                        continue
                    if port <= 0 or port > 65535:
                        continue

                    address = str(addr[0]).strip()
                    stream = OBSTeleportDiscoveredStream(
                        key=f"{name}|{address}|{port}",
                        name=name,
                        address=address,
                        port=port,
                        audio_and_video=bool(packet.get("AudioAndVideo", False)),
                        version=str(packet.get("Version", "")).strip(),
                    )

                    now = time.monotonic()
                    with self._lock:
                        self._streams[stream.key] = (stream, now)
                        self._prune_locked(now)

                sock.close()
        finally:
            self._running.clear()


_discovery_manager = _DiscoveryManager()


def teleport_ensure_discovery_running() -> None:
    _discovery_manager.ensure_running()


def teleport_get_discovered_streams() -> List[Dict[str, object]]:
    teleport_ensure_discovery_running()
    return [asdict(item) for item in _discovery_manager.get_streams()]


def teleport_get_connection_snapshot() -> Dict[str, object]:
    with _connection_state_lock:
        snapshot = OBSTeleportConnectionSnapshot(
            phase=_connection_state.phase,
            discovery_running=_connection_state.discovery_running,
            discovered_count=_connection_state.discovered_count,
            endpoint=_connection_state.endpoint,
            stream_key=_connection_state.stream_key,
            stream_name=_connection_state.stream_name,
            last_error=_connection_state.last_error,
        )

    discovered = _discovery_manager.get_streams()
    snapshot.discovery_running = _discovery_manager.is_running()
    snapshot.discovered_count = len(discovered)
    return asdict(snapshot)


class OBSTeleportReceiver:
    """OBS Teleport TCP receiver.

    支援兩種 endpoint 來源:
    - stream_key discovery (preferred)
    - manual host/port fallback
    """

    HEADER_LE = struct.Struct("<4sQi")
    HEADER_BE = struct.Struct(">4sQi")
    IMAGE_HEADER_SIZE = struct.calcsize("<22f")
    WAVE_HEADER_SIZE = struct.calcsize("<4i")
    MAX_PACKET_SIZE = 32 * 1024 * 1024
    MAX_QUEUE_SIZE = 5

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        stream_key: str = "",
        verbose: bool = False,
    ) -> None:
        self.host = str(host).strip()
        self.port = int(port) if str(port).strip() else 0
        self.stream_key = str(stream_key).strip()
        self.verbose = bool(verbose)

        self._socket: Optional[socket.socket] = None
        self._socket_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._connected = threading.Event()

        self._frame_lock = threading.Lock()
        self._frame_queue: deque[np.ndarray] = deque()
        self._latest_frame: Optional[np.ndarray] = None

        self._stats_lock = threading.Lock()
        self.received_frames = 0
        self.dropped_frames = 0
        self.current_fps = 0.0
        self.decode_delay_ms = 0.0
        self.receive_delay_ms = 0.0
        self.processing_delay_ms = 0.0
        self._fps_counter = 0
        self._fps_window_start = time.perf_counter()

    def connect(self) -> bool:
        self.disconnect()
        teleport_ensure_discovery_running()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._receive_loop, name="OBSTeleportReceiver", daemon=True)
        self._thread.start()
        return True

    def disconnect(self) -> None:
        self._stop_event.set()
        self._disconnect_socket()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._connected.clear()
        _set_connection_state(OBSTeleportConnectionPhase.DISCONNECTED, "", self.stream_key, "", "")

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def get_current_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            if not self._frame_queue:
                return None
            return self._frame_queue.popleft()

    def get_frame_dimensions(self) -> Tuple[Optional[int], Optional[int]]:
        with self._frame_lock:
            if self._latest_frame is None:
                return None, None
            h, w = self._latest_frame.shape[:2]
            return w, h

    def get_performance_stats(self) -> Dict[str, float]:
        with self._stats_lock:
            return {
                "current_fps": float(self.current_fps),
                "decode_delay_ms": float(self.decode_delay_ms),
                "receive_delay_ms": float(self.receive_delay_ms),
                "processing_delay_ms": float(self.processing_delay_ms),
                "received_frames": float(self.received_frames),
                "dropped_frames": float(self.dropped_frames),
            }

    def _update_stats(self, decode_delay_ms: float) -> None:
        now = time.perf_counter()
        with self._stats_lock:
            self.decode_delay_ms = decode_delay_ms
            self._fps_counter += 1
            elapsed = now - self._fps_window_start
            if elapsed >= 1.0:
                self.current_fps = self._fps_counter / elapsed
                self._fps_counter = 0
                self._fps_window_start = now

    def _resolve_endpoint(self) -> Tuple[Optional[str], int, str]:
        if self.stream_key:
            stream = _discovery_manager.resolve(self.stream_key)
            if not stream:
                _set_connection_state(
                    OBSTeleportConnectionPhase.WAITING_FOR_DISCOVERY,
                    "",
                    self.stream_key,
                    "",
                    "",
                )
                return None, 0, ""
            return stream.address, stream.port, stream.name

        if not self.host or self.port <= 0 or self.port > 65535:
            _set_connection_state(
                OBSTeleportConnectionPhase.WAITING_FOR_ENDPOINT,
                "",
                self.stream_key,
                "",
                "",
            )
            return None, 0, ""

        return self.host, self.port, "Manual"

    def _connect_socket(self, host: str, port: int) -> Tuple[Optional[socket.socket], str]:
        try:
            sock = socket.create_connection((host, port), timeout=1.5)
            sock.settimeout(1.0)
            return sock, ""
        except OSError as exc:
            return None, str(exc)

    def _disconnect_socket(self) -> None:
        active_socket = None
        with self._socket_lock:
            active_socket = self._socket
            self._socket = None

        if active_socket is None:
            return

        try:
            active_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            active_socket.close()
        except OSError:
            pass

    def _read_exact(self, sock: socket.socket, size: int) -> Optional[bytes]:
        buffer = bytearray()
        while not self._stop_event.is_set() and len(buffer) < size:
            try:
                chunk = sock.recv(size - len(buffer))
            except socket.timeout:
                continue
            except OSError:
                return None
            if not chunk:
                return None
            buffer.extend(chunk)
        if len(buffer) != size:
            return None
        return bytes(buffer)

    def _skip_exact(self, sock: socket.socket, size: int) -> bool:
        remaining = size
        while remaining > 0 and not self._stop_event.is_set():
            chunk_size = min(8192, remaining)
            payload = self._read_exact(sock, chunk_size)
            if payload is None:
                return False
            remaining -= len(payload)
        return remaining == 0

    def _parse_packet_header(self, raw: bytes) -> Tuple[bytes, int]:
        packet_type, _timestamp, size = self.HEADER_LE.unpack(raw)
        if 0 <= size <= self.MAX_PACKET_SIZE:
            return packet_type, size

        packet_type, _timestamp, size = self.HEADER_BE.unpack(raw)
        if 0 <= size <= self.MAX_PACKET_SIZE:
            return packet_type, size

        raise ValueError("invalid packet size")

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set():
            host, port, stream_name = self._resolve_endpoint()
            if not host:
                time.sleep(0.25)
                continue

            endpoint = f"{host}:{port}"
            _set_connection_state(
                OBSTeleportConnectionPhase.CONNECTING,
                endpoint,
                self.stream_key,
                stream_name,
                "",
            )

            sock, connect_error = self._connect_socket(host, port)
            if sock is None:
                _set_connection_state(
                    OBSTeleportConnectionPhase.ERROR,
                    endpoint,
                    self.stream_key,
                    stream_name,
                    connect_error or "connect failed",
                )
                time.sleep(0.5)
                continue

            with self._socket_lock:
                self._socket = sock
            self._connected.set()
            _set_connection_state(
                OBSTeleportConnectionPhase.CONNECTED,
                endpoint,
                self.stream_key,
                stream_name,
                "",
            )

            if self.verbose:
                log_print(f"[Teleport] Connected to {endpoint}")

            stream_failed = False
            while not self._stop_event.is_set() and not stream_failed:
                header_raw = self._read_exact(sock, self.HEADER_LE.size)
                if header_raw is None:
                    break

                try:
                    packet_type, payload_size = self._parse_packet_header(header_raw)
                except Exception:
                    _set_connection_state(
                        OBSTeleportConnectionPhase.ERROR,
                        endpoint,
                        self.stream_key,
                        stream_name,
                        "invalid packet size",
                    )
                    stream_failed = True
                    break

                if packet_type == b"JPEG":
                    image_header = self._read_exact(sock, self.IMAGE_HEADER_SIZE)
                    if image_header is None:
                        break
                    payload = self._read_exact(sock, payload_size)
                    if payload is None:
                        break

                    decode_start = time.perf_counter()
                    frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                    decode_delay = (time.perf_counter() - decode_start) * 1000.0
                    self._update_stats(decode_delay)

                    if frame is None or frame.size == 0:
                        _set_connection_state(
                            OBSTeleportConnectionPhase.ERROR,
                            endpoint,
                            self.stream_key,
                            stream_name,
                            "jpeg decode failed",
                        )
                        continue

                    with self._frame_lock:
                        while len(self._frame_queue) >= self.MAX_QUEUE_SIZE:
                            self._frame_queue.popleft()
                            with self._stats_lock:
                                self.dropped_frames += 1
                        self._frame_queue.append(frame)
                        self._latest_frame = frame
                        with self._stats_lock:
                            self.received_frames += 1
                    continue

                if packet_type == b"WAVE":
                    wave_header = self._read_exact(sock, self.WAVE_HEADER_SIZE)
                    if wave_header is None:
                        break
                    if not self._skip_exact(sock, payload_size):
                        break
                    continue

                if not self._skip_exact(sock, payload_size):
                    break

            if not self._stop_event.is_set():
                _set_connection_state(
                    OBSTeleportConnectionPhase.DISCONNECTED,
                    endpoint,
                    self.stream_key,
                    stream_name,
                    "",
                )
            self._connected.clear()
            self._disconnect_socket()

            if self.verbose and not self._stop_event.is_set():
                log_print(f"[Teleport] Disconnected from {endpoint}")

            if not self._stop_event.is_set():
                time.sleep(0.25)


class OBSTeleportManager:
    """High-level manager for UI/CaptureService integration."""

    def __init__(self) -> None:
        self.receiver: Optional[OBSTeleportReceiver] = None
        self.is_connected = False

    def ensure_discovery_running(self) -> None:
        teleport_ensure_discovery_running()

    def get_discovered_streams(self) -> List[Dict[str, object]]:
        return teleport_get_discovered_streams()

    def get_connection_snapshot(self) -> Dict[str, object]:
        return teleport_get_connection_snapshot()

    def connect(
        self,
        host: str = "",
        port: int = 0,
        stream_key: str = "",
        verbose: bool = False,
    ) -> bool:
        if self.receiver:
            self.disconnect()
        self.receiver = OBSTeleportReceiver(host=host, port=port, stream_key=stream_key, verbose=verbose)
        started = self.receiver.connect()
        self.is_connected = started
        return started

    def disconnect(self) -> None:
        if self.receiver:
            self.receiver.disconnect()
            self.receiver = None
        self.is_connected = False
        _clear_connection_state()

    def get_receiver(self) -> Optional[OBSTeleportReceiver]:
        return self.receiver

    def is_stream_active(self) -> bool:
        return bool(self.receiver and self.receiver.is_connected())

