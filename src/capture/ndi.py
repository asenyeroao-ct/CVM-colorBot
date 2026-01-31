"""
NDI 管理模組
處理 NDI 來源的搜尋、連接和視頻幀捕獲
"""
import queue
import threading
from cyndilib.finder import Finder
from cyndilib.receiver import Receiver
from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth
from cyndilib.video_frame import VideoFrameSync
from cyndilib.audio_frame import AudioFrameSync


class NDIManager:
    """管理 NDI 連接和視頻幀"""
    
    def __init__(self):
        """初始化 NDI 管理器"""
        self.finder = Finder()
        self.receiver = Receiver(
            color_format=RecvColorFormat.RGBX_RGBA, 
            bandwidth=RecvBandwidth.highest
        )
        
        self.video_frame = VideoFrameSync()
        self.audio_frame = AudioFrameSync()
        self.receiver.frame_sync.set_video_frame(self.video_frame)
        self.receiver.frame_sync.set_audio_frame(self.audio_frame)
        
        self.connected = False
        self.ndi_sources = []
        self.selected_source = None
        self.source_queue = queue.Queue()
        
        # 設置 finder 回調
        self.finder.set_change_callback(self._on_finder_change)
        self.finder.open()
        
        # 用於 UI 更新的回調
        self._source_update_callback = None
    
    def set_source_update_callback(self, callback):
        """設置當 NDI 來源列表更新時的回調函數"""
        self._source_update_callback = callback
    
    def _on_finder_change(self):
        """當 NDI 來源發生變化時的內部回調"""
        try:
            names = self.finder.get_source_names() or []
        except Exception:
            names = []
        self.source_queue.put(names)
    
    def get_pending_source_updates(self):
        """獲取所有待處理的來源更新"""
        updates = []
        while not self.source_queue.empty():
            updates.append(self.source_queue.get())
        return updates
    
    def refresh_sources(self):
        """刷新 NDI 來源列表
        
        Returns:
            list: NDI 來源名稱列表,如果沒有找到則返回空列表
        """
        try:
            names = self.finder.get_source_names() or []
        except Exception:
            names = []
        
        if names:
            self.ndi_sources = names
            self.selected_source = names[0]
        else:
            self.ndi_sources = []
            self.selected_source = None
        
        return names
    
    def connect_to_source(self, source_name=None):
        """連接到指定的 NDI 來源
        
        Args:
            source_name: 要連接的來源名稱,如果為 None 則使用 selected_source
            
        Returns:
            tuple: (成功與否, 錯誤訊息或 None)
        """
        if not self.ndi_sources:
            return False, "No NDI sources available"
        
        if source_name is None:
            if self.selected_source is None:
                if self.ndi_sources:
                    self.selected_source = self.ndi_sources[0]
                else:
                    return False, "No sources available"
            source_name = self.selected_source
        else:
            self.selected_source = source_name
        
        try:
            with self.finder.notify:
                src = self.finder.get_source(source_name)
                self.receiver.set_source(src)
                self.connected = True
                return True, None
        except Exception as e:
            self.connected = False
            return False, str(e)
    
    def is_connected(self):
        """檢查是否已連接到 NDI 來源
        
        Returns:
            bool: 連接狀態
        """
        try:
            is_conn = self.receiver.is_connected()
            self.connected = is_conn
            return is_conn
        except Exception:
            self.connected = False
            return False
    
    def capture_frame(self):
        """捕獲當前視頻幀
        
        Returns:
            VideoFrameSync: 視頻幀物件,如果失敗返回 None
        """
        if not self.connected:
            return None
        
        try:
            self.receiver.frame_sync.capture_video()
            return self.video_frame
        except Exception:
            return None
    
    def get_source_list(self):
        """獲取當前 NDI 來源列表
        
        Returns:
            list: NDI 來源名稱列表
        """
        return self.ndi_sources.copy()
    
    def set_selected_source(self, source_name):
        """設置選中的 NDI 來源
        
        Args:
            source_name: 來源名稱
        """
        if source_name in self.ndi_sources:
            self.selected_source = source_name
    
    def cleanup(self):
        """清理 NDI 資源"""
        try:
            if self.finder:
                self.finder.close()
        except Exception as e:
            print(f"[NDI] Finder cleanup error: {e}")
        
        try:
            if self.receiver:
                # 斷開接收器
                self.receiver.set_source(None)
        except Exception as e:
            print(f"[NDI] Receiver cleanup error: {e}")
        
        self.connected = False
        print("[INFO] NDI resources cleaned up.")

