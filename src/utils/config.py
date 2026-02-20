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
        self.aim_offsetX = 0  # Aimbot 灏堢敤 X 鍋忕Щ
        self.aim_offsetY = 0  # Aimbot 灏堢敤 Y 鍋忕Щ
        self.aim_type = "head"  # Aimbot 鐬勬簴椤炲瀷: head, body, nearest

        self.color = "purple"
        
        # --- Detection Parameters ---
        self.detection_merge_distance = 12
        self.detection_min_contour_points = 5  # 鏈€灏忚吉寤撻粸鏁?(3-100)
        self.detection_open_kernel = 3
        self.detection_close_kernel = 5
        self.detection_mask_blur = 3
        self.detection_min_bbox_area = 120
        self.detection_min_contour_area = 40
        self.detection_min_fill_ratio = 0.16
        self.detection_edge_reject_area = 220
        self.detection_edge_min_contour_area = 140
        self.detection_edge_min_side = 10
        self.detection_border_margin = 1
        self.detection_min_width = 6
        self.detection_min_height = 8
        self.detection_min_aspect = 0.12
        self.detection_max_aspect = 2.8
        self.detection_require_vertical_line = False
        self.min_detection_bbox_area = 150
        self.head_estimate_ratio = 0.22
        self.head_refine_min_pixels = 20
        self.aim_latest_frame_priority = True
        self.enable_target_temporal_smoothing = False
        self.move_queue_merge_batch = 4
        
        # --- Custom HSV Settings ---
        self.custom_hsv_min_h = 0    # H 鏈€灏忓€?(0-179)
        self.custom_hsv_min_s = 0    # S 鏈€灏忓€?(0-255)
        self.custom_hsv_min_v = 0    # V 鏈€灏忓€?(0-255)
        self.custom_hsv_max_h = 179  # H 鏈€澶у€?(0-179)
        self.custom_hsv_max_s = 255  # S 鏈€澶у€?(0-255)
        self.custom_hsv_max_v = 255  # V 鏈€澶у€?(0-255)

        
        # --- Mouse / MAKCU ---
        self.selected_mouse_button = 1
        self.selected_tb_btn = 1
        self.selected_2_tb = 2
        self.in_game_sens = 0.235
        self.mouse_dpi = 800
        self.mouse_api = "Serial"  # Serial, Arduino, SendInput, Net, KmboxA, MakV2, DHZ
        self.auto_connect_mouse_api = False
        self.serial_auto_switch_4m = False
        self.serial_port_mode = "Auto"  # Auto, Manual
        self.serial_port = ""
        self.arduino_port = ""
        self.arduino_baud = 115200
        self.arduino_16_bit_mouse = True
        self.net_ip = "192.168.2.188"
        self.net_port = "6234"
        self.net_uuid = ""
        self.net_mac = ""  # deprecated alias of net_uuid
        self.kmboxa_vid = 0
        self.kmboxa_pid = 0
        self.kmboxa_vid_pid = "0/0"
        self.makv2_port = ""
        self.makv2_baud = 4000000
        self.dhz_ip = "192.168.2.188"
        self.dhz_port = "5000"
        self.dhz_random = 0
        # --- Aimbot Activation Type ---
        self.aimbot_activation_type = "hold_enable"  # Main Aimbot: hold_enable, hold_disable, toggle, use_enable
        self.aimbot_activation_type_sec = "hold_enable"  # Sec Aimbot: hold_enable, hold_disable, toggle, use_enable
        # --- Aimbot Mode ---
        self.mode = "Normal"        # Main Aimbot 妯″紡: Normal, Silent, NCAF, WindMouse, Bezier
        self.mode_sec = "Normal"    # Sec Aimbot 妯″紡: Normal, Silent, NCAF, WindMouse, Bezier

        self.fovsize = 100
        self.ads_fov_enabled = False
        self.ads_fovsize = 100
        self.ads_key = "Right Mouse Button"
        self.ads_key_type = "hold"  # hold, toggle
        self.tbfovsize = 5 
        self.trigger_ads_fov_enabled = False
        self.trigger_ads_fovsize = 5
        self.trigger_ads_key = "Right Mouse Button"
        self.trigger_ads_key_type = "hold"  # hold, toggle
        self.trigger_type = "current"  # current, rgb
        # Triggerbot delay range (seconds)
        self.tbdelay_min = 0.08
        self.tbdelay_max = 0.15
        # Triggerbot hold range (milliseconds)
        self.tbhold_min = 40
        self.tbhold_max = 60
        # Triggerbot cooldown range
        self.tbcooldown_min = 0.0  # seconds
        self.tbcooldown_max = 0.0  # seconds
        # RGB Trigger delay/hold/cooldown
        self.rgb_tbdelay_min = 0.08  # seconds
        self.rgb_tbdelay_max = 0.15  # seconds
        self.rgb_tbhold_min = 40  # ms
        self.rgb_tbhold_max = 60  # ms
        self.rgb_tbcooldown_min = 0.0  # seconds
        self.rgb_tbcooldown_max = 0.0  # seconds
        self.rgb_color_profile = "purple"  # red, yellow, purple, custom
        self.rgb_custom_r = 161
        self.rgb_custom_g = 69
        self.rgb_custom_b = 163
        self.tbburst_count_min = 1  # minimum shots per burst
        self.tbburst_count_max = 1  # maximum shots per burst
        self.tbburst_interval_min = 0.0  # minimum interval between burst shots (ms)
        self.tbburst_interval_max = 0.0  # maximum interval between burst shots (ms)
        self.trigger_activation_type = "hold_enable"  # hold_enable, hold_disable, toggle
        self.trigger_strafe_mode = "off"  # off, auto, manual_wait
        self.trigger_strafe_auto_lead_ms = 8  # ms
        self.trigger_strafe_manual_neutral_ms = 0  # ms
        
        self.trigger_roi_size = 8
        self.trigger_min_pixels = 4
        self.trigger_min_ratio = 0.03
        self.trigger_confirm_frames = 2
        self.switch_confirm_frames = 3
        self.ema_alpha = 0.35
        
        # RCS (Recoil Control System) 瑷疆
        self.enablercs = False  # 鏄惁鍟熺敤 RCS
        self.rcs_pull_speed = 10  # 涓嬫媺閫熷害锛?-20锛?
        self.rcs_activation_delay = 100  # 鍟熷嫊寤堕伈锛?0-500ms锛?
        self.rcs_rapid_click_threshold = 200  # 蹇€熼粸鎿婇柧鍊硷紙100-1000ms锛?
        # RCS Y 杌歌В閹栬ō缃?
        self.rcs_release_y_enabled = False  # 鏄惁鍟熺敤宸﹂嵉鎸変笅鏅傝В閹?Y 杌哥Щ鍕?
        self.rcs_release_y_duration = 1.0  # Y 杌歌В閹栨寔绾屾檪闁擄紙0.1~5绉掞級
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
        self.ads_fov_enabled_sec = False
        self.ads_fovsize_sec = 150
        self.ads_key_sec = "Right Mouse Button"
        self.ads_key_type_sec = "hold"  # hold, toggle
        self.selected_mouse_button_sec = 2
        self.aim_offsetX_sec = 0  # Sec Aimbot X 鍋忕Щ
        self.aim_offsetY_sec = 0  # Sec Aimbot Y 鍋忕Щ
        self.aim_type_sec = "head"  # Sec Aimbot 鐬勬簴椤炲瀷
        
        # --- NCAF Parameters (Main) ---
        # Snap Radius = outer engagement zone (larger), Near Radius = inner precision zone (smaller)
        self.ncaf_snap_radius = 150.0
        self.ncaf_near_radius = 50.0
        self.ncaf_alpha = 1.5
        self.ncaf_snap_boost = 0.3
        self.ncaf_max_step = 50.0
        self.ncaf_min_speed_multiplier = 0.01  # 婊戦紶绉诲嫊閫熷害鐨勬渶灏忓€嶇巼
        self.ncaf_max_speed_multiplier = 10.0  # 婊戦紶绉诲嫊閫熷害鐨勬渶澶у€嶇巼
        self.ncaf_prediction_interval = 0.016  # 鐩闋愭脯鍑芥暩鐨勮檿鐞嗛€熷害锛堢锛岀磩60fps锛?
        
        # --- NCAF Parameters (Sec) ---
        self.ncaf_snap_radius_sec = 150.0
        self.ncaf_near_radius_sec = 50.0
        self.ncaf_alpha_sec = 1.5
        self.ncaf_snap_boost_sec = 0.3
        self.ncaf_max_step_sec = 50.0
        self.ncaf_min_speed_multiplier_sec = 0.01  # 婊戦紶绉诲嫊閫熷害鐨勬渶灏忓€嶇巼
        self.ncaf_max_speed_multiplier_sec = 10.0  # 婊戦紶绉诲嫊閫熷害鐨勬渶澶у€嶇巼
        self.ncaf_prediction_interval_sec = 0.016  # 鐩闋愭脯鍑芥暩鐨勮檿鐞嗛€熷害锛堢锛岀磩60fps锛?
        
        # --- WindMouse Parameters (Main) ---
        self.wm_gravity = 9.0
        self.wm_wind = 3.0
        self.wm_max_step = 15.0
        self.wm_min_step = 2.0
        self.wm_min_delay = 0.001
        self.wm_max_delay = 0.003
        self.wm_distance_threshold = 50.0  # 璺濋洟闁惧€硷紝浣庢柤姝ゅ€兼檪绉诲嫊鏇寸簿纰?
        
        # --- WindMouse Parameters (Sec) ---
        self.wm_gravity_sec = 9.0
        self.wm_wind_sec = 3.0
        self.wm_max_step_sec = 15.0
        self.wm_min_step_sec = 2.0
        self.wm_min_delay_sec = 0.001
        self.wm_max_delay_sec = 0.003
        self.wm_distance_threshold_sec = 50.0  # 璺濋洟闁惧€硷紝浣庢柤姝ゅ€兼檪绉诲嫊鏇寸簿纰?
        
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
        self.silent_distance = 1.0  # 绉诲嫊鍊嶇巼锛堢敤鏂艰鏁寸Щ鍕曡窛闆㈢殑鍊嶆暩锛?
        self.silent_delay = 100.0  # 鍏╂闁嬫鐨勬渶灏忛枔闅旓紙姣锛?
        self.silent_move_delay = 500.0  # 绉诲嫊婊戦紶鍒扮洰妯欎綅缃殑寤堕伈锛堟绉掞級
        self.silent_return_delay = 500.0  # 绉诲嫊鍥炲師浣嶇疆鐨勫欢閬诧紙姣锛?
        
        # --- Anti-Smoke Settings ---
        self.anti_smoke_enabled = False  # Main Aimbot Anti-Smoke
        self.anti_smoke_enabled_sec = False  # Sec Aimbot Anti-Smoke
        
        # --- OpenCV Display Settings ---
        self.show_opencv_windows = True
        # 鍠崹鐨?OpenCV 瑕栫獥闁嬮棞
        self.show_opencv_mask = True  # MASK 瑕栫獥锛坢ain.py锛?
        self.show_opencv_detection = True  # Detection 瑕栫獥锛坢ain.py锛?
        self.show_opencv_roi = True  # ROI 瑕栫獥锛圱riggerbot.py锛?
        self.show_opencv_triggerbot_mask = True  # Mask 瑕栫獥锛圱riggerbot.py锛?
        self.show_ndi_raw_stream_window = False
        self.show_udp_raw_stream_window = False
        self.show_mode_text = True
        self.show_aimbot_status = True
        self.show_triggerbot_status = True
        self.show_target_count = True
        self.show_crosshair = True
        self.show_distance_text = True
        # Persist UI collapsible section open/closed state per tab.
        self.ui_collapsible_states = {}
        self.legacy_ui_mode = False
        
        # --- Capture Settings ---
        self.udp_ip = "127.0.0.1"
        self.udp_port = "1234"
        self.capture_mode = "NDI"
        self.last_ndi_source = None
        
        # --- MSS Settings ---
        self.mss_monitor_index = 1  # 铻㈠箷绱㈠紩 (1=涓昏灑骞?
        self.mss_fov_x = 320       # 鎿峰彇鍗€鍩熷搴︾殑涓€鍗?(鍍忕礌)
        self.mss_fov_y = 320       # 鎿峰彇鍗€鍩熼珮搴︾殑涓€鍗?(鍍忕礌)
        
        # --- NDI FOV Settings ---
        self.ndi_fov_enabled = False  # 鏄惁鍟熺敤 NDI 涓績瑁佸垏
        self.ndi_fov = 320            # NDI 姝ｆ柟褰㈣鍒囧崁鍩熼倞闀风殑涓€鍗?(鍍忕礌)
        
        # --- UDP FOV Settings ---
        self.udp_fov_enabled = False  # 鏄惁鍟熺敤 UDP 涓績瑁佸垏
        self.udp_fov = 320            # UDP 姝ｆ柟褰㈣鍒囧崁鍩熼倞闀风殑涓€鍗?(鍍忕礌)
        
        # --- CaptureCard Settings ---
        self.capture_device_index = 0
        self.capture_width = 1920
        self.capture_height = 1080
        self.capture_fps = 240
        self.capture_fourcc_preference = ["NV12", "YUY2", "MJPG"]
        self.capture_card_force_bgr = True
        self.capture_card_set_convert_rgb = True
        self.capture_card_probe_frames = 3
        self.capture_card_debug_color_log = False
        self.capture_range_x = 128  # 鏈€浣庡€?128
        self.capture_range_y = 128  # 鏈€浣庡€?128
        self.capture_offset_x = 0
        self.capture_offset_y = 0
        
        # --- Processing FPS Limit ---
        self.target_fps = 80  # Target processing FPS (limits main loop frequency)
        
        # --- Button Mask Settings ---
        self.button_mask_enabled = False  # 绺介枊闂?
        self.mask_left_button = False     # L (0)
        self.mask_right_button = False    # R (1)
        self.mask_middle_button = False   # M (2)
        self.mask_side4_button = False    # S4 (3)
        self.mask_side5_button = False    # S5 (4)
        
        # --- Mouse Lock Settings ---
        self.mouse_lock_main_x = False        # 閹栧畾 Main Aimbot X 杌?
        self.mouse_lock_main_y = False        # 閹栧畾 Main Aimbot Y 杌?
        self.mouse_lock_sec_x = False         # 閹栧畾 Sec Aimbot X 杌?
        self.mouse_lock_sec_y = False         # 閹栧畾 Sec Aimbot Y 杌?
        
        # 杓夊叆淇濆瓨鐨勯厤缃紙濡傛灉瀛樺湪锛?
        self.load_from_file()
    
    def to_dict(self):
        """灏囬厤缃綁鎻涚偤瀛楀吀 - 鍖呭惈鎵€鏈夎ō缃?"""
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
            "detection_open_kernel": self.detection_open_kernel,
            "detection_close_kernel": self.detection_close_kernel,
            "detection_mask_blur": self.detection_mask_blur,
            "detection_min_bbox_area": self.detection_min_bbox_area,
            "detection_min_contour_area": self.detection_min_contour_area,
            "detection_min_fill_ratio": self.detection_min_fill_ratio,
            "detection_edge_reject_area": self.detection_edge_reject_area,
            "detection_edge_min_contour_area": self.detection_edge_min_contour_area,
            "detection_edge_min_side": self.detection_edge_min_side,
            "detection_border_margin": self.detection_border_margin,
            "detection_min_width": self.detection_min_width,
            "detection_min_height": self.detection_min_height,
            "detection_min_aspect": self.detection_min_aspect,
            "detection_max_aspect": self.detection_max_aspect,
            "detection_require_vertical_line": self.detection_require_vertical_line,
            "min_detection_bbox_area": self.min_detection_bbox_area,
            "head_estimate_ratio": self.head_estimate_ratio,
            "head_refine_min_pixels": self.head_refine_min_pixels,
            "aim_latest_frame_priority": self.aim_latest_frame_priority,
            "enable_target_temporal_smoothing": self.enable_target_temporal_smoothing,
            "move_queue_merge_batch": self.move_queue_merge_batch,
            
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
            "serial_auto_switch_4m": self.serial_auto_switch_4m,
            "serial_port_mode": self.serial_port_mode,
            "serial_port": self.serial_port,
            "arduino_port": self.arduino_port,
            "arduino_baud": self.arduino_baud,
            "arduino_16_bit_mouse": self.arduino_16_bit_mouse,
            "net_ip": self.net_ip,
            "net_port": self.net_port,
            "net_uuid": self.net_uuid,
            "net_mac": self.net_mac,
            "kmboxa_vid": self.kmboxa_vid,
            "kmboxa_pid": self.kmboxa_pid,
            "kmboxa_vid_pid": self.kmboxa_vid_pid,
            "makv2_port": self.makv2_port,
            "makv2_baud": self.makv2_baud,
            "dhz_ip": self.dhz_ip,
            "dhz_port": self.dhz_port,
            "dhz_random": self.dhz_random,
            "aimbot_activation_type": self.aimbot_activation_type,
            "aimbot_activation_type_sec": self.aimbot_activation_type_sec,
            
            # Aimbot Mode
            "mode": self.mode,
            "mode_sec": self.mode_sec,
            "fovsize": self.fovsize,
            "ads_fov_enabled": self.ads_fov_enabled,
            "ads_fovsize": self.ads_fovsize,
            "ads_key": self.ads_key,
            "ads_key_type": self.ads_key_type,
            "tbfovsize": self.tbfovsize,
            "trigger_ads_fov_enabled": self.trigger_ads_fov_enabled,
            "trigger_ads_fovsize": self.trigger_ads_fovsize,
            "trigger_ads_key": self.trigger_ads_key,
            "trigger_ads_key_type": self.trigger_ads_key_type,
            "trigger_type": self.trigger_type,
            "tbdelay_min": self.tbdelay_min,
            "tbdelay_max": self.tbdelay_max,
            "tbhold_min": self.tbhold_min,
            "tbhold_max": self.tbhold_max,
            "tbcooldown_min": self.tbcooldown_min,
            "tbcooldown_max": self.tbcooldown_max,
            "rgb_tbdelay_min": self.rgb_tbdelay_min,
            "rgb_tbdelay_max": self.rgb_tbdelay_max,
            "rgb_tbhold_min": self.rgb_tbhold_min,
            "rgb_tbhold_max": self.rgb_tbhold_max,
            "rgb_tbcooldown_min": self.rgb_tbcooldown_min,
            "rgb_tbcooldown_max": self.rgb_tbcooldown_max,
            "rgb_color_profile": self.rgb_color_profile,
            "rgb_custom_r": self.rgb_custom_r,
            "rgb_custom_g": self.rgb_custom_g,
            "rgb_custom_b": self.rgb_custom_b,
            "tbburst_count_min": self.tbburst_count_min,
            "tbburst_count_max": self.tbburst_count_max,
            "tbburst_interval_min": self.tbburst_interval_min,
            "tbburst_interval_max": self.tbburst_interval_max,
            "trigger_activation_type": self.trigger_activation_type,
            "trigger_strafe_mode": self.trigger_strafe_mode,
            "trigger_strafe_auto_lead_ms": self.trigger_strafe_auto_lead_ms,
            "trigger_strafe_manual_neutral_ms": self.trigger_strafe_manual_neutral_ms,
            "trigger_roi_size": self.trigger_roi_size,
            "trigger_min_pixels": self.trigger_min_pixels,
            "trigger_min_ratio": self.trigger_min_ratio,
            "trigger_confirm_frames": self.trigger_confirm_frames,
            "switch_confirm_frames": self.switch_confirm_frames,
            "ema_alpha": self.ema_alpha,
            
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
            "ads_fov_enabled_sec": self.ads_fov_enabled_sec,
            "ads_fovsize_sec": self.ads_fovsize_sec,
            "ads_key_sec": self.ads_key_sec,
            "ads_key_type_sec": self.ads_key_type_sec,
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
            "ui_collapsible_states": self.ui_collapsible_states,
            "legacy_ui_mode": self.legacy_ui_mode,
            
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
            "capture_card_force_bgr": self.capture_card_force_bgr,
            "capture_card_set_convert_rgb": self.capture_card_set_convert_rgb,
            "capture_card_probe_frames": self.capture_card_probe_frames,
            "capture_card_debug_color_log": self.capture_card_debug_color_log,
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
        """寰炲瓧鍏歌級鍏ラ厤缃?"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        serial_mode = str(getattr(self, "serial_port_mode", "Auto")).strip().lower()
        self.serial_port_mode = "Manual" if serial_mode == "manual" else "Auto"
        self.serial_auto_switch_4m = bool(getattr(self, "serial_auto_switch_4m", False))
        self.serial_port = str(getattr(self, "serial_port", "")).strip()
        self.arduino_port = str(getattr(self, "arduino_port", "")).strip()
        try:
            self.arduino_baud = int(getattr(self, "arduino_baud", 115200))
        except Exception:
            self.arduino_baud = 115200
        self.arduino_16_bit_mouse = bool(getattr(self, "arduino_16_bit_mouse", True))
        self.ads_fov_enabled = bool(getattr(self, "ads_fov_enabled", False))
        self.ads_fov_enabled_sec = bool(getattr(self, "ads_fov_enabled_sec", False))
        try:
            self.ads_fovsize = float(getattr(self, "ads_fovsize", getattr(self, "fovsize", 100)))
        except Exception:
            self.ads_fovsize = float(getattr(self, "fovsize", 100))
        try:
            self.ads_fovsize_sec = float(getattr(self, "ads_fovsize_sec", getattr(self, "fovsize_sec", 150)))
        except Exception:
            self.ads_fovsize_sec = float(getattr(self, "fovsize_sec", 150))
        self.ads_key = str(getattr(self, "ads_key", "Right Mouse Button")).strip() or "Right Mouse Button"
        self.ads_key_sec = str(getattr(self, "ads_key_sec", "Right Mouse Button")).strip() or "Right Mouse Button"
        ads_key_type = str(getattr(self, "ads_key_type", "hold")).strip().lower()
        self.ads_key_type = "toggle" if ads_key_type == "toggle" else "hold"
        ads_key_type_sec = str(getattr(self, "ads_key_type_sec", "hold")).strip().lower()
        self.ads_key_type_sec = "toggle" if ads_key_type_sec == "toggle" else "hold"
        self.trigger_ads_fov_enabled = bool(getattr(self, "trigger_ads_fov_enabled", False))
        try:
            self.trigger_ads_fovsize = float(
                getattr(self, "trigger_ads_fovsize", getattr(self, "tbfovsize", 5))
            )
        except Exception:
            self.trigger_ads_fovsize = float(getattr(self, "tbfovsize", 5))
        self.trigger_ads_key = (
            str(getattr(self, "trigger_ads_key", "Right Mouse Button")).strip()
            or "Right Mouse Button"
        )
        trigger_ads_key_type = str(getattr(self, "trigger_ads_key_type", "hold")).strip().lower()
        self.trigger_ads_key_type = "toggle" if trigger_ads_key_type == "toggle" else "hold"
        # Backward compatibility: old config used `net_mac`.
        net_uuid = str(getattr(self, "net_uuid", "")).strip()
        net_mac = str(getattr(self, "net_mac", "")).strip()
        if not net_uuid and net_mac:
            self.net_uuid = net_mac
        self.net_mac = self.net_uuid
        try:
            self.kmboxa_vid = int(getattr(self, "kmboxa_vid", 0))
        except Exception:
            self.kmboxa_vid = 0
        try:
            self.kmboxa_pid = int(getattr(self, "kmboxa_pid", 0))
        except Exception:
            self.kmboxa_pid = 0
        raw_vid_pid = str(getattr(self, "kmboxa_vid_pid", "")).strip()
        if raw_vid_pid:
            def _parse_kmboxa_token(token):
                token_str = str(token).strip()
                if token_str.lower().startswith("v"):
                    token_str = token_str[1:].strip()
                if token_str.lower().startswith("d:"):
                    return int(token_str[2:].strip(), 10)
                if token_str.lower().startswith("h:"):
                    return int(token_str[2:].strip(), 16)
                if token_str.lower().startswith("0x"):
                    return int(token_str, 16)
                if token_str.isdigit() and len(token_str) == 4:
                    return int(token_str, 16)
                if any(ch in "abcdefABCDEF" for ch in token_str):
                    return int(token_str, 16)
                return int(token_str, 10)

            parsed_vid = self.kmboxa_vid
            parsed_pid = self.kmboxa_pid
            is_v_prefixed = raw_vid_pid.lower().startswith("v")
            compact_v = raw_vid_pid[1:].strip() if is_v_prefixed else raw_vid_pid
            if is_v_prefixed and compact_v and all(ch in "0123456789abcdefABCDEF" for ch in compact_v) and 5 <= len(compact_v) <= 8:
                try:
                    parsed_vid = int(compact_v[:4], 16)
                    parsed_pid = int(compact_v[4:], 16)
                except Exception:
                    pass
                self.kmboxa_vid = int(parsed_vid)
                self.kmboxa_pid = int(parsed_pid)
                self.kmboxa_vid_pid = f"{int(self.kmboxa_vid)}/{int(self.kmboxa_pid)}"
                raw_vid_pid = ""
            for sep in ("/", ":", ",", ";", "|", " "):
                if sep in raw_vid_pid:
                    parts = [p for p in raw_vid_pid.split(sep) if str(p).strip()]
                    if len(parts) >= 2:
                        try:
                            parsed_vid = _parse_kmboxa_token(parts[0])
                            parsed_pid = _parse_kmboxa_token(parts[1])
                        except Exception:
                            pass
                    break
            else:
                compact = raw_vid_pid[1:].strip() if raw_vid_pid.lower().startswith("v") else raw_vid_pid
                if compact.isdigit() and len(compact) == 8:
                    try:
                        parsed_vid = int(compact[:4], 16)
                        parsed_pid = int(compact[4:], 16)
                    except Exception:
                        pass
                else:
                    try:
                        packed = _parse_kmboxa_token(compact)
                        if packed > 0xFFFF:
                            parsed_vid = (packed >> 16) & 0xFFFF
                            parsed_pid = packed & 0xFFFF
                        else:
                            parsed_vid = packed
                    except Exception:
                        pass
            self.kmboxa_vid = int(parsed_vid)
            self.kmboxa_pid = int(parsed_pid)
        self.kmboxa_vid_pid = f"{int(self.kmboxa_vid)}/{int(self.kmboxa_pid)}"
        # Ensure UI section state is always a dict[str, bool].
        raw_states = getattr(self, "ui_collapsible_states", {})
        if isinstance(raw_states, dict):
            self.ui_collapsible_states = {str(k): bool(v) for k, v in raw_states.items()}
        else:
            self.ui_collapsible_states = {}
        self.legacy_ui_mode = bool(getattr(self, "legacy_ui_mode", False))

        mode = str(getattr(self, "trigger_strafe_mode", "off")).strip().lower()
        if mode not in {"off", "auto", "manual_wait"}:
            mode = "off"
        self.trigger_strafe_mode = mode
        rgb_profile = str(getattr(self, "rgb_color_profile", "purple")).strip().lower()
        if rgb_profile not in {"red", "yellow", "purple", "custom"}:
            rgb_profile = "purple"
        self.rgb_color_profile = rgb_profile
        for channel_key, default in (
            ("rgb_custom_r", 161),
            ("rgb_custom_g", 69),
            ("rgb_custom_b", 163),
        ):
            try:
                channel_value = int(getattr(self, channel_key, default))
            except Exception:
                channel_value = int(default)
            setattr(self, channel_key, max(0, min(255, channel_value)))
        try:
            self.trigger_strafe_auto_lead_ms = max(0, min(50, int(getattr(self, "trigger_strafe_auto_lead_ms", 8))))
        except Exception:
            self.trigger_strafe_auto_lead_ms = 8
        try:
            self.trigger_strafe_manual_neutral_ms = max(
                0, min(300, int(getattr(self, "trigger_strafe_manual_neutral_ms", 0)))
            )
        except Exception:
            self.trigger_strafe_manual_neutral_ms = 0
    
    def save_to_file(self, filename="config.json"):
        """淇濆瓨閰嶇疆鍒版枃浠?"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            log_print(f"[Config] Failed to save configuration: {e}")
    
    def load_from_file(self, filename="config.json"):
        """寰炴枃浠惰級鍏ラ厤缃?"""
        try:
            if os.path.exists(filename):
                if os.path.getsize(filename) == 0:
                    return
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.from_dict(data)
                log_print(f"[Config] Configuration loaded from {filename}")
        except Exception as e:
            log_print(f"[Config] Failed to load configuration: {e}")
    


config = Config()



