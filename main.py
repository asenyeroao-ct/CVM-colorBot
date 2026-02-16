import threading
import queue
import time
import math
import numpy as np
import cv2
import ctypes
import sys
import os

# 瑷疆 AppUserModelID 浠ヤ究鍦?Windows 浠诲嫏娆勬纰洪’绀哄湒妯?
try:
    myappid = 'mycompany.colorbot.v2.0' # 浠绘剰鍞竴鐨勫瓧绗︿覆
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from src.utils.config import config
from src.utils.mouse import Mouse, is_button_pressed
from src.utils.detection import load_model, perform_detection
from src.capture.capture_service import CaptureService
from src.aim_system.normal import process_normal_mode
from src.aim_system.anti_smoke_detector import AntiSmokeDetector
from src.aim_system.target_smoother import TargetSmoother

class FrameInfo:
    """绨″柈鐨勫箑淇℃伅椤烇紝鐢ㄦ柤鍏煎鐝炬湁浠ｇ⒓"""
    def __init__(self, width, height):
        self.xres = width
        self.yres = height

class AimTracker:
    """
    鐩杩借工鍣ㄩ
    
    璨犺铂铏曠悊瑕栭牷骞€鐨勬崟鐛层€佺洰妯欐娓€佺瀯婧栬▓绠楀拰婊戦紶绉诲嫊鎺у埗銆?    鏀寔澶氱ó妯″紡锛圢ormal銆丼ilent锛夊拰閰嶇疆閬搁爡銆?    """
    
    RAW_STREAM_NDI_WINDOW = "NDI Raw Stream"
    RAW_STREAM_UDP_WINDOW = "UDP Raw Stream"

    def __init__(self, app, target_fps=80):
        """
        鍒濆鍖?AimTracker
        
        Args:
            app: 鎳夌敤绋嬪紡瀵︿緥锛岄渶瑕佸寘鍚?capture 灞€э紙CaptureService锛?            target_fps: 鐩骞€鐜囷紝榛樿獚鐐?80 FPS
        """
        self.app = app
        # --- Params (avec valeurs fallback) ---
        self.normal_x_speed = float(getattr(config, "normal_x_speed", 0.5))
        self.normal_y_speed = float(getattr(config, "normal_y_speed", 0.5))
        self.normalsmooth = float(getattr(config, "normalsmooth", 10))
        self.normalsmoothfov = float(getattr(config, "normalsmoothfov", 10))
        self.mouse_dpi = float(getattr(config, "mouse_dpi", 800))
        self.fovsize = float(getattr(config, "fovsize", 300))
        self.tbfovsize = float(getattr(config, "tbfovsize", 70))
        # Triggerbot delay range
        self.tbdelay_min = float(getattr(config, "tbdelay_min", 0.08))
        self.tbdelay_max = float(getattr(config, "tbdelay_max", 0.15))
        # Triggerbot hold range
        self.tbhold_min = float(getattr(config, "tbhold_min", 40))
        self.tbhold_max = float(getattr(config, "tbhold_max", 60))
        # Triggerbot 閫ｇ櫦瑷疆锛堢瘎鍦嶏級
        self.tbcooldown_min = float(getattr(config, "tbcooldown_min", 0.0))
        self.tbcooldown_max = float(getattr(config, "tbcooldown_max", 0.0))
        self.tbburst_count_min = int(getattr(config, "tbburst_count_min", 1))
        self.tbburst_count_max = int(getattr(config, "tbburst_count_max", 1))
        self.tbburst_interval_min = float(getattr(config, "tbburst_interval_min", 0.0))
        self.tbburst_interval_max = float(getattr(config, "tbburst_interval_max", 0.0))
        self.trigger_roi_size = int(getattr(config, "trigger_roi_size", 8))
        self.trigger_min_pixels = int(getattr(config, "trigger_min_pixels", 4))
        self.trigger_min_ratio = float(getattr(config, "trigger_min_ratio", 0.03))
        self.trigger_confirm_frames = int(getattr(config, "trigger_confirm_frames", 2))
        # 娉ㄦ剰锛歭ast_tb_click_time 鐝惧湪鐢?Triggerbot.py 涓殑鍏ㄥ眬鐙€鎱嬬鐞?        
        # RCS (Recoil Control System) 瑷疆
        self.rcs_pull_speed = int(getattr(config, "rcs_pull_speed", 10))
        self.rcs_activation_delay = int(getattr(config, "rcs_activation_delay", 100))
        self.rcs_rapid_click_threshold = int(getattr(config, "rcs_rapid_click_threshold", 200))
        
        # Silent Mode 瑷疆
        self.silent_distance = float(getattr(config, "silent_distance", 1.0))
        self.silent_delay = float(getattr(config, "silent_delay", 100.0))
        self.silent_move_delay = float(getattr(config, "silent_move_delay", 500.0))
        self.silent_return_delay = float(getattr(config, "silent_return_delay", 500.0))
        self.last_silent_click_time = 0  # 鐢ㄦ柤杩借工鏈€寰屼竴娆￠枊妲嶆檪闁?
        self.in_game_sens = float(getattr(config, "in_game_sens", 0.235))
        self.color = getattr(config, "color", "yellow")
        self.mode = getattr(config, "mode", "Normal")
        self.mode_sec = getattr(config, "mode_sec", "Normal")
        self.selected_mouse_button = getattr(config, "selected_mouse_button", 3)
        self.selected_tb_btn= getattr(config, "selected_tb_btn", 3)
        self.max_speed = float(getattr(config, "max_speed", 1000.0))

        # --- Main Aimbot Offset & Aim Type ---
        self.aim_offsetX = float(getattr(config, "aim_offsetX", 0))
        self.aim_offsetY = float(getattr(config, "aim_offsetY", 0))
        self.aim_type = getattr(config, "aim_type", "head")

        # --- Secondary Aimbot Parameters ---
        self.normal_x_speed_sec = float(getattr(config, "normal_x_speed_sec", 2))
        self.normal_y_speed_sec = float(getattr(config, "normal_y_speed_sec", 2))
        self.normalsmooth_sec = float(getattr(config, "normalsmooth_sec", 20))
        self.normalsmoothfov_sec = float(getattr(config, "normalsmoothfov_sec", 20))
        self.fovsize_sec = float(getattr(config, "fovsize_sec", 150))
        self.selected_mouse_button_sec = getattr(config, "selected_mouse_button_sec", 2)
        
        # --- Secondary Aimbot Offset & Aim Type ---
        self.aim_offsetX_sec = float(getattr(config, "aim_offsetX_sec", 0))
        self.aim_offsetY_sec = float(getattr(config, "aim_offsetY_sec", 0))
        self.aim_type_sec = getattr(config, "aim_type_sec", "head")

        self.controller = Mouse()
        self._stop_event = threading.Event()
        self._raw_stream_window_visible = {
            self.RAW_STREAM_NDI_WINDOW: False,
            self.RAW_STREAM_UDP_WINDOW: False,
        }
        self.move_queue = queue.Queue(maxsize=50)
        self._move_batch_size = 4
        self._move_batch_small_step = 3.0
        self._move_thread = threading.Thread(target=self._process_move_queue, daemon=True)
        self._move_thread.start()

        self.model, self.class_names = load_model()
        print("Classes:", self.class_names)
        self._target_fps = target_fps
        self._track_thread = threading.Thread(target=self._track_loop, daemon=True)
        self._track_thread.start()
        
        # 骞€瑷堟暩鍣紙鐢ㄦ柤瑾胯│锛?
        self._frame_count = 0
        self._last_frame_log_time = time.time()
        
        # --- Anti-Smoke Detector 鍒濆鍖?---
        self.anti_smoke_detector = AntiSmokeDetector()
        self.anti_smoke_detector.set_enabled(getattr(config, "anti_smoke_enabled", False))
        
        self.anti_smoke_detector_sec = AntiSmokeDetector()
        self.anti_smoke_detector_sec.set_enabled(getattr(config, "anti_smoke_enabled_sec", False))
        
        self.ema_alpha = float(getattr(config, "ema_alpha", 0.35))
        self.switch_confirm_frames = int(getattr(config, "switch_confirm_frames", 3))
        self._target_smoother = TargetSmoother(
            ema_alpha=self.ema_alpha,
            switch_confirm_frames=self.switch_confirm_frames,
        )
        self.last_target = None
        self.stable_candidate = None
        self.stable_count = 0
        

    def stop(self):
        """
        鍋滄杩借工鍣?        
        瑷疆鍋滄浜嬩欢涓︾瓑寰呰拷韫ょ窔绋嬬祼鏉燂紝鐢ㄦ柤娓呯悊璩囨簮銆?        """
        self._stop_event.set()
        try:
            self._track_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self._move_thread.join(timeout=1.0)
        except Exception:
            pass
        self._close_raw_stream_windows()

    def _process_move_queue(self):
        """
        铏曠悊绉诲嫊闅婂垪
        
        鍦ㄥ緦鍙扮窔绋嬩腑鎸佺簩寰炵Щ鍕曢殜鍒椾腑鐛插彇绉诲嫊鎸囦护涓﹀煼琛屻€?        鏀寔寤堕伈鎺у埗锛岀⒑淇濈Щ鍕曟搷浣滅殑骞虫粦鍩疯銆?        
        閫欐槸涓€鍊嬬劇闄愬惊鐠帮紝鐩村埌绶氱▼琚祩姝€?        """
        while not self._stop_event.is_set() or not self.move_queue.empty():
            try:
                dx, dy, delay = self.move_queue.get(timeout=0.1)
                latest_only = bool(getattr(config, "aim_latest_frame_priority", True))
                if latest_only:
                    # Keep only the newest N commands, then merge them.
                    # This preserves immediate latest-frame behavior while avoiding
                    # dropped Bezier/WindMouse sub-steps that cause jitter.
                    pending = [(dx, dy, delay)]
                    while True:
                        try:
                            pending.append(self.move_queue.get_nowait())
                        except queue.Empty:
                            break
                    max_batch = max(
                        1,
                        int(getattr(config, "move_queue_merge_batch", self._move_batch_size)),
                    )
                    if len(pending) > max_batch:
                        pending = pending[-max_batch:]
                    merged_dx = float(sum(float(item[0]) for item in pending))
                    merged_dy = float(sum(float(item[1]) for item in pending))
                    merged_delay = min(
                        (max(0.0, float(item[2])) for item in pending),
                        default=0.0,
                    )
                else:
                    merged_dx = float(dx)
                    merged_dy = float(dy)
                    merged_delay = float(delay) if delay else 0.0

                try:
                    if merged_dx != 0.0 or merged_dy != 0.0:
                        self.controller.move(merged_dx, merged_dy)
                except Exception as e:
                    print("[Mouse.move error]", e)
                if merged_delay > 0:
                    time.sleep(merged_delay)
            except queue.Empty:
                time.sleep(0.001)
                continue
            except Exception as e:
                print(f"[Move Queue Error] {e}")
                time.sleep(0.01)

    def _clip_movement(self, dx, dy):
        """
        闄愬埗绉诲嫊閫熷害
        
        灏囩Щ鍕曡窛闆㈤檺鍒跺湪鏈€澶ч€熷害绡勫湇鍏э紝闃叉绉诲嫊閬庡揩銆?        
        Args:
            dx: X 鏂瑰悜鐨勭Щ鍕曡窛闆?            dy: Y 鏂瑰悜鐨勭Щ鍕曡窛闆?            
        Returns:
            tuple: (clipped_dx, clipped_dy) 闄愬埗寰岀殑绉诲嫊璺濋洟
        """
        clipped_dx = np.clip(dx, -abs(self.max_speed), abs(self.max_speed))
        clipped_dy = np.clip(dy, -abs(self.max_speed), abs(self.max_speed))
        return float(clipped_dx), float(clipped_dy)

    def _track_loop(self):
        """
        涓昏拷韫ゅ惊鐠?        
        鍦ㄥ緦鍙扮窔绋嬩腑鎸佺簩鍩疯杩借工鎿嶄綔锛屾帶鍒跺箑鐜囦互閬斿埌鐩 FPS銆?        姣忔寰挵瑾跨敤 track_once() 閫茶涓€娆″畬鏁寸殑杩借工铏曠悊銆?        """
        while not self._stop_event.is_set():
            period = 1.0 / float(self._target_fps)
            start = time.time()
            try:
                self.track_once()
            except Exception as e:
                print("[Track error]", e)
            elapsed = time.time() - start
            to_sleep = max(0, period - elapsed)
            if to_sleep > 0:
                time.sleep(to_sleep)
    
    def set_target_fps(self, fps):
        """
        Dynamically update target FPS
        
        Args:
            fps: New target FPS value
        """
        if fps < 1 or fps > 1000:
            print(f"[AimTracker] Invalid FPS: {fps}, using default 80")
            fps = 80
        self._target_fps = float(fps)
        print(f"[AimTracker] Target FPS updated to: {fps}")
    
    def _handle_button_mask(self):
        """
        铏曠悊鎸夐垥閬僵閭忚集
        
        鏍规摎閰嶇疆姹哄畾鏄惁閹栧畾鐗瑰畾鐨勬粦榧犳寜閳曪紝闃叉鍦ㄧ瀯婧栨檪瑾よЦ銆?        """
        # 濡傛灉鏈暉鐢?Button Mask锛岃В閹栨墍鏈夋寜閳?
        if not getattr(config, "button_mask_enabled", False):
            try:
                from src.utils.mouse import unlock_all_locks
                unlock_all_locks()
            except Exception as e:
                pass
            return
        
        # 妾㈡煡鏄惁鏈変换浣?aimbot 姝ｅ湪閬嬭
        aimbot_running = (
            getattr(config, "enableaim", False) or 
            getattr(config, "enableaim_sec", False) or 
            getattr(config, "enabletb", False)
        )
        
        if not aimbot_running:
            try:
                from src.utils.mouse import unlock_all_locks
                unlock_all_locks()
            except Exception as e:
                pass
            return
        
        # 妲嬪缓闇€瑕侀伄缃╃殑鎸夐垥闆嗗悎
        mask_set = set()
        
        button_mapping = {
            "mask_left_button": 0,    # L
            "mask_right_button": 1,   # R
            "mask_middle_button": 2,  # M
            "mask_side4_button": 3,   # S4
            "mask_side5_button": 4,   # S5
        }
        
        for config_key, button_idx in button_mapping.items():
            if getattr(config, config_key, False):
                mask_set.add(button_idx)
        
        # 鎳夌敤閬僵
        try:
            from src.utils.mouse import lock_button_idx, unlock_button_idx, is_connected
            
            if not is_connected:
                return
            
            # 杩借釜鐣跺墠宸查帠瀹氱殑鎸夐垥
            if not hasattr(self, '_current_masked_buttons'):
                self._current_masked_buttons = set()
            
            # 瑙ｉ帠涓嶅啀闇€瑕侀伄缃╃殑鎸夐垥
            for idx in list(self._current_masked_buttons - mask_set):
                unlock_button_idx(idx)
            
            # 閹栧畾鏂伴渶瑕侀伄缃╃殑鎸夐垥
            for idx in list(mask_set - self._current_masked_buttons):
                lock_button_idx(idx)
            
            # 鏇存柊鐣跺墠鐙€鎱?
            self._current_masked_buttons = mask_set
            
        except Exception as e:
            print(f"[Button Mask Error] {e}")

    def _draw_fovs(self, img, frame):
        """
        绻＝ FOV锛堣閲庣瘎鍦嶏級鍦撳湀
        
        鍦ㄥ湒鍍忎笂绻＝ Aimbot 鍜?Triggerbot 鐨?FOV 绡勫湇鍦撳湀锛?        鐢ㄦ柤瑕栬鍖栭’绀虹瀯婧栧拰瑙哥櫦鍗€鍩熴€?        
        Args:
            img: BGR 鍦栧儚闄ｅ垪
            frame: 瑕栭牷骞€鐗╀欢锛屽寘鍚В鏋愬害淇℃伅
        """
        center_x = int(frame.xres / 2)
        center_y = int(frame.yres / 2)
        if getattr(config, "enableaim", False):
            mode_main = getattr(config, "mode", "Normal")
            # 鍦?NCAF 涓嬩笉鐣師鏈?FOV 鍦擄紝鍙’绀?NCAF 鍗婂緫
            if mode_main != "NCAF":
                cv2.circle(img, (center_x, center_y), int(getattr(config, "fovsize", self.fovsize)), (255, 255, 255), 2)
                # Correct: cercle smoothing = normalsmoothFOV
                cv2.circle(img, (center_x, center_y), int(getattr(config, "normalsmoothfov", self.normalsmoothfov)), (51, 255, 255), 2)
            # NCAF Radius 鍦?(Main)
            if mode_main == "NCAF":
                snap_r = int(getattr(config, "ncaf_snap_radius", 150))
                near_r = int(getattr(config, "ncaf_near_radius", 50))
                self._draw_dashed_circle(img, center_x, center_y, snap_r, (180, 180, 180), 1)
                cv2.circle(img, (center_x, center_y), near_r, (255, 200, 100), 1)
        if getattr(config, "enabletb", False):
            cv2.circle(img, (center_x, center_y), int(getattr(config, "tbfovsize", self.tbfovsize)), (255, 255, 255), 2)

    def _update_raw_stream_windows(self, raw_img):
        """Show or close raw-stream windows for NDI/UDP based on settings."""
        mode = getattr(self.app.capture, "mode", "")
        show_windows = bool(getattr(config, "show_opencv_windows", True))
        show_ndi = show_windows and mode == "NDI" and bool(getattr(config, "show_ndi_raw_stream_window", False))
        show_udp = show_windows and mode == "UDP" and bool(getattr(config, "show_udp_raw_stream_window", False))

        try:
            if show_ndi:
                cv2.imshow(self.RAW_STREAM_NDI_WINDOW, raw_img)
                self._raw_stream_window_visible[self.RAW_STREAM_NDI_WINDOW] = True
            elif self._raw_stream_window_visible.get(self.RAW_STREAM_NDI_WINDOW, False):
                cv2.destroyWindow(self.RAW_STREAM_NDI_WINDOW)
                self._raw_stream_window_visible[self.RAW_STREAM_NDI_WINDOW] = False
        except Exception:
            pass

        try:
            if show_udp:
                cv2.imshow(self.RAW_STREAM_UDP_WINDOW, raw_img)
                self._raw_stream_window_visible[self.RAW_STREAM_UDP_WINDOW] = True
            elif self._raw_stream_window_visible.get(self.RAW_STREAM_UDP_WINDOW, False):
                cv2.destroyWindow(self.RAW_STREAM_UDP_WINDOW)
                self._raw_stream_window_visible[self.RAW_STREAM_UDP_WINDOW] = False
        except Exception:
            pass

        if show_ndi or show_udp:
            try:
                cv2.waitKey(1)
            except Exception:
                pass

    def _close_raw_stream_windows(self):
        """Close raw-stream windows."""
        try:
            if self._raw_stream_window_visible.get(self.RAW_STREAM_NDI_WINDOW, False):
                cv2.destroyWindow(self.RAW_STREAM_NDI_WINDOW)
                self._raw_stream_window_visible[self.RAW_STREAM_NDI_WINDOW] = False
        except Exception:
            pass
        try:
            if self._raw_stream_window_visible.get(self.RAW_STREAM_UDP_WINDOW, False):
                cv2.destroyWindow(self.RAW_STREAM_UDP_WINDOW)
                self._raw_stream_window_visible[self.RAW_STREAM_UDP_WINDOW] = False
        except Exception:
            pass

    def _filter_targets_with_anti_smoke(self, targets, target_bboxes, mask, frame_shape, detector):
        """Filter targets using nearest bbox contour checks from anti-smoke detector."""
        if not targets or not target_bboxes or detector is None:
            return targets
        if not detector.is_enabled() or mask is None:
            return targets

        filtered_targets = []
        for target in targets:
            if len(target) < 2:
                continue
            tx, ty = float(target[0]), float(target[1])
            nearest_bbox = min(
                target_bboxes,
                key=lambda item: (float(item[0][0]) - tx) ** 2 + (float(item[0][1]) - ty) ** 2,
            )[1]
            if detector.is_bbox_plausible(nearest_bbox, mask, frame_shape):
                filtered_targets.append(target)
        return filtered_targets

    def track_once(self):
        """
        鍩疯涓€娆″畬鏁寸殑杩借工铏曠悊
        
        閫欐槸杩借工鍣ㄧ殑鏍稿績鏂规硶锛屽煼琛屼互涓嬫椹燂細
        1. 妾㈡煡閫ｆ帴鐙€鎱?        2. 铏曠悊 Button Mask
        3. 鎹曠嵅鐣跺墠瑕栭牷骞€
        4. 鍩疯鐩妾㈡脯
        5. 铏曠悊妾㈡脯绲愭灉涓︿及绠楅牠閮ㄤ綅缃?        6. 绻＝ FOV 鍜岀洰妯欐瑷?        7. 鍩疯鐬勬簴鍜岀Щ鍕曢倧杓?        8. 椤ず妾㈡脯绲愭灉绐楀彛
        """
        if not self.app.capture.is_connected():
            self._close_raw_stream_windows()
            return

        # Button Mask 绠＄悊
        self._handle_button_mask()
        
        # Mouse Lock 绠＄悊鍣?tick
        try:
            from src.utils.mouse import tick_movement_lock_manager
            tick_movement_lock_manager()
        except Exception:
            pass

        # 浣跨敤 CaptureService 璁€鍙?BGR 骞€
        raw_bgr_img = self.app.capture.read_frame(apply_fov=False)
        if raw_bgr_img is None:
            return

        # 纰轰繚鍦栧儚鏄€ｇ簩涓斿彲瀵殑鏁哥祫锛屼互閬垮厤 OpenCV 閷
        if not raw_bgr_img.flags['C_CONTIGUOUS']:
            raw_bgr_img = np.ascontiguousarray(raw_bgr_img)

        self._update_raw_stream_windows(raw_bgr_img)

        bgr_img = self.app.capture.apply_mode_fov(raw_bgr_img)
        if bgr_img is None:
            return
        if not bgr_img.flags['C_CONTIGUOUS']:
            bgr_img = np.ascontiguousarray(bgr_img)

        # 骞€瑷堟暩锛堜緵 UI 璁€鍙栵紝涓嶅啀鍙嶈鎵撳嵃锛?
        self._frame_count += 1
        current_time = time.time()
        if current_time - self._last_frame_log_time >= 5.0:
            self._frame_count = 0
            self._last_frame_log_time = current_time
        
        # 椹楄瓑骞€鐨勬湁鏁堟€?
        if bgr_img.size == 0:
            print("[Track] Empty frame received")
            return

        # 鍓靛缓铏涙摤骞€灏嶈薄浠ュ吋瀹硅垔浠ｇ⒓
        h, w = bgr_img.shape[:2]
        if w == 0 or h == 0: 
            print(f"[Track] Invalid frame dimensions: {w}x{h}")
            return
        frame = FrameInfo(w, h)

        try:
            detection_results, mask = perform_detection(self.model, bgr_img)
            # 椤ず MASK 瑕栫獥锛堝鏋滃暉鐢級
            if (getattr(config, "show_opencv_windows", True) and 
                getattr(config, "show_opencv_mask", True) and 
                mask is not None):
                cv2.imshow("MASK", mask)
                cv2.waitKey(1)
        except Exception as e:
            print("[perform_detection error]", e)
            detection_results = []
            mask = None
            # 鍗充娇妾㈡脯澶辨晽锛屼篃椤ず鍘熷鍦栧儚锛堝鏋滃暉鐢級
            if (getattr(config, "show_opencv_windows", True) and 
                getattr(config, "show_opencv_detection", True)):
                try:
                    cv2.imshow("Detection", bgr_img)
                    cv2.waitKey(1)
                except:
                    pass

        targets = []
        target_bboxes = []
        if detection_results:
            # 鐛插彇鐣跺墠 aim_type锛圡ain Aimbot锛?
            aim_type = getattr(config, "aim_type", "head")
            frame_area = max(1, int(frame.xres) * int(frame.yres))
            dynamic_min_area = int(
                getattr(
                    config,
                    "min_detection_bbox_area",
                    max(120, int(frame_area * 0.0015)),
                )
            )
            if str(getattr(config, "detection_morph_mode", "legacy")).strip().lower() != "stable":
                dynamic_min_area = min(dynamic_min_area, max(40, int(frame_area * 0.00035)))
            
            for det in detection_results:
                try:
                    x, y, w, h = det['bbox']
                    conf = det.get('confidence', 1.0)
                    if int(w) <= 0 or int(h) <= 0:
                        continue
                    # Ignore tiny blobs to reduce per-frame target flicker.
                    if int(w) * int(h) < dynamic_min_area:
                        continue
                    x1, y1 = int(x), int(y)
                    x2, y2 = int(x + w), int(y + h)
                    # Dessin corps
                    self._draw_body(bgr_img, x1, y1, x2, y2, conf)
                    
                    # 瑷堢畻 body 鐨勪腑蹇冮粸鍜?Y 绡勫湇
                    body_cx = (x1 + x2) / 2.0
                    body_cy = (y1 + y2) / 2.0
                    body_y_min = y1  # body 鐨?Y 杌告渶楂樺€硷紙鍦栧儚搴ф绯讳腑 y 瓒婂皬瓒婇潬涓婏級
                    body_y_max = y2  # body 鐨?Y 杌告渶浣庡€?                    
                    # Estimation t锚tes dans la bbox
                    head_positions = self._estimate_head_positions(x1, y1, x2, y2, bgr_img, mask)
                    
                    if aim_type == "body":
                        # Body 妯″紡锛氫娇鐢?body 涓績榛?
                        d = math.hypot(body_cx - frame.xres / 2.0, body_cy - frame.yres / 2.0)
                        target_tuple = (body_cx, body_cy, d, None, None)
                        targets.append(target_tuple)  # 鏈€寰屽叐鍊嬪弮鏁哥偤 head_y_min, body_y_max锛坆ody 妯″紡涓嶉渶瑕侊級
                        target_bboxes.append(((body_cx, body_cy), (x1, y1, int(w), int(h))))
                    else:
                        # Head 鎴?Nearest 妯″紡锛氫娇鐢?head 浣嶇疆
                        for head_cx, head_cy, bbox in head_positions:
                            self._draw_head_bbox(bgr_img, head_cx, head_cy)
                            d = math.hypot(head_cx - frame.xres / 2.0, head_cy - frame.yres / 2.0)
                            
                            # 瑷堢畻 head 鐨?Y 绡勫湇锛堢敤鏂?nearest 妯″紡锛?
                            # head_y_min 鏄?head 鐨勬渶楂?Y 鍊硷紙鏈€灏忕殑 y锛屽湪鍦栧儚搴ф绯讳腑锛?
                            # 浣跨敤 head_cy 娓涘幓涓€鍊嬩及绠楃殑 head 鍗婇珮锛堢磩 15 鍍忕礌锛?
                            estimated_head_height = 30  # 浼扮畻 head 楂樺害
                            head_y_min = head_cy - estimated_head_height // 2  # head 鏈€楂?Y 鍊?                            
                            if aim_type == "nearest":
                                # Nearest 妯″紡锛氫繚瀛?Y 绡勫湇淇℃伅
                                target_tuple = (head_cx, head_cy, d, head_y_min, body_y_max)
                            else:  # head 妯″紡
                                target_tuple = (head_cx, head_cy, d, None, None)
                            targets.append(target_tuple)
                            target_bboxes.append(((head_cx, head_cy), (x1, y1, int(w), int(h))))
                except Exception as e:
                    print("Erreur dans _estimate_head_positions:", e)

        targets_all = targets
        use_temporal_smoothing = bool(getattr(config, "enable_target_temporal_smoothing", False))
        if targets_all and use_temporal_smoothing:
            targets_all = self._target_smoother.stabilize(targets_all, frame.xres / 2.0, frame.yres / 2.0)
            self.last_target = self._target_smoother.last_target
            self.stable_candidate = self._target_smoother.stable_candidate
            self.stable_count = self._target_smoother.stable_count

        targets_main = list(targets_all)
        targets_sec = list(targets_all)
        if targets_all and target_bboxes:
            frame_shape = bgr_img.shape
            targets_main = self._filter_targets_with_anti_smoke(
                targets_all, target_bboxes, mask, frame_shape, self.anti_smoke_detector
            )
            targets_sec = self._filter_targets_with_anti_smoke(
                targets_all, target_bboxes, mask, frame_shape, self.anti_smoke_detector_sec
            )

        # FOVs une fois par frame
        try:
            self._draw_fovs(bgr_img, frame)
        except Exception:
            pass

        try:
            self._aim_and_move(
                targets_main,
                frame,
                bgr_img,
                targets_sec=targets_sec,
                targets_trigger=targets_all,
            )
        except Exception as e:
            print("[Aim error]", e)

        # 椤ず Detection 瑕栫獥锛堟牴鎿氳ō缃級
        if (getattr(config, "show_opencv_windows", True) and 
            getattr(config, "show_opencv_detection", True)):
            try:
                # 鍎寲绻＝锛氭坊鍔犳洿澶氳瑕轰俊鎭?
                display_img = self._draw_enhanced_detection(bgr_img.copy(), targets_all, frame)
                cv2.imshow("Detection", display_img)
                cv2.waitKey(1)
            except Exception as e:
                print(f"[OpenCV display error] {e}")
    
    def _draw_enhanced_detection(self, img, targets, frame):
        """
        绻＝澧炲挤鐨勬娓瑕哄寲
        
        Args:
            img: BGR 鍦栧儚
            targets: 鐩鍒楄〃 [(cx, cy, distance), ...]
            frame: 骞€淇℃伅灏嶈薄
            
        Returns:
            绻＝寰岀殑鍦栧儚
        """
        center_x = int(frame.xres / 2)
        center_y = int(frame.yres / 2)
        
        # 1. 绻＝鍗佸瓧婧栨槦锛堜腑蹇冿級- 鏍规摎瑷疆
        if getattr(config, "show_crosshair", True):
            crosshair_size = 20
            crosshair_color = (0, 255, 0)  # 缍犺壊
            cv2.line(img, (center_x - crosshair_size, center_y), 
                    (center_x + crosshair_size, center_y), crosshair_color, 2)
            cv2.line(img, (center_x, center_y - crosshair_size), 
                    (center_x, center_y + crosshair_size), crosshair_color, 2)
            cv2.circle(img, (center_x, center_y), 3, crosshair_color, -1)
        
        # 2. 绻＝ FOV 鍦撳湀
        if getattr(config, "enableaim", False):
            mode_main = getattr(config, "mode", "Normal")
            # NCAF 鏅備笉绻＝鍘熸湰鐨?FOV 鍦?
            if mode_main != "NCAF":
                # Main Aimbot FOV
                main_fov = int(getattr(config, "fovsize", self.fovsize))
                cv2.circle(img, (center_x, center_y), main_fov, (255, 255, 255), 2)
                
                # Smooth FOV
                smooth_fov = int(getattr(config, "normalsmoothfov", self.normalsmoothfov))
                cv2.circle(img, (center_x, center_y), smooth_fov, (0, 255, 255), 1)
            
            # NCAF Radius 鍦?(Main Aimbot)
            if mode_main == "NCAF":
                snap_r = int(getattr(config, "ncaf_snap_radius", 150))
                near_r = int(getattr(config, "ncaf_near_radius", 50))
                # Snap Radius (outer) 鈥?铏涚窔棰ㄦ牸
                self._draw_dashed_circle(img, center_x, center_y, snap_r, (180, 180, 180), 1, dash_len=12)
                # Near Radius (inner) 鈥?娣鸿棈鑹?
                cv2.circle(img, (center_x, center_y), near_r, (255, 200, 100), 1)
            
            # Sec Aimbot FOV (濡傛灉鍟熺敤)
            if getattr(config, "enableaim_sec", False):
                mode_sec = getattr(config, "mode_sec", "Normal")
                if mode_sec != "NCAF":
                    sec_fov = int(getattr(config, "fovsize_sec", self.fovsize_sec))
                    # 鑸囦富鐬勬簴涓嶅悓鑹诧紝鎺＄敤闈掕壊
                    cv2.circle(img, (center_x, center_y), sec_fov, (255, 255, 0), 2)
                
                # NCAF Radius 鍦?(Sec Aimbot)
                if mode_sec == "NCAF":
                    snap_r_sec = int(getattr(config, "ncaf_snap_radius_sec", 150))
                    near_r_sec = int(getattr(config, "ncaf_near_radius_sec", 50))
                    self._draw_dashed_circle(img, center_x, center_y, snap_r_sec, (200, 100, 200), 1, dash_len=12)
                    cv2.circle(img, (center_x, center_y), near_r_sec, (200, 150, 255), 1)
        
        # Triggerbot FOV
        if getattr(config, "enabletb", False):
            tb_fov = int(getattr(config, "tbfovsize", self.tbfovsize))
            cv2.circle(img, (center_x, center_y), tb_fov, (0, 165, 255), 2)
        
        # 3. 绻＝鐩淇℃伅
        if targets:
            # 鎵惧埌鏈€浣崇洰妯欙紙璺濋洟涓績鏈€杩戠殑锛?
            best_target = min(targets, key=lambda t: t[2])
            
            for i, target in enumerate(targets):
                # targets 绲愭: (cx, cy, distance, head_y_min, body_y_max)
                if len(target) >= 5:
                    tx, ty, dist, _, _ = target
                else:
                    # 鍏煎鑸婃牸寮?
                    tx, ty, dist = target[:3]
                
                is_best = target == best_target
                
                # 鐩榛為鑹诧紙鏈€浣崇洰妯欑敤涓嶅悓椤忚壊锛?
                if is_best:
                    target_color = (0, 0, 255)  # 绱呰壊
                    circle_radius = 8
                    thickness = -1  # 瀵﹀績
                else:
                    target_color = (255, 0, 0)  # 钘嶈壊
                    circle_radius = 5
                    thickness = 2
                
                # 绻＝鐩榛?
                cv2.circle(img, (int(tx), int(ty)), circle_radius, target_color, thickness)
                
                # 绻＝寰炰腑蹇冨埌鐩鐨勯€ｇ窔锛堝儏鏈€浣崇洰妯欙級
                if is_best:
                    cv2.line(img, (center_x, center_y), (int(tx), int(ty)), 
                            (0, 255, 0), 1, cv2.LINE_AA)
                
                # 绻＝璺濋洟鏂囧瓧 - 鏍规摎瑷疆
                if getattr(config, "show_distance_text", True):
                    dist_text = f"{int(dist)}px"
                    cv2.putText(img, dist_text, (int(tx) + 10, int(ty) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, target_color, 1, cv2.LINE_AA)
        
        # 4. 绻＝鐙€鎱嬩俊鎭紙宸︿笂瑙掞級- 鏍规摎瑷疆
        y_offset = 30
        line_height = 25
        
        # 妯″紡淇℃伅
        if getattr(config, "show_mode_text", True):
            mode = getattr(config, "mode", "Normal")
            cv2.putText(img, f"Mode: {mode}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            y_offset += line_height
        
        # Aimbot 鐙€鎱?
        if getattr(config, "show_aimbot_status", True):
            if getattr(config, "enableaim", False):
                main_status = "ON" if getattr(config, "enableaim", False) else "OFF"
                status_color = (0, 255, 0) if main_status == "ON" else (0, 0, 255)
                cv2.putText(img, f"Main Aim: {main_status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_AA)
                y_offset += line_height
            
            if getattr(config, "enableaim_sec", False):
                sec_status = "ON" if getattr(config, "enableaim_sec", False) else "OFF"
                status_color = (255, 0, 255) if sec_status == "ON" else (128, 128, 128)
                cv2.putText(img, f"Sec Aim: {sec_status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_AA)
                y_offset += line_height
        
        # Triggerbot 鐙€鎱?
        if getattr(config, "show_triggerbot_status", True) and getattr(config, "enabletb", False):
            tb_status = "ON" if getattr(config, "enabletb", False) else "OFF"
            status_color = (0, 165, 255) if tb_status == "ON" else (128, 128, 128)
            cv2.putText(img, f"Trigger: {tb_status}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_AA)
            y_offset += line_height
        
        # 鐩鏁搁噺
        if getattr(config, "show_target_count", True):
            cv2.putText(img, f"Targets: {len(targets)}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        
        return img

    @staticmethod
    def _draw_dashed_circle(img, cx, cy, radius, color, thickness=1, dash_len=10):
        """
        绻＝铏涚窔鍦撳湀

        Args:
            img: BGR 鍦栧儚
            cx, cy: 鍦撳績
            radius: 鍗婂緫 (px)
            color: BGR 椤忚壊
            thickness: 绶氱矖
            dash_len: 姣忔寮х殑瑙掑害 (搴?
        """
        import numpy as np
        if radius <= 0:
            return
        for angle_start in range(0, 360, dash_len * 2):
            angle_end = min(angle_start + dash_len, 360)
            cv2.ellipse(img, (cx, cy), (radius, radius), 0,
                        angle_start, angle_end, color, thickness, cv2.LINE_AA)

    def _draw_head_bbox(self, img, headx, heady):
        """
        绻＝闋儴浣嶇疆妯欒锛堝劒鍖栫増鏈級
        
        鍦ㄥ湒鍍忎笂绻＝涓€鍊嬪付澶栧湀鐨勯牠閮ㄦ瑷橈紝鏇村鏄撹瓨鍒ャ€?        
        Args:
            img: BGR 鍦栧儚闄ｅ垪
            headx: 闋儴 X 搴ф
            heady: 闋儴 Y 搴ф
        """
        # 澶栧湀锛堢櫧鑹诧級
        cv2.circle(img, (int(headx), int(heady)), 6, (255, 255, 255), 2)
        # 鍏у湀锛堢磪鑹诧級
        cv2.circle(img, (int(headx), int(heady)), 3, (0, 0, 255), -1)

    def _estimate_head_positions(self, x1, y1, x2, y2, img, mask=None):
        """
        Estimate head position from body bbox geometry only.
        """
        if not img.flags['C_CONTIGUOUS']:
            img = np.ascontiguousarray(img)

        offset_y = float(getattr(config, "offsetY", 0))
        offset_x = float(getattr(config, "offsetX", 0))

        width = max(1, int(x2) - int(x1))
        height = max(1, int(y2) - int(y1))

        top_crop_factor = 0.10
        side_crop_factor = 0.10

        effective_y1 = float(y1) + float(height) * top_crop_factor
        effective_height = float(height) * (1.0 - top_crop_factor)
        effective_x1 = float(x1) + float(width) * side_crop_factor
        effective_x2 = float(x2) - float(width) * side_crop_factor
        effective_width = max(1.0, effective_x2 - effective_x1)

        center_x = (effective_x1 + effective_x2) / 2.0
        headx_base = center_x + effective_width * (offset_x / 100.0)
        # Keep Y estimate deterministic (no mask-driven jitter).
        base_head_ratio = float(getattr(config, "head_estimate_ratio", 0.22))
        heady_base = float(y1) + float(height) * base_head_ratio + effective_height * (offset_y / 100.0)

        # Optional one-pass refinement from the already computed global mask.
        # Use only the upper body band and median X to reduce left/right arm jitter.
        if mask is not None:
            mx1 = max(0, min(int(x1), mask.shape[1] - 1))
            my1 = max(0, min(int(y1), mask.shape[0] - 1))
            mx2 = max(mx1 + 1, min(int(x2), mask.shape[1]))
            my2 = max(my1 + 1, min(int(y2), mask.shape[0]))
            upper_h = max(6, int((my2 - my1) * 0.42))
            upper_y2 = min(my2, my1 + upper_h)
            upper_mask = mask[my1:upper_y2, mx1:mx2]
            if upper_mask.size > 0:
                ys, xs = np.where(upper_mask > 0)
                if len(xs) >= int(getattr(config, "head_refine_min_pixels", 20)):
                    headx_base = float(mx1 + int(np.median(xs)))

        pixel_marginx = max(12, int(width * 0.20))
        pixel_marginy = max(8, int(height * 0.10))
        x1_roi = int(max(headx_base - pixel_marginx, 0))
        y1_roi = int(max(heady_base - pixel_marginy, 0))
        x2_roi = int(min(headx_base + pixel_marginx, img.shape[1]))
        y2_roi = int(min(heady_base + pixel_marginy, img.shape[0]))

        if x2_roi <= x1_roi or y2_roi <= y1_roi:
            return [(int(round(headx_base)), int(round(heady_base)), (x1_roi, y1_roi, x2_roi, y2_roi))]

        cv2.rectangle(img, (x1_roi, y1_roi), (x2_roi, y2_roi), (0, 255, 255), 1)

        return [(int(round(headx_base)), int(round(heady_base)), (x1_roi, y1_roi, x2_roi, y2_roi))]

    def _draw_body(self, img, x1, y1, x2, y2, conf):
        """
        绻＝韬珨妾㈡脯妗嗭紙鍎寲鐗堟湰锛?        
        鍦ㄥ湒鍍忎笂绻＝韬珨妾㈡脯妗嗗拰缃俊搴︽绫わ紝浣跨敤鏇村ソ鐨勮瑕烘晥鏋溿€?        
        Args:
            img: BGR 鍦栧儚闄ｅ垪
            x1, y1: 妾㈡脯妗嗗乏涓婅搴ф
            x2, y2: 妾㈡脯妗嗗彸涓嬭搴ф
            conf: 妾㈡脯缃俊搴?        """
        # 绻＝鐭╁舰妗嗭紙钘嶈壊锛岃純绮楋級
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
        
        # 绻＝瑙掓锛堜娇鍏舵洿鏄庨’锛?
        corner_len = 20
        thickness = 3
        # 宸︿笂瑙?
        cv2.line(img, (int(x1), int(y1)), (int(x1 + corner_len), int(y1)), (0, 255, 0), thickness)
        cv2.line(img, (int(x1), int(y1)), (int(x1), int(y1 + corner_len)), (0, 255, 0), thickness)
        # 鍙充笂瑙?
        cv2.line(img, (int(x2), int(y1)), (int(x2 - corner_len), int(y1)), (0, 255, 0), thickness)
        cv2.line(img, (int(x2), int(y1)), (int(x2), int(y1 + corner_len)), (0, 255, 0), thickness)
        # 宸︿笅瑙?
        cv2.line(img, (int(x1), int(y2)), (int(x1 + corner_len), int(y2)), (0, 255, 0), thickness)
        cv2.line(img, (int(x1), int(y2)), (int(x1), int(y2 - corner_len)), (0, 255, 0), thickness)
        # 鍙充笅瑙?
        cv2.line(img, (int(x2), int(y2)), (int(x2 - corner_len), int(y2)), (0, 255, 0), thickness)
        cv2.line(img, (int(x2), int(y2)), (int(x2), int(y2 - corner_len)), (0, 255, 0), thickness)
        
        # 绻＝妯欑堡鑳屾櫙锛堝崐閫忔槑榛戣壊鐭╁舰锛?
        label_text = f"Body {conf:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, font_thickness)
        
        # 妯欑堡浣嶇疆
        label_x1 = int(x1)
        label_y1 = int(y1) - text_height - 10
        label_x2 = int(x1) + text_width + 10
        label_y2 = int(y1)
        
        # 绻＝鑳屾櫙鐭╁舰
        cv2.rectangle(img, (label_x1, label_y1), (label_x2, label_y2), (0, 0, 0), -1)
        
        # 绻＝鏂囧瓧
        cv2.putText(img, label_text, (int(x1) + 5, int(y1) - 5), 
                   font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    def _aim_and_move(self, targets_main, frame, img, targets_sec=None, targets_trigger=None):
        """
        铏曠悊鐬勬簴鍜岀Щ鍕曢倧杓?        
        绲变竴瑾垮害鍣細Main Aimbot 鍜?Sec Aimbot 鍚勮嚜浣跨敤鐛ㄧ珛鐨?Operation Mode銆?        鏀寔 Normal銆丼ilent銆丯CAF銆乄indMouse 鍥涚ó妯″紡銆?        
        Args:
            targets_main: Main Aimbot target list
            frame: 瑕栭牷骞€鐗╀欢
            img: BGR 鍦栧儚闄ｅ垪
            targets_sec: Secondary Aimbot target list
            targets_trigger: Triggerbot target list
        """
        try:
            process_normal_mode(
                targets_main,
                frame,
                img,
                self,
                targets_sec=targets_sec,
                targets_trigger=targets_trigger,
            )
        except Exception as e:
            print("[Aim dispatch error]", e)


if __name__ == "__main__":
    """
    涓荤▼搴忓叆鍙?    
    鍒濆鍖栨墍鏈夊繀瑕佺殑绲勪欢涓﹀暉鍕曟噳鐢ㄧ▼寮忥細
    1. 鍒濆鍖?Capture Service
    2. 鍓靛缓 AimTracker 瀵︿緥
    3. 瑷疆 UI 澶栬
    4. 鍓靛缓涓﹀暉鍕?UI 鎳夌敤
    """
    import customtkinter as ctk
    from src.ui import ViewerApp
    
    # 鍒濆鍖栨崟鐛叉湇鍕?
    capture_service = CaptureService()
    
    # 鍓靛缓涓€鍊嬭嚚鏅傛噳鐢ㄥ渚嬬敤鏂?AimTracker
    class TempApp:
        """鑷ㄦ檪鎳夌敤椤?"""
        def __init__(self, capture):
            self.capture = capture
    
    temp_app = TempApp(capture_service)
    
    # 鍓靛缓 AimTracker (use config value if available)
    target_fps = getattr(config, "target_fps", 80)
    tracker = AimTracker(app=temp_app, target_fps=target_fps)
    
    # 瑷疆澶栬
    ctk.set_appearance_mode("Dark")
    try:
        ctk.set_default_color_theme("themes/metal.json")
    except Exception:
        pass
    
    # 鍓靛缓 UI 鎳夌敤
    app = ViewerApp(tracker=tracker, capture_service=capture_service)
    
    # 鏇存柊 tracker 鐨?app 寮曠敤
    tracker.app = app
    
    # 杓夊叆涓︽噳鐢ㄩ厤缃紙纰轰繚鎵€鏈夎ō缃兘姝ｇ⒑锛?
    config.load_from_file()
    app._sync_config_to_tracker()
    
    print("[Main] Application initialized")
    
    # Print version info
    from src.utils.updater import get_update_checker
    updater = get_update_checker()
    print(f"[Main] Current version: v{updater.get_current_version()}")
    
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    
    # Schedule update check after UI is ready (2 seconds delay)
    app.after(2000, app._check_for_updates)
    
    app.mainloop()


