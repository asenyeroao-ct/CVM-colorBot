"""
CaptureCard 模組
包含所有與 Capture Card 相關的邏輯代碼，可獨立調用
"""

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
        
        # 按優先順序嘗試不同的後端
        preferred_backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        for backend in preferred_backends:
            self.cap = cv2.VideoCapture(self.device_index, backend)
            if self.cap.isOpened():
                # 設置分辨率和幀率
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.frame_width))
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.frame_height))
                self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
                
                # 嘗試設置首選的 fourcc 格式
                for fourcc in self.fourcc_pref:
                    try:
                        fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
                        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc_code)
                        print(f"[CaptureCard] Set fourcc to {fourcc}")
                        break
                    except Exception as e:
                        print(f"[CaptureCard] Failed to set fourcc {fourcc}: {e}")
                        continue
                
                print(f"[CaptureCard] Successfully opened camera {self.device_index} with backend {backend}")
                print(f"[CaptureCard] Resolution: {self.frame_width}x{self.frame_height}, FPS: {self.target_fps}")
                break
            else:
                self.cap.release()
                self.cap = None
        
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open capture card at device index {self.device_index}")

    def get_latest_frame(self):
        """
        獲取最新的視頻幀
        
        Returns:
            numpy.ndarray or None: 最新的視頻幀，如果無法讀取則返回 None
        """
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        
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
            print(f"[Warning] Unknown capture card config key: {key}")


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

