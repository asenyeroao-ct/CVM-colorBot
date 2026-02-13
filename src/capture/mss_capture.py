"""
MSS 螢幕擷取模組
使用 mss 進行高效螢幕擷取，基於螢幕中心點和可調 FOV 範圍
"""

from src.utils.debug_logger import log_print
import numpy as np
import threading
import time

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    log_print("[MSS] mss module not installed. Run: pip install mss")


class MSSCapture:
    """
    MSS 螢幕擷取器
    以螢幕中心為基準，根據 FOV 大小擷取指定範圍的畫面
    
    注意：mss 的 GDI handle 在 Windows 上是 thread-local 的，
    因此使用 threading.local() 確保每個執行緒有自己的 mss 實例。
    """
    
    def __init__(self, monitor_index=1, fov_x=320, fov_y=320):
        """
        初始化 MSS 擷取器
        
        Args:
            monitor_index: 螢幕索引（1=主螢幕, 2=第二螢幕...）
            fov_x: 擷取區域寬度的一半（像素）
            fov_y: 擷取區域高度的一半（像素）
        """
        if not HAS_MSS:
            raise RuntimeError("mss module not installed. Run: pip install mss")
        
        self.monitor_index = monitor_index
        self.fov_x = fov_x
        self.fov_y = fov_y
        
        # 使用 thread-local 儲存 mss 實例（Windows GDI handle 不可跨執行緒）
        self._thread_local = threading.local()
        self._connected = False
        
        # 螢幕資訊（連接後填入，所有執行緒共用）
        self.screen_width = 0
        self.screen_height = 0
        self.center_x = 0
        self.center_y = 0
        self._monitor_info = None  # 快取 monitor dict
        
        # 效能統計
        self._fps_counter = 0
        self._fps_last_time = time.time()
        self.current_fps = 0.0
        self._last_grab_time = 0.0
        self.grab_delay_ms = 0.0
    
    def _get_sct(self):
        """取得當前執行緒的 mss 實例（lazy init per-thread）"""
        sct = getattr(self._thread_local, 'sct', None)
        if sct is None:
            sct = mss.mss()
            self._thread_local.sct = sct
        return sct
    
    def connect(self):
        """
        初始化 MSS 並讀取螢幕資訊
        
        Returns:
            tuple: (成功與否, 錯誤訊息或 None)
        """
        try:
            sct = self._get_sct()
            
            # 取得螢幕列表
            monitors = sct.monitors
            if self.monitor_index >= len(monitors):
                return False, f"Monitor index {self.monitor_index} not found. Available: {len(monitors) - 1}"
            
            mon = monitors[self.monitor_index]
            self.screen_width = mon["width"]
            self.screen_height = mon["height"]
            self.center_x = mon["left"] + self.screen_width // 2
            self.center_y = mon["top"] + self.screen_height // 2
            self._monitor_info = mon
            
            self._connected = True
            self._fps_last_time = time.time()
            self._fps_counter = 0
            
            return True, None
        except Exception as e:
            self._connected = False
            return False, str(e)
    
    def disconnect(self):
        """斷開 MSS 擷取"""
        self._connected = False
        # 清理當前執行緒的 sct
        sct = getattr(self._thread_local, 'sct', None)
        if sct:
            try:
                sct.close()
            except Exception:
                pass
            self._thread_local.sct = None
    
    def is_connected(self):
        """檢查是否已連接"""
        return self._connected
    
    def set_fov(self, fov_x, fov_y):
        """
        設置擷取範圍（FOV）
        
        Args:
            fov_x: 擷取區域寬度的一半（像素）
            fov_y: 擷取區域高度的一半（像素）
        """
        self.fov_x = max(16, int(fov_x))
        self.fov_y = max(16, int(fov_y))
    
    def set_monitor(self, monitor_index):
        """
        切換螢幕索引（需重新連接）
        
        Args:
            monitor_index: 螢幕索引
        """
        self.monitor_index = monitor_index
    
    def get_monitor_list(self):
        """
        取得可用螢幕列表
        
        Returns:
            list: 螢幕資訊字串列表
        """
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                result = []
                for i, mon in enumerate(monitors):
                    if i == 0:
                        continue  # index 0 是所有螢幕的合併
                    result.append(f"Monitor {i}: {mon['width']}x{mon['height']}")
                return result
        except Exception as e:
            log_print(f"[MSS] Failed to get monitor list: {e}")
            return []
    
    def get_frame(self):
        """
        擷取以螢幕中心為基準的 FOV 範圍畫面
        
        Returns:
            numpy.ndarray: BGR 格式的圖像（contiguous），失敗返回 None
        """
        if not self._connected:
            return None
        
        try:
            grab_start = time.time()
            
            # 取得當前執行緒的 mss 實例
            sct = self._get_sct()
            
            # 計算擷取區域（基於中心點）
            left = self.center_x - self.fov_x
            top = self.center_y - self.fov_y
            width = self.fov_x * 2
            height = self.fov_y * 2
            
            region = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            
            # 擷取螢幕
            screenshot = sct.grab(region)
            
            # 轉換為 numpy array (BGRA → BGR)
            # 使用 np.ascontiguousarray 確保記憶體連續，避免 OpenCV 錯誤
            img = np.array(screenshot, dtype=np.uint8)
            bgr = np.ascontiguousarray(img[:, :, :3])
            
            # 更新效能統計
            grab_end = time.time()
            self.grab_delay_ms = (grab_end - grab_start) * 1000.0
            self._last_grab_time = grab_end
            
            self._fps_counter += 1
            elapsed = grab_end - self._fps_last_time
            if elapsed >= 1.0:
                self.current_fps = self._fps_counter / elapsed
                self._fps_counter = 0
                self._fps_last_time = grab_end
            
            return bgr
            
        except Exception as e:
            log_print(f"[MSS] get_frame error: {e}")
            return None
    
    def get_performance_stats(self):
        """
        取得效能統計資訊
        
        Returns:
            dict: 包含 fps, grab_delay_ms
        """
        return {
            "current_fps": self.current_fps,
            "grab_delay_ms": self.grab_delay_ms,
        }
    
    def cleanup(self):
        """清理資源"""
        self.disconnect()
