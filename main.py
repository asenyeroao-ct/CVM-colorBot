import threading
import queue
import time
import math
import numpy as np
import cv2
import ctypes
import sys
import os

# 設置 AppUserModelID 以便在 Windows 任務欄正確顯示圖標
try:
    myappid = 'mycompany.colorbot.v2.0' # 任意唯一的字符串
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from src.utils.config import config
from src.utils.mouse import Mouse, is_button_pressed
from src.utils.detection import load_model, perform_detection
from src.capture.capture_service import CaptureService
from src.aim_system.normal import process_normal_mode
from src.aim_system.silent import process_silent_mode
from src.aim_system.anti_smoke_detector import AntiSmokeDetector

class FrameInfo:
    """簡單的幀信息類，用於兼容現有代碼"""
    def __init__(self, width, height):
        self.xres = width
        self.yres = height

class AimTracker:
    """
    目標追蹤器類
    
    負責處理視頻幀的捕獲、目標檢測、瞄準計算和滑鼠移動控制。
    支持多種模式（Normal、Silent）和配置選項。
    """
    
    def __init__(self, app, target_fps=80):
        """
        初始化 AimTracker
        
        Args:
            app: 應用程式實例，需要包含 capture 屬性（CaptureService）
            target_fps: 目標幀率，默認為 80 FPS
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
        # Triggerbot 連發設置（範圍）
        self.tbcooldown_min = float(getattr(config, "tbcooldown_min", 0.0))
        self.tbcooldown_max = float(getattr(config, "tbcooldown_max", 0.0))
        self.tbburst_count_min = int(getattr(config, "tbburst_count_min", 1))
        self.tbburst_count_max = int(getattr(config, "tbburst_count_max", 1))
        self.tbburst_interval_min = float(getattr(config, "tbburst_interval_min", 0.0))
        self.tbburst_interval_max = float(getattr(config, "tbburst_interval_max", 0.0))
        # 注意：last_tb_click_time 現在由 Triggerbot.py 中的全局狀態管理
        
        # RCS (Recoil Control System) 設置
        self.rcs_pull_speed = int(getattr(config, "rcs_pull_speed", 10))
        self.rcs_activation_delay = int(getattr(config, "rcs_activation_delay", 100))
        self.rcs_rapid_click_threshold = int(getattr(config, "rcs_rapid_click_threshold", 200))

        self.in_game_sens = float(getattr(config, "in_game_sens", 0.235))
        self.color = getattr(config, "color", "yellow")
        self.mode = getattr(config, "mode", "Normal")
        self.selected_mouse_button = getattr(config, "selected_mouse_button", 3),
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
        self.move_queue = queue.Queue(maxsize=50)
        self._move_thread = threading.Thread(target=self._process_move_queue, daemon=True)
        self._move_thread.start()

        self.model, self.class_names = load_model()
        print("Classes:", self.class_names)
        self._stop_event = threading.Event()
        self._target_fps = target_fps
        self._track_thread = threading.Thread(target=self._track_loop, daemon=True)
        self._track_thread.start()
        
        # 幀計數器（用於調試）
        self._frame_count = 0
        self._last_frame_log_time = time.time()
        
        # --- Anti-Smoke Detector 初始化 ---
        self.anti_smoke_detector = AntiSmokeDetector()
        self.anti_smoke_detector.set_enabled(getattr(config, "anti_smoke_enabled", False))
        
        self.anti_smoke_detector_sec = AntiSmokeDetector()
        self.anti_smoke_detector_sec.set_enabled(getattr(config, "anti_smoke_enabled_sec", False))
        
        print(f"[AntiSmoke] Main Aimbot Anti-Smoke: {self.anti_smoke_detector.is_enabled()}")
        print(f"[AntiSmoke] Sec Aimbot Anti-Smoke: {self.anti_smoke_detector_sec.is_enabled()}")

    def stop(self):
        """
        停止追蹤器
        
        設置停止事件並等待追蹤線程結束，用於清理資源。
        """
        self._stop_event.set()
        try:
            self._track_thread.join(timeout=1.0)
        except Exception:
            pass

    def _process_move_queue(self):
        """
        處理移動隊列
        
        在後台線程中持續從移動隊列中獲取移動指令並執行。
        支持延遲控制，確保移動操作的平滑執行。
        
        這是一個無限循環，直到線程被終止。
        """
        while True:
            try:
                dx, dy, delay = self.move_queue.get(timeout=0.1)
                try:
                    self.controller.move(dx, dy)
                except Exception as e:
                    print("[Mouse.move error]", e)
                if delay and delay > 0:
                    time.sleep(delay)
            except queue.Empty:
                time.sleep(0.001)
                continue
            except Exception as e:
                print(f"[Move Queue Error] {e}")
                time.sleep(0.01)

    def _clip_movement(self, dx, dy):
        """
        限制移動速度
        
        將移動距離限制在最大速度範圍內，防止移動過快。
        
        Args:
            dx: X 方向的移動距離
            dy: Y 方向的移動距離
            
        Returns:
            tuple: (clipped_dx, clipped_dy) 限制後的移動距離
        """
        clipped_dx = np.clip(dx, -abs(self.max_speed), abs(self.max_speed))
        clipped_dy = np.clip(dy, -abs(self.max_speed), abs(self.max_speed))
        return float(clipped_dx), float(clipped_dy)

    def _track_loop(self):
        """
        主追蹤循環
        
        在後台線程中持續執行追蹤操作，控制幀率以達到目標 FPS。
        每次循環調用 track_once() 進行一次完整的追蹤處理。
        """
        period = 1.0 / float(self._target_fps)
        while not self._stop_event.is_set():
            start = time.time()
            try:
                self.track_once()
            except Exception as e:
                print("[Track error]", e)
            elapsed = time.time() - start
            to_sleep = period - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
    
    def _handle_button_mask(self):
        """
        處理按鈕遮罩邏輯
        
        根據配置決定是否鎖定特定的滑鼠按鈕，防止在瞄準時誤觸。
        """
        # 如果未啟用 Button Mask，解鎖所有按鈕
        if not getattr(config, "button_mask_enabled", False):
            try:
                from src.utils.mouse import unlock_all_locks
                unlock_all_locks()
            except Exception as e:
                pass
            return
        
        # 檢查是否有任何 aimbot 正在運行
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
        
        # 構建需要遮罩的按鈕集合
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
        
        # 應用遮罩
        try:
            from src.utils.mouse import lock_button_idx, unlock_button_idx, is_connected
            
            if not is_connected:
                return
            
            # 追踪當前已鎖定的按鈕
            if not hasattr(self, '_current_masked_buttons'):
                self._current_masked_buttons = set()
            
            # 解鎖不再需要遮罩的按鈕
            for idx in list(self._current_masked_buttons - mask_set):
                unlock_button_idx(idx)
            
            # 鎖定新需要遮罩的按鈕
            for idx in list(mask_set - self._current_masked_buttons):
                lock_button_idx(idx)
            
            # 更新當前狀態
            self._current_masked_buttons = mask_set
            
        except Exception as e:
            print(f"[Button Mask Error] {e}")

    def _draw_fovs(self, img, frame):
        """
        繪製 FOV（視野範圍）圓圈
        
        在圖像上繪製 Aimbot 和 Triggerbot 的 FOV 範圍圓圈，
        用於視覺化顯示瞄準和觸發區域。
        
        Args:
            img: BGR 圖像陣列
            frame: 視頻幀物件，包含解析度信息
        """
        center_x = int(frame.xres / 2)
        center_y = int(frame.yres / 2)
        if getattr(config, "enableaim", False):
            cv2.circle(img, (center_x, center_y), int(getattr(config, "fovsize", self.fovsize)), (255, 255, 255), 2)
            # Correct: cercle smoothing = normalsmoothFOV
            cv2.circle(img, (center_x, center_y), int(getattr(config, "normalsmoothfov", self.normalsmoothfov)), (51, 255, 255), 2)
        if getattr(config, "enabletb", False):
            cv2.circle(img, (center_x, center_y), int(getattr(config, "tbfovsize", self.tbfovsize)), (255, 255, 255), 2)

    def track_once(self):
        """
        執行一次完整的追蹤處理
        
        這是追蹤器的核心方法，執行以下步驟：
        1. 檢查連接狀態
        2. 處理 Button Mask
        3. 捕獲當前視頻幀
        4. 執行目標檢測
        5. 處理檢測結果並估算頭部位置
        6. 繪製 FOV 和目標標記
        7. 執行瞄準和移動邏輯
        8. 顯示檢測結果窗口
        """
        if not self.app.capture.is_connected():
            return

        # Button Mask 管理
        self._handle_button_mask()

        # 使用 CaptureService 讀取 BGR 幀
        bgr_img = self.app.capture.read_frame()
        if bgr_img is None:
            return

        # 確保圖像是連續且可寫的數組，以避免 OpenCV 錯誤
        if not bgr_img.flags['C_CONTIGUOUS']:
            bgr_img = np.ascontiguousarray(bgr_img)

        # 幀計數和日誌（每 5 秒打印一次）
        self._frame_count += 1
        current_time = time.time()
        if current_time - self._last_frame_log_time >= 5.0:
            fps = self._frame_count / (current_time - self._last_frame_log_time)
            print(f"[Track] Receiving frames: {self._frame_count} frames in 5s (FPS: {fps:.2f})")
            self._frame_count = 0
            self._last_frame_log_time = current_time
        
        # 驗證幀的有效性
        if bgr_img.size == 0:
            print("[Track] Empty frame received")
            return

        # 創建虛擬幀對象以兼容舊代碼
        h, w = bgr_img.shape[:2]
        if w == 0 or h == 0: 
            print(f"[Track] Invalid frame dimensions: {w}x{h}")
            return
        frame = FrameInfo(w, h)

        try:
            detection_results, mask = perform_detection(self.model, bgr_img)
            # 顯示 MASK 視窗（如果啟用）
            if (getattr(config, "show_opencv_windows", True) and 
                getattr(config, "show_opencv_mask", True) and 
                mask is not None):
                cv2.imshow("MASK", mask)
                cv2.waitKey(1)
        except Exception as e:
            print("[perform_detection error]", e)
            detection_results = []
            # 即使檢測失敗，也顯示原始圖像（如果啟用）
            if (getattr(config, "show_opencv_windows", True) and 
                getattr(config, "show_opencv_detection", True)):
                try:
                    cv2.imshow("Detection", bgr_img)
                    cv2.waitKey(1)
                except:
                    pass

        targets = []
        if detection_results:
            # 獲取當前 aim_type（Main Aimbot）
            aim_type = getattr(config, "aim_type", "head")
            
            for det in detection_results:
                try:
                    x, y, w, h = det['bbox']
                    conf = det.get('confidence', 1.0)
                    x1, y1 = int(x), int(y)
                    x2, y2 = int(x + w), int(y + h)
                    y1 *= 1.03
                    # Dessin corps
                    self._draw_body(bgr_img, x1, y1, x2, y2, conf)
                    
                    # 計算 body 的中心點和 Y 範圍
                    body_cx = (x1 + x2) / 2.0
                    body_cy = (y1 + y2) / 2.0
                    body_y_min = y1  # body 的 Y 軸最高值（圖像座標系中 y 越小越靠上）
                    body_y_max = y2  # body 的 Y 軸最低值
                    
                    # Estimation têtes dans la bbox
                    head_positions = self._estimate_head_positions(x1, y1, x2, y2, bgr_img)
                    
                    if aim_type == "body":
                        # Body 模式：使用 body 中心點
                        d = math.hypot(body_cx - frame.xres / 2.0, body_cy - frame.yres / 2.0)
                        targets.append((body_cx, body_cy, d, None, None))  # 最後兩個參數為 head_y_min, body_y_max（body 模式不需要）
                    else:
                        # Head 或 Nearest 模式：使用 head 位置
                        for head_cx, head_cy, bbox in head_positions:
                            self._draw_head_bbox(bgr_img, head_cx, head_cy)
                            d = math.hypot(head_cx - frame.xres / 2.0, head_cy - frame.yres / 2.0)
                            
                            # 計算 head 的 Y 範圍（用於 nearest 模式）
                            # head_y_min 是 head 的最高 Y 值（最小的 y，在圖像座標系中）
                            # 使用 head_cy 減去一個估算的 head 半高（約 15 像素）
                            estimated_head_height = 30  # 估算 head 高度
                            head_y_min = head_cy - estimated_head_height // 2  # head 最高 Y 值
                            
                            if aim_type == "nearest":
                                # Nearest 模式：保存 Y 範圍信息
                                targets.append((head_cx, head_cy, d, head_y_min, body_y_max))
                            else:  # head 模式
                                targets.append((head_cx, head_cy, d, None, None))
                except Exception as e:
                    print("Erreur dans _estimate_head_positions:", e)


        # FOVs une fois par frame
        try:
            self._draw_fovs(bgr_img, frame)
        except Exception:
            pass

        try:
            self._aim_and_move(targets, frame, bgr_img)
        except Exception as e:
            print("[Aim error]", e)

        # 顯示 Detection 視窗（根據設置）
        if (getattr(config, "show_opencv_windows", True) and 
            getattr(config, "show_opencv_detection", True)):
            try:
                # 優化繪製：添加更多視覺信息
                display_img = self._draw_enhanced_detection(bgr_img.copy(), targets, frame)
                cv2.imshow("Detection", display_img)
                cv2.waitKey(1)
            except Exception as e:
                print(f"[OpenCV display error] {e}")
    
    def _draw_enhanced_detection(self, img, targets, frame):
        """
        繪製增強的檢測視覺化
        
        Args:
            img: BGR 圖像
            targets: 目標列表 [(cx, cy, distance), ...]
            frame: 幀信息對象
            
        Returns:
            繪製後的圖像
        """
        center_x = int(frame.xres / 2)
        center_y = int(frame.yres / 2)
        
        # 1. 繪製十字準星（中心）- 根據設置
        if getattr(config, "show_crosshair", True):
            crosshair_size = 20
            crosshair_color = (0, 255, 0)  # 綠色
            cv2.line(img, (center_x - crosshair_size, center_y), 
                    (center_x + crosshair_size, center_y), crosshair_color, 2)
            cv2.line(img, (center_x, center_y - crosshair_size), 
                    (center_x, center_y + crosshair_size), crosshair_color, 2)
            cv2.circle(img, (center_x, center_y), 3, crosshair_color, -1)
        
        # 2. 繪製 FOV 圓圈
        if getattr(config, "enableaim", False):
            # Main Aimbot FOV
            main_fov = int(getattr(config, "fovsize", self.fovsize))
            cv2.circle(img, (center_x, center_y), main_fov, (255, 255, 255), 2)
            
            # Smooth FOV
            smooth_fov = int(getattr(config, "normalsmoothfov", self.normalsmoothfov))
            cv2.circle(img, (center_x, center_y), smooth_fov, (0, 255, 255), 1)
            
            # Sec Aimbot FOV (如果啟用)
            if getattr(config, "enableaim_sec", False):
                sec_fov = int(getattr(config, "fovsize_sec", self.fovsize_sec))
                cv2.circle(img, (center_x, center_y), sec_fov, (255, 0, 255), 2)
        
        # Triggerbot FOV
        if getattr(config, "enabletb", False):
            tb_fov = int(getattr(config, "tbfovsize", self.tbfovsize))
            cv2.circle(img, (center_x, center_y), tb_fov, (0, 165, 255), 2)
        
        # 3. 繪製目標信息
        if targets:
            # 找到最佳目標（距離中心最近的）
            best_target = min(targets, key=lambda t: t[2])
            
            for i, target in enumerate(targets):
                # targets 結構: (cx, cy, distance, head_y_min, body_y_max)
                if len(target) >= 5:
                    tx, ty, dist, _, _ = target
                else:
                    # 兼容舊格式
                    tx, ty, dist = target[:3]
                
                is_best = target == best_target
                
                # 目標點顏色（最佳目標用不同顏色）
                if is_best:
                    target_color = (0, 0, 255)  # 紅色
                    circle_radius = 8
                    thickness = -1  # 實心
                else:
                    target_color = (255, 0, 0)  # 藍色
                    circle_radius = 5
                    thickness = 2
                
                # 繪製目標點
                cv2.circle(img, (int(tx), int(ty)), circle_radius, target_color, thickness)
                
                # 繪製從中心到目標的連線（僅最佳目標）
                if is_best:
                    cv2.line(img, (center_x, center_y), (int(tx), int(ty)), 
                            (0, 255, 0), 1, cv2.LINE_AA)
                
                # 繪製距離文字 - 根據設置
                if getattr(config, "show_distance_text", True):
                    dist_text = f"{int(dist)}px"
                    cv2.putText(img, dist_text, (int(tx) + 10, int(ty) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, target_color, 1, cv2.LINE_AA)
        
        # 4. 繪製狀態信息（左上角）- 根據設置
        y_offset = 30
        line_height = 25
        
        # 模式信息
        if getattr(config, "show_mode_text", True):
            mode = getattr(config, "mode", "Normal")
            cv2.putText(img, f"Mode: {mode}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            y_offset += line_height
        
        # Aimbot 狀態
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
        
        # Triggerbot 狀態
        if getattr(config, "show_triggerbot_status", True) and getattr(config, "enabletb", False):
            tb_status = "ON" if getattr(config, "enabletb", False) else "OFF"
            status_color = (0, 165, 255) if tb_status == "ON" else (128, 128, 128)
            cv2.putText(img, f"Trigger: {tb_status}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_AA)
            y_offset += line_height
        
        # 目標數量
        if getattr(config, "show_target_count", True):
            cv2.putText(img, f"Targets: {len(targets)}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        
        return img

    def _draw_head_bbox(self, img, headx, heady):
        """
        繪製頭部位置標記（優化版本）
        
        在圖像上繪製一個帶外圈的頭部標記，更容易識別。
        
        Args:
            img: BGR 圖像陣列
            headx: 頭部 X 座標
            heady: 頭部 Y 座標
        """
        # 外圈（白色）
        cv2.circle(img, (int(headx), int(heady)), 6, (255, 255, 255), 2)
        # 內圈（紅色）
        cv2.circle(img, (int(headx), int(heady)), 3, (0, 0, 255), -1)

    def _estimate_head_positions(self, x1, y1, x2, y2, img):
        """
        估算頭部位置
        
        根據身體檢測框估算頭部位置。首先計算預期頭部位置（考慮偏移），
        然後在該區域執行二次檢測以精確定位頭部。
        
        Args:
            x1, y1: 身體檢測框左上角座標
            x2, y2: 身體檢測框右下角座標
            img: BGR 圖像陣列
            
        Returns:
            list: 頭部位置列表，每個元素為 (headx, heady, bbox) 元組
        """
        # 確保圖像是連續的數組（應該已經在讀取時處理，但這裡作為安全檢查）
        if not img.flags['C_CONTIGUOUS']:
            img = np.ascontiguousarray(img)
        
        offsetY = getattr(config, 'offsetY', 0)
        offsetX = getattr(config, 'offsetX', 0)

        width = x2 - x1
        height = y2 - y1

        # Crop léger
        top_crop_factor = 0.10
        side_crop_factor = 0.10

        effective_y1 = y1 + height * top_crop_factor
        effective_height = height * (1 - top_crop_factor)

        effective_x1 = x1 + width * side_crop_factor
        effective_x2 = x2 - width * side_crop_factor
        effective_width = effective_x2 - effective_x1

        center_x = (effective_x1 + effective_x2) / 2
        headx_base = center_x + effective_width * (offsetX / 100)
        heady_base = effective_y1 + effective_height * (offsetY / 100)

        pixel_marginx = 40
        pixel_marginy = 10

        x1_roi = int(max(headx_base - pixel_marginx, 0))
        y1_roi = int(max(heady_base - pixel_marginy, 0))
        x2_roi = int(min(headx_base + pixel_marginx, img.shape[1]))
        y2_roi = int(min(heady_base + pixel_marginy, img.shape[0]))

        roi = img[y1_roi:y2_roi, x1_roi:x2_roi]
        # 繪製 ROI 區域（半透明黃色邊框）
        cv2.rectangle(img, (x1_roi, y1_roi), (x2_roi, y2_roi), (0, 255, 255), 1)

        results = []
        detections = []
        try:
            detections, mask = perform_detection(self.model, roi)
        except Exception as e:
            print("[perform_detection ROI error]", e)

        if not detections:
            # Sans détection → garder le head position avec offset
            results.append((headx_base, heady_base, (x1_roi, y1_roi, x2_roi, y2_roi)))
        else:
            for det in detections:
                x, y, w, h = det["bbox"]
                cv2.rectangle(img, (x1_roi + x, y1_roi + y), (x1_roi + x + w, y1_roi + y + h), (0, 255, 0), 2)

                # Position détection brute
                headx_det = x1_roi + x + w / 2
                heady_det = y1_roi + y + h / 2

                # Application de l'offset aussi sur la détection
                headx_det += effective_width * (offsetX / 100)
                heady_det += effective_height * (offsetY / 100)

                results.append((headx_det, heady_det, (x1_roi + x, y1_roi + y, w, h)))

        return results

    def _draw_body(self, img, x1, y1, x2, y2, conf):
        """
        繪製身體檢測框（優化版本）
        
        在圖像上繪製身體檢測框和置信度標籤，使用更好的視覺效果。
        
        Args:
            img: BGR 圖像陣列
            x1, y1: 檢測框左上角座標
            x2, y2: 檢測框右下角座標
            conf: 檢測置信度
        """
        # 繪製矩形框（藍色，較粗）
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
        
        # 繪製角標（使其更明顯）
        corner_len = 20
        thickness = 3
        # 左上角
        cv2.line(img, (int(x1), int(y1)), (int(x1 + corner_len), int(y1)), (0, 255, 0), thickness)
        cv2.line(img, (int(x1), int(y1)), (int(x1), int(y1 + corner_len)), (0, 255, 0), thickness)
        # 右上角
        cv2.line(img, (int(x2), int(y1)), (int(x2 - corner_len), int(y1)), (0, 255, 0), thickness)
        cv2.line(img, (int(x2), int(y1)), (int(x2), int(y1 + corner_len)), (0, 255, 0), thickness)
        # 左下角
        cv2.line(img, (int(x1), int(y2)), (int(x1 + corner_len), int(y2)), (0, 255, 0), thickness)
        cv2.line(img, (int(x1), int(y2)), (int(x1), int(y2 - corner_len)), (0, 255, 0), thickness)
        # 右下角
        cv2.line(img, (int(x2), int(y2)), (int(x2 - corner_len), int(y2)), (0, 255, 0), thickness)
        cv2.line(img, (int(x2), int(y2)), (int(x2), int(y2 - corner_len)), (0, 255, 0), thickness)
        
        # 繪製標籤背景（半透明黑色矩形）
        label_text = f"Body {conf:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, font_thickness)
        
        # 標籤位置
        label_x1 = int(x1)
        label_y1 = int(y1) - text_height - 10
        label_x2 = int(x1) + text_width + 10
        label_y2 = int(y1)
        
        # 繪製背景矩形
        cv2.rectangle(img, (label_x1, label_y1), (label_x2, label_y2), (0, 0, 0), -1)
        
        # 繪製文字
        cv2.putText(img, label_text, (int(x1) + 5, int(y1) - 5), 
                   font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    def _aim_and_move(self, targets, frame, img):
        """
        處理瞄準和移動邏輯
        
        根據當前模式（Normal 或 Silent）執行相應的瞄準和移動邏輯。
        
        Args:
            targets: 目標列表，每個元素為 (cx, cy, distance) 元組
            frame: 視頻幀物件
            img: BGR 圖像陣列
        """
        mode = getattr(config, "mode", "Normal")
        
        if mode == "Normal":
            try:
                process_normal_mode(targets, frame, img, self)
            except Exception as e:
                print("[Normal mode error]", e)

        elif mode == "Silent":
            try:
                process_silent_mode(targets, frame, self)
            except Exception as e:
                print("[Silent mode error]", e)


if __name__ == "__main__":
    """
    主程序入口
    
    初始化所有必要的組件並啟動應用程式：
    1. 初始化 Capture Service
    2. 創建 AimTracker 實例
    3. 設置 UI 外觀
    4. 創建並啟動 UI 應用
    """
    import customtkinter as ctk
    from src.ui import ViewerApp
    
    # 初始化捕獲服務
    capture_service = CaptureService()
    
    # 創建一個臨時應用實例用於 AimTracker
    class TempApp:
        """臨時應用類"""
        def __init__(self, capture):
            self.capture = capture
    
    temp_app = TempApp(capture_service)
    
    # 創建 AimTracker
    tracker = AimTracker(app=temp_app, target_fps=80)
    
    # 設置外觀
    ctk.set_appearance_mode("Dark")
    try:
        ctk.set_default_color_theme("themes/metal.json")
    except Exception:
        pass
    
    # 創建 UI 應用
    app = ViewerApp(tracker=tracker, capture_service=capture_service)
    
    # 更新 tracker 的 app 引用
    tracker.app = app
    
    # 載入並應用配置（確保所有設置都正確）
    config.load_from_file()
    app._sync_config_to_tracker()
    
    print("[Main] Application initialized with configuration")
    print(f"[Main] Current settings - Aim: {config.enableaim}, Mode: {config.mode}, FOV: {config.fovsize}")
    
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()
