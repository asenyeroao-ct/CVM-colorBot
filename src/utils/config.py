import json
import os

class Config:
    def __init__(self):
        # --- General Settings ---

        self.enableaim = True
        self.enabletb = False
        self.offsetX = -2
        self.offsetY = 3
        
        # --- Aimbot Offsets ---
        self.aim_offsetX = 0  # Aimbot 專用 X 偏移
        self.aim_offsetY = 0  # Aimbot 專用 Y 偏移
        self.aim_type = "head"  # Aimbot 瞄準類型: head, body, nearest

        self.color = "purple"

        
        # --- Mouse / MAKCU ---
        self.selected_mouse_button = 1
        self.selected_tb_btn = 1
        self.selected_2_tb = 2
        self.in_game_sens = 0.235
        self.mouse_dpi = 800
        # --- Aimbot Mode ---
        self.mode = "Normal"    

        self.fovsize = 100
        self.tbfovsize = 5 
        # Triggerbot delay range (隨機範圍，秒)
        self.tbdelay_min = 0.08
        self.tbdelay_max = 0.15
        # Triggerbot hold range (隨機範圍，毫秒)
        self.tbhold_min = 40
        self.tbhold_max = 60
        # Triggerbot 連發設置（範圍）
        self.tbcooldown_min = 0.0  # 冷卻時間最小值（秒）
        self.tbcooldown_max = 0.0  # 冷卻時間最大值（秒）
        self.tbburst_count_min = 1  # 連發次數最小值
        self.tbburst_count_max = 1  # 連發次數最大值
        self.tbburst_interval_min = 0.0  # 連發間隔最小值（毫秒）
        self.tbburst_interval_max = 0.0  # 連發間隔最大值（毫秒）
        
        # RCS (Recoil Control System) 設置
        self.enablercs = False  # 是否啟用 RCS
        self.rcs_pull_speed = 10  # 下拉速度（1-20）
        self.rcs_activation_delay = 100  # 啟動延遲（50-500ms）
        self.rcs_rapid_click_threshold = 200  # 快速點擊閾值（100-1000ms）
        # --- Normal Aim ---
        self.normal_x_speed = 3
        self.normal_y_speed = 3

        self.normalsmooth = 30
        self.normalsmoothfov = 30
        
        # --- Secondary Aimbot ---
        self.enableaim_sec = False
        self.normal_x_speed_sec = 2
        self.normal_y_speed_sec = 2
        self.normalsmooth_sec = 20
        self.normalsmoothfov_sec = 20
        self.fovsize_sec = 150
        self.selected_mouse_button_sec = 2
        self.aim_offsetX_sec = 0  # Sec Aimbot X 偏移
        self.aim_offsetY_sec = 0  # Sec Aimbot Y 偏移
        self.aim_type_sec = "head"  # Sec Aimbot 瞄準類型
        
        # --- Anti-Smoke Settings ---
        self.anti_smoke_enabled = False  # Main Aimbot Anti-Smoke
        self.anti_smoke_enabled_sec = False  # Sec Aimbot Anti-Smoke
        
        # --- OpenCV Display Settings ---
        self.show_opencv_windows = True
        # 單獨的 OpenCV 視窗開關
        self.show_opencv_mask = True  # MASK 視窗（main.py）
        self.show_opencv_detection = True  # Detection 視窗（main.py）
        self.show_opencv_roi = True  # ROI 視窗（Triggerbot.py）
        self.show_opencv_triggerbot_mask = True  # Mask 視窗（Triggerbot.py）
        self.show_mode_text = True
        self.show_aimbot_status = True
        self.show_triggerbot_status = True
        self.show_target_count = True
        self.show_crosshair = True
        self.show_distance_text = True
        
        # --- Capture Settings ---
        self.udp_ip = "127.0.0.1"
        self.udp_port = "1234"
        self.capture_mode = "NDI"
        self.last_ndi_source = None
        
        # --- CaptureCard Settings ---
        self.capture_device_index = 0
        self.capture_width = 1920
        self.capture_height = 1080
        self.capture_fps = 240
        self.capture_fourcc_preference = ["NV12", "YUY2", "MJPG"]
        self.capture_range_x = 128  # 最低值 128
        self.capture_range_y = 128  # 最低值 128
        self.capture_offset_x = 0
        self.capture_offset_y = 0
        
        # --- Button Mask Settings ---
        self.button_mask_enabled = False  # 總開關
        self.mask_left_button = False     # L (0)
        self.mask_right_button = False    # R (1)
        self.mask_middle_button = False   # M (2)
        self.mask_side4_button = False    # S4 (3)
        self.mask_side5_button = False    # S5 (4)
        
        # 載入保存的配置（如果存在）
        self.load_from_file()
    
    def to_dict(self):
        """將配置轉換為字典 - 包含所有設置"""
        return {
            # General Settings
            "enableaim": self.enableaim,
            "enabletb": self.enabletb,
            "offsetX": self.offsetX,
            "offsetY": self.offsetY,
            "aim_offsetX": self.aim_offsetX,
            "aim_offsetY": self.aim_offsetY,
            "aim_type": self.aim_type,
            "color": self.color,
            
            # Mouse / MAKCU
            "selected_mouse_button": self.selected_mouse_button,
            "selected_tb_btn": self.selected_tb_btn,
            "selected_2_tb": self.selected_2_tb,
            "in_game_sens": self.in_game_sens,
            "mouse_dpi": self.mouse_dpi,
            
            # Aimbot Mode
            "mode": self.mode,
            "fovsize": self.fovsize,
            "tbfovsize": self.tbfovsize,
            "tbdelay_min": self.tbdelay_min,
            "tbdelay_max": self.tbdelay_max,
            "tbhold_min": self.tbhold_min,
            "tbhold_max": self.tbhold_max,
            "tbcooldown_min": self.tbcooldown_min,
            "tbcooldown_max": self.tbcooldown_max,
            "tbburst_count_min": self.tbburst_count_min,
            "tbburst_count_max": self.tbburst_count_max,
            "tbburst_interval_min": self.tbburst_interval_min,
            "tbburst_interval_max": self.tbburst_interval_max,
            
            # RCS Settings
            "enablercs": self.enablercs,
            "rcs_pull_speed": self.rcs_pull_speed,
            "rcs_activation_delay": self.rcs_activation_delay,
            "rcs_rapid_click_threshold": self.rcs_rapid_click_threshold,
            
            # Normal Aim
            "normal_x_speed": self.normal_x_speed,
            "normal_y_speed": self.normal_y_speed,
            "normalsmooth": self.normalsmooth,
            "normalsmoothfov": self.normalsmoothfov,
            
            # Secondary Aimbot
            "enableaim_sec": self.enableaim_sec,
            "normal_x_speed_sec": self.normal_x_speed_sec,
            "normal_y_speed_sec": self.normal_y_speed_sec,
            "normalsmooth_sec": self.normalsmooth_sec,
            "normalsmoothfov_sec": self.normalsmoothfov_sec,
            "fovsize_sec": self.fovsize_sec,
            "selected_mouse_button_sec": self.selected_mouse_button_sec,
            "aim_offsetX_sec": self.aim_offsetX_sec,
            "aim_offsetY_sec": self.aim_offsetY_sec,
            "aim_type_sec": self.aim_type_sec,
            
            # Anti-Smoke Settings
            "anti_smoke_enabled": self.anti_smoke_enabled,
            "anti_smoke_enabled_sec": self.anti_smoke_enabled_sec,
            
            # OpenCV Display Settings
            "show_opencv_windows": self.show_opencv_windows,
            "show_opencv_mask": self.show_opencv_mask,
            "show_opencv_detection": self.show_opencv_detection,
            "show_opencv_roi": self.show_opencv_roi,
            "show_opencv_triggerbot_mask": self.show_opencv_triggerbot_mask,
            "show_mode_text": self.show_mode_text,
            "show_aimbot_status": self.show_aimbot_status,
            "show_triggerbot_status": self.show_triggerbot_status,
            "show_target_count": self.show_target_count,
            "show_crosshair": self.show_crosshair,
            "show_distance_text": self.show_distance_text,
            
            # Capture Settings
            "udp_ip": self.udp_ip,
            "udp_port": self.udp_port,
            "capture_mode": self.capture_mode,
            "last_ndi_source": self.last_ndi_source,
            
            # CaptureCard Settings
            "capture_device_index": self.capture_device_index,
            "capture_width": self.capture_width,
            "capture_height": self.capture_height,
            "capture_fps": self.capture_fps,
            "capture_fourcc_preference": self.capture_fourcc_preference,
            "capture_range_x": self.capture_range_x,
            "capture_range_y": self.capture_range_y,
            "capture_offset_x": self.capture_offset_x,
            "capture_offset_y": self.capture_offset_y,
            
            # Button Mask Settings
            "button_mask_enabled": self.button_mask_enabled,
            "mask_left_button": self.mask_left_button,
            "mask_right_button": self.mask_right_button,
            "mask_middle_button": self.mask_middle_button,
            "mask_side4_button": self.mask_side4_button,
            "mask_side5_button": self.mask_side5_button
        }
    
    def from_dict(self, data):
        """從字典載入配置"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def save_to_file(self, filename="config.json"):
        """保存配置到文件"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
            print(f"[Config] Configuration saved to {filename}")
        except Exception as e:
            print(f"[Config] Failed to save configuration: {e}")
    
    def load_from_file(self, filename="config.json"):
        """從文件載入配置"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.from_dict(data)
                print(f"[Config] Configuration loaded from {filename}")
        except Exception as e:
            print(f"[Config] Failed to load configuration: {e}")
    


config = Config()

