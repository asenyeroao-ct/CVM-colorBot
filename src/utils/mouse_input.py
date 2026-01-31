"""
滑鼠按鈕輸入監控模組
用於追蹤和統計滑鼠按鈕的按下狀態和次數
"""
from src.utils.mouse import is_button_pressed

# 按鈕名稱映射
BUTTON_NAMES = {
    0: "左鍵",
    1: "右鍵",
    2: "中鍵",
    3: "側鍵4",
    4: "側鍵5"
}

class MouseInputMonitor:
    """滑鼠按鈕監控器"""
    
    def __init__(self):
        self.button_counts = {i: 0 for i in range(5)}  # 按鈕按下次數
        self.last_button_states = {i: False for i in range(5)}  # 上次按鈕狀態
        self.is_enabled = False  # 監控開關
        
    def enable(self):
        """啟用監控"""
        self.is_enabled = True
        # 重置計數
        self.button_counts = {i: 0 for i in range(5)}
        # 初始化當前狀態
        for i in range(5):
            self.last_button_states[i] = is_button_pressed(i)
    
    def disable(self):
        """停用監控"""
        self.is_enabled = False
    
    def update(self):
        """更新按鈕狀態和計數（需要定期調用）"""
        if not self.is_enabled:
            return
        
        for i in range(5):
            current_state = is_button_pressed(i)
            last_state = self.last_button_states[i]
            
            # 檢測按下事件（從 False 變為 True）
            if not last_state and current_state:
                self.button_counts[i] += 1
            
            # 更新狀態
            self.last_button_states[i] = current_state
    
    def get_button_state(self, button_idx: int) -> bool:
        """獲取按鈕當前狀態"""
        if not self.is_enabled:
            return False
        return is_button_pressed(button_idx)
    
    def get_button_count(self, button_idx: int) -> int:
        """獲取按鈕按下次數"""
        return self.button_counts.get(button_idx, 0)
    
    def reset_counts(self):
        """重置所有按鈕計數"""
        self.button_counts = {i: 0 for i in range(5)}
    
    def get_all_states(self) -> dict:
        """獲取所有按鈕的狀態"""
        return {
            i: self.get_button_state(i) for i in range(5)
        }
    
    def get_all_counts(self) -> dict:
        """獲取所有按鈕的計數"""
        return self.button_counts.copy()

