from src.utils.debug_logger import log_print
import numpy as np
from .ndi import NDIManager
import cv2

# 導入 OBS_UDP 模組 (使用 OBS_UDP.py)
try:
    # 優先使用包導入方式 (從 OBS_UDP.py)
    from .OBS_UDP import OBS_UDP_Manager
    HAS_UDP = True
    log_print("[Capture] OBS_UDP module loaded successfully from OBS_UDP.py")
except ImportError as e:
    HAS_UDP = False
    log_print(f"[Capture] OBS_UDP module import failed: {e}")
    log_print("[Capture] UDP mode will be unavailable. Please ensure OBS_UDP.py exists in 'capture/' folder.")

# 嘗試導入 CaptureCard
try:
    from .CaptureCard import create_capture_card_camera
    HAS_CAPTURECARD = True
    log_print("[Capture] CaptureCard module loaded successfully.")
except ImportError as e:
    HAS_CAPTURECARD = False
    log_print(f"[Capture] CaptureCard module import failed: {e}")
    log_print("[Capture] CaptureCard mode will be unavailable.")

# 嘗試導入 MSS
try:
    from .mss_capture import MSSCapture, HAS_MSS
    if HAS_MSS:
        log_print("[Capture] MSS module loaded successfully.")
    else:
        log_print("[Capture] MSS python package not installed. Run: pip install mss")
except ImportError as e:
    HAS_MSS = False
    log_print(f"[Capture] MSS module import failed: {e}")

class CaptureService:
    """
    捕獲服務管理器
    統一管理 NDI、UDP、CaptureCard 和 MSS 四種捕獲方式，提供統一的接口。
    """
    def __init__(self):
        self.mode = "NDI" # "NDI", "UDP", "CaptureCard", or "MSS"
        
        # NDI
        self.ndi = NDIManager()
        
        # UDP
        self.udp_manager = OBS_UDP_Manager() if HAS_UDP else None
        
        # CaptureCard
        self.capture_card_camera = None
        
        # MSS
        self.mss_capture = None
        
        self._ip = "127.0.0.1"
        self._port = 1234

    def set_mode(self, mode):
        """切換捕獲模式"""
        if mode not in ["NDI", "UDP", "CaptureCard", "MSS"]:
            return
        
        # 如果切換模式，先斷開當前連接
        if self.mode != mode:
            self.disconnect()
            
        self.mode = mode

    def get_frame_dimensions(self):
        """
        獲取當前模式的畫面尺寸
        
        Returns:
            tuple: (width, height) 或 (None, None) 如果無法獲取
        """
        if self.mode == "NDI":
            if not self.ndi.is_connected():
                return None, None
            try:
                frame = self.ndi.capture_frame()
                if frame is None:
                    return None, None
                return frame.xres, frame.yres
            except Exception:
                return None, None
        elif self.mode == "UDP":
            if not self.is_connected():
                return None, None
            try:
                receiver = self.udp_manager.get_receiver() if self.udp_manager else None
                if not receiver:
                    return None, None
                frame = receiver.get_current_frame()
                if frame is None or frame.size == 0:
                    return None, None
                h, w = frame.shape[:2]
                return w, h
            except Exception:
                return None, None
        elif self.mode == "MSS":
            if not self.mss_capture or not self.mss_capture.is_connected():
                return None, None
            return self.mss_capture.screen_width, self.mss_capture.screen_height
        return None, None
    
    def get_frame_dimensions(self):
        """
        獲取當前模式的畫面尺寸（需要先連接）
        
        Returns:
            tuple: (width, height) 或 (None, None) 如果無法獲取
        """
        if self.mode == "NDI":
            if not self.ndi.is_connected():
                return None, None
            try:
                frame = self.ndi.capture_frame()
                if frame is None:
                    return None, None
                return frame.xres, frame.yres
            except Exception:
                return None, None
        elif self.mode == "UDP":
            if not self.is_connected():
                return None, None
            try:
                receiver = self.udp_manager.get_receiver() if self.udp_manager else None
                if not receiver:
                    return None, None
                frame = receiver.get_current_frame()
                if frame is None or frame.size == 0:
                    return None, None
                h, w = frame.shape[:2]
                return w, h
            except Exception:
                return None, None
        elif self.mode == "MSS":
            if not self.mss_capture or not self.mss_capture.is_connected():
                return None, None
            return self.mss_capture.screen_width, self.mss_capture.screen_height
        return None, None
    
    def connect_ndi(self, source_name):
        """連接 NDI 來源"""
        self.mode = "NDI"
        return self.ndi.connect_to_source(source_name)

    def connect_udp(self, ip, port):
        """連接 UDP 來源"""
        self.mode = "UDP"
        self._ip = ip
        self._port = int(port)
        
        if not HAS_UDP:
            return False, "UDP module not loaded (OBS_UDP.py missing or failed to import)"
            
        if not self.udp_manager:
            return False, "UDP manager not initialized"
            
        try:
            success = self.udp_manager.connect(self._ip, self._port, target_fps=0)
            if success:
                return True, None
            else:
                return False, "Connection failed - check IP/Port and ensure OBS is streaming"
        except Exception as e:
            log_print(f"[Capture] UDP connection exception: {e}")
            return False, str(e)

    def connect_capture_card(self, config):
        """連接 CaptureCard 來源"""
        self.mode = "CaptureCard"
        
        if not HAS_CAPTURECARD:
            return False, "CaptureCard module not loaded"
        
        try:
            from src.utils.config import config as global_config
            # 使用全局 config 或傳入的 config
            config_to_use = config if config else global_config
            
            self.capture_card_camera = create_capture_card_camera(config_to_use)
            return True, None
        except Exception as e:
            log_print(f"[Capture] CaptureCard connection exception: {e}")
            return False, str(e)

    def connect_mss(self, monitor_index=1, fov_x=320, fov_y=320):
        """連接 MSS 螢幕擷取"""
        self.mode = "MSS"
        
        if not HAS_MSS:
            return False, "MSS module not loaded (pip install mss)"
        
        try:
            self.mss_capture = MSSCapture(
                monitor_index=monitor_index,
                fov_x=fov_x,
                fov_y=fov_y
            )
            success, err = self.mss_capture.connect()
            if success:
                return True, None
            else:
                return False, err
        except Exception as e:
            log_print(f"[Capture] MSS connection exception: {e}")
            return False, str(e)

    def disconnect(self):
        """斷開連接"""
        if self.mode == "NDI":
            pass 
        elif self.mode == "UDP":
            if self.udp_manager:
                self.udp_manager.disconnect()
        elif self.mode == "CaptureCard":
            if self.capture_card_camera:
                self.capture_card_camera.stop()
                self.capture_card_camera = None
        elif self.mode == "MSS":
            if self.mss_capture:
                self.mss_capture.disconnect()
                self.mss_capture = None

    def is_connected(self):
        """檢查當前模式是否已連接"""
        if self.mode == "NDI":
            return self.ndi.is_connected()
        elif self.mode == "UDP":
            if not self.udp_manager:
                return False
            try:
                return self.udp_manager.is_stream_active()
            except:
                return getattr(self.udp_manager, 'is_connected', False)
        elif self.mode == "CaptureCard":
            if not self.capture_card_camera:
                return False
            return self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
        elif self.mode == "MSS":
            if not self.mss_capture:
                return False
            return self.mss_capture.is_connected()
        return False

    def _crop_frame_center(self, frame, fov_x, fov_y):
        """
        以畫面中心為基準裁切畫面
        
        Args:
            frame: numpy.ndarray BGR 格式的圖像
            fov_x: 擷取區域寬度的一半（像素）
            fov_y: 擷取區域高度的一半（像素）
        
        Returns:
            numpy.ndarray: 裁切後的 BGR 圖像
        """
        if frame is None:
            return None
        
        h, w = frame.shape[:2]
        
        # 計算中心點
        center_x = w // 2
        center_y = h // 2
        
        # 計算裁切區域
        left = max(0, center_x - fov_x)
        top = max(0, center_y - fov_y)
        right = min(w, center_x + fov_x)
        bottom = min(h, center_y + fov_y)
        
        # 確保區域有效
        if right <= left or bottom <= top:
            return frame
        
        # 裁切畫面
        cropped = frame[top:bottom, left:right]
        return cropped

    def _apply_mode_fov(self, frame):
        """Apply mode-specific center crop (NDI/UDP only)."""
        if frame is None:
            return None

        from src.utils.config import config as global_config

        if self.mode == "NDI" and getattr(global_config, "ndi_fov_enabled", False):
            fov = int(getattr(global_config, "ndi_fov", 320))
            return self._crop_frame_center(frame, fov, fov)

        if self.mode == "UDP" and getattr(global_config, "udp_fov_enabled", False):
            fov = int(getattr(global_config, "udp_fov", 320))
            return self._crop_frame_center(frame, fov, fov)

        return frame

    def apply_mode_fov(self, frame):
        """Public wrapper for applying mode-specific FOV crop."""
        try:
            return self._apply_mode_fov(frame)
        except Exception:
            return frame

    def read_frame(self, apply_fov=True):
        """
        讀取當前幀
        
        Returns:
            numpy.ndarray: BGR 格式的圖像，如果讀取失敗則返回 None
        """
        if self.mode == "NDI":
            frame = self.ndi.capture_frame()
            if frame is None:
                return None
            
            # NDI 返回的是 VideoFrameSync
            try:
                # 假設 frame 是 RGBA/RGBX，轉換為 numpy
                img = np.array(frame, dtype=np.uint8).reshape((frame.yres, frame.xres, 4))
                # 轉換為 BGR (OpenCV 格式)
                # 原始代碼：bgr_img = img[:, :, [2, 1, 0]].copy()
                # RGBA: R=0, G=1, B=2. 
                # [2, 1, 0] -> B, G, R
                bgr_img = img[:, :, [2, 1, 0]]
                
                # 如果啟用裁切，則應用中心裁切（正方形）
                if apply_fov:
                    bgr_img = self._apply_mode_fov(bgr_img)
                
                return bgr_img
            except Exception as e:
                log_print(f"[Capture] NDI frame conversion error: {e}")
                return None
                
        elif self.mode == "UDP":
            if not self.udp_manager:
                return None
            
            try:
                receiver = self.udp_manager.get_receiver()
                if not receiver:
                    log_print("[Capture] UDP receiver is None")
                    return None
                
                # OBS_UDP_Receiver.get_current_frame() 返回 BGR numpy array
                frame = receiver.get_current_frame()
                if frame is None:
                    # 這是正常的，在剛連接或沒有新幀時會返回 None
                    return None
                
                # 驗證幀的有效性
                if frame.size == 0:
                    return None
                
                # 如果啟用裁切，則應用中心裁切（正方形）
                if apply_fov:
                    frame = self._apply_mode_fov(frame)
                    
                return frame
            except Exception as e:
                log_print(f"[Capture] UDP read frame error: {e}")
                return None
        
        elif self.mode == "CaptureCard":
            if not self.capture_card_camera:
                return None
            
            try:
                # CaptureCardCamera guarantees BGR output before returning.
                frame = self.capture_card_camera.get_latest_frame()
                if frame is None:
                    return None
                
                if frame.size == 0:
                    return None
                    
                return frame
            except Exception as e:
                log_print(f"[Capture] CaptureCard read frame error: {e}")
                return None
        
        elif self.mode == "MSS":
            if not self.mss_capture:
                return None
            
            try:
                # 動態更新 FOV（允許即時調整）
                from src.utils.config import config as global_config
                fov_x = int(getattr(global_config, "mss_fov_x", self.mss_capture.fov_x))
                fov_y = int(getattr(global_config, "mss_fov_y", self.mss_capture.fov_y))
                if fov_x != self.mss_capture.fov_x or fov_y != self.mss_capture.fov_y:
                    self.mss_capture.set_fov(fov_x, fov_y)
                
                frame = self.mss_capture.get_frame()
                if frame is None:
                    return None
                
                if frame.size == 0:
                    return None
                
                return frame
            except Exception as e:
                log_print(f"[Capture] MSS read frame error: {e}")
                return None
            
        return None

    def cleanup(self):
        """清理資源"""
        try:
            self.ndi.cleanup()
        except Exception as e:
            log_print(f"[Capture] NDI cleanup error (ignored): {e}")
        
        try:
            if self.udp_manager and self.udp_manager.is_connected:
                # 抑制 UDP 清理時的錯誤輸出
                import sys
                import io
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                
                try:
                    self.udp_manager.disconnect()
                finally:
                    sys.stderr = old_stderr
        except Exception as e:
            log_print(f"[Capture] UDP cleanup error (ignored): {e}")
        
        try:
            if self.capture_card_camera:
                self.capture_card_camera.stop()
                self.capture_card_camera = None
        except Exception as e:
            log_print(f"[Capture] CaptureCard cleanup error (ignored): {e}")
        
        try:
            if self.mss_capture:
                self.mss_capture.cleanup()
                self.mss_capture = None
        except Exception as e:
            log_print(f"[Capture] MSS cleanup error (ignored): {e}")

