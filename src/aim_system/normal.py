"""
Normal 模式瞄準算法
處理 Normal 模式下的 Aimbot 和 Triggerbot 邏輯
"""
import math

from src.utils.config import config
from src.utils.mouse import is_button_pressed
from src.utils.debug_logger import log_move
from .Triggerbot import process_triggerbot
from .RCS import process_rcs


def calculate_movement(dx, dy, sens, dpi):
    """
    計算移動量（基於靈敏度和 DPI）
    
    Args:
        dx: X 方向像素差
        dy: Y 方向像素差
        sens: 遊戲內靈敏度
        dpi: 滑鼠 DPI
        
    Returns:
        tuple: (ndx, ndy) 轉換後的移動量
    """
    cm_per_rev_base = 54.54
    cm_per_rev = cm_per_rev_base / max(sens, 0.01)
    
    count_per_cm = dpi / 2.54
    deg_per_count = 360.0 / (cm_per_rev * count_per_cm)
    
    ndx = dx * deg_per_count
    ndy = dy * deg_per_count
    
    return ndx, ndy


def process_aimbot(targets, center_x, center_y, distance_to_center, 
                   normal_x_speed, normal_y_speed, normalsmooth, normalsmoothfov,
                   aim_enabled, selected_btn, clip_movement_func, move_queue):
    """
    處理 Aimbot 邏輯
    
    Args:
        targets: 目標列表
        center_x: 螢幕中心 X 座標
        center_y: 螢幕中心 Y 座標
        distance_to_center: 目標到中心的距離
        normal_x_speed: X 軸速度
        normal_y_speed: Y 軸速度
        normalsmooth: 平滑度
        normalsmoothfov: 平滑 FOV
        aim_enabled: 是否啟用 Aimbot
        selected_btn: 選中的按鈕索引
        clip_movement_func: 限制移動量的函數
        move_queue: 移動隊列
        
    Returns:
        bool: 是否執行了移動
    """
    if not (aim_enabled and selected_btn is not None and 
            is_button_pressed(selected_btn) and targets):
        return False
    
    try:
        # 計算移動量
        sens = float(getattr(config, "in_game_sens", 7))
        dpi = float(getattr(config, "mouse_dpi", 800))
        
        dx = targets[0][0] - center_x  # 假設 targets[0] 是最佳目標
        dy = targets[0][1] - center_y
        
        ndx, ndy = calculate_movement(dx, dy, sens, dpi)
        
        # 根據距離應用不同的平滑度
        if distance_to_center < float(getattr(config, "normalsmoothfov", normalsmoothfov)):
            # 在平滑 FOV 內，應用平滑度
            ndx *= float(getattr(config, "normal_x_speed", normal_x_speed)) / max(
                float(getattr(config, "normalsmooth", normalsmooth)), 0.01)
            ndy *= float(getattr(config, "normal_y_speed", normal_y_speed)) / max(
                float(getattr(config, "normalsmooth", normalsmooth)), 0.01)
        else:
            # 在平滑 FOV 外，只應用速度
            ndx *= float(getattr(config, "normal_x_speed", normal_x_speed))
            ndy *= float(getattr(config, "normal_y_speed", normal_y_speed))
        
        # 限制移動量並加入隊列
        ddx, ddy = clip_movement_func(ndx, ndy)
        move_queue.put((ddx, ddy, 0.005))
        return True
    except Exception:
        return False


def process_normal_mode(targets, frame, img, tracker):
    """
    處理 Normal 模式的完整邏輯（Main Aimbot + Sec Aimbot + Triggerbot）
    優先級：Main Aimbot > Sec Aimbot
    
    Args:
        targets: 目標列表 [(cx, cy, distance), ...]
        frame: 視頻幀物件
        img: BGR 圖像
        tracker: AimTracker 實例
        
    Returns:
        None
    """
    # Main Aimbot 配置
    aim_enabled = getattr(config, "enableaim", False)
    selected_btn = getattr(config, "selected_mouse_button", None)
    
    # Sec Aimbot 配置
    aim_enabled_sec = getattr(config, "enableaim_sec", False)
    selected_btn_sec = getattr(config, "selected_mouse_button_sec", None)
    
    center_x = frame.xres / 2.0
    center_y = frame.yres / 2.0
    
    main_aimbot_active = False
    
    # 處理 RCS（每幀調用，檢查是否應該啟動）
    rcs_active = process_rcs(
        tracker.controller,
        tracker.rcs_pull_speed,
        tracker.rcs_activation_delay,
        tracker.rcs_rapid_click_threshold
    )
    
    # 處理 Aimbot（優先級：Main > Sec）
    if targets:
        # 選擇最佳目標
        best_target = min(targets, key=lambda t: t[2])
        # targets 結構: (cx, cy, distance, head_y_min, body_y_max)
        if len(best_target) >= 5:
            cx, cy, _, head_y_min, body_y_max = best_target
        else:
            # 兼容舊格式
            cx, cy, _ = best_target[:3]
            head_y_min, body_y_max = None, None
        
        distance_to_center = math.hypot(cx - center_x, cy - center_y)
        
        # === 優先處理 Main Aimbot ===
        main_fov = float(getattr(config, 'fovsize', tracker.fovsize))
        if distance_to_center <= main_fov:
            if aim_enabled and selected_btn is not None and is_button_pressed(selected_btn):
                try:
                    # 獲取 Main Aimbot 的 aim_type
                    aim_type = getattr(config, "aim_type", "head")
                    
                    # 應用 Offset（Main Aimbot）
                    aim_offsetX = float(getattr(config, "aim_offsetX", tracker.aim_offsetX))
                    aim_offsetY = float(getattr(config, "aim_offsetY", tracker.aim_offsetY))
                    
                    # 計算移動量（包含 offset）
                    dx = (cx + aim_offsetX) - center_x
                    dy = (cy + aim_offsetY) - center_y
                    
                    # Nearest 模式：如果目標 Y 在 head_y_min 到 body_y_max 範圍內，Y 軸不移動
                    if aim_type == "nearest" and head_y_min is not None and body_y_max is not None:
                        # 確保 head_y_min < body_y_max（head 在 body 上方）
                        if head_y_min < body_y_max:
                            target_y = cy + aim_offsetY
                            # 只有在目標 Y 在範圍內時，才禁用 Y 軸移動
                            if head_y_min <= target_y <= body_y_max:
                                dy = 0  # Y 軸不移動
                            # 如果不在範圍內，dy 保持原值（正常移動 Y 軸）
                    
                    # RCS 整合：如果 RCS 正在運行，Y 軸設為 0（僅發送水平移動）
                    if rcs_active:
                        dy = 0  # RCS 啟動時，Aimbot 僅發送水平移動
                    
                    sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
                    dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))
                    
                    ndx, ndy = calculate_movement(dx, dy, sens, dpi)
                    
                    # 根據距離應用不同的平滑度
                    main_smoothfov = float(getattr(config, "normalsmoothfov", tracker.normalsmoothfov))
                    if distance_to_center < main_smoothfov:
                        # 在平滑 FOV 內，應用平滑度
                        ndx *= float(getattr(config, "normal_x_speed", tracker.normal_x_speed)) / max(
                            float(getattr(config, "normalsmooth", tracker.normalsmooth)), 0.01)
                        ndy *= float(getattr(config, "normal_y_speed", tracker.normal_y_speed)) / max(
                            float(getattr(config, "normalsmooth", tracker.normalsmooth)), 0.01)
                    else:
                        # 在平滑 FOV 外，只應用速度
                        ndx *= float(getattr(config, "normal_x_speed", tracker.normal_x_speed))
                        ndy *= float(getattr(config, "normal_y_speed", tracker.normal_y_speed))
                    
                    # 限制移動量並加入隊列
                    ddx, ddy = tracker._clip_movement(ndx, ndy)
                    tracker.move_queue.put((ddx, ddy, 0.005))
                    # 記錄移動日誌
                    log_move(ddx, ddy, "Main Aimbot")
                    main_aimbot_active = True
                    print("[Aimbot] Main Aimbot Active")
                except Exception as e:
                    print(f"[Main Aimbot error] {e}")
        
        # === 如果 Main Aimbot 未啟動，嘗試 Sec Aimbot ===
        if not main_aimbot_active:
            sec_fov = float(getattr(config, 'fovsize_sec', tracker.fovsize_sec))
            if distance_to_center <= sec_fov:
                if aim_enabled_sec and selected_btn_sec is not None and is_button_pressed(selected_btn_sec):
                    try:
                        # 獲取 Sec Aimbot 的 aim_type
                        aim_type_sec = getattr(config, "aim_type_sec", "head")
                        
                        # 應用 Offset（Sec Aimbot）
                        aim_offsetX_sec = float(getattr(config, "aim_offsetX_sec", tracker.aim_offsetX_sec))
                        aim_offsetY_sec = float(getattr(config, "aim_offsetY_sec", tracker.aim_offsetY_sec))
                        
                        # 計算移動量（包含 offset）
                        dx = (cx + aim_offsetX_sec) - center_x
                        dy = (cy + aim_offsetY_sec) - center_y
                        
                        # Nearest 模式：如果目標 Y 在 head_y_min 到 body_y_max 範圍內，Y 軸不移動
                        if aim_type_sec == "nearest" and head_y_min is not None and body_y_max is not None:
                            # 確保 head_y_min < body_y_max（head 在 body 上方）
                            if head_y_min < body_y_max:
                                target_y = cy + aim_offsetY_sec
                                # 只有在目標 Y 在範圍內時，才禁用 Y 軸移動
                                if head_y_min <= target_y <= body_y_max:
                                    dy = 0  # Y 軸不移動
                                # 如果不在範圍內，dy 保持原值（正常移動 Y 軸）
                        
                        # RCS 整合：如果 RCS 正在運行，Y 軸設為 0（僅發送水平移動）
                        if rcs_active:
                            dy = 0  # RCS 啟動時，Aimbot 僅發送水平移動
                        
                        sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
                        dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))
                        
                        ndx, ndy = calculate_movement(dx, dy, sens, dpi)
                        
                        # 根據距離應用不同的平滑度（使用 Sec 參數）
                        sec_smoothfov = float(getattr(config, "normalsmoothfov_sec", tracker.normalsmoothfov_sec))
                        if distance_to_center < sec_smoothfov:
                            # 在平滑 FOV 內，應用平滑度
                            ndx *= float(getattr(config, "normal_x_speed_sec", tracker.normal_x_speed_sec)) / max(
                                float(getattr(config, "normalsmooth_sec", tracker.normalsmooth_sec)), 0.01)
                            ndy *= float(getattr(config, "normal_y_speed_sec", tracker.normal_y_speed_sec)) / max(
                                float(getattr(config, "normalsmooth_sec", tracker.normalsmooth_sec)), 0.01)
                        else:
                            # 在平滑 FOV 外，只應用速度
                            ndx *= float(getattr(config, "normal_x_speed_sec", tracker.normal_x_speed_sec))
                            ndy *= float(getattr(config, "normal_y_speed_sec", tracker.normal_y_speed_sec))
                        
                        # 限制移動量並加入隊列
                        ddx, ddy = tracker._clip_movement(ndx, ndy)
                        tracker.move_queue.put((ddx, ddy, 0.005))
                        # 記錄移動日誌
                        log_move(ddx, ddy, "Sec Aimbot")
                        print("[Aimbot] Sec Aimbot Active")
                    except Exception as e:
                        print(f"[Sec Aimbot error] {e}")
    
    # 處理 Triggerbot（無論是否有目標都會執行）
    try:
        status = process_triggerbot(
            frame, img, tracker.model, tracker.controller,
            tracker.tbdelay_min, tracker.tbdelay_max,
            tracker.tbhold_min, tracker.tbhold_max,
            tracker.tbcooldown_min, tracker.tbcooldown_max,
            tracker.tbburst_count_min, tracker.tbburst_count_max,
            tracker.tbburst_interval_min, tracker.tbburst_interval_max
        )
        # 可選：顯示狀態信息（用於調試）
        # print(f"[Triggerbot] {status}")
    except Exception as e:
        print("[Triggerbot error]", e)

