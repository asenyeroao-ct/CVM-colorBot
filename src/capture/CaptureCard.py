"""
CaptureCard module.
Contains capture-card specific capture and frame normalization logic.
"""

from src.utils.debug_logger import log_print
import cv2
from typing import Optional, Tuple


class CaptureCardCamera:
    """Capture Card camera wrapper."""

    def __init__(self, config, region=None):
        del region  # reserved for compatibility

        self.frame_width = int(getattr(config, "capture_width", 1920))
        self.frame_height = int(getattr(config, "capture_height", 1080))
        self.target_fps = float(getattr(config, "capture_fps", 240))
        self.device_index = int(getattr(config, "capture_device_index", 0))
        self.fourcc_pref = list(getattr(config, "capture_fourcc_preference", ["NV12", "YUY2", "MJPG"]))

        self.force_bgr = bool(getattr(config, "capture_card_force_bgr", True))
        self.set_convert_rgb = bool(getattr(config, "capture_card_set_convert_rgb", True))
        self.probe_frames = max(1, int(getattr(config, "capture_card_probe_frames", 3)))
        self.debug_color_log = bool(getattr(config, "capture_card_debug_color_log", False))

        self.config = config
        self.cap = None
        self.running = True
        self.backend_used = None
        self.active_fourcc = None

        preferred_backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]

        for backend in preferred_backends:
            self.cap = cv2.VideoCapture(self.device_index, backend)
            if not self.cap.isOpened():
                if self.cap:
                    self.cap.release()
                self.cap = None
                continue

            self.backend_used = backend
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.frame_width))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.frame_height))

            if self.set_convert_rgb and hasattr(cv2, "CAP_PROP_CONVERT_RGB"):
                try:
                    self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
                except Exception:
                    pass

            config_success = False

            for fourcc in self.fourcc_pref:
                try:
                    fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
                    self.cap.set(cv2.CAP_PROP_FOURCC, fourcc_code)

                    actual_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                    if actual_fourcc != fourcc_code:
                        log_print(f"[CaptureCard] Format {fourcc} not accepted, got {actual_fourcc}")
                        continue

                    log_print(f"[CaptureCard] Set fourcc to {fourcc}")
                    self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))

                    actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    fps_diff = abs(actual_fps - self.target_fps)
                    if fps_diff > 1.0:
                        log_print(
                            f"[CaptureCard] Format {fourcc}: Requested {self.target_fps} FPS, "
                            f"but got {actual_fps} FPS"
                        )
                        if actual_fps < self.target_fps * 0.5:
                            log_print(
                                f"[CaptureCard] Format {fourcc} doesn't support "
                                f"{self.target_fps} FPS, trying next format..."
                            )
                            continue
                        log_print(
                            f"[CaptureCard] FPS close enough: {actual_fps} FPS "
                            f"(target: {self.target_fps})"
                        )
                    else:
                        log_print(
                            f"[CaptureCard] FPS set successfully: {actual_fps} FPS "
                            f"(target: {self.target_fps})"
                        )

                    if not self._probe_frame_format(fourcc):
                        log_print(f"[CaptureCard] Format {fourcc} failed probe validation, trying next format...")
                        continue

                    self.active_fourcc = fourcc
                    config_success = True
                    break
                except Exception as e:
                    log_print(f"[CaptureCard] Failed to set fourcc {fourcc}: {e}")
                    continue

            if not config_success:
                log_print(f"[CaptureCard] Warning: Could not find a format that supports {self.target_fps} FPS")
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                log_print(f"[CaptureCard] Using available FPS: {actual_fps}")
                self.active_fourcc = self._read_active_fourcc_label()

            # 不設置 buffer size，使用默認值以獲得更好的性能
            # 設置為 1 會導致每次讀取都要等待新幀，嚴重限制 FPS
            # try:
            #     self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            #     buffer_size = self.cap.get(cv2.CAP_PROP_BUFFERSIZE)
            #     log_print(f"[CaptureCard] Buffer size set to: {buffer_size}")
            # except Exception as e:
            #     log_print(f"[CaptureCard] Failed to set buffer size: {e}")

            self._try_enable_hardware_acceleration()

            if backend == cv2.CAP_DSHOW:
                try:
                    self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                    self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
                except Exception:
                    pass

            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            log_print(f"[CaptureCard] Successfully opened camera {self.device_index} with backend {backend}")
            log_print(f"[CaptureCard] Resolution: {self.frame_width}x{self.frame_height}, FPS: {actual_fps}")
            if self.active_fourcc:
                log_print(f"[CaptureCard] Active fourcc: {self.active_fourcc}")
            break

        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open capture card at device index {self.device_index}")

    def _try_enable_hardware_acceleration(self):
        """Try enabling hardware acceleration if supported by backend/OpenCV build."""
        if self.cap is None:
            return

        try:
            if self.backend_used == cv2.CAP_MSMF:
                try:
                    if hasattr(cv2, "CAP_PROP_HW_ACCELERATION"):
                        self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, 1)
                        hw_accel = self.cap.get(cv2.CAP_PROP_HW_ACCELERATION)
                        if hw_accel > 0:
                            log_print(f"[CaptureCard] Hardware acceleration enabled: {hw_accel}")
                except Exception:
                    pass

                try:
                    if hasattr(cv2, "CAP_PROP_HW_DEVICE"):
                        self.cap.set(cv2.CAP_PROP_HW_DEVICE, 0)
                except Exception:
                    pass
        except Exception as e:
            log_print(f"[CaptureCard] Hardware acceleration check failed: {e}")

    @staticmethod
    def _decode_fourcc_int(fourcc_int: int) -> str:
        try:
            val = int(fourcc_int)
            return "".join(chr((val >> (8 * i)) & 0xFF) for i in range(4))
        except Exception:
            return "UNKN"

    def _read_active_fourcc_label(self) -> str:
        if self.cap is None:
            return "UNKN"
        try:
            return self._decode_fourcc_int(self.cap.get(cv2.CAP_PROP_FOURCC)).strip()
        except Exception:
            return "UNKN"

    def _log_color_debug(self, frame, stage: str):
        if not self.debug_color_log:
            return
        try:
            convert_rgb = None
            if self.cap is not None and hasattr(cv2, "CAP_PROP_CONVERT_RGB"):
                convert_rgb = self.cap.get(cv2.CAP_PROP_CONVERT_RGB)
            log_print(
                f"[CaptureCard] {stage}: shape={getattr(frame, 'shape', None)}, "
                f"dtype={getattr(frame, 'dtype', None)}, fourcc={self.active_fourcc}, "
                f"convert_rgb={convert_rgb}"
            )
        except Exception:
            pass

    def _normalize_frame_to_bgr(self, frame, active_fourcc: Optional[str]):
        if frame is None:
            return None

        if frame.ndim == 3 and frame.shape[2] == 3:
            return frame

        if frame.ndim == 3 and frame.shape[2] == 4:
            try:
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                return None

        fmt = str(active_fourcc or "").strip().upper()

        if frame.ndim == 3 and frame.shape[2] == 2:
            if fmt == "YUY2":
                try:
                    return cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUY2)
                except Exception:
                    return None

            for conv in ("COLOR_YUV2BGR_YUY2", "COLOR_YUV2BGR_YUYV", "COLOR_YUV2BGR_UYVY"):
                if hasattr(cv2, conv):
                    try:
                        return cv2.cvtColor(frame, getattr(cv2, conv))
                    except Exception:
                        continue
            return None

        if frame.ndim == 2:
            if fmt == "NV12":
                try:
                    return cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_NV12)
                except Exception:
                    return None

            if fmt == "YUY2":
                try:
                    return cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUY2)
                except Exception:
                    return None

            for conv in ("COLOR_YUV2BGR_NV12", "COLOR_YUV2BGR_NV21", "COLOR_YUV2BGR_YUY2", "COLOR_YUV2BGR_YUYV"):
                if hasattr(cv2, conv):
                    try:
                        return cv2.cvtColor(frame, getattr(cv2, conv))
                    except Exception:
                        continue
            return None

        return None

    def _probe_frame_format(self, fourcc: str) -> bool:
        for _ in range(self.probe_frames):
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                return False

            if self.force_bgr:
                normalized = self._normalize_frame_to_bgr(frame, fourcc)
                if normalized is None or normalized.size == 0:
                    return False
                if normalized.ndim != 3 or normalized.shape[2] != 3:
                    return False
        return True

    def get_latest_frame(self):
        """Get latest frame from capture card and return BGR image (or None)."""
        if not self.cap or not self.cap.isOpened():
            return None

        # 只讀取一幀，避免多幀丟棄造成的延遲和性能損失
        # 舊版使用單次讀取可以達到 240 FPS
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        self._log_color_debug(frame, "raw")

        # 只有在需要時才進行 BGR 轉換
        # 如果已經是 3 通道 BGR 格式，則跳過轉換以提高性能
        if self.force_bgr:
            # 檢查是否已經是 BGR 格式（3 通道）
            if not (frame.ndim == 3 and frame.shape[2] == 3):
                frame = self._normalize_frame_to_bgr(frame, self.active_fourcc)
                if frame is None or frame.size == 0:
                    return None
            self._log_color_debug(frame, "normalized_bgr")

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

    def stop(self):
        """Stop capture card camera."""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None


def get_capture_card_region(config) -> Tuple[int, int, int, int]:
    """Calculate capture-card capture region."""
    base_w = int(getattr(config, "capture_width", getattr(config, "screen_width", 1920)))
    base_h = int(getattr(config, "capture_height", getattr(config, "screen_height", 1080)))

    range_x = int(getattr(config, "capture_range_x", 0))
    range_y = int(getattr(config, "capture_range_y", 0))
    if range_x <= 0:
        range_x = getattr(config, "region_size", 200)
    if range_y <= 0:
        range_y = getattr(config, "region_size", 200)

    offset_x = int(getattr(config, "capture_offset_x", 0))
    offset_y = int(getattr(config, "capture_offset_y", 0))

    left = (base_w - range_x) // 2 + offset_x
    top = (base_h - range_y) // 2 + offset_y
    right = left + range_x
    bottom = top + range_y

    left = max(0, min(left, base_w))
    top = max(0, min(top, base_h))
    right = max(left, min(right, base_w))
    bottom = max(top, min(bottom, base_h))

    return left, top, right, bottom


def validate_capture_card_config(config) -> Tuple[bool, Optional[str]]:
    """Validate capture-card configuration values."""
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

        fourcc_list = getattr(config, "capture_fourcc_preference", ["NV12", "YUY2", "MJPG"])
        if not isinstance(fourcc_list, list) or len(fourcc_list) == 0:
            return False, "FourCC preference must be a non-empty list"

        return True, None
    except Exception as e:
        return False, f"Configuration validation error: {str(e)}"


def create_capture_card_camera(config, region=None):
    """Factory for CaptureCardCamera."""
    is_valid, error_msg = validate_capture_card_config(config)
    if not is_valid:
        raise ValueError(f"Invalid capture card configuration: {error_msg}")
    return CaptureCardCamera(config, region)


def get_default_capture_card_config() -> dict:
    """Get default capture-card config dict."""
    return {
        "capture_width": 1920,
        "capture_height": 1080,
        "capture_fps": 240,
        "capture_device_index": 0,
        "capture_fourcc_preference": ["NV12", "YUY2", "MJPG"],
        "capture_card_force_bgr": True,
        "capture_card_set_convert_rgb": True,
        "capture_card_probe_frames": 3,
        "capture_card_debug_color_log": False,
        "capture_range_x": 0,
        "capture_range_y": 0,
        "capture_offset_x": 0,
        "capture_offset_y": 0,
        "capture_center_offset_x": 0,
        "capture_center_offset_y": 0,
    }


def apply_capture_card_config(config, **kwargs):
    """Apply capture-card config values to an existing config object."""
    valid_keys = {
        "capture_width", "capture_height", "capture_fps",
        "capture_device_index", "capture_fourcc_preference",
        "capture_card_force_bgr", "capture_card_set_convert_rgb",
        "capture_card_probe_frames", "capture_card_debug_color_log",
        "capture_range_x", "capture_range_y",
        "capture_offset_x", "capture_offset_y",
        "capture_center_offset_x", "capture_center_offset_y"
    }

    for key, value in kwargs.items():
        if key in valid_keys:
            setattr(config, key, value)
        else:
            log_print(f"[Warning] Unknown capture card config key: {key}")


if __name__ == "__main__":
    pass
