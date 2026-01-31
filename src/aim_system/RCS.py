"""
RCS (Recoil Control System) 模組
處理後座力補償邏輯
"""
import time
import threading
from src.utils.config import config
from src.utils.mouse import is_button_pressed


# 全局變量用於管理 RCS 狀態
_rcs_state = {
    "is_active": False,  # RCS 是否啟動
    "last_click_time": 0.0,  # 上次點擊時間（用於檢測快速點擊）
    "button_press_time": None,  # 按鈕按下時間（用於檢測長按）
    "rcs_thread": None,  # RCS 線程
    "rcs_lock": threading.Lock()  # 線程鎖
}


def _rcs_pull_loop(controller, pull_speed):
    """
    RCS 下拉循環
    
    持續發送向下移動指令（Y 軸正值）
    
    Args:
        controller: 滑鼠控制器
        pull_speed: 下拉速度（1-20）
    """
    # 將 pull_speed 轉換為實際移動量
    # pull_speed 範圍是 1-20，轉換為像素移動量
    # 可以根據需要調整這個轉換公式
    move_amount = pull_speed * 0.5  # 每個循環移動的像素數
    
    while True:
        with _rcs_state["rcs_lock"]:
            if not _rcs_state["is_active"]:
                break
        
        # 發送向下移動指令（Y 軸正值）
        try:
            controller.move(0, move_amount)
        except Exception as e:
            print(f"[RCS] Move error: {e}")
            break
        
        # 控制循環頻率（約 80 FPS）
        time.sleep(1.0 / 80.0)


def check_rcs_activation(activation_delay, rapid_click_threshold):
    """
    檢查 RCS 是否應該啟動
    
    Args:
        activation_delay: 啟動延遲（毫秒）
        rapid_click_threshold: 快速點擊閾值（毫秒）
        
    Returns:
        bool: 是否應該啟動 RCS
    """
    now = time.time()
    
    # 檢查左鍵是否按下
    left_button_pressed = is_button_pressed(0)  # 0 = 左鍵
    
    with _rcs_state["rcs_lock"]:
        if left_button_pressed:
            # 如果按鈕剛按下，記錄按下時間
            if _rcs_state["button_press_time"] is None:
                _rcs_state["button_press_time"] = now
                # 檢查快速點擊（按鈕剛按下時，檢查與上次點擊的間隔）
                if _rcs_state["last_click_time"] > 0:
                    click_interval = (now - _rcs_state["last_click_time"]) * 1000  # 轉換為毫秒
                    if click_interval <= rapid_click_threshold:
                        _rcs_state["last_click_time"] = now
                        return True
                _rcs_state["last_click_time"] = now
            
            # 檢查是否按住超過 activation_delay
            if _rcs_state["button_press_time"] is not None:
                hold_time = (now - _rcs_state["button_press_time"]) * 1000  # 轉換為毫秒
                if hold_time >= activation_delay:
                    return True
        else:
            # 按鈕未按下，重置按下時間
            if _rcs_state["button_press_time"] is not None:
                # 按鈕剛釋放，記錄為點擊時間（用於下次快速點擊檢測）
                _rcs_state["last_click_time"] = now
            _rcs_state["button_press_time"] = None
    
    return False


def start_rcs(controller, pull_speed):
    """
    啟動 RCS
    
    Args:
        controller: 滑鼠控制器
        pull_speed: 下拉速度（1-20）
    """
    with _rcs_state["rcs_lock"]:
        if _rcs_state["is_active"]:
            return  # 已經啟動
        
        _rcs_state["is_active"] = True
        
        # 如果線程正在運行，先停止它
        if _rcs_state["rcs_thread"] is not None and _rcs_state["rcs_thread"].is_alive():
            return
        
        # 創建新的 RCS 線程
        _rcs_state["rcs_thread"] = threading.Thread(
            target=_rcs_pull_loop,
            args=(controller, pull_speed),
            daemon=True
        )
        _rcs_state["rcs_thread"].start()


def stop_rcs():
    """
    停止 RCS
    """
    with _rcs_state["rcs_lock"]:
        _rcs_state["is_active"] = False
        _rcs_state["button_press_time"] = None


def is_rcs_active():
    """
    檢查 RCS 是否正在運行
    
    Returns:
        bool: RCS 是否啟動
    """
    with _rcs_state["rcs_lock"]:
        return _rcs_state["is_active"]


def process_rcs(controller, pull_speed, activation_delay, rapid_click_threshold):
    """
    處理 RCS 邏輯（每幀調用）
    
    Args:
        controller: 滑鼠控制器
        pull_speed: 下拉速度（1-20）
        activation_delay: 啟動延遲（毫秒）
        rapid_click_threshold: 快速點擊閾值（毫秒）
        
    Returns:
        bool: RCS 是否正在運行（用於 Aimbot 整合）
    """
    if not getattr(config, "enablercs", False):
        stop_rcs()
        return False
    
    # 檢查是否應該啟動 RCS
    should_activate = check_rcs_activation(activation_delay, rapid_click_threshold)
    
    if should_activate:
        start_rcs(controller, pull_speed)
    else:
        # 檢查左鍵是否還按下，如果沒有按下則停止 RCS
        if not is_button_pressed(0):
            stop_rcs()
    
    return is_rcs_active()

