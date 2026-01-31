"""
Triggerbot 模組
處理自動觸發射擊邏輯，支持連發功能
"""
import time
import cv2
import random
import threading

from src.utils.config import config
from src.utils.mouse import is_button_pressed


# 全局變量用於管理連發狀態
_triggerbot_state = {
    "last_trigger_time": 0.0,  # 最後觸發時間（用於 cooldown）
    "current_cooldown": 0.0,  # 當前使用的 cooldown 值（從範圍中隨機選擇）
    "enter_range_time": None,  # 第一次進入範圍的時間
    "burst_state": None,  # 連發狀態：None, "waiting", "bursting"
    "burst_thread": None,  # 連發線程
    "burst_lock": threading.Lock()  # 線程鎖
}


def _execute_burst_sequence(controller, burst_count_min, burst_count_max, hold_min, hold_max, interval_min, interval_max):
    """
    執行連發序列
    
    Args:
        controller: 滑鼠控制器
        burst_count_min: 連發次數最小值
        burst_count_max: 連發次數最大值
        hold_min: 按鍵保持時間最小值（毫秒）
        hold_max: 按鍵保持時間最大值（毫秒）
        interval_min: 連發間隔最小值（毫秒）
        interval_max: 連發間隔最大值（毫秒）
    """
    # 從範圍中隨機選擇連發次數
    burst_count = random.randint(burst_count_min, burst_count_max)
    with _triggerbot_state["burst_lock"]:
        _triggerbot_state["burst_state"] = "bursting"
    
    try:
        for i in range(burst_count):
            # 從範圍中隨機選擇 hold 時間
            random_hold = random.uniform(hold_min, hold_max)
            
            # 按下滑鼠按鈕
            controller.press()
            time.sleep(random_hold / 1000.0)  # 等待隨機 hold 時間（轉換為秒）
            # 釋放滑鼠按鈕
            controller.release()
            
            # 如果不是最後一發，等待隨機 Interval 時間
            if i < burst_count - 1:
                random_interval = random.uniform(interval_min, interval_max)
                if random_interval > 0:
                    time.sleep(random_interval / 1000.0)
    finally:
        with _triggerbot_state["burst_lock"]:
            _triggerbot_state["burst_state"] = None
            _triggerbot_state["burst_thread"] = None


def process_triggerbot(frame, img, model, controller, tbdelay_min, tbdelay_max, 
                      tbhold_min, tbhold_max, tbcooldown_min, tbcooldown_max,
                      tbburst_count_min, tbburst_count_max, tbburst_interval_min, tbburst_interval_max):
    """
    處理 Triggerbot 邏輯（支持連發功能）
    
    Args:
        frame: 視頻幀物件
        img: BGR 圖像
        model: 檢測模型（包含 HSV 範圍）
        controller: 滑鼠控制器
        tbdelay_min: Triggerbot 延遲最小值（秒）
        tbdelay_max: Triggerbot 延遲最大值（秒）
        tbhold_min: 按鍵保持時間最小值（毫秒）
        tbhold_max: 按鍵保持時間最大值（毫秒）
        tbcooldown_min: 冷卻時間最小值（秒）
        tbcooldown_max: 冷卻時間最大值（秒）
        tbburst_count_min: 連發次數最小值
        tbburst_count_max: 連發次數最大值
        tbburst_interval_min: 連發間隔最小值（毫秒）
        tbburst_interval_max: 連發間隔最大值（毫秒）
        
    Returns:
        str: 狀態信息（用於調試顯示）
    """
    if not getattr(config, "enabletb", False):
        return "DISABLED"
    
    # 檢查按鈕是否按下
    selected_tb_btn = getattr(config, "selected_tb_btn", None)
    selected_2_tb = getattr(config, "selected_2_tb", None)
    
    if not (is_button_pressed(selected_tb_btn) or is_button_pressed(selected_2_tb)):
        # 按鈕未按下，重置進入範圍計時器
        with _triggerbot_state["burst_lock"]:
            if _triggerbot_state["burst_state"] != "bursting":
                _triggerbot_state["enter_range_time"] = None
                _triggerbot_state["burst_state"] = None
        return "BUTTON_NOT_PRESSED"
    
    try:
        # 螢幕中心
        cx0, cy0 = int(frame.xres // 2), int(frame.yres // 2)
        ROI_SIZE = 5  # 中心周圍的小正方形
        
        x1, y1 = max(cx0 - ROI_SIZE, 0), max(cy0 - ROI_SIZE, 0)
        x2, y2 = min(cx0 + ROI_SIZE, img.shape[1]), min(cy0 + ROI_SIZE, img.shape[0])
        roi = img[y1:y2, x1:x2]
        
        if roi.size == 0:
            return "INVALID_ROI"  # 安全檢查
        
        # 轉換為 HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # HSV 範圍（從模型獲取）
        HSV_UPPER = model[1]
        HSV_LOWER = model[0]
        
        mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
        detected = cv2.countNonZero(mask) > 0
        
        # 調試顯示（根據設置）
        if (getattr(config, "show_opencv_windows", True) and 
            getattr(config, "show_opencv_roi", True)):
            cv2.imshow("ROI", roi)
            cv2.waitKey(1)
        
        if (getattr(config, "show_opencv_windows", True) and 
            getattr(config, "show_opencv_triggerbot_mask", True)):
            cv2.imshow("Mask", mask)
            cv2.waitKey(1)
        
        now = time.time()
        
        # 如果未檢測到目標顏色，重置進入範圍計時器
        if not detected:
            with _triggerbot_state["burst_lock"]:
                if _triggerbot_state["burst_state"] != "bursting":
                    _triggerbot_state["enter_range_time"] = None
                    _triggerbot_state["burst_state"] = None
            return "NO_TARGET"
        
        # 檢測到目標顏色
        cv2.putText(img, "TARGET DETECTED", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        with _triggerbot_state["burst_lock"]:
            current_state = _triggerbot_state["burst_state"]
            enter_time = _triggerbot_state["enter_range_time"]
            last_trigger = _triggerbot_state["last_trigger_time"]
        
        # 【Cooldown 檢查】- 使用上次觸發時選擇的 cooldown 值
        current_cooldown = _triggerbot_state.get("current_cooldown", 0.0)
        if tbcooldown_max > 0 and current_cooldown > 0:
            if (now - last_trigger) < current_cooldown:
                remaining = current_cooldown - (now - last_trigger)
                return f"COOLDOWN ({remaining:.2f}s)"
        
        # 如果正在連發中，不處理
        if current_state == "bursting":
            return "BURSTING"
        
        # 【Delay 等待】- 第一次進入範圍時，開始計時
        if enter_time is None:
            with _triggerbot_state["burst_lock"]:
                _triggerbot_state["enter_range_time"] = now
                _triggerbot_state["burst_state"] = "waiting"
            enter_time = now
        
        # 從範圍中隨機選擇 delay
        random_delay = random.uniform(tbdelay_min, tbdelay_max)
        elapsed = now - enter_time
        
        if elapsed < random_delay:
            # Delay 時間未到
            return f"WAITING ({elapsed:.2f}s/{random_delay:.2f}s)"
        
        # 【連發射擊】- Delay 時間已到，開始執行連發序列
        with _triggerbot_state["burst_lock"]:
            # 檢查是否已經有連發線程在運行
            if _triggerbot_state["burst_thread"] is not None and _triggerbot_state["burst_thread"].is_alive():
                return "BURST_IN_PROGRESS"
            
            # 創建新的連發線程
            burst_thread = threading.Thread(
                target=_execute_burst_sequence,
                args=(controller, tbburst_count_min, tbburst_count_max, tbhold_min, tbhold_max, 
                      tbburst_interval_min, tbburst_interval_max),
                daemon=True
            )
            _triggerbot_state["burst_thread"] = burst_thread
            _triggerbot_state["burst_state"] = "bursting"
            _triggerbot_state["last_trigger_time"] = now
            _triggerbot_state["enter_range_time"] = None  # 重置進入範圍計時器
            # 為下次觸發從範圍中隨機選擇新的 cooldown 值
            if tbcooldown_max > 0:
                _triggerbot_state["current_cooldown"] = random.uniform(tbcooldown_min, tbcooldown_max)
            else:
                _triggerbot_state["current_cooldown"] = 0.0
        
        # 啟動連發線程
        burst_thread.start()
        
        return f"BURST_STARTED ({tbburst_count_min}-{tbburst_count_max} shots)"
        
    except Exception as e:
        print("[Triggerbot error]", e)
        return f"ERROR: {str(e)}"

