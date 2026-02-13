from src.utils.debug_logger import log_print
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
        
        # --- Detection Parameters ---
        self.detection_merge_distance = 250  # 矩形合併距離閾值 (50-500)
        self.detection_min_contour_points = 5  # 最小輪廓點數 (3-100)
        
        # --- Custom HSV Settings ---
        self.custom_hsv_min_h = 0    # H 最小值 (0-179)
        self.custom_hsv_min_s = 0    # S 最小值 (0-255)
        self.custom_hsv_min_v = 0    # V 最小值 (0-255)
        self.custom_hsv_max_h = 179  # H 最大值 (0-179)
        self.custom_hsv_max_s = 255  # S 最大值 (0-255)
        self.custom_hsv_max_v = 255  # V 最大值 (0-255)

        
        # --- Mouse / MAKCU ---
        self.selected_mouse_button = 1
        self.selected_tb_btn = 1
        self.selected_2_tb = 2
        self.in_game_sens = 0.235
        self.mouse_dpi = 800
        self.mouse_api = "Serial"  # Serial, Arduino, SendInput, Net, MakV2, DHZ
        self.auto_connect_mouse_api = False
        self.serial_port_mode = "Auto"  # Auto, Manual
        self.serial_port = ""
        self.arduino_port = ""
        self.arduino_baud = 115200
        self.arduino_16_bit_mouse = True
        self.net_ip = "192.168.2.188"
        self.net_port = "6234"
        self.net_uuid = ""
        self.net_mac = ""  # deprecated alias of net_uuid
        self.makv2_port = ""
        self.makv2_baud = 4000000
        self.dhz_ip = "192.168.2.188"
        self.dhz_port = "5000"
        self.dhz_random = 0
        # --- Aimbot Activation Type ---
        self.aimbot_activation_type = "hold_enable"  # Main Aimbot: hold_enable, hold_disable, toggle, use_enable
        self.aimbot_activation_type_sec = "hold_enable"  # Sec Aimbot: hold_enable, hold_disable, toggle, use_enable
        # --- Aimbot Mode ---
        self.mode = "Normal"        # Main Aimbot 模式: Normal, Silent, NCAF, WindMouse, Bezier
        self.mode_sec = "Normal"    # Sec Aimbot 模式: Normal, Silent, NCAF, WindMouse, Bezier

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
        # RCS Y 軸解鎖設置
        self.rcs_release_y_enabled = False  # 是否啟用左鍵按下時解鎖 Y 軸移動
        self.rcs_release_y_duration = 1.0  # Y 軸解鎖持續時間（0.1~5秒）
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
        
        # --- NCAF Parameters (Main) ---
        # Snap Radius = outer engagement zone (larger), Near Radius = inner precision zone (smaller)
        self.ncaf_snap_radius = 150.0
        self.ncaf_near_radius = 50.0
        self.ncaf_alpha = 1.5
        self.ncaf_snap_boost = 0.3
        self.ncaf_max_step = 50.0
        self.ncaf_min_speed_multiplier = 0.01  # 滑鼠移動速度的最小倍率
        self.ncaf_max_speed_multiplier = 10.0  # 滑鼠移動速度的最大倍率
        self.ncaf_prediction_interval = 0.016  # 目標預測函數的處理速度（秒，約60fps）
        
        # --- NCAF Parameters (Sec) ---
        self.ncaf_snap_radius_sec = 150.0
        self.ncaf_near_radius_sec = 50.0
        self.ncaf_alpha_sec = 1.5
        self.ncaf_snap_boost_sec = 0.3
        self.ncaf_max_step_sec = 50.0
        self.ncaf_min_speed_multiplier_sec = 0.01  # 滑鼠移動速度的最小倍率
        self.ncaf_max_speed_multiplier_sec = 10.0  # 滑鼠移動速度的最大倍率
        self.ncaf_prediction_interval_sec = 0.016  # 目標預測函數的處理速度（秒，約60fps）
        
        # --- WindMouse Parameters (Main) ---
        self.wm_gravity = 9.0
        self.wm_wind = 3.0
        self.wm_max_step = 15.0
        self.wm_min_step = 2.0
        self.wm_min_delay = 0.001
        self.wm_max_delay = 0.003
        self.wm_distance_threshold = 50.0  # 距離閾值，低於此值時移動更精確
        
        # --- WindMouse Parameters (Sec) ---
        self.wm_gravity_sec = 9.0
        self.wm_wind_sec = 3.0
        self.wm_max_step_sec = 15.0
        self.wm_min_step_sec = 2.0
        self.wm_min_delay_sec = 0.001
        self.wm_max_delay_sec = 0.003
        self.wm_distance_threshold_sec = 50.0  # 距離閾值，低於此值時移動更精確
        
        # --- Bezier Parameters (Main) ---
        self.bezier_segments = 8
        self.bezier_ctrl_x = 16.0
        self.bezier_ctrl_y = 16.0
        self.bezier_speed = 1.0
        self.bezier_delay = 0.002
        
        # --- Bezier Parameters (Sec) ---
        self.bezier_segments_sec = 8
        self.bezier_ctrl_x_sec = 16.0
        self.bezier_ctrl_y_sec = 16.0
        self.bezier_speed_sec = 1.0
        self.bezier_delay_sec = 0.002
        
        # --- Silent Mode Parameters ---
        self.silent_distance = 1.0  # 移動倍率（用於調整移動距離的倍數）
        self.silent_delay = 100.0  # 兩次開槍的最小間隔（毫秒）
        self.silent_move_delay = 500.0  # 移動滑鼠到目標位置的延遲（毫秒）
        self.silent_return_delay = 500.0  # 移動回原位置的延遲（毫秒）
        
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
        self.show_ndi_raw_stream_window = False
        self.show_udp_raw_stream_window = False
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
        
        # --- MSS Settings ---
        self.mss_monitor_index = 1  # 螢幕索引 (1=主螢幕)
        self.mss_fov_x = 320       # 擷取區域寬度的一半 (像素)
        self.mss_fov_y = 320       # 擷取區域高度的一半 (像素)
        
        # --- NDI FOV Settings ---
        self.ndi_fov_enabled = False  # 是否啟用 NDI 中心裁切
        self.ndi_fov = 320            # NDI 正方形裁切區域邊長的一半 (像素)
        
        # --- UDP FOV Settings ---
        self.udp_fov_enabled = False  # 是否啟用 UDP 中心裁切
        self.udp_fov = 320            # UDP 正方形裁切區域邊長的一半 (像素)
        
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
        
        # --- Processing FPS Limit ---
        self.target_fps = 80  # Target processing FPS (limits main loop frequency)
        
        # --- Button Mask Settings ---
        self.button_mask_enabled = False  # 總開關
        self.mask_left_button = False     # L (0)
        self.mask_right_button = False    # R (1)
        self.mask_middle_button = False   # M (2)
        self.mask_side4_button = False    # S4 (3)
        self.mask_side5_button = False    # S5 (4)
        
        # --- Mouse Lock Settings ---
        self.mouse_lock_main_x = False        # 鎖定 Main Aimbot X 軸
        self.mouse_lock_main_y = False        # 鎖定 Main Aimbot Y 軸
        self.mouse_lock_sec_x = False         # 鎖定 Sec Aimbot X 軸
        self.mouse_lock_sec_y = False         # 鎖定 Sec Aimbot Y 軸
        
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
            
            # Detection Parameters
            "detection_merge_distance": self.detection_merge_distance,
            "detection_min_contour_points": self.detection_min_contour_points,
            
            # Custom HSV Settings
            "custom_hsv_min_h": self.custom_hsv_min_h,
            "custom_hsv_min_s": self.custom_hsv_min_s,
            "custom_hsv_min_v": self.custom_hsv_min_v,
            "custom_hsv_max_h": self.custom_hsv_max_h,
            "custom_hsv_max_s": self.custom_hsv_max_s,
            "custom_hsv_max_v": self.custom_hsv_max_v,
            
            # Mouse / MAKCU
            "selected_mouse_button": self.selected_mouse_button,
            "selected_tb_btn": self.selected_tb_btn,
            "selected_2_tb": self.selected_2_tb,
            "in_game_sens": self.in_game_sens,
            "mouse_dpi": self.mouse_dpi,
            "mouse_api": self.mouse_api,
            "auto_connect_mouse_api": self.auto_connect_mouse_api,
            "serial_port_mode": self.serial_port_mode,
            "serial_port": self.serial_port,
            "arduino_port": self.arduino_port,
            "arduino_baud": self.arduino_baud,
            "arduino_16_bit_mouse": self.arduino_16_bit_mouse,
            "net_ip": self.net_ip,
            "net_port": self.net_port,
            "net_uuid": self.net_uuid,
            "net_mac": self.net_mac,
            "makv2_port": self.makv2_port,
            "makv2_baud": self.makv2_baud,
            "dhz_ip": self.dhz_ip,
            "dhz_port": self.dhz_port,
            "dhz_random": self.dhz_random,
            
            # Aimbot Mode
            "mode": self.mode,
            "mode_sec": self.mode_sec,
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
            "rcs_release_y_enabled": self.rcs_release_y_enabled,
            "rcs_release_y_duration": self.rcs_release_y_duration,
            
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
            
            # NCAF Parameters (Main)
            "ncaf_near_radius": self.ncaf_near_radius,
            "ncaf_snap_radius": self.ncaf_snap_radius,
            "ncaf_alpha": self.ncaf_alpha,
            "ncaf_snap_boost": self.ncaf_snap_boost,
            "ncaf_max_step": self.ncaf_max_step,
            "ncaf_min_speed_multiplier": self.ncaf_min_speed_multiplier,
            "ncaf_max_speed_multiplier": self.ncaf_max_speed_multiplier,
            "ncaf_prediction_interval": self.ncaf_prediction_interval,
            # NCAF Parameters (Sec)
            "ncaf_near_radius_sec": self.ncaf_near_radius_sec,
            "ncaf_snap_radius_sec": self.ncaf_snap_radius_sec,
            "ncaf_alpha_sec": self.ncaf_alpha_sec,
            "ncaf_snap_boost_sec": self.ncaf_snap_boost_sec,
            "ncaf_max_step_sec": self.ncaf_max_step_sec,
            "ncaf_min_speed_multiplier_sec": self.ncaf_min_speed_multiplier_sec,
            "ncaf_max_speed_multiplier_sec": self.ncaf_max_speed_multiplier_sec,
            "ncaf_prediction_interval_sec": self.ncaf_prediction_interval_sec,
            # WindMouse Parameters (Main)
            "wm_gravity": self.wm_gravity,
            "wm_wind": self.wm_wind,
            "wm_max_step": self.wm_max_step,
            "wm_min_step": self.wm_min_step,
            "wm_min_delay": self.wm_min_delay,
            "wm_max_delay": self.wm_max_delay,
            "wm_distance_threshold": self.wm_distance_threshold,
            # WindMouse Parameters (Sec)
            "wm_gravity_sec": self.wm_gravity_sec,
            "wm_wind_sec": self.wm_wind_sec,
            "wm_max_step_sec": self.wm_max_step_sec,
            "wm_min_step_sec": self.wm_min_step_sec,
            "wm_min_delay_sec": self.wm_min_delay_sec,
            "wm_max_delay_sec": self.wm_max_delay_sec,
            "wm_distance_threshold_sec": self.wm_distance_threshold_sec,
            # Bezier Parameters (Main)
            "bezier_segments": self.bezier_segments,
            "bezier_ctrl_x": self.bezier_ctrl_x,
            "bezier_ctrl_y": self.bezier_ctrl_y,
            "bezier_speed": self.bezier_speed,
            "bezier_delay": self.bezier_delay,
            # Bezier Parameters (Sec)
            "bezier_segments_sec": self.bezier_segments_sec,
            "bezier_ctrl_x_sec": self.bezier_ctrl_x_sec,
            "bezier_ctrl_y_sec": self.bezier_ctrl_y_sec,
            "bezier_speed_sec": self.bezier_speed_sec,
            "bezier_delay_sec": self.bezier_delay_sec,
            
            # Silent Mode Parameters
            "silent_distance": self.silent_distance,
            "silent_delay": self.silent_delay,
            "silent_move_delay": self.silent_move_delay,
            "silent_return_delay": self.silent_return_delay,
            
            # Anti-Smoke Settings
            "anti_smoke_enabled": self.anti_smoke_enabled,
            "anti_smoke_enabled_sec": self.anti_smoke_enabled_sec,
            
            # OpenCV Display Settings
            "show_opencv_windows": self.show_opencv_windows,
            "show_opencv_mask": self.show_opencv_mask,
            "show_opencv_detection": self.show_opencv_detection,
            "show_opencv_roi": self.show_opencv_roi,
            "show_opencv_triggerbot_mask": self.show_opencv_triggerbot_mask,
            "show_ndi_raw_stream_window": self.show_ndi_raw_stream_window,
            "show_udp_raw_stream_window": self.show_udp_raw_stream_window,
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
            
            # MSS Settings
            "mss_monitor_index": self.mss_monitor_index,
            "mss_fov_x": self.mss_fov_x,
            "mss_fov_y": self.mss_fov_y,
            
            # NDI FOV Settings
            "ndi_fov_enabled": self.ndi_fov_enabled,
            "ndi_fov": self.ndi_fov,
            
            # UDP FOV Settings
            "udp_fov_enabled": self.udp_fov_enabled,
            "udp_fov": self.udp_fov,
            
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
            "mask_side5_button": self.mask_side5_button,
            
            # Mouse Lock Settings
            "mouse_lock_main_x": self.mouse_lock_main_x,
            "mouse_lock_main_y": self.mouse_lock_main_y,
            "mouse_lock_sec_x": self.mouse_lock_sec_x,
            "mouse_lock_sec_y": self.mouse_lock_sec_y
        }
    
    def from_dict(self, data):
        """從字典載入配置"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        serial_mode = str(getattr(self, "serial_port_mode", "Auto")).strip().lower()
        self.serial_port_mode = "Manual" if serial_mode == "manual" else "Auto"
        self.serial_port = str(getattr(self, "serial_port", "")).strip()
        self.arduino_port = str(getattr(self, "arduino_port", "")).strip()
        try:
            self.arduino_baud = int(getattr(self, "arduino_baud", 115200))
        except Exception:
            self.arduino_baud = 115200
        self.arduino_16_bit_mouse = bool(getattr(self, "arduino_16_bit_mouse", True))
        # Backward compatibility: old config used `net_mac`.
        net_uuid = str(getattr(self, "net_uuid", "")).strip()
        net_mac = str(getattr(self, "net_mac", "")).strip()
        if not net_uuid and net_mac:
            self.net_uuid = net_mac
        self.net_mac = self.net_uuid
    
    def save_to_file(self, filename="config.json"):
        """保存配置到文件"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            log_print(f"[Config] Failed to save configuration: {e}")
    
    def load_from_file(self, filename="config.json"):
        """從文件載入配置"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.from_dict(data)
                log_print(f"[Config] Configuration loaded from {filename}")
        except Exception as e:
            log_print(f"[Config] Failed to load configuration: {e}")
    


config = Config()
