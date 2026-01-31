"""
Silent 模式瞄準算法
處理 Silent 模式下的隱蔽瞄準和射擊邏輯
"""
import threading
import time

from src.utils.config import config
from .RCS import process_rcs


def threaded_silent_move(controller, dx, dy):
    """
    Silent 模式的移動-點擊-恢復函數
    
    在 Silent 模式下，先移動滑鼠到目標位置，點擊後立即恢復到原位置，
    以實現隱蔽的瞄準和射擊。
    
    Args:
        controller: 滑鼠控制器實例
        dx: X 方向的移動距離
        dy: Y 方向的移動距離
    """
    controller.move(dx, dy)
    time.sleep(0.001)
    controller.click()
    time.sleep(0.001)
    controller.move(-dx, -dy)


def process_silent_mode(targets, frame, tracker):
    """
    處理 Silent 模式的完整邏輯
    
    Silent 模式的特點：
    - 選擇最佳目標（距離中心最近的）
    - 計算移動距離
    - 應用速度倍數
    - 在獨立線程中執行移動-點擊-恢復操作
    
    Args:
        targets: 目標列表 [(cx, cy, distance), ...]
        frame: 視頻幀物件
        tracker: AimTracker 實例
        
    Returns:
        None
    """
    if not targets:
        return  # 避免沒有目標時崩潰
    
    # 計算螢幕中心
    center_x = frame.xres / 2.0
    center_y = frame.yres / 2.0
    
    # 選擇最佳目標（距離中心最近的）
    best_target = min(targets, key=lambda t: t[2])
    # targets 結構: (cx, cy, distance, head_y_min, body_y_max)
    if len(best_target) >= 5:
        cx, cy, _, head_y_min, body_y_max = best_target
    else:
        # 兼容舊格式
        cx, cy, _ = best_target[:3]
        head_y_min, body_y_max = None, None
    
    # 獲取 aim_type（Main Aimbot，Silent 模式通常只使用 Main）
    aim_type = getattr(config, "aim_type", "head")
    
    # 計算移動距離
    dx = cx - center_x
    dy = cy - center_y
    
    # Nearest 模式：如果目標 Y 在 head_y_min 到 body_y_max 範圍內，Y 軸不移動
    if aim_type == "nearest" and head_y_min is not None and body_y_max is not None:
        # 確保 head_y_min < body_y_max（head 在 body 上方）
        if head_y_min < body_y_max:
            # 只有在目標 Y 在範圍內時，才禁用 Y 軸移動
            if head_y_min <= cy <= body_y_max:
                dy = 0  # Y 軸不移動
            # 如果不在範圍內，dy 保持原值（正常移動 Y 軸）
    
    # RCS 整合：如果 RCS 正在運行，Y 軸設為 0（僅發送水平移動）
    rcs_active = process_rcs(
        tracker.controller,
        tracker.rcs_pull_speed,
        tracker.rcs_activation_delay,
        tracker.rcs_rapid_click_threshold
    )
    if rcs_active:
        dy = 0  # RCS 啟動時，Aimbot 僅發送水平移動
    
    # 轉換為整數並應用速度倍數
    dx_raw = int(dx)
    dy_raw = int(dy)
    dx_raw *= tracker.normal_x_speed
    dy_raw *= tracker.normal_y_speed
    
    # 在獨立線程中執行 Silent 移動（移動-點擊-恢復）
    threading.Thread(
        target=threaded_silent_move,
        args=(tracker.controller, dx_raw, dy_raw),
        daemon=True
    ).start()

