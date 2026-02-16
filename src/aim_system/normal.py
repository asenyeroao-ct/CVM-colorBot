"""
瞄準算法調度器
處理所有瞄準模式下的 Aimbot 和 Triggerbot 邏輯
支持 Normal, Silent, NCAF, WindMouse, Bezier 五種模式
"""
import math
import queue
import threading
import time

from src.utils.config import config
from src.utils.debug_logger import log_move, log_print
from src.utils.activation import check_aimbot_activation
from .Triggerbot import process_triggerbot
from .RCS import process_rcs, check_y_release


def _queue_move(tracker, dx, dy, delay=0.0, drop_oldest=True):
    """Non-blocking queue push with light backpressure handling."""
    item = (dx, dy, max(0.0, float(delay)))
    try:
        tracker.move_queue.put_nowait(item)
        return True
    except queue.Full:
        if drop_oldest:
            try:
                tracker.move_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                tracker.move_queue.put_nowait(item)
                return True
            except queue.Full:
                return False
        return False


def _enqueue_path(tracker, path, max_steps=24, clear_existing=False):
    """Queue smooth-path steps into move queue instead of spawning worker threads."""
    if not path:
        return

    latest_only = bool(getattr(config, "aim_latest_frame_priority", True))

    # In latest-frame mode, collapse path into one command so each detection frame
    # immediately maps to one movement decision (no stale sub-steps trailing behind).
    if latest_only:
        total_dx = 0.0
        total_dy = 0.0
        used_steps = 0
        for step in path:
            if used_steps >= max_steps:
                break
            if len(step) < 3:
                continue
            step_dx, step_dy, _ = step
            step_dx, step_dy = tracker._clip_movement(step_dx, step_dy)
            total_dx += float(step_dx)
            total_dy += float(step_dy)
            used_steps += 1
        qdx = int(round(total_dx))
        qdy = int(round(total_dy))
        if qdx == 0 and qdy == 0 and (abs(total_dx) + abs(total_dy)) >= 0.35:
            if abs(total_dx) >= abs(total_dy):
                qdx = 1 if total_dx > 0 else -1
            else:
                qdy = 1 if total_dy > 0 else -1
        if qdx != 0 or qdy != 0:
            _queue_move(tracker, qdx, qdy, 0.0, drop_oldest=True)
        return

    if clear_existing:
        try:
            while not tracker.move_queue.empty():
                tracker.move_queue.get_nowait()
        except queue.Empty:
            pass

    queued = 0
    residual_x = 0.0
    residual_y = 0.0
    for step in path:
        if queued >= max_steps:
            break
        if len(step) < 3:
            continue
        step_dx, step_dy, delay = step
        step_dx, step_dy = tracker._clip_movement(step_dx, step_dy)
        accum_x = float(step_dx) + residual_x
        accum_y = float(step_dy) + residual_y
        qdx = int(round(accum_x))
        qdy = int(round(accum_y))
        residual_x = accum_x - qdx
        residual_y = accum_y - qdy
        if qdx == 0 and qdy == 0:
            continue
        if _queue_move(tracker, qdx, qdy, delay, drop_oldest=False):
            queued += 1
        else:
            break


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


def _quantize_with_residual(tracker, ndx, ndy, is_sec=False):
    """Carry sub-pixel movement to reduce stop-go jitter from integer conversion."""
    residual_key = "_normal_residual_sec" if is_sec else "_normal_residual_main"
    residual_x, residual_y = getattr(tracker, residual_key, (0.0, 0.0))

    sum_x = float(ndx) + residual_x
    sum_y = float(ndy) + residual_y
    out_x = int(round(sum_x))
    out_y = int(round(sum_y))

    setattr(tracker, residual_key, (sum_x - out_x, sum_y - out_y))
    return out_x, out_y


def compute_silent_delta(dx, dy, multiplier, max_speed):
    """Scale silent movement and clamp into safe range."""
    dx_scaled = float(dx) * float(multiplier)
    dy_scaled = float(dy) * float(multiplier)
    speed_cap = abs(float(max_speed))
    dx_scaled = max(-speed_cap, min(speed_cap, dx_scaled))
    dy_scaled = max(-speed_cap, min(speed_cap, dy_scaled))
    return int(round(dx_scaled)), int(round(dy_scaled))


def _flush_move_queue(tracker):
    """清空移動隊列，防止堆積"""
    if tracker.move_queue.full():
        try:
            while not tracker.move_queue.empty():
                tracker.move_queue.get_nowait()
        except queue.Empty:
            pass


# =====================================================
# Normal 模式
# =====================================================

def _apply_normal_aim(dx, dy, distance_to_center, tracker, is_sec=False):
    """
    Normal 模式瞄準：每幀計算 delta → 應用速度/平滑 → 移動
    """
    if is_sec:
        x_speed = float(getattr(config, "normal_x_speed_sec", tracker.normal_x_speed_sec))
        y_speed = float(getattr(config, "normal_y_speed_sec", tracker.normal_y_speed_sec))
        smooth = float(getattr(config, "normalsmooth_sec", tracker.normalsmooth_sec))
        smoothfov = float(getattr(config, "normalsmoothfov_sec", tracker.normalsmoothfov_sec))
        fov = float(getattr(config, 'fovsize_sec', tracker.fovsize_sec))
        label = "Sec Aimbot (Normal)"
    else:
        x_speed = float(getattr(config, "normal_x_speed", tracker.normal_x_speed))
        y_speed = float(getattr(config, "normal_y_speed", tracker.normal_y_speed))
        smooth = float(getattr(config, "normalsmooth", tracker.normalsmooth))
        smoothfov = float(getattr(config, "normalsmoothfov", tracker.normalsmoothfov))
        fov = float(getattr(config, 'fovsize', tracker.fovsize))
        label = "Main Aimbot (Normal)"
    
    sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
    dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))
    
    ndx, ndy = calculate_movement(dx, dy, sens, dpi)
    
    if distance_to_center < smoothfov:
        ndx *= x_speed / max(smooth, 0.01)
        ndy *= y_speed / max(smooth, 0.01)
    else:
        ndx *= x_speed
        ndy *= y_speed
    
    ddx, ddy = tracker._clip_movement(ndx, ndy)
    qdx, qdy = _quantize_with_residual(tracker, ddx, ddy, is_sec=is_sec)
    if qdx == 0 and qdy == 0 and (abs(dx) + abs(dy)) >= 3.0:
        if abs(dx) >= abs(dy):
            qdx = 1 if dx > 0 else -1
        else:
            qdy = 1 if dy > 0 else -1
    
    # 更新移動鎖定狀態（如果啟用）
    try:
        from src.utils.mouse import update_movement_lock
        if not is_sec:
            # Main Aimbot
            lock_x = getattr(config, "mouse_lock_main_x", False)
            lock_y = getattr(config, "mouse_lock_main_y", False)
        else:
            # Sec Aimbot
            lock_x = getattr(config, "mouse_lock_sec_x", False)
            lock_y = getattr(config, "mouse_lock_sec_y", False)
        if lock_x or lock_y:
            update_movement_lock(lock_x, lock_y, is_main=not is_sec)
    except Exception:
        pass
    
    # 根據距離動態調整延遲
    distance_factor = min(distance_to_center / max(fov, 1.0), 1.0)
    dynamic_delay = 0.005 * (1.0 - distance_factor * 0.4)
    
    if qdx != 0 or qdy != 0:
        _queue_move(tracker, qdx, qdy, dynamic_delay, drop_oldest=True)
        log_move(qdx, qdy, label)


# =====================================================
# Silent 模式
# =====================================================

def _apply_silent_aim(dx, dy, tracker, is_sec=False):
    """
    Silent 模式瞄準：移動 → 點擊 → 恢復原位
    """
    from .silent import threaded_silent_move
    
    # 更新移動鎖定狀態（如果啟用）
    try:
        from src.utils.mouse import update_movement_lock
        if not is_sec:
            # Main Aimbot
            lock_x = getattr(config, "mouse_lock_main_x", False)
            lock_y = getattr(config, "mouse_lock_main_y", False)
        else:
            # Sec Aimbot
            lock_x = getattr(config, "mouse_lock_sec_x", False)
            lock_y = getattr(config, "mouse_lock_sec_y", False)
        if lock_x or lock_y:
            update_movement_lock(lock_x, lock_y, is_main=not is_sec)
    except Exception:
        pass
    
    # 轉換為整數（不再應用速度倍數，因為 Silent 模式使用固定移動）
    distance_multiplier = float(getattr(tracker, "silent_distance", 1.0))
    dx_raw, dy_raw = compute_silent_delta(
        dx,
        dy,
        distance_multiplier,
        getattr(tracker, "max_speed", 1000.0),
    )
    if dx_raw == 0 and dy_raw == 0:
        return
    current_time = time.time()
    silent_delay_sec = max(0.0, float(getattr(tracker, "silent_delay", 100.0)) / 1000.0)
    last_click_time = float(getattr(tracker, "last_silent_click_time", 0.0))
    if current_time - last_click_time < silent_delay_sec:
        return
    if getattr(tracker, "_silent_move_active", False):
        return
    
    # 使用 Silent 模式的延遲參數（毫秒）
    move_delay = getattr(tracker, "silent_move_delay", 500.0)
    return_delay = getattr(tracker, "silent_return_delay", 500.0)

    tracker.last_silent_click_time = current_time
    tracker._silent_move_active = True

    def _run_silent_move():
        try:
            threaded_silent_move(tracker.controller, dx_raw, dy_raw, move_delay, return_delay)
        finally:
            tracker._silent_move_active = False

    threading.Thread(target=_run_silent_move, daemon=True).start()


# =====================================================
# NCAF 模式
# =====================================================

def _apply_ncaf_aim(dx, dy, distance_to_center, tracker, is_sec=False):
    """
    NCAF 模式瞄準：非線性近距曲線 + 穩定追蹤

    使用像素距離 (distance_to_center) 計算 NCAF 3-zone 速度因子：
      Zone 1 – 在 Snap Radius 外：全速 (factor=1.0)
      Zone 2 – Snap Radius 與 Near Radius 之間：線性過渡至 snap_boost
      Zone 3 – 在 Near Radius 內：snap_boost × (d/near_radius)^α（精確減速）
    """
    from .NCAF import NCAFController
    import time

    if is_sec:
        x_speed = float(getattr(config, "normal_x_speed_sec", tracker.normal_x_speed_sec))
        y_speed = float(getattr(config, "normal_y_speed_sec", tracker.normal_y_speed_sec))
        snap_radius = float(getattr(config, "ncaf_snap_radius_sec", 150.0))
        near_radius = float(getattr(config, "ncaf_near_radius_sec", 50.0))
        alpha = float(getattr(config, "ncaf_alpha_sec", 1.5))
        snap_boost = float(getattr(config, "ncaf_snap_boost_sec", 0.3))
        max_step = float(getattr(config, "ncaf_max_step_sec", 50.0))
        min_speed_multiplier = float(getattr(config, "ncaf_min_speed_multiplier_sec", 0.01))
        max_speed_multiplier = float(getattr(config, "ncaf_max_speed_multiplier_sec", 10.0))
        prediction_interval = float(getattr(config, "ncaf_prediction_interval_sec", 0.016))
        fov = float(getattr(config, 'fovsize_sec', tracker.fovsize_sec))
        label = "Sec Aimbot (NCAF)"
    else:
        x_speed = float(getattr(config, "normal_x_speed", tracker.normal_x_speed))
        y_speed = float(getattr(config, "normal_y_speed", tracker.normal_y_speed))
        snap_radius = float(getattr(config, "ncaf_snap_radius", 150.0))
        near_radius = float(getattr(config, "ncaf_near_radius", 50.0))
        alpha = float(getattr(config, "ncaf_alpha", 1.5))
        snap_boost = float(getattr(config, "ncaf_snap_boost", 0.3))
        max_step = float(getattr(config, "ncaf_max_step", 50.0))
        min_speed_multiplier = float(getattr(config, "ncaf_min_speed_multiplier", 0.01))
        max_speed_multiplier = float(getattr(config, "ncaf_max_speed_multiplier", 10.0))
        prediction_interval = float(getattr(config, "ncaf_prediction_interval", 0.016))
        fov = float(getattr(config, 'fovsize', tracker.fovsize))
        label = "Main Aimbot (NCAF)"

    sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
    dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))

    # 1. 目標預測（簡單線性預測）
    # 初始化預測歷史（如果不存在）
    pred_key = f"_ncaf_prediction_{'sec' if is_sec else 'main'}"
    if not hasattr(tracker, pred_key):
        setattr(tracker, pred_key, {
            'last_dx': None,
            'last_dy': None,
            'last_time': None,
            'velocity': (0.0, 0.0)
        })
    
    pred_data = getattr(tracker, pred_key)
    current_time = time.time()
    
    # 計算預測偏移（如果啟用預測且時間間隔足夠）
    pred_dx, pred_dy = 0.0, 0.0
    if prediction_interval > 0 and pred_data['last_dx'] is not None and pred_data['last_time'] is not None:
        dt = current_time - pred_data['last_time']
        if dt > 0:
            # 使用上次計算的速度進行預測
            vx = pred_data['velocity'][0]
            vy = pred_data['velocity'][1]
            # 預測未來位置（使用 prediction_interval 作為預測時間）
            pred_dx = vx * prediction_interval
            pred_dy = vy * prediction_interval
    
    # 更新預測歷史（計算速度）
    if pred_data['last_dx'] is not None and pred_data['last_time'] is not None:
        dt = current_time - pred_data['last_time']
        if dt > 0:
            # 計算速度（像素/秒）
            vx = (dx - pred_data['last_dx']) / dt
            vy = (dy - pred_data['last_dy']) / dt
            # 平滑速度（使用指數移動平均）
            old_vx, old_vy = pred_data['velocity']
            alpha = 0.3  # 平滑係數
            pred_data['velocity'] = (
                alpha * vx + (1 - alpha) * old_vx,
                alpha * vy + (1 - alpha) * old_vy
            )
    
    pred_data['last_dx'] = dx
    pred_data['last_dy'] = dy
    pred_data['last_time'] = current_time
    
    # 應用預測偏移
    dx_with_pred = dx + pred_dx
    dy_with_pred = dy + pred_dy
    distance_with_pred = math.hypot(dx_with_pred, dy_with_pred)

    # 2. 轉換為滑鼠移動量，並乘以速度係數
    ndx, ndy = calculate_movement(dx_with_pred, dy_with_pred, sens, dpi)
    ndx *= x_speed
    ndy *= y_speed

    # 3. 用像素距離查詢 NCAF 3-zone 速度因子
    pixel_dist = distance_with_pred
    if pixel_dist <= 1e-6:
        return

    factor = NCAFController.compute_ncaf_factor(
        pixel_dist, snap_radius, near_radius, alpha, snap_boost
    )
    
    # 4. 應用 min/max speed multiplier 限制
    factor = max(min_speed_multiplier, min(factor, max_speed_multiplier))

    ndx *= factor
    ndy *= factor

    # 5. 限制每步最大移動量
    step = math.hypot(ndx, ndy)
    if max_step > 0 and step > max_step:
        scale = max_step / step
        ndx *= scale
        ndy *= scale

    ddx, ddy = tracker._clip_movement(ndx, ndy)
    
    # 更新移動鎖定狀態（如果啟用）
    try:
        from src.utils.mouse import update_movement_lock
        if not is_sec:
            # Main Aimbot
            lock_x = getattr(config, "mouse_lock_main_x", False)
            lock_y = getattr(config, "mouse_lock_main_y", False)
        else:
            # Sec Aimbot
            lock_x = getattr(config, "mouse_lock_sec_x", False)
            lock_y = getattr(config, "mouse_lock_sec_y", False)
        if lock_x or lock_y:
            update_movement_lock(lock_x, lock_y, is_main=not is_sec)
    except Exception:
        pass

    distance_factor = min(distance_with_pred / max(fov, 1.0), 1.0)
    dynamic_delay = 0.003 * (1.0 - distance_factor * 0.3)

    qdx, qdy = _quantize_with_residual(tracker, ddx, ddy, is_sec=is_sec)
    if qdx == 0 and qdy == 0 and pixel_dist >= 3.0:
        if abs(dx_with_pred) >= abs(dy_with_pred):
            qdx = 1 if dx_with_pred > 0 else -1
        else:
            qdy = 1 if dy_with_pred > 0 else -1

    if qdx != 0 or qdy != 0:
        _queue_move(tracker, qdx, qdy, dynamic_delay, drop_oldest=True)
        log_move(qdx, qdy, label)


# =====================================================
# WindMouse 模式
# =====================================================

class _WindMouseConfig:
    """WindMouse 所需的配置包裝器"""
    def __init__(self, is_sec=False):
        if is_sec:
            self.smooth_gravity = float(getattr(config, "wm_gravity_sec", 9.0))
            self.smooth_wind = float(getattr(config, "wm_wind_sec", 3.0))
            self.smooth_max_step = float(getattr(config, "wm_max_step_sec", 15.0))
            self.smooth_min_step = float(getattr(config, "wm_min_step_sec", 2.0))
            self.smooth_min_delay = float(getattr(config, "wm_min_delay_sec", 0.001))
            self.smooth_max_delay = float(getattr(config, "wm_max_delay_sec", 0.003))
            self.smooth_distance_threshold = float(getattr(config, "wm_distance_threshold_sec", 50.0))
        else:
            self.smooth_gravity = float(getattr(config, "wm_gravity", 9.0))
            self.smooth_wind = float(getattr(config, "wm_wind", 3.0))
            self.smooth_max_step = float(getattr(config, "wm_max_step", 15.0))
            self.smooth_min_step = float(getattr(config, "wm_min_step", 2.0))
            self.smooth_min_delay = float(getattr(config, "wm_min_delay", 0.001))
            self.smooth_max_delay = float(getattr(config, "wm_max_delay", 0.003))
            self.smooth_distance_threshold = float(getattr(config, "wm_distance_threshold", 50.0))
        
        # 固定的內部參數
        self.smooth_reaction_min = 0.02
        self.smooth_reaction_max = 0.08
        self.smooth_close_range = 30.0
        self.smooth_close_speed = 0.3
        self.smooth_far_range = 200.0
        self.smooth_far_speed = 0.8
        self.smooth_fatigue_effect = 0.5
        self.smooth_max_step_ratio = 0.15
        self.smooth_target_area_ratio = 0.05
        self.smooth_acceleration = 0.8
        self.smooth_deceleration = 0.6
        self.smooth_micro_corrections = 1


def _apply_windmouse_aim(dx, dy, tracker, is_sec=False):
    """
    WindMouse 模式瞄準：生成類人化滑鼠路徑並執行
    
    必須先乘以 x_speed/y_speed，否則 calculate_movement 產出的度數值太小
    (通常 < 1)，WindMouse 的 distance < 2 判斷會直接丟棄。
    """
    from .windmouse_smooth import smooth_aimer
    
    wm_config = _WindMouseConfig(is_sec)
    label = "Sec Aimbot (WindMouse)" if is_sec else "Main Aimbot (WindMouse)"
    
    if is_sec:
        x_speed = float(getattr(config, "normal_x_speed_sec", tracker.normal_x_speed_sec))
        y_speed = float(getattr(config, "normal_y_speed_sec", tracker.normal_y_speed_sec))
    else:
        x_speed = float(getattr(config, "normal_x_speed", tracker.normal_x_speed))
        y_speed = float(getattr(config, "normal_y_speed", tracker.normal_y_speed))
    
    sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
    dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))
    
    # 轉換為滑鼠移動量，並乘以速度係數（與 Normal 模式一致）
    ndx, ndy = calculate_movement(dx, dy, sens, dpi)
    ndx *= x_speed
    ndy *= y_speed
    
    path = smooth_aimer.calculate_smooth_path(ndx, ndy, wm_config)
    
    if path:
        # 更新移動鎖定狀態（如果啟用）
        try:
            from src.utils.mouse import update_movement_lock
            if not is_sec:
                # Main Aimbot
                lock_x = getattr(config, "mouse_lock_main_x", False)
                lock_y = getattr(config, "mouse_lock_main_y", False)
            else:
                # Sec Aimbot
                lock_x = getattr(config, "mouse_lock_sec_x", False)
                lock_y = getattr(config, "mouse_lock_sec_y", False)
            if lock_x or lock_y:
                update_movement_lock(lock_x, lock_y, is_main=not is_sec)
        except Exception:
            pass
        
        _enqueue_path(tracker, path, max_steps=24, clear_existing=False)
        log_move(ndx, ndy, label)


# =====================================================
# Bezier 模式
# =====================================================

def _apply_bezier_aim(dx, dy, distance_to_center, tracker, is_sec=False):
    """
    Bezier 模式瞄準：使用貝茲曲線生成平滑移動路徑
    """
    from .Bezier import BezierMovement

    if is_sec:
        segments = int(getattr(config, "bezier_segments_sec", 8))
        ctrl_x = float(getattr(config, "bezier_ctrl_x_sec", 16.0))
        ctrl_y = float(getattr(config, "bezier_ctrl_y_sec", 16.0))
        speed = float(getattr(config, "bezier_speed_sec", 1.0))
        delay = float(getattr(config, "bezier_delay_sec", 0.002))
        fov = float(getattr(config, 'fovsize_sec', tracker.fovsize_sec))
        label = "Sec Aimbot (Bezier)"
    else:
        segments = int(getattr(config, "bezier_segments", 8))
        ctrl_x = float(getattr(config, "bezier_ctrl_x", 16.0))
        ctrl_y = float(getattr(config, "bezier_ctrl_y", 16.0))
        speed = float(getattr(config, "bezier_speed", 1.0))
        delay = float(getattr(config, "bezier_delay", 0.002))
        fov = float(getattr(config, 'fovsize', tracker.fovsize))
        label = "Main Aimbot (Bezier)"

    sens = float(getattr(config, "in_game_sens", tracker.in_game_sens))
    dpi = float(getattr(config, "mouse_dpi", tracker.mouse_dpi))

    ndx, ndy = calculate_movement(dx, dy, sens, dpi)
    ndx *= speed
    ndy *= speed

    bezier = BezierMovement(segments=segments, ctrl_x=ctrl_x, ctrl_y=ctrl_y)
    deltas = bezier.get_movement_deltas(ndx, ndy)

    if deltas:
        # 更新移動鎖定狀態（如果啟用）
        try:
            from src.utils.mouse import update_movement_lock
            if not is_sec:
                # Main Aimbot
                lock_x = getattr(config, "mouse_lock_main_x", False)
                lock_y = getattr(config, "mouse_lock_main_y", False)
            else:
                # Sec Aimbot
                lock_x = getattr(config, "mouse_lock_sec_x", False)
                lock_y = getattr(config, "mouse_lock_sec_y", False)
            if lock_x or lock_y:
                update_movement_lock(lock_x, lock_y, is_main=not is_sec)
        except Exception:
            pass
        
        # 根據距離動態調整延遲
        distance_factor = min(distance_to_center / max(fov, 1.0), 1.0)
        step_delay = delay * (1.0 - distance_factor * 0.3)

        path = []
        for step_dx, step_dy in deltas:
            sdx = int(round(step_dx))
            sdy = int(round(step_dy))
            if sdx != 0 or sdy != 0:
                path.append((sdx, sdy, step_delay))

        _enqueue_path(tracker, path, max_steps=24, clear_existing=False)
        log_move(ndx, ndy, label)


# =====================================================
# 主調度器
# =====================================================

def _dispatch_aimbot(dx, dy, distance_to_center, mode, tracker, is_sec=False):
    """根據模式調度瞄準邏輯"""
    if mode == "Normal":
        _apply_normal_aim(dx, dy, distance_to_center, tracker, is_sec)
    elif mode == "Silent":
        _apply_silent_aim(dx, dy, tracker, is_sec)
    elif mode == "NCAF":
        _apply_ncaf_aim(dx, dy, distance_to_center, tracker, is_sec)
    elif mode == "WindMouse":
        _apply_windmouse_aim(dx, dy, tracker, is_sec)
    elif mode == "Bezier":
        _apply_bezier_aim(dx, dy, distance_to_center, tracker, is_sec)
    else:
        # 預設使用 Normal
        _apply_normal_aim(dx, dy, distance_to_center, tracker, is_sec)

def _unpack_target(target):
    """Unpack target tuple while keeping backward compatibility."""
    if not target or len(target) < 3:
        return None, None, None, None, None
    cx, cy, distance = target[:3]
    head_y_min = target[3] if len(target) >= 4 else None
    body_y_max = target[4] if len(target) >= 5 else None
    return cx, cy, distance, head_y_min, body_y_max


def process_normal_mode(targets_main, frame, img, tracker, targets_sec=None, targets_trigger=None):
    """
    主瞄準調度器（Main Aimbot + Sec Aimbot + Triggerbot）
    Main Aimbot 和 Sec Aimbot 各自使用獨立的 Operation Mode
    優先級：Main Aimbot > Sec Aimbot
    
    Args:
        targets_main: 主自瞄目標列表 [(cx, cy, distance, head_y_min, body_y_max), ...]
        frame: 視頻幀物件
        img: BGR 圖像
        tracker: AimTracker 實例
        targets_sec: 副自瞄目標列表（None 時回退為 targets_main）
        targets_trigger: Triggerbot 目標列表（None 時回退為 targets_main）
    """
    if targets_sec is None:
        targets_sec = targets_main
    if targets_trigger is None:
        targets_trigger = targets_main

    # Main Aimbot 配置
    aim_enabled = getattr(config, "enableaim", False)
    selected_btn = getattr(config, "selected_mouse_button", None)
    activation_type = getattr(config, "aimbot_activation_type", "hold_enable")
    
    # Sec Aimbot 配置
    aim_enabled_sec = getattr(config, "enableaim_sec", False)
    selected_btn_sec = getattr(config, "selected_mouse_button_sec", None)
    activation_type_sec = getattr(config, "aimbot_activation_type_sec", "hold_enable")
    
    center_x = frame.xres / 2.0
    center_y = frame.yres / 2.0
    
    main_aimbot_active = False
    
    # 取得各自的 Operation Mode
    mode_main = getattr(config, "mode", "Normal")
    mode_sec = getattr(config, "mode_sec", "Normal")
    
    # 處理 RCS（每幀調用，檢查是否應該啟動）
    rcs_active = process_rcs(
        tracker.controller,
        tracker.rcs_pull_speed,
        tracker.rcs_activation_delay,
        tracker.rcs_rapid_click_threshold
    )
    
    # 處理 Aimbot（優先級：Main > Sec）
    best_target_main = min(targets_main, key=lambda t: t[2]) if targets_main else None
    best_target_sec = min(targets_sec, key=lambda t: t[2]) if targets_sec else None

    if best_target_main:
        cx, cy, _, head_y_min, body_y_max = _unpack_target(best_target_main)
        if cx is not None and cy is not None:
            distance_to_center = math.hypot(cx - center_x, cy - center_y)

            # === 優先處理 Main Aimbot ===
            main_fov = float(getattr(config, 'fovsize', tracker.fovsize))
            if distance_to_center <= main_fov:
                if aim_enabled and selected_btn is not None and check_aimbot_activation(selected_btn, activation_type, is_sec=False):
                    try:
                        aim_type = getattr(config, "aim_type", "head")
                        aim_offsetX = float(getattr(config, "aim_offsetX", tracker.aim_offsetX))
                        aim_offsetY = float(getattr(config, "aim_offsetY", tracker.aim_offsetY))
                        
                        dx = (cx + aim_offsetX) - center_x
                        dy = (cy + aim_offsetY) - center_y
                        
                        # Nearest 模式
                        if aim_type == "nearest" and head_y_min is not None and body_y_max is not None:
                            if head_y_min < body_y_max:
                                target_y = cy + aim_offsetY
                                if head_y_min <= target_y <= body_y_max:
                                    dy = 0
                        
                        # RCS 整合
                        if rcs_active:
                            dy = 0
                        
                        # Y 軸解鎖功能（左鍵按下時解鎖 Y 軸控制）
                        if check_y_release():
                            dy = 0
                        
                        # 根據 Main 模式調度
                        _dispatch_aimbot(dx, dy, distance_to_center, mode_main, tracker, is_sec=False)
                        main_aimbot_active = True
                    except Exception as e:
                        log_print(f"[Main Aimbot error] {e}")
    
    # === 如果 Main Aimbot 未啟動，嘗試 Sec Aimbot ===
    if not main_aimbot_active and best_target_sec:
        cx, cy, _, head_y_min, body_y_max = _unpack_target(best_target_sec)
        if cx is not None and cy is not None:
            distance_to_center_sec = math.hypot(cx - center_x, cy - center_y)
            sec_fov = float(getattr(config, 'fovsize_sec', tracker.fovsize_sec))
            if distance_to_center_sec <= sec_fov:
                if aim_enabled_sec and selected_btn_sec is not None and check_aimbot_activation(selected_btn_sec, activation_type_sec, is_sec=True):
                    try:
                        aim_type_sec = getattr(config, "aim_type_sec", "head")
                        aim_offsetX_sec = float(getattr(config, "aim_offsetX_sec", tracker.aim_offsetX_sec))
                        aim_offsetY_sec = float(getattr(config, "aim_offsetY_sec", tracker.aim_offsetY_sec))
                        
                        dx = (cx + aim_offsetX_sec) - center_x
                        dy = (cy + aim_offsetY_sec) - center_y
                        
                        # Nearest 模式
                        if aim_type_sec == "nearest" and head_y_min is not None and body_y_max is not None:
                            if head_y_min < body_y_max:
                                target_y = cy + aim_offsetY_sec
                                if head_y_min <= target_y <= body_y_max:
                                    dy = 0
                        
                        # RCS 整合
                        if rcs_active:
                            dy = 0
                        
                        # Y 軸解鎖功能（左鍵按下時解鎖 Y 軸控制）
                        if check_y_release():
                            dy = 0
                        
                        # 根據 Sec 模式調度
                        _dispatch_aimbot(dx, dy, distance_to_center_sec, mode_sec, tracker, is_sec=True)
                    except Exception as e:
                        log_print(f"[Sec Aimbot error] {e}")
    
    # 處理 Triggerbot（無論是否有目標都會執行）
    try:
        status = process_triggerbot(
            frame, img, tracker.model, tracker.controller,
            tracker.tbdelay_min, tracker.tbdelay_max,
            tracker.tbhold_min, tracker.tbhold_max,
            tracker.tbcooldown_min, tracker.tbcooldown_max,
            tracker.tbburst_count_min, tracker.tbburst_count_max,
            tracker.tbburst_interval_min, tracker.tbburst_interval_max,
            targets=targets_trigger,
        )
    except Exception as e:
        log_print("[Triggerbot error]", e)
