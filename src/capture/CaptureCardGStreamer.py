"""
CaptureCardGStreamer module.
Contains GStreamer-based capture card implementation using ctypes to directly call GStreamer DLL.
"""

from src.utils.debug_logger import log_print
import ctypes
import os
import numpy as np
from typing import Optional, Tuple
from ctypes import c_int, c_void_p, c_char_p, POINTER, Structure, byref


# GStreamer state constants
GST_STATE_NULL = 0
GST_STATE_READY = 1
GST_STATE_PAUSED = 2
GST_STATE_PLAYING = 3

# GStreamer buffer map flags
GST_MAP_READ = 1


class GstMapInfo(Structure):
    """GStreamer buffer map info structure."""
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
    """Capture Card camera wrapper using GStreamer via ctypes."""

    def __init__(self, config, region=None):
        del region  # reserved for compatibility

        self.frame_width = int(getattr(config, "capture_width", 1920))
        self.frame_height = int(getattr(config, "capture_height", 1080))
        self.target_fps = float(getattr(config, "capture_fps", 240))
        self.device_index = int(getattr(config, "capture_device_index", 0))

        self.config = config
        self.running = True
        self.gst_dll = None  # Core GStreamer DLL (gstreamer-1.0-0.dll)
        self.gstapp_dll = None  # GStreamer App DLL (gstapp-1.0-0.dll)
        self.pipeline = None
        self.appsink = None
        self.bus = None

        # Load GStreamer DLLs
        self._load_gstreamer_dlls()
        if not self.gst_dll:
            raise RuntimeError("Failed to load GStreamer core DLL (gstreamer-1.0-0.dll)")
        if not self.gstapp_dll:
            raise RuntimeError("Failed to load GStreamer app DLL (gstapp-1.0-0.dll)")

        # Initialize GStreamer
        self._init_gstreamer()

        # Create pipeline
        self._create_pipeline()

    def _load_gstreamer_dlls(self):
        """Load GStreamer DLLs from common locations."""
        possible_paths = [
            os.environ.get("GSTREAMER_1_0_ROOT_MSVC_X86_64", ""),
            r"C:\gstreamer\1.0\msvc_x86_64",
            r"C:\gstreamer\1.0\mingw_x86_64",
            r"C:\Program Files\gstreamer\1.0\msvc_x86_64",
            r"C:\Program Files (x86)\gstreamer\1.0\msvc_x86_64",
        ]

        # MSVC version uses gstreamer-1.0-0.dll, MinGW uses gst-1.0.dll
        core_dll_names = ["gstreamer-1.0-0.dll", "gst-1.0.dll"]
        app_dll_names = ["gstapp-1.0-0.dll", "gstapp-1.0.dll"]

        def load_dll(dll_names, dll_type="core"):
            """Helper function to load a DLL."""
            # Try loading from PATH first
            for dll_name in dll_names:
                try:
                    dll = ctypes.CDLL(dll_name)
                    log_print(f"[CaptureCardGStreamer] Loaded {dll_name} ({dll_type}) from PATH")
                    return dll
                except OSError:
                    continue

            # Try loading from possible paths
            for base_path in possible_paths:
                if not base_path:
                    continue
                for dll_name in dll_names:
                    dll_paths = [
                        os.path.join(base_path, "bin", dll_name),
                        os.path.join(base_path, dll_name),  # In case base_path already includes bin
                    ]
                    for dll_path in dll_paths:
                        if os.path.exists(dll_path):
                            try:
                                dll = ctypes.CDLL(dll_path)
                                log_print(f"[CaptureCardGStreamer] Loaded {dll_name} ({dll_type}) from {dll_path}")
                                return dll
                            except OSError as e:
                                log_print(f"[CaptureCardGStreamer] Failed to load {dll_path}: {e}")
                                continue
            return None

        # Load core DLL
        self.gst_dll = load_dll(core_dll_names, "core")
        if not self.gst_dll:
            log_print(f"[CaptureCardGStreamer] Could not find GStreamer core DLL (tried: {', '.join(core_dll_names)})")
            return

        # Load app DLL
        self.gstapp_dll = load_dll(app_dll_names, "app")
        if not self.gstapp_dll:
            log_print(f"[CaptureCardGStreamer] Could not find GStreamer app DLL (tried: {', '.join(app_dll_names)})")
            return

    def _init_gstreamer(self):
        """Initialize GStreamer and set up function signatures."""
        if not self.gst_dll:
            return

        # Set up function signatures
        # gst_init(int *argc, char ***argv)
        self.gst_dll.gst_init.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
        self.gst_dll.gst_init.restype = None

        # gst_parse_launch(const gchar *pipeline_description, GError **error)
        self.gst_dll.gst_parse_launch.argtypes = [c_char_p, POINTER(c_void_p)]
        self.gst_dll.gst_parse_launch.restype = c_void_p

        # gst_element_set_state(GstElement *element, GstState state)
        self.gst_dll.gst_element_set_state.argtypes = [c_void_p, c_int]
        self.gst_dll.gst_element_set_state.restype = c_int

        # gst_element_get_state(GstElement *element, GstState *state, GstState *pending, GstClockTime timeout)
        self.gst_dll.gst_element_get_state.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int), ctypes.c_uint64]
        self.gst_dll.gst_element_get_state.restype = c_int

        # gst_bin_get_by_name(GstBin *bin, const gchar *name)
        self.gst_dll.gst_bin_get_by_name.argtypes = [c_void_p, c_char_p]
        self.gst_dll.gst_bin_get_by_name.restype = c_void_p

        # gst_app_sink_pull_sample(GstAppSink *appsink) - from gstapp DLL
        if self.gstapp_dll:
            self.gstapp_dll.gst_app_sink_pull_sample.argtypes = [c_void_p]
            self.gstapp_dll.gst_app_sink_pull_sample.restype = c_void_p

        # gst_sample_get_buffer(GstSample *sample)
        self.gst_dll.gst_sample_get_buffer.argtypes = [c_void_p]
        self.gst_dll.gst_sample_get_buffer.restype = c_void_p

        # gst_buffer_map(GstBuffer *buffer, GstMapInfo *info, GstMapFlags flags)
        self.gst_dll.gst_buffer_map.argtypes = [c_void_p, POINTER(GstMapInfo), c_int]
        self.gst_dll.gst_buffer_map.restype = ctypes.c_bool

        # gst_buffer_unmap(GstBuffer *buffer, GstMapInfo *info)
        self.gst_dll.gst_buffer_unmap.argtypes = [c_void_p, POINTER(GstMapInfo)]
        self.gst_dll.gst_buffer_unmap.restype = None

        # gst_object_unref(gpointer object)
        self.gst_dll.gst_object_unref.argtypes = [c_void_p]
        self.gst_dll.gst_object_unref.restype = None

        # gst_element_get_bus(GstElement *element)
        self.gst_dll.gst_element_get_bus.argtypes = [c_void_p]
        self.gst_dll.gst_element_get_bus.restype = c_void_p

        # Initialize GStreamer
        argc = c_int(0)
        argv = POINTER(c_char_p)()
        self.gst_dll.gst_init(byref(argc), byref(argv))
        log_print("[CaptureCardGStreamer] GStreamer initialized")

    def _create_pipeline(self):
        """Create GStreamer pipeline from configuration."""
        # Build pipeline string
        pipeline_str = (
            f"ksvideosrc device-index={self.device_index} ! "
            f"video/x-raw,format=NV12,width={self.frame_width},height={self.frame_height},framerate={int(self.target_fps)}/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=BGR ! "
            f"appsink drop=true max-buffers=1 name=sink"
        )

        log_print(f"[CaptureCardGStreamer] Creating pipeline: {pipeline_str}")

        # Create pipeline
        pipeline_bytes = pipeline_str.encode('utf-8')
        self.pipeline = self.gst_dll.gst_parse_launch(pipeline_bytes, None)

        if not self.pipeline:
            raise RuntimeError(f"Failed to create GStreamer pipeline: {pipeline_str}")

        # Get appsink element
        sink_name = b"sink"
        self.appsink = self.gst_dll.gst_bin_get_by_name(self.pipeline, sink_name)

        if not self.appsink:
            self.gst_dll.gst_object_unref(self.pipeline)
            self.pipeline = None
            raise RuntimeError("Failed to get appsink element from pipeline")

        # Set pipeline to PLAYING state
        state_ret = self.gst_dll.gst_element_set_state(self.pipeline, GST_STATE_PLAYING)
        if state_ret == GST_STATE_NULL:
            self.gst_dll.gst_object_unref(self.appsink)
            self.gst_dll.gst_object_unref(self.pipeline)
            self.appsink = None
            self.pipeline = None
            raise RuntimeError("Failed to set pipeline to PLAYING state")

        log_print(f"[CaptureCardGStreamer] Pipeline created and started successfully")
        log_print(f"[CaptureCardGStreamer] Resolution: {self.frame_width}x{self.frame_height}, FPS: {self.target_fps}")

    def get_latest_frame(self):
        """Get latest frame from capture card and return BGR image (or None)."""
        if not self.pipeline or not self.appsink or not self.running:
            return None

        try:
            # Pull sample from appsink (using gstapp DLL)
            if not self.gstapp_dll:
                return None
            sample = self.gstapp_dll.gst_app_sink_pull_sample(self.appsink)
            if not sample:
                return None

            # Get buffer from sample
            buffer = self.gst_dll.gst_sample_get_buffer(sample)
            if not buffer:
                self.gst_dll.gst_object_unref(sample)
                return None

            # Map buffer
            map_info = GstMapInfo()
            if not self.gst_dll.gst_buffer_map(buffer, byref(map_info), GST_MAP_READ):
                self.gst_dll.gst_object_unref(sample)
                return None

            try:
                # Get frame data
                frame_size = self.frame_width * self.frame_height * 3
                if map_info.size < frame_size:
                    log_print(f"[CaptureCardGStreamer] Buffer size mismatch: got {map_info.size}, expected {frame_size}")
                    return None

                # Create numpy array from buffer data
                data_ptr = ctypes.cast(map_info.data, POINTER(ctypes.c_uint8 * frame_size))
                frame_data = np.ctypeslib.as_array(data_ptr.contents)
                frame = frame_data.reshape((self.frame_height, self.frame_width, 3)).copy()

            finally:
                # Unmap buffer
                self.gst_dll.gst_buffer_unmap(buffer, byref(map_info))

            # Release sample
            self.gst_dll.gst_object_unref(sample)

            # Apply cropping (same logic as CaptureCard.py)
            base_w = int(getattr(self.config, "capture_width", 1920))
            base_h = int(getattr(self.config, "capture_height", 1080))

            range_x = int(getattr(self.config, "capture_range_x", 128))
            range_y = int(getattr(self.config, "capture_range_y", 128))
            if range_x < 128:
                range_x = max(128, getattr(self.config, "region_size", 200))
            if range_y < 128:
                range_y = max(128, getattr(self.config, "region_size", 200))

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

            x1, y1, x2, y2 = left, top, right, bottom
            frame = frame[y1:y2, x1:x2]

            return frame

        except Exception as e:
            log_print(f"[CaptureCardGStreamer] Error getting frame: {e}")
            return None

    def stop(self):
        """Stop capture card camera."""
        self.running = False

        if self.pipeline:
            # Set pipeline to NULL state
            self.gst_dll.gst_element_set_state(self.pipeline, GST_STATE_NULL)

            # Release references
            if self.appsink:
                self.gst_dll.gst_object_unref(self.appsink)
                self.appsink = None

            self.gst_dll.gst_object_unref(self.pipeline)
            self.pipeline = None

        log_print("[CaptureCardGStreamer] Pipeline stopped and resources released")


def validate_capture_card_gstreamer_config(config) -> Tuple[bool, Optional[str]]:
    """Validate capture-card GStreamer configuration values."""
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
        return False, f"Configuration validation error: {str(e)}"


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
        "capture_range_x": 0,
        "capture_range_y": 0,
        "capture_offset_x": 0,
        "capture_offset_y": 0,
        "capture_center_offset_x": 0,
        "capture_center_offset_y": 0,
    }


if __name__ == "__main__":
    pass
