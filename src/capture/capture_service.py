import numpy as np
from .ndi import NDIManager
import cv2

# 導入 OBS_UDP 模組 (使用 OBS_UDP.py)
try:
    # 優先使用包導入方式 (從 OBS_UDP.py)
        from .OBS_UDP import OBS_UDP_Manager
        HAS_UDP = True
    print("[Capture] OBS_UDP module loaded successfully from OBS_UDP.py")
except ImportError as e:
    HAS_UDP = False
    print(f"[Capture] OBS_UDP module import failed: {e}")
    print("[Capture] UDP mode will be unavailable. Please ensure OBS_UDP.py exists in 'capture/' folder.")

# 嘗試導入 CaptureCard
try:
    from .CaptureCard import create_capture_card_camera
    HAS_CAPTURECARD = True
    print("[Capture] CaptureCard module loaded successfully.")
except ImportError as e:
    HAS_CAPTURECARD = False
    print(f"[Capture] CaptureCard module import failed: {e}")
    print("[Capture] CaptureCard mode will be unavailable.")

class CaptureService:
    """
    捕獲服務管理器
    統一管理 NDI、UDP 和 CaptureCard 三種捕獲方式，提供統一的接口。
    """
    def __init__(self):
        self.mode = "NDI" # "NDI", "UDP", or "CaptureCard"
        
        # NDI
        self.ndi = NDIManager()
        
        # UDP
        self.udp_manager = OBS_UDP_Manager() if HAS_UDP else None
        
        # CaptureCard
        self.capture_card_camera = None
        
        self._ip = "127.0.0.1"
        self._port = 1234

    def set_mode(self, mode):
        """切換捕獲模式"""
        if mode not in ["NDI", "UDP", "CaptureCard"]:
            return
        
        # 如果切換模式，先斷開當前連接
        if self.mode != mode:
            self.disconnect()
            
        self.mode = mode

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
            print(f"[Capture] Attempting to connect to UDP {self._ip}:{self._port}...")
            # 使用 OBS_UDP.py 的 API: connect(ip, port, target_fps)
            # target_fps=0 表示不限制 FPS，讓系統自動處理
            success = self.udp_manager.connect(self._ip, self._port, target_fps=0)
            if success:
                print(f"[Capture] UDP connected successfully to {self._ip}:{self._port}")
                return True, None
            else:
                print(f"[Capture] UDP connection failed to {self._ip}:{self._port}")
                return False, "Connection failed - check IP/Port and ensure OBS is streaming"
        except Exception as e:
            print(f"[Capture] UDP connection exception: {e}")
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
            
            print(f"[Capture] Attempting to connect to CaptureCard...")
            self.capture_card_camera = create_capture_card_camera(config_to_use)
            print(f"[Capture] CaptureCard connected successfully")
            return True, None
        except Exception as e:
            print(f"[Capture] CaptureCard connection exception: {e}")
            return False, str(e)

    def disconnect(self):
        """斷開連接"""
        if self.mode == "NDI":
            # NDI cleanup/disconnect logic if exposed
            # 目前 NDI 類主要通過 set_source(None) 在 cleanup 中處理，
            # 這裡我們可以暫時不強制斷開，或者擴展 NDI 類
            pass 
        elif self.mode == "UDP":
            if self.udp_manager:
                self.udp_manager.disconnect()
        elif self.mode == "CaptureCard":
            if self.capture_card_camera:
                self.capture_card_camera.stop()
                self.capture_card_camera = None

    def is_connected(self):
        """檢查當前模式是否已連接"""
        if self.mode == "NDI":
            return self.ndi.is_connected()
        elif self.mode == "UDP":
            if not self.udp_manager:
                return False
            # 使用 is_stream_active() 方法而不是 is_connected 屬性
            try:
                return self.udp_manager.is_stream_active()
            except:
                # 如果方法失敗，回退到屬性檢查
                return getattr(self.udp_manager, 'is_connected', False)
        elif self.mode == "CaptureCard":
            if not self.capture_card_camera:
                return False
            return self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
        return False

    def read_frame(self):
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
                return img[:, :, [2, 1, 0]]
            except Exception as e:
                print(f"[Capture] NDI frame conversion error: {e}")
                return None
                
        elif self.mode == "UDP":
            if not self.udp_manager:
                return None
            
            try:
                receiver = self.udp_manager.get_receiver()
                if not receiver:
                    print("[Capture] UDP receiver is None")
                    return None
                
                # OBS_UDP_Receiver.get_current_frame() 返回 BGR numpy array
                frame = receiver.get_current_frame()
                if frame is None:
                    # 這是正常的，在剛連接或沒有新幀時會返回 None
                    return None
                
                # 驗證幀的有效性
                if frame.size == 0:
                    return None
                    
                return frame
            except Exception as e:
                print(f"[Capture] UDP read frame error: {e}")
                return None
        
        elif self.mode == "CaptureCard":
            if not self.capture_card_camera:
                return None
            
            try:
                frame = self.capture_card_camera.get_latest_frame()
                if frame is None:
                    return None
                
                # 驗證幀的有效性
                if frame.size == 0:
                    return None
                    
                return frame
            except Exception as e:
                print(f"[Capture] CaptureCard read frame error: {e}")
                return None
            
        return None

    def cleanup(self):
        """清理資源"""
        try:
            self.ndi.cleanup()
        except Exception as e:
            print(f"[Capture] NDI cleanup error (ignored): {e}")
        
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
            print(f"[Capture] UDP cleanup error (ignored): {e}")
        
        try:
            if self.capture_card_camera:
                self.capture_card_camera.stop()
                self.capture_card_camera = None
        except Exception as e:
            print(f"[Capture] CaptureCard cleanup error (ignored): {e}")

