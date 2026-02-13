"""
CaptureCard 模組
包含所有與 Capture Card 相關的邏輯代碼，可獨立調用
"""

from src.utils.debug_logger import log_print
import cv2
import numpy as np
from typing import Tuple, Optional, List


class CaptureCardCamera:
    """
    Capture Card 相機類
    用於從捕獲卡設備讀取視頻幀
    """
    
    def __init__(self, config, region=None):
        """
        初始化 Capture Card 相機
        
        Args:
            config: 配置對象，需要包含以下屬性：
                - capture_width: 捕獲寬度（默認 1920）
                - capture_height: 捕獲高度（默認 1080）
                - capture_fps: 目標幀率（默認 240）
                - capture_device_index: 設備索引（默認 0）
                - capture_fourcc_preference: FourCC 格式偏好列表（默認 ["NV12", "YUY2", "MJPG"]）
            region: 可選的區域元組 (left, top, right, bottom)，用於裁剪
        """
        # 從 config 獲取捕獲卡參數
        self.frame_width = int(getattr(config, "capture_width", 1920))
        self.frame_height = int(getattr(config, "capture_height", 1080))
        self.target_fps = float(getattr(config, "capture_fps", 240))
        self.device_index = int(getattr(config, "capture_device_index", 0))
        self.fourcc_pref = list(getattr(config, "capture_fourcc_preference", ["NV12", "YUY2", "MJPG"]))
        self.config = config  # 保存 config 引用以便動態讀取
        
        # 不存儲靜態區域 - 將在 get_latest_frame 中動態計算
        self.cap = None
        self.running = True
        self.backend_used = None
        
        # 優先使用 MSMF 後端（對高 FPS 支持更好）
        preferred_backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        
        for backend in preferred_backends:
            self.cap = cv2.VideoCapture(self.device_index, backend)
            if self.cap.isOpened():
                self.backend_used = backend
                
                # 1. 先設置分辨率
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.frame_width))
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.frame_height))
                
                # 2. 嘗試設置 FourCC 格式（必須在設置 FPS 之前）
                # 不同的格式支持不同的 FPS 範圍，所以要先確定格式
                # 對於每個格式，都嘗試設置並驗證 FPS
                config_success = False
                
                for fourcc in self.fourcc_pref:
                    try:
                        # 重新設置格式
                        fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
                        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc_code)
                        
                        # 驗證格式是否設置成功
                        actual_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                        if actual_fourcc != fourcc_code:
                            log_print(f"[CaptureCard] Format {fourcc} not accepted, got {actual_fourcc}")
                            continue
                        
                        log_print(f"[CaptureCard] Set fourcc to {fourcc}")
                        
                        # 3. 在格式確定後，再設置 FPS（關鍵！）
                        self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
                        
                        # 4. 驗證實際獲得的 FPS
                        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                        fps_diff = abs(actual_fps - self.target_fps)
                        
                        if fps_diff > 1.0:  # 允許 1 FPS 誤差
                            log_print(f"[CaptureCard] Format {fourcc}: Requested {self.target_fps} FPS, but got {actual_fps} FPS")
                            # 如果 FPS 差距太大（例如只有 60），嘗試下一個格式
                            if actual_fps < self.target_fps * 0.5:
                                log_print(f"[CaptureCard] Format {fourcc} doesn't support {self.target_fps} FPS, trying next format...")
                                continue  # 嘗試下一個格式
                            else:
                                # FPS 接近目標，接受這個配置
                                log_print(f"[CaptureCard] FPS close enough: {actual_fps} FPS (target: {self.target_fps})")
                                config_success = True
                                break
                        else:
                            log_print(f"[CaptureCard] FPS set successfully: {actual_fps} FPS (target: {self.target_fps})")
                            config_success = True
                            break
                            
                    except Exception as e:
                        log_print(f"[CaptureCard] Failed to set fourcc {fourcc}: {e}")
                        continue
                
                if not config_success:
                    log_print(f"[CaptureCard] Warning: Could not find a format that supports {self.target_fps} FPS")
                    # 繼續使用當前配置，即使 FPS 不達標
                    actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    log_print(f"[CaptureCard] Using available FPS: {actual_fps}")
                
                # 5. 設置最小緩衝區以降低延遲
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    buffer_size = self.cap.get(cv2.CAP_PROP_BUFFERSIZE)
                    log_print(f"[CaptureCard] Buffer size set to: {buffer_size}")
                except Exception as e:
                    log_print(f"[CaptureCard] Failed to set buffer size: {e}")
                
                # 6. 嘗試啟用硬體加速（如果支援）
                self._try_enable_hardware_acceleration()
                
                # 7. DirectShow 特定優化
                if backend == cv2.CAP_DSHOW:
                    try:
                        # 設置自動曝光為關閉（如果支援）可以降低延遲
                        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 = 手動模式
                        # 設置自動白平衡為關閉
                        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
                    except Exception as e:
                        pass  # 某些設備可能不支援這些屬性
                
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                log_print(f"[CaptureCard] Successfully opened camera {self.device_index} with backend {backend}")
                log_print(f"[CaptureCard] Resolution: {self.frame_width}x{self.frame_height}, FPS: {actual_fps}")
                break
            else:
                if self.cap:
                    self.cap.release()
                self.cap = None
        
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open capture card at device index {self.device_index}")

    def _try_enable_hardware_acceleration(self):
        """
        嘗試啟用硬體加速（如果支援）
        檢查並設置硬體解碼相關屬性
        """
        if self.cap is None:
            return
        
        # 檢查 OpenCV 是否編譯了硬體加速支援
        try:
            # 嘗試設置硬體加速相關屬性（如果後端支援）
            if self.backend_used == cv2.CAP_MSMF:
                # Media Foundation 後端可能支援硬體加速
                try:
                    # CAP_PROP_HW_ACCELERATION = 171 (OpenCV 4.5+)
                    # 嘗試啟用硬體加速
                    if hasattr(cv2, 'CAP_PROP_HW_ACCELERATION'):
                        self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, 1)  # 1 = 啟用
                        hw_accel = self.cap.get(cv2.CAP_PROP_HW_ACCELERATION)
                        if hw_accel > 0:
                            log_print(f"[CaptureCard] Hardware acceleration enabled: {hw_accel}")
                except Exception as e:
                    pass  # 某些版本可能不支援
                    
                # 嘗試設置硬體設備類型
                try:
                    # CAP_PROP_HW_DEVICE = 172 (OpenCV 4.5+)
                    if hasattr(cv2, 'CAP_PROP_HW_DEVICE'):
                        # 0 = AUTO, 1 = D3D11, 2 = CUDA, 3 = OPENCL
                        self.cap.set(cv2.CAP_PROP_HW_DEVICE, 0)  # AUTO
                except Exception as e:
                    pass
        except Exception as e:
            log_print(f"[CaptureCard] Hardware acceleration check failed: {e}")

    def get_latest_frame(self):
        """
        獲取最新的視頻幀
        優化：丟棄緩衝區中的舊幀，只讀取最新幀以降低延遲
        
        Returns:
            numpy.ndarray or None: 最新的視頻幀，如果無法讀取則返回 None
        """
        if not self.cap or not self.cap.isOpened():
            return None
        
        # 優化 3: 丟棄緩衝區中的舊幀，只取最新幀
        # 連續讀取多次以清空緩衝區，最後一次才是最新幀
        # 這樣可以確保獲取的是最新的畫面，而不是緩衝區中的舊畫面
        latest_frame = None
        max_discard = 3  # 最多丟棄 3 幀（根據 240 FPS 和緩衝區設置，通常 1-2 幀就夠了）
        
        for _ in range(max_discard):
            ret, frame = self.cap.read()
            if ret and frame is not None:
                latest_frame = frame
            else:
                # 如果讀取失敗，返回最後一次成功讀取的幀
                break
        
        if latest_frame is None:
            return None
        
        frame = latest_frame
        
        # 動態計算區域基於當前 config 值
        # 這允許在 X/Y Range 或 Offset 更改時實時更新
        base_w = int(getattr(self.config, "capture_width", 1920))
        base_h = int(getattr(self.config, "capture_height", 1080))
        
        # 如果指定了自定義範圍，則使用它，否則使用 region_size
        # 最低值為 128
        range_x = int(getattr(self.config, "capture_range_x", 128))
        range_y = int(getattr(self.config, "capture_range_y", 128))
        if range_x < 128:
            range_x = max(128, getattr(self.config, "region_size", 200))
        if range_y < 128:
            range_y = max(128, getattr(self.config, "region_size", 200))
        
        # 獲取偏移量
        offset_x = int(getattr(self.config, "capture_offset_x", 0))
        offset_y = int(getattr(self.config, "capture_offset_y", 0))
        
        # 計算中心位置：基於 range_x 和 range_y 的中心點 (X/2, Y/2)
        # 中心點相對於整個畫面 (base_w, base_h) 的位置
        center_x = base_w // 2
        center_y = base_h // 2
        
        # 從中心點開始，向左右各延伸 range_x/2，向上下各延伸 range_y/2
        left = center_x - range_x // 2 + offset_x
        top = center_y - range_y // 2 + offset_y
        right = left + range_x
        bottom = top + range_y
        
        # 確保區域在邊界內
        left = max(0, min(left, base_w))
        top = max(0, min(top, base_h))
        right = max(left, min(right, base_w))
        bottom = max(top, min(bottom, base_h))
        
        # 應用區域裁剪
        x1, y1, x2, y2 = left, top, right, bottom
        frame = frame[y1:y2, x1:x2]
        
        return frame

    def stop(self):
        """停止捕獲卡相機"""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None


def get_capture_card_region(config) -> Tuple[int, int, int, int]:
    """
    計算 Capture Card 的捕獲區域
    
    Args:
        config: 配置對象，需要包含以下屬性：
            - capture_width: 捕獲寬度（默認 1920）
            - capture_height: 捕獲高度（默認 1080）
            - capture_range_x: X 軸範圍（0 = 使用 region_size，>0 = 自定義範圍）
            - capture_range_y: Y 軸範圍（0 = 使用 region_size，>0 = 自定義範圍）
            - capture_offset_x: X 軸偏移（像素，可為負數）
            - capture_offset_y: Y 軸偏移（像素，可為負數）
            - region_size: 默認區域大小（如果 range_x/range_y 為 0）
    
    Returns:
        Tuple[int, int, int, int]: (left, top, right, bottom) 區域座標
    """
    base_w = int(getattr(config, "capture_width", getattr(config, "screen_width", 1920)))
    base_h = int(getattr(config, "capture_height", getattr(config, "screen_height", 1080)))
    
    # 如果指定了自定義範圍，則使用它，否則使用 region_size
    range_x = int(getattr(config, "capture_range_x", 0))
    range_y = int(getattr(config, "capture_range_y", 0))
    if range_x <= 0:
        range_x = getattr(config, "region_size", 200)
    if range_y <= 0:
        range_y = getattr(config, "region_size", 200)
    
    # 獲取偏移量
    offset_x = int(getattr(config, "capture_offset_x", 0))
    offset_y = int(getattr(config, "capture_offset_y", 0))
    
    # 計算中心位置並應用偏移量
    left = (base_w - range_x) // 2 + offset_x
    top = (base_h - range_y) // 2 + offset_y
    right = left + range_x
    bottom = top + range_y
    
    # 確保區域在邊界內
    left = max(0, min(left, base_w))
    top = max(0, min(top, base_h))
    right = max(left, min(right, base_w))
    bottom = max(top, min(bottom, base_h))
    
    return (left, top, right, bottom)


def validate_capture_card_config(config) -> Tuple[bool, Optional[str]]:
    """
    驗證 Capture Card 配置是否有效
    
    Args:
        config: 配置對象
    
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 錯誤訊息)
    """
    try:
        # 檢查必要的配置屬性
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
    """
    創建 Capture Card 相機實例的工廠函數
    
    Args:
        config: 配置對象
        region: 可選的區域元組 (left, top, right, bottom)
    
    Returns:
        CaptureCardCamera: Capture Card 相機實例
    
    Raises:
        RuntimeError: 如果無法打開捕獲卡設備
        ValueError: 如果配置無效
    """
    # 驗證配置
    is_valid, error_msg = validate_capture_card_config(config)
    if not is_valid:
        raise ValueError(f"Invalid capture card configuration: {error_msg}")
    
    # 創建相機實例
    return CaptureCardCamera(config, region)


# 配置輔助函數
def get_default_capture_card_config() -> dict:
    """
    獲取默認的 Capture Card 配置
    
    Returns:
        dict: 默認配置字典
    """
    return {
        "capture_width": 1920,
        "capture_height": 1080,
        "capture_fps": 240,
        "capture_device_index": 0,
        "capture_fourcc_preference": ["NV12", "YUY2", "MJPG"],
        "capture_range_x": 0,
        "capture_range_y": 0,
        "capture_offset_x": 0,
        "capture_offset_y": 0,
        "capture_center_offset_x": 0,
        "capture_center_offset_y": 0,
    }


def apply_capture_card_config(config, **kwargs):
    """
    將配置值應用到配置對象
    
    Args:
        config: 配置對象
        **kwargs: 要設置的配置鍵值對
            - capture_width: 捕獲寬度
            - capture_height: 捕獲高度
            - capture_fps: 目標幀率
            - capture_device_index: 設備索引
            - capture_fourcc_preference: FourCC 格式偏好列表
            - capture_range_x: X 軸範圍
            - capture_range_y: Y 軸範圍
            - capture_offset_x: X 軸偏移
            - capture_offset_y: Y 軸偏移
            - capture_center_offset_x: X 軸中心偏移
            - capture_center_offset_y: Y 軸中心偏移
    """
    valid_keys = {
        "capture_width", "capture_height", "capture_fps",
        "capture_device_index", "capture_fourcc_preference",
        "capture_range_x", "capture_range_y",
        "capture_offset_x", "capture_offset_y",
        "capture_center_offset_x", "capture_center_offset_y"
    }
    
    for key, value in kwargs.items():
        if key in valid_keys:
            setattr(config, key, value)
        else:
            log_print(f"[Warning] Unknown capture card config key: {key}")


# 使用示例（僅供參考，不會被執行）
if __name__ == "__main__":
    """
    使用示例：
    
    # 方式 1: 使用現有的 config 對象
    from src.utils.config import config
    from src.capture.CaptureCard import create_capture_card_camera, get_capture_card_region
    
    # 創建相機
    camera = create_capture_card_camera(config)
    
    # 獲取區域
    region = get_capture_card_region(config)
    
    # 讀取幀
    frame = camera.get_latest_frame()
    
    # 停止相機
    camera.stop()
    
    # 方式 2: 使用自定義配置
    class MyConfig:
        capture_width = 1920
        capture_height = 1080
        capture_fps = 240
        capture_device_index = 0
        capture_fourcc_preference = ["NV12", "YUY2", "MJPG"]
        capture_range_x = 0
        capture_range_y = 0
        capture_offset_x = 0
        capture_offset_y = 0
        region_size = 200
    
    my_config = MyConfig()
    camera = create_capture_card_camera(my_config)
    """
    pass

