"""
CaptureCardGStreamer module.
Pure GStreamer capture path using ctypes (Windows).
"""

import ctypes
import os
import threading
import time
from ctypes import POINTER, Structure, byref, c_char_p, c_int, c_void_p
from typing import Optional, Tuple

import numpy as np

from src.utils.debug_logger import log_print


# GstState enum (official): VOID_PENDING=0, NULL=1, READY=2, PAUSED=3, PLAYING=4
GST_STATE_VOID_PENDING = 0
GST_STATE_NULL = 1
GST_STATE_READY = 2
GST_STATE_PAUSED = 3
GST_STATE_PLAYING = 4
GST_STATE_CHANGE_FAILURE = 0
GST_MAP_READ = 1
GST_CLOCK_TIME_NONE = ctypes.c_uint64(-1).value
GST_MESSAGE_EOS = 1 << 0
GST_MESSAGE_ERROR = 1 << 1
GST_MESSAGE_WARNING = 1 << 2
GST_MESSAGE_STATE_CHANGED = 1 << 6
GST_MESSAGE_MASK = (
    GST_MESSAGE_EOS
    | GST_MESSAGE_ERROR
    | GST_MESSAGE_WARNING
    | GST_MESSAGE_STATE_CHANGED
)

# API-only strict DLL policy / 嚴格 API-only DLL 政策
REQUIRED_DLLS = {
    "core": ["gstreamer-1.0-0.dll", "gst-1.0.dll"],
    "app": ["gstapp-1.0-0.dll", "gstapp-1.0.dll"],
}

# Single source of truth: symbol -> DLL owner / 單一真相來源
SYMBOL_OWNER_MAP = {
    "gst_init": "core",
    "gst_parse_launch": "core",
    "gst_element_set_state": "core",
    "gst_element_get_state": "core",
    "gst_bin_get_by_name": "core",
    "gst_sample_get_buffer": "core",
    "gst_sample_unref": "core",
    "gst_buffer_map": "core",
    "gst_buffer_unmap": "core",
    "gst_object_unref": "core",
    "gst_element_get_bus": "core",
    "gst_bus_timed_pop_filtered": "core",
    "gst_message_get_type": "core",
    "gst_message_type_get_name": "core",
    "gst_message_unref": "core",
    "gst_app_sink_try_pull_sample": "app",
    "gst_app_sink_pull_sample": "app",
    "gst_app_sink_set_callbacks": "app",
}


class GstMapInfo(Structure):
    """GstMapInfo 绲愭 / GstMapInfo structure."""

    _fields_ = [
        ("memory", c_void_p),
        ("flags", c_int),
        ("data", POINTER(ctypes.c_uint8)),
        ("size", ctypes.c_size_t),
        ("maxsize", ctypes.c_size_t),
        ("user_data", POINTER(c_void_p)),
        ("_gst_reserved", POINTER(c_void_p) * 4),
    ]


class CaptureCardGStreamer:
    """Capture card wrapper using pure GStreamer path."""

    _init_lock = threading.Lock()
    _gst_initialized = False

    def __init__(self, config, region=None):
        del region  # 淇濈暀浠嬮潰鐩稿 / reserved for API compatibility

        self.config = config
        self.frame_width = int(getattr(config, "capture_width", 1920))
        self.frame_height = int(getattr(config, "capture_height", 1080))
        self.target_fps = float(getattr(config, "capture_fps", 240))
        self.device_index = int(getattr(config, "capture_device_index", 0))
        self.device_path = str(getattr(config, "capture_gst_device_path", "")).strip()

        self.running = True
        self.pipeline = None
        self.appsink = None
        self.bus = None

        self.gst_dll = None
        self.gstapp_dll = None
        self._dll_search_handles = []
        self._dll_paths = {"core": "<not loaded>", "app": "<not loaded>"}
        self._dll_last_errors = {"core": "", "app": ""}

        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._first_frame_time = None
        self._last_no_frame_log_ts = 0.0

        pull_timeout_ms = float(getattr(config, "capture_gst_pull_timeout_ms", 5.0))
        idle_sleep_ms = float(getattr(config, "capture_gst_idle_sleep_ms", 1.0))
        self._pull_timeout_ns = max(0, int(pull_timeout_ms * 1_000_000))
        self._idle_sleep_seconds = max(0.0, idle_sleep_ms / 1000.0)

        self._reader_stop = threading.Event()
        self._reader_thread = None
        self._has_try_pull_sample = False
        self._has_pull_sample = False
        self._candidate_probe_timeout_ms = max(
            100, int(float(getattr(config, "capture_gst_candidate_probe_timeout_ms", 500.0)))
        )
        self._strict_candidate_probe = bool(
            getattr(config, "capture_gst_strict_candidate_probe", False)
        )

        self._load_gstreamer_dlls()
        self._setup_function_signatures()
        self._init_gstreamer_once()
        self._create_pipeline()
        self._start_reader_thread()

    def _load_gstreamer_dlls(self):
        """Load required GStreamer DLLs and keep resolved paths for diagnostics."""
        possible_roots = [
            os.environ.get("GSTREAMER_1_0_ROOT_MSVC_X86_64", ""),
            os.environ.get("GSTREAMER_1_0_ROOT_MINGW_X86_64", ""),
            r"C:\gstreamer\1.0\msvc_x86_64",
            r"C:\gstreamer\1.0\mingw_x86_64",
            r"C:\Program Files\gstreamer\1.0\msvc_x86_64",
            r"C:\Program Files\gstreamer\1.0\mingw_x86_64",
            r"C:\Program Files (x86)\gstreamer\1.0\msvc_x86_64",
            r"C:\Program Files (x86)\gstreamer\1.0\mingw_x86_64",
        ]

        search_dirs = []
        for root in possible_roots:
            if not root:
                continue
            root = os.path.normpath(root)
            for path in (root, os.path.join(root, "bin")):
                if os.path.isdir(path) and path not in search_dirs:
                    search_dirs.append(path)

        if hasattr(os, "add_dll_directory"):
            for path in search_dirs:
                try:
                    self._dll_search_handles.append(os.add_dll_directory(path))
                except Exception:
                    continue

        self.gst_dll, self._dll_paths["core"], self._dll_last_errors["core"] = self._load_single_dll(
            REQUIRED_DLLS["core"], search_dirs, "core"
        )
        self.gstapp_dll, self._dll_paths["app"], self._dll_last_errors["app"] = self._load_single_dll(
            REQUIRED_DLLS["app"], search_dirs, "app"
        )

        missing_groups = []
        if not self.gst_dll:
            missing_groups.append(
                "core "
                f"(expected one of: {', '.join(REQUIRED_DLLS['core'])}; "
                f"last_error={self._dll_last_errors['core']})"
            )
        if not self.gstapp_dll:
            missing_groups.append(
                "app "
                f"(expected one of: {', '.join(REQUIRED_DLLS['app'])}; "
                f"last_error={self._dll_last_errors['app']})"
            )

        if missing_groups:
            message = "Missing required DLL group(s): " + " | ".join(missing_groups)
            log_print(f"[CaptureCardGStreamer] DLL validation failed: {message}")
            raise RuntimeError(message)

        return dict(self._dll_paths)

    def _resolve_loaded_dll_path(self, dll_obj, requested_name):
        """Resolve loaded DLL absolute path when possible / 嘗試解析完整 DLL 路徑."""
        candidate = str(getattr(dll_obj, "_name", "") or requested_name)
        if candidate and os.path.isabs(candidate) and os.path.isfile(candidate):
            return os.path.normpath(candidate)

        if os.name == "nt":
            try:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                get_module_handle = kernel32.GetModuleHandleW
                get_module_handle.argtypes = [ctypes.c_wchar_p]
                get_module_handle.restype = c_void_p
                get_module_filename = kernel32.GetModuleFileNameW
                get_module_filename.argtypes = [c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
                get_module_filename.restype = ctypes.c_uint32

                module_name = os.path.basename(candidate) if candidate else requested_name
                h_module = get_module_handle(module_name)
                if h_module:
                    buffer = ctypes.create_unicode_buffer(32768)
                    copied = get_module_filename(h_module, buffer, ctypes.c_uint32(len(buffer)))
                    if copied:
                        return os.path.normpath(buffer.value)
            except Exception:
                pass

        return candidate or requested_name

    def _load_single_dll(self, dll_names, search_dirs, dll_type):
        last_error = ""
        for dll_name in dll_names:
            try:
                dll = ctypes.CDLL(dll_name)
                resolved_path = self._resolve_loaded_dll_path(dll, dll_name)
                log_print(f"[CaptureCardGStreamer] Loaded {dll_name} ({dll_type}) from {resolved_path}")
                return dll, resolved_path, ""
            except OSError as e:
                last_error = str(e)
                continue

        for directory in search_dirs:
            for dll_name in dll_names:
                dll_path = os.path.join(directory, dll_name)
                if not os.path.isfile(dll_path):
                    continue
                try:
                    dll = ctypes.CDLL(dll_path)
                    resolved_path = self._resolve_loaded_dll_path(dll, dll_path)
                    log_print(f"[CaptureCardGStreamer] Loaded {dll_name} ({dll_type}) from {resolved_path}")
                    return dll, resolved_path, ""
                except OSError as e:
                    log_print(f"[CaptureCardGStreamer] Failed to load {dll_path}: {e}")
                    last_error = str(e)
                    continue

        log_print(
            f"[CaptureCardGStreamer] Could not locate {dll_type} DLL. "
            f"Tried: {', '.join(dll_names)}"
        )
        return None, "<not loaded>", last_error or "No candidate DLL could be loaded."

    def _validate_required_symbols(self):
        """Validate strict required symbol set before binding argtypes/restype."""
        dll_map = {"core": self.gst_dll, "app": self.gstapp_dll}
        missing_items = []
        available_symbols = []

        for symbol_name, owner in SYMBOL_OWNER_MAP.items():
            dll_handle = dll_map.get(owner)
            dll_path = self._dll_paths.get(owner, "<not loaded>")
            if not dll_handle:
                missing_items.append(
                    f"symbol={symbol_name}, expected_dll={owner}, actual={dll_path}"
                )
                continue

            if hasattr(dll_handle, symbol_name):
                available_symbols.append(symbol_name)
            else:
                missing_items.append(
                    f"symbol={symbol_name}, expected_dll={owner}, actual={dll_path}"
                )

        if missing_items:
            message = "; ".join(missing_items)
            log_print(f"[CaptureCardGStreamer] DLL validation failed: {message}")
            raise RuntimeError(
                "Missing required GStreamer symbol(s): "
                f"{message}"
            )

        if bool(getattr(self.config, "capture_gst_log_symbol_validation", False)):
            symbol_list = ", ".join(available_symbols)
            log_print(f"[CaptureCardGStreamer] Symbol validation detail: {symbol_list}")

        log_print(
            "[CaptureCardGStreamer] DLL validation passed: "
            f"core={self._dll_paths.get('core')}, "
            f"app={self._dll_paths.get('app')}, "
            f"symbols={len(SYMBOL_OWNER_MAP)}"
        )

    def _setup_function_signatures(self):
        """Bind required Gst/GstApp symbols for ctypes calls."""
        self._validate_required_symbols()

        self.gst_dll.gst_init.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
        self.gst_dll.gst_init.restype = None

        self.gst_dll.gst_parse_launch.argtypes = [c_char_p, POINTER(c_void_p)]
        self.gst_dll.gst_parse_launch.restype = c_void_p

        self.gst_dll.gst_element_set_state.argtypes = [c_void_p, c_int]
        self.gst_dll.gst_element_set_state.restype = c_int

        self.gst_dll.gst_element_get_state.argtypes = [
            c_void_p,
            POINTER(c_int),
            POINTER(c_int),
            ctypes.c_uint64,
        ]
        self.gst_dll.gst_element_get_state.restype = c_int

        self.gst_dll.gst_bin_get_by_name.argtypes = [c_void_p, c_char_p]
        self.gst_dll.gst_bin_get_by_name.restype = c_void_p

        self.gst_dll.gst_sample_get_buffer.argtypes = [c_void_p]
        self.gst_dll.gst_sample_get_buffer.restype = c_void_p

        self.gst_dll.gst_sample_unref.argtypes = [c_void_p]
        self.gst_dll.gst_sample_unref.restype = None

        self.gst_dll.gst_buffer_map.argtypes = [c_void_p, POINTER(GstMapInfo), c_int]
        self.gst_dll.gst_buffer_map.restype = ctypes.c_bool

        self.gst_dll.gst_buffer_unmap.argtypes = [c_void_p, POINTER(GstMapInfo)]
        self.gst_dll.gst_buffer_unmap.restype = None

        self.gst_dll.gst_object_unref.argtypes = [c_void_p]
        self.gst_dll.gst_object_unref.restype = None

        self.gst_dll.gst_element_get_bus.argtypes = [c_void_p]
        self.gst_dll.gst_element_get_bus.restype = c_void_p

        self.gst_dll.gst_bus_timed_pop_filtered.argtypes = [c_void_p, ctypes.c_uint64, ctypes.c_uint]
        self.gst_dll.gst_bus_timed_pop_filtered.restype = c_void_p

        self.gst_dll.gst_message_get_type.argtypes = [c_void_p]
        self.gst_dll.gst_message_get_type.restype = ctypes.c_uint

        self.gst_dll.gst_message_type_get_name.argtypes = [ctypes.c_uint]
        self.gst_dll.gst_message_type_get_name.restype = c_char_p

        self.gst_dll.gst_message_unref.argtypes = [c_void_p]
        self.gst_dll.gst_message_unref.restype = None

        if hasattr(self.gstapp_dll, "gst_app_sink_try_pull_sample"):
            self.gstapp_dll.gst_app_sink_try_pull_sample.argtypes = [c_void_p, ctypes.c_uint64]
            self.gstapp_dll.gst_app_sink_try_pull_sample.restype = c_void_p
            self._has_try_pull_sample = True

        if hasattr(self.gstapp_dll, "gst_app_sink_pull_sample"):
            self.gstapp_dll.gst_app_sink_pull_sample.argtypes = [c_void_p]
            self.gstapp_dll.gst_app_sink_pull_sample.restype = c_void_p
            self._has_pull_sample = True

        if not self._has_try_pull_sample and not self._has_pull_sample:
            raise RuntimeError("GStreamer app DLL does not expose app sink pull APIs.")

    def _init_gstreamer_once(self):
        """Init GStreamer once per process / 鍏ㄧ▼搴忓彧鍒濆鍖栦竴娆?"""
        with self._init_lock:
            if self._gst_initialized:
                return
            argc = c_int(0)
            argv = POINTER(c_char_p)()
            self.gst_dll.gst_init(byref(argc), byref(argv))
            self.__class__._gst_initialized = True
            log_print("[CaptureCardGStreamer] GStreamer initialized")

    def _build_pipeline_candidates(self):
        """Build fallback pipeline list / 建立多組 fallback pipeline."""
        fps = max(1, int(round(self.target_fps)))
        source_pref = str(getattr(self.config, "capture_gst_source", "auto")).strip().lower()

        source_order = ["mfvideosrc", "ksvideosrc"]
        if source_pref in ("mfvideosrc", "mfvideo", "mf"):
            source_order = ["mfvideosrc", "ksvideosrc"]
        elif source_pref in ("ksvideosrc", "ksvideo", "ks"):
            source_order = ["ksvideosrc", "mfvideosrc"]

        sink = "appsink name=sink emit-signals=false sync=false max-buffers=1 drop=true"
        candidates = []

        # 優先使用固定 device-path（避免 index 對錯裝置）/ prefer stable device-path.
        def build_source_selector(src_name: str) -> str:
            if self.device_path:
                quoted_path = self.device_path.replace("\\", "\\\\").replace("'", "\\'")
                return f"{src_name} device-path='{quoted_path}'"
            return f"{src_name} device-index={self.device_index}"

        for src in source_order:
            src_selector = build_source_selector(src)
            # 優先 raw path，低延遲組合 / prefer raw path first
            candidates.append(
                f"{src_selector} ! "
                "videoconvert ! videoscale ! videorate ! "
                f"video/x-raw,format=BGR,width={self.frame_width},height={self.frame_height},framerate={fps}/1 ! "
                f"{sink}"
            )
            # 某些卡輸出 image/jpeg，需要 decodebin
            candidates.append(
                f"{src_selector} ! "
                "decodebin ! videoconvert ! videoscale ! videorate ! "
                f"video/x-raw,format=BGR,width={self.frame_width},height={self.frame_height},framerate={fps}/1 ! "
                f"{sink}"
            )
            # Explicit JPEG decode fallback
            candidates.append(
                f"{src_selector} ! "
                f"image/jpeg,width={self.frame_width},height={self.frame_height},framerate={fps}/1 ! "
                "jpegdec ! videoconvert ! videoscale ! "
                f"video/x-raw,format=BGR,width={self.frame_width},height={self.frame_height} ! "
                f"{sink}"
            )
            candidates.append(
                f"{src_selector} ! "
                "videoconvert ! videoscale ! "
                f"video/x-raw,format=BGR,width={self.frame_width},height={self.frame_height} ! "
                f"{sink}"
            )
            candidates.append(
                f"{src_selector} ! "
                "decodebin ! videoconvert ! videoscale ! "
                f"video/x-raw,format=BGR,width={self.frame_width},height={self.frame_height} ! "
                f"{sink}"
            )
            candidates.append(
                f"{src_selector} ! "
                "videoconvert ! "
                "video/x-raw,format=BGR ! "
                f"{sink}"
            )
            candidates.append(
                f"{src_selector} ! "
                "decodebin ! videoconvert ! video/x-raw,format=BGR ! "
                f"{sink}"
            )

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            unique_candidates.append(candidate)
        return unique_candidates

    def _poll_bus_messages(self, pipeline, max_wait_ms=300):
        """Poll bus briefly for startup errors / 啟動時快速檢查錯誤."""
        if not pipeline:
            return False

        bus = None
        has_error = False
        try:
            bus = self.gst_dll.gst_element_get_bus(pipeline)
            if not bus:
                return False

            deadline = time.time() + max(0.05, float(max_wait_ms) / 1000.0)
            while time.time() < deadline:
                msg = self.gst_dll.gst_bus_timed_pop_filtered(
                    bus,
                    ctypes.c_uint64(50_000_000),
                    ctypes.c_uint(GST_MESSAGE_MASK),
                )
                if not msg:
                    continue

                try:
                    msg_type = int(self.gst_dll.gst_message_get_type(msg))
                    msg_name_raw = self.gst_dll.gst_message_type_get_name(ctypes.c_uint(msg_type))
                    msg_name = msg_name_raw.decode("utf-8", errors="ignore") if msg_name_raw else str(msg_type)

                    if msg_type == GST_MESSAGE_ERROR:
                        has_error = True
                        log_print(f"[CaptureCardGStreamer] Pipeline bus ERROR: {msg_name}")
                    elif msg_type == GST_MESSAGE_WARNING:
                        log_print(f"[CaptureCardGStreamer] Pipeline bus WARNING: {msg_name}")
                    elif msg_type == GST_MESSAGE_EOS:
                        log_print("[CaptureCardGStreamer] Pipeline bus EOS during startup")
                    elif msg_type == GST_MESSAGE_STATE_CHANGED:
                        # 狀態變更很頻繁，這裡不逐條列印
                        pass
                finally:
                    self.gst_dll.gst_message_unref(msg)
        except Exception as e:
            log_print(f"[CaptureCardGStreamer] Bus polling error: {e}")
        finally:
            if bus:
                try:
                    self.gst_dll.gst_object_unref(bus)
                except Exception:
                    pass

        return has_error

    def _create_pipeline(self):
        pipeline_candidates = self._build_pipeline_candidates()
        last_error = "No usable pipeline candidate"

        if self._strict_candidate_probe:
            log_print(
                "[CaptureCardGStreamer] Strict candidate sample probe enabled "
                f"(timeout={self._candidate_probe_timeout_ms}ms)"
            )

        for idx, pipeline_str in enumerate(pipeline_candidates, start=1):
            log_print(
                f"[CaptureCardGStreamer] Trying pipeline {idx}/{len(pipeline_candidates)}: {pipeline_str}"
            )

            parse_error = c_void_p()
            pipeline = self.gst_dll.gst_parse_launch(pipeline_str.encode("utf-8"), byref(parse_error))
            if not pipeline:
                last_error = f"gst_parse_launch failed for candidate {idx}"
                continue

            appsink = self.gst_dll.gst_bin_get_by_name(pipeline, b"sink")
            if not appsink:
                self.gst_dll.gst_object_unref(pipeline)
                last_error = f"appsink not found in candidate {idx}"
                continue

            state_ret = self.gst_dll.gst_element_set_state(pipeline, GST_STATE_PLAYING)
            if state_ret == GST_STATE_CHANGE_FAILURE:
                self._cleanup_candidate_pipeline(pipeline, appsink, timeout_ms=1200)
                last_error = f"Failed to set candidate {idx} to PLAYING"
                continue

            if self._poll_bus_messages(pipeline, max_wait_ms=350):
                self._cleanup_candidate_pipeline(pipeline, appsink, timeout_ms=1200)
                last_error = f"Candidate {idx} reported bus ERROR"
                continue

            if self._strict_candidate_probe:
                if not self._probe_candidate_sample(appsink, timeout_ms=self._candidate_probe_timeout_ms):
                    self._cleanup_candidate_pipeline(pipeline, appsink, timeout_ms=1200)
                    last_error = (
                        f"Candidate {idx} produced no sample within "
                        f"{self._candidate_probe_timeout_ms}ms"
                    )
                    continue

            self.pipeline = pipeline
            self.appsink = appsink
            log_print(
                "[CaptureCardGStreamer] Pipeline started "
                f"(candidate {idx}, {self.frame_width}x{self.frame_height} @ {self.target_fps} FPS target)"
            )
            return

        raise RuntimeError(last_error)

    def _start_reader_thread(self):
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name="CaptureCardGStreamerReader",
            daemon=True,
        )
        self._reader_thread.start()

    def _set_pipeline_to_null(self, pipeline, timeout_ms=1500) -> bool:
        """Best-effort state transition to NULL before unref / 先轉 NULL 再釋放."""
        if not pipeline:
            return True

        state = c_int(-1)
        pending = c_int(-1)
        try:
            self.gst_dll.gst_element_set_state(pipeline, GST_STATE_NULL)
        except Exception as e:
            log_print(f"[CaptureCardGStreamer] Failed to request NULL state: {e}")
            return False

        timeout_ms = max(100, int(timeout_ms))
        deadline = time.time() + (timeout_ms / 1000.0)
        while time.time() < deadline:
            try:
                self.gst_dll.gst_element_get_state(
                    pipeline,
                    byref(state),
                    byref(pending),
                    ctypes.c_uint64(200_000_000),
                )
            except Exception as e:
                log_print(f"[CaptureCardGStreamer] gst_element_get_state error: {e}")
                return False

            if state.value == GST_STATE_NULL and pending.value in (
                GST_STATE_VOID_PENDING,
                GST_STATE_NULL,
                -1,
            ):
                return True

            # 某些 source 會卡住，重送一次狀態請求 / resend NULL request for stubborn sources.
            try:
                self.gst_dll.gst_element_set_state(pipeline, GST_STATE_NULL)
            except Exception:
                pass
            time.sleep(0.02)

        log_print(
            "[CaptureCardGStreamer] Pipeline did not fully reach NULL before timeout "
            f"(state={state.value}, pending={pending.value})"
        )
        return False

    def _cleanup_candidate_pipeline(self, pipeline, appsink, timeout_ms=1200):
        """Cleanup candidate safely / 候選 pipeline 安全清理."""
        null_ok = self._set_pipeline_to_null(pipeline, timeout_ms=timeout_ms)
        if not null_ok:
            log_print(
                "[CaptureCardGStreamer] Skip unref for candidate pipeline because "
                "NULL state was not reached in time."
            )
            return

        try:
            if appsink:
                self.gst_dll.gst_object_unref(appsink)
        except Exception:
            pass
        try:
            if pipeline:
                self.gst_dll.gst_object_unref(pipeline)
        except Exception:
            pass

    def _probe_candidate_sample(self, appsink, timeout_ms=500) -> bool:
        """Probe whether candidate can emit sample quickly / 快速驗證候選是否有 sample."""
        timeout_ms = max(50, int(timeout_ms))
        deadline = time.time() + (timeout_ms / 1000.0)

        while time.time() < deadline:
            remaining_ns = int(max(0.0, (deadline - time.time()) * 1_000_000_000))
            wait_ns = min(remaining_ns, 120_000_000)
            sample = self._try_pull_sample_from(appsink, wait_ns)
            if sample:
                self.gst_dll.gst_sample_unref(sample)
                return True
            time.sleep(0.005)

        log_print(
            "[CaptureCardGStreamer] Candidate probe timeout: no sample "
            f"within {timeout_ms}ms"
        )
        return False

    def _reader_loop(self):
        """Background loop: keep only newest sample / 涓熻垔淇濇柊."""
        while self.running and not self._reader_stop.is_set():
            if not self.pipeline or not self.appsink:
                break

            sample = self._pull_latest_sample()
            if not sample:
                if self._idle_sleep_seconds > 0:
                    time.sleep(self._idle_sleep_seconds)
                continue

            try:
                frame = self._sample_to_frame(sample)
                if frame is None:
                    continue
                with self._frame_lock:
                    self._latest_frame = frame
                    if self._first_frame_time is None:
                        self._first_frame_time = time.time()
                        log_print(
                            "[CaptureCardGStreamer] First frame received "
                            f"({frame.shape[1]}x{frame.shape[0]})"
                        )
            except Exception as e:
                log_print(f"[CaptureCardGStreamer] Reader loop decode error: {e}")
            finally:
                self.gst_dll.gst_sample_unref(sample)

    def _pull_latest_sample(self):
        """Pull one sample then drain queue so caller gets the newest frame."""
        first = self._try_pull_sample(self._pull_timeout_ns)
        if not first:
            return None

        latest = first
        while True:
            newer = self._try_pull_sample(0)
            if not newer:
                break
            self.gst_dll.gst_sample_unref(latest)
            latest = newer
        return latest

    def _try_pull_sample(self, timeout_ns: int):
        return self._try_pull_sample_from(self.appsink, timeout_ns)

    def _try_pull_sample_from(self, appsink, timeout_ns: int):
        if not appsink or not self.gstapp_dll:
            return None

        if self._has_try_pull_sample:
            return self.gstapp_dll.gst_app_sink_try_pull_sample(
                appsink,
                ctypes.c_uint64(max(0, int(timeout_ns))),
            )

        if timeout_ns > 0 and self._has_pull_sample:
            return self.gstapp_dll.gst_app_sink_pull_sample(appsink)
        return None

    def _sample_to_frame(self, sample):
        """Convert GstSample -> BGR numpy frame."""
        buffer = self.gst_dll.gst_sample_get_buffer(sample)
        if not buffer:
            return None

        map_info = GstMapInfo()
        if not self.gst_dll.gst_buffer_map(buffer, byref(map_info), GST_MAP_READ):
            return None

        try:
            expected_size = self.frame_width * self.frame_height * 3
            if map_info.size < expected_size:
                log_print(
                    "[CaptureCardGStreamer] Buffer size too small: "
                    f"{map_info.size} < {expected_size}"
                )
                return None

            frame_data = np.ctypeslib.as_array(map_info.data, shape=(expected_size,))
            frame = frame_data.reshape((self.frame_height, self.frame_width, 3)).copy()
            return frame
        finally:
            self.gst_dll.gst_buffer_unmap(buffer, byref(map_info))

    def get_latest_frame(self):
        """Return latest cached BGR frame cropped by capture config."""
        if not self.running:
            return None

        with self._frame_lock:
            if self._latest_frame is None:
                now = time.time()
                if now - self._last_no_frame_log_ts >= 2.0:
                    self._last_no_frame_log_ts = now
                    log_print(
                        "[CaptureCardGStreamer] No frame available yet. "
                        "OpenCV window will not show until frame arrives."
                    )
                return None
            frame = self._latest_frame

        return self._crop_frame(frame)

    def has_frame(self) -> bool:
        """Whether at least one frame is ready / 鏄惁宸叉敹鍒伴骞€."""
        with self._frame_lock:
            return self._latest_frame is not None

    def wait_for_first_frame(self, timeout_s: float = 2.0) -> bool:
        """Wait for first frame within timeout / 鍦?timeout 鍏х瓑寰呴骞€."""
        timeout_s = max(0.1, float(timeout_s))
        deadline = time.time() + timeout_s
        while self.running and time.time() < deadline:
            if self.has_frame():
                return True
            time.sleep(0.01)
        return self.has_frame()

    def _crop_frame(self, frame):
        base_w = int(getattr(self.config, "capture_width", self.frame_width))
        base_h = int(getattr(self.config, "capture_height", self.frame_height))

        range_x = int(getattr(self.config, "capture_range_x", 128))
        range_y = int(getattr(self.config, "capture_range_y", 128))
        if range_x < 128:
            range_x = max(128, int(getattr(self.config, "region_size", 200)))
        if range_y < 128:
            range_y = max(128, int(getattr(self.config, "region_size", 200)))

        offset_x = int(getattr(self.config, "capture_offset_x", 0))
        offset_y = int(getattr(self.config, "capture_offset_y", 0))

        center_x = base_w // 2
        center_y = base_h // 2

        left = center_x - range_x // 2 + offset_x
        top = center_y - range_y // 2 + offset_y
        right = left + range_x
        bottom = top + range_y

        left = max(0, min(left, base_w))
        top = max(0, min(top, base_h))
        right = max(left, min(right, base_w))
        bottom = max(top, min(bottom, base_h))

        return frame[top:bottom, left:right]

    def _release_pipeline_handles(self, skip_unref=False):
        if self.appsink:
            if not skip_unref:
                try:
                    self.gst_dll.gst_object_unref(self.appsink)
                except Exception:
                    pass
            self.appsink = None

        if self.pipeline:
            if not skip_unref:
                try:
                    self.gst_dll.gst_object_unref(self.pipeline)
                except Exception:
                    pass
            self.pipeline = None

    def stop(self):
        """Stop capture and release GStreamer resources."""
        if not self.running:
            return

        self.running = False
        self._reader_stop.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)

        skip_unref = False
        if self.pipeline:
            null_ok = self._set_pipeline_to_null(self.pipeline, timeout_ms=2500)
            skip_unref = not null_ok
            if skip_unref:
                log_print(
                    "[CaptureCardGStreamer] Skip unref on stop because pipeline "
                    "did not reach NULL. Handles detached to avoid GST critical."
                )

        self._release_pipeline_handles(skip_unref=skip_unref)

        with self._frame_lock:
            self._latest_frame = None

        log_print("[CaptureCardGStreamer] Pipeline stopped and resources released")


def validate_capture_card_gstreamer_config(config) -> Tuple[bool, Optional[str]]:
    """Validate capture-card GStreamer settings."""
    try:
        device_index = int(getattr(config, "capture_device_index", 0))
        if device_index < 0 or device_index > 10:
            return False, f"Device index {device_index} is out of valid range (0-10)"

        width = int(getattr(config, "capture_width", 1920))
        height = int(getattr(config, "capture_height", 1080))
        if width < 320 or width > 7680:
            return False, f"Capture width {width} is out of valid range (320-7680)"
        if height < 240 or height > 4320:
            return False, f"Capture height {height} is out of valid range (240-4320)"

        fps = float(getattr(config, "capture_fps", 240))
        if fps < 1 or fps > 300:
            return False, f"Capture FPS {fps} is out of valid range (1-300)"

        return True, None
    except Exception as e:
        return False, f"Configuration validation error: {e}"


def create_capture_card_gstreamer_camera(config, region=None):
    """Factory for CaptureCardGStreamer."""
    is_valid, error_msg = validate_capture_card_gstreamer_config(config)
    if not is_valid:
        raise ValueError(f"Invalid capture card GStreamer configuration: {error_msg}")
    return CaptureCardGStreamer(config, region)


def get_default_capture_card_gstreamer_config() -> dict:
    """Get default capture-card GStreamer config dict."""
    return {
        "capture_width": 1920,
        "capture_height": 1080,
        "capture_fps": 240,
        "capture_device_index": 0,
        "capture_gst_device_path": "",
        "capture_range_x": 0,
        "capture_range_y": 0,
        "capture_offset_x": 0,
        "capture_offset_y": 0,
        "capture_center_offset_x": 0,
        "capture_center_offset_y": 0,
        "capture_gst_source": "auto",
        "capture_gst_connect_timeout": 2.5,
        "capture_gst_auto_fallback_opencv": False,
        "capture_gst_pull_timeout_ms": 5.0,
        "capture_gst_idle_sleep_ms": 1.0,
        "capture_gst_candidate_probe_timeout_ms": 500.0,
        "capture_gst_strict_candidate_probe": False,
        "capture_gst_log_symbol_validation": False,
    }


if __name__ == "__main__":
    pass

