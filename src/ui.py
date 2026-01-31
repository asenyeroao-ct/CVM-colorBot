"""
UI 模組 - Ultra Minimalist 風格
處理所有用戶界面相關的功能
"""
import customtkinter as ctk
import tkinter as tk
import os
import json
import cv2

from src.utils.config import config
from src.capture.capture_service import CaptureService
from src.utils.mouse_input import MouseInputMonitor
from src.utils.debug_logger import get_recent_logs, clear_logs, get_log_count

# --- 風格配置 (Ultra Minimalist) ---
COLOR_BG = "#121212"          # 統一深灰背景
COLOR_SIDEBAR = "#121212"     # 與背景同色，僅靠留白區分
COLOR_SURFACE = "#1E1E1E"     # 極淡的表面色，用於輸入框
COLOR_ACCENT = "#FFFFFF"      # 白色作為強調色 (極簡黑白)
COLOR_ACCENT_HOVER = "#E0E0E0"
COLOR_TEXT = "#E0E0E0"        # 灰白文字
COLOR_TEXT_DIM = "#757575"    # 暗灰輔助文字
COLOR_BORDER = "#2C2C2C"      # 非常淡的分割線
COLOR_DANGER = "#CF6679"      # 柔和紅

FONT_MAIN = ("Roboto", 11)
FONT_BOLD = ("Roboto", 11, "bold")
FONT_TITLE = ("Roboto", 18, "bold")

BUTTONS = {
    0: 'Left Mouse Button',
    1: 'Right Mouse Button',
    2: 'Middle Mouse Button',
    3: 'Side Mouse 4 Button',
    4: 'Side Mouse 5 Button'
}

class ViewerApp(ctk.CTk):
    """主應用程式 UI 類 (Ultra Minimalist)"""
    
    def __init__(self, tracker, capture_service):
        super().__init__()
        
        # --- 視窗設置 ---
        self.title("CVM colorBot")
        self.geometry("1210x950")
        
        # 注意：使用 overrideredirect 會導致任務欄不顯示
        # 如果需要任務欄圖標，註釋掉下面這行
        # self.overrideredirect(True)
        
        self.configure(fg_color=COLOR_BG)
        
        # 設置窗口屬性以確保任務欄顯示
        self.attributes('-topmost', False)
        
        # --- 數據引用 ---
        self.tracker = tracker
        self.capture = capture_service
        
        # --- 滑鼠輸入監控 ---
        self.mouse_input_monitor = MouseInputMonitor()
        
        # --- Debug tab 狀態變量（需要在 __init__ 中初始化以保持狀態） ---
        self.debug_mouse_input_var = tk.BooleanVar(value=False)
        
        # --- UI 狀態 ---
        self._slider_widgets = {}
        self._checkbox_vars = {}
        self._option_widgets = {}
        self.current_frame = None
        
        # 初始化時應用 config 中的 capture_mode
        init_mode = getattr(config, "capture_mode", "NDI")
        self.capture.set_mode(init_mode)
        self.capture_method_var = tk.StringVar(value=init_mode)
        
        # --- Capture Controls 狀態保存（從 config 讀取） ---
        self.saved_udp_ip = getattr(config, "udp_ip", "127.0.0.1")
        self.saved_udp_port = getattr(config, "udp_port", "1234")
        self.saved_ndi_source = getattr(config, "last_ndi_source", None)
        
        # --- 構建界面 ---
        self._build_layout()
        
        # --- 啟動任務 ---
        self.after(100, self._process_source_updates)
        self.after(500, self._update_connection_status_loop)
        self.after(200, self._load_initial_config)
        self.after(300, self._update_performance_stats)  # 性能統計更新
        self.after(50, self._update_mouse_input_debug)  # 滑鼠輸入調試更新
        self.after(100, self._update_debug_log)  # Debug 日誌更新

    def _build_layout(self):
        """構建佈局：無明顯邊界的側邊欄 + 內容區"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 標題欄 (隱形)
        self._build_title_bar()
        
        # 側邊欄
        self._build_sidebar()
        
        # 內容區
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=1, sticky="nsew", padx=40, pady=20)
        
        self._show_general_tab()

    def _build_title_bar(self):
        """極簡標題欄"""
        self.title_bar = ctk.CTkFrame(self, height=30, fg_color=COLOR_BG, corner_radius=0)
        self.title_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # 僅顯示一個小的標識
        title_lbl = ctk.CTkLabel(
            self.title_bar, 
            text="CVM colorBot", 
            font=("Roboto", 10, "bold"),
            text_color=COLOR_TEXT_DIM
        )
        title_lbl.pack(side="left", padx=20)
        
        # 關閉按鈕 (純文字)
        close_btn = ctk.CTkButton(
            self.title_bar, 
            text="✕", 
            width=30, 
            height=30,
            fg_color="transparent", 
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            font=("Arial", 12),
            command=self._on_close,
            corner_radius=0
        )
        close_btn.pack(side="right", padx=5)
        
        # 拖動
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        title_lbl.bind("<Button-1>", self.start_move)
        title_lbl.bind("<B1-Motion>", self.do_move)

    def _build_sidebar(self):
        """側邊欄：純圖標或簡約文字"""
        self.sidebar = ctk.CTkFrame(self, width=180, fg_color=COLOR_BG, corner_radius=0)
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        
        # 分隔線 (細微)
        sep = ctk.CTkFrame(self.sidebar, width=1, fg_color=COLOR_BORDER)
        sep.pack(side="right", fill="y")

        # 導航容器
        nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_container.pack(fill="x", padx=20, pady=20)
        
        self.nav_buttons = {}
        tabs = [
            ("General", self._show_general_tab),
            ("Aimbot", self._show_aimbot_tab),
            ("Sec Aimbot", self._show_sec_aimbot_tab),
            ("Trigger", self._show_tb_tab),
            ("RCS", self._show_rcs_tab),
            ("Config", self._show_config_tab),
            ("Debug", self._show_debug_tab)
        ]
        
        for text, cmd in tabs:
            btn = self._create_nav_btn(nav_container, text, cmd)
            self.nav_buttons[text] = btn
            btn.pack(pady=2, fill="x")
            
        # 底部區域
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        # 主題切換 (文字)
        self.theme_btn = ctk.CTkButton(
            bottom_frame,
            text="Dark Mode",
            fg_color="transparent",
            text_color=COLOR_TEXT_DIM,
            hover_color=COLOR_SURFACE,
            anchor="w",
            height=25,
            font=("Roboto", 10),
            command=self._toggle_theme
        )
        self.theme_btn.pack(fill="x", pady=5)
        
        # 性能信息顯示
        self.fps_label = ctk.CTkLabel(
            bottom_frame, 
            text="FPS: --", 
            text_color=COLOR_TEXT_DIM, 
            font=("Roboto", 9), 
            anchor="w"
        )
        self.fps_label.pack(fill="x", pady=2)
        
        self.decode_delay_label = ctk.CTkLabel(
            bottom_frame, 
            text="Decode: -- ms", 
            text_color=COLOR_TEXT_DIM, 
            font=("Roboto", 9), 
            anchor="w"
        )
        self.decode_delay_label.pack(fill="x", pady=2)
        
        self.total_delay_label = ctk.CTkLabel(
            bottom_frame, 
            text="Delay: -- ms", 
            text_color=COLOR_TEXT_DIM, 
            font=("Roboto", 9), 
            anchor="w"
        )
        self.total_delay_label.pack(fill="x", pady=2)
        
        # 狀態 (極簡點)
        self.status_indicator = ctk.CTkLabel(bottom_frame, text="● Offline", text_color=COLOR_TEXT_DIM, font=("Roboto", 10), anchor="w")
        self.status_indicator.pack(fill="x")
        
        # 設置按鈕
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="⚙️ settings",
            command=self._open_settings_window,
            fg_color="transparent",
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=("Roboto", 11),
            anchor="w",
            height=30
        )
        settings_btn.pack(fill="x", pady=(10, 0))

    def _create_nav_btn(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            height=35,
            fg_color="transparent",
            text_color=COLOR_TEXT_DIM,
            hover_color=None, # 無背景懸停
            anchor="w",
            font=FONT_BOLD,
            command=lambda: self._handle_nav_click(text, command)
        )

    def _handle_nav_click(self, text, command):
        for btn_text, btn in self.nav_buttons.items():
            if btn_text == text:
                btn.configure(text_color=COLOR_ACCENT) # 僅改變文字顏色
            else:
                btn.configure(text_color=COLOR_TEXT_DIM)
        command()

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _toggle_theme(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="Light Mode")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="Dark Mode")

    # --- 頁面內容 ---

    def _show_general_tab(self):
        self._clear_content()
        self._add_title("General")
        
        self._add_subtitle("CAPTURE CONTROLS")
        
        # Capture Method Selection
        self.capture_method_var.set(self.capture.mode)
        # 創建 option menu
        self.capture_method_option = self._add_option_row("Method", ["NDI", "UDP", "CaptureCard"], self._on_capture_method_changed)
        # 顯式設置當前值
        self.capture_method_option.set(self.capture.mode)
        
        self._add_spacer()
        
        # Dynamic Capture Content Frame
        self.capture_content_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.capture_content_frame.pack(fill="x", pady=5)
        
        self._update_capture_ui()

        self._add_spacer()
        self._add_subtitle("SETTINGS")
        
        # In-Game Sensitivity (預設 0.235, 範圍 0.1-20)
        self._add_slider("In-Game Sensitivity", "in_game_sens", 0.1, 20, 
                        float(getattr(config, "in_game_sens", 0.235)), 
                        self._on_config_in_game_sens_changed, is_float=True)
        
        self._add_spacer()
        
        self.mode_option = self._add_option_row("Operation Mode", ["Normal"], self._on_mode_selected)
        self._option_widgets["mode"] = self.mode_option
        # 設置當前值
        current_mode = getattr(config, "mode", "Normal")
        self.mode_option.set(current_mode)
        
        self.color_option = self._add_option_row("Target Color", ["yellow", "purple"], self._on_color_selected)
        self._option_widgets["color"] = self.color_option
        # 設置當前值
        current_color = getattr(config, "color", "yellow")
        self.color_option.set(current_color)
        
        # --- Button Mask Section (Moved to Bottom) ---
        self._add_spacer()
        
        # Container with slight background for better visual separation
        mask_container = ctk.CTkFrame(self.content_frame, fg_color=COLOR_SURFACE, corner_radius=6)
        mask_container.pack(fill="x", pady=(10, 5), padx=0)
        
        # Header inside container
        header_frame = ctk.CTkFrame(mask_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            header_frame, 
            text="BUTTON MASK", 
            font=("Roboto", 11, "bold"), 
            text_color=COLOR_TEXT
        ).pack(side="left")
        
        # Button Mask 總開關 (Right aligned in header)
        if not hasattr(self, 'var_button_mask_enabled'):
            self.var_button_mask_enabled = tk.BooleanVar(value=getattr(config, "button_mask_enabled", False))
        
        master_switch = ctk.CTkSwitch(
            header_frame,
            text="Enable",
            variable=self.var_button_mask_enabled,
            command=self._on_button_mask_enabled_changed,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 11),
            width=80,
            height=20
        )
        master_switch.pack(side="right")
        self._checkbox_vars["button_mask_enabled"] = self.var_button_mask_enabled
        
        # Grid for individual buttons
        grid_frame = ctk.CTkFrame(mask_container, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Configure grid columns
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)
        
        button_masks = [
            ("L-Click", "mask_left_button", 0, 0),
            ("R-Click", "mask_right_button", 0, 1),
            ("M-Click", "mask_middle_button", 0, 2),
            ("Side 4", "mask_side4_button", 1, 0),
            ("Side 5", "mask_side5_button", 1, 1),
        ]
        
        for label, key, row, col in button_masks:
            var_name = f"var_{key}"
            if not hasattr(self, var_name):
                var = tk.BooleanVar(value=getattr(config, key, False))
                setattr(self, var_name, var)
            else:
                var = getattr(self, var_name)
            
            # 使用更簡約的 Switch 風格
            btn_switch = ctk.CTkSwitch(
                grid_frame,
                text=label,
                variable=var,
                command=lambda k=key, v=var: self._on_button_mask_changed(k, v),
                fg_color=COLOR_BORDER,
                progress_color=COLOR_TEXT, # 統一黑白風格
                button_color=COLOR_TEXT,
                button_hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_TEXT_DIM,
                font=("Roboto", 10),
                height=18,
                width=30, # Smaller switch width
                switch_width=30,
                switch_height=16
            )
            btn_switch.grid(row=row, column=col, sticky="w", padx=5, pady=6)
            self._checkbox_vars[key] = var

    def _update_capture_ui(self):
        """根據選擇的捕獲方法更新 UI"""
        # 保存當前 UDP 輸入框的值（如果存在）
        if hasattr(self, 'udp_ip_entry') and self.udp_ip_entry.winfo_exists():
            self.saved_udp_ip = self.udp_ip_entry.get()
        if hasattr(self, 'udp_port_entry') and self.udp_port_entry.winfo_exists():
            self.saved_udp_port = self.udp_port_entry.get()
        
        # 保存當前 NDI 選擇的源（如果存在）
        if hasattr(self, 'source_option') and self.source_option.winfo_exists():
            current_selection = self.source_option.get()
            if current_selection not in ["(Scanning...)", "(no sources)"]:
                self.saved_ndi_source = current_selection
        
        # 清除舊的 UI 元素
        for widget in self.capture_content_frame.winfo_children():
            widget.destroy()
            
        method = self.capture_method_var.get()
        
        if method == "NDI":
            # NDI Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "NDI SOURCE")
            self.source_option = self._add_option_menu(["(Scanning...)"], self._on_source_selected, parent=self.capture_content_frame)
            self.source_option.pack(fill="x", pady=5)
            
            # 如果有保存的 NDI 源，嘗試恢復
            if self.saved_ndi_source:
                # 稍後在 _apply_sources_to_ui 中會更新源列表並恢復選擇
                pass
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "REFRESH", self._refresh_sources).pack(side="left")
            self._add_text_button(btn_frame, "CONNECT", self._connect_to_selected).pack(side="left", padx=15)
            
        elif method == "UDP":
            # UDP Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "UDP SETTINGS")
            
            # IP Input - 使用保存的值
            ip_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            ip_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(ip_frame, text="IP Address", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.udp_ip_entry = ctk.CTkEntry(ip_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.udp_ip_entry.pack(side="right")
            self.udp_ip_entry.insert(0, self.saved_udp_ip)
            # 綁定事件以實時保存
            self.udp_ip_entry.bind("<KeyRelease>", self._on_udp_ip_changed)
            self.udp_ip_entry.bind("<FocusOut>", self._on_udp_ip_changed)
            
            # Port Input - 使用保存的值
            port_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            port_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(port_frame, text="Port", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.udp_port_entry = ctk.CTkEntry(port_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.udp_port_entry.pack(side="right")
            self.udp_port_entry.insert(0, self.saved_udp_port)
            # 綁定事件以實時保存
            self.udp_port_entry.bind("<KeyRelease>", self._on_udp_port_changed)
            self.udp_port_entry.bind("<FocusOut>", self._on_udp_port_changed)
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "CONNECT", self._connect_udp).pack(side="left")
            
        elif method == "CaptureCard":
            # CaptureCard Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "CAPTURE CARD SETTINGS")
            
            # Device Index
            device_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            device_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(device_frame, text="Device Index", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.capture_card_device_entry = ctk.CTkEntry(device_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.capture_card_device_entry.pack(side="right")
            device_index = str(getattr(config, "capture_device_index", 0))
            self.capture_card_device_entry.insert(0, device_index)
            self.capture_card_device_entry.bind("<KeyRelease>", self._on_capture_card_device_changed)
            self.capture_card_device_entry.bind("<FocusOut>", self._on_capture_card_device_changed)
            
            # Resolution
            res_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            res_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(res_frame, text="Resolution (WxH)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            res_input_frame = ctk.CTkFrame(res_frame, fg_color="transparent")
            res_input_frame.pack(side="right")
            self.capture_card_width_entry = ctk.CTkEntry(res_input_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=70)
            self.capture_card_width_entry.pack(side="left", padx=2)
            ctk.CTkLabel(res_input_frame, text="x", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left", padx=5)
            self.capture_card_height_entry = ctk.CTkEntry(res_input_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=70)
            self.capture_card_height_entry.pack(side="left", padx=2)
            width = str(getattr(config, "capture_width", 1920))
            height = str(getattr(config, "capture_height", 1080))
            self.capture_card_width_entry.insert(0, width)
            self.capture_card_height_entry.insert(0, height)
            self.capture_card_width_entry.bind("<KeyRelease>", self._on_capture_card_resolution_changed)
            self.capture_card_width_entry.bind("<FocusOut>", self._on_capture_card_resolution_changed)
            self.capture_card_height_entry.bind("<KeyRelease>", self._on_capture_card_resolution_changed)
            self.capture_card_height_entry.bind("<FocusOut>", self._on_capture_card_resolution_changed)
            
            # FPS
            fps_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fps_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(fps_frame, text="FPS", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.capture_card_fps_entry = ctk.CTkEntry(fps_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.capture_card_fps_entry.pack(side="right")
            fps = str(getattr(config, "capture_fps", 240))
            self.capture_card_fps_entry.insert(0, fps)
            self.capture_card_fps_entry.bind("<KeyRelease>", self._on_capture_card_fps_changed)
            self.capture_card_fps_entry.bind("<FocusOut>", self._on_capture_card_fps_changed)
            
            self._add_spacer_in_frame(self.capture_content_frame)
            self._add_subtitle_in_frame(self.capture_content_frame, "CAPTURE REGION")
            
            # Capture Range X
            range_x_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            range_x_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(range_x_frame, text="Range X (min: 128)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.capture_card_range_x_entry = ctk.CTkEntry(range_x_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.capture_card_range_x_entry.pack(side="right")
            range_x = str(getattr(config, "capture_range_x", 128))
            self.capture_card_range_x_entry.insert(0, range_x)
            self.capture_card_range_x_entry.bind("<KeyRelease>", self._on_capture_card_range_keyrelease)
            self.capture_card_range_x_entry.bind("<FocusOut>", self._on_capture_card_range_focusout)
            
            # Capture Range Y
            range_y_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            range_y_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(range_y_frame, text="Range Y (min: 128)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.capture_card_range_y_entry = ctk.CTkEntry(range_y_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.capture_card_range_y_entry.pack(side="right")
            range_y = str(getattr(config, "capture_range_y", 128))
            self.capture_card_range_y_entry.insert(0, range_y)
            self.capture_card_range_y_entry.bind("<KeyRelease>", self._on_capture_card_range_keyrelease)
            self.capture_card_range_y_entry.bind("<FocusOut>", self._on_capture_card_range_focusout)
            
            # 顯示中心點信息
            center_info_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            center_info_frame.pack(fill="x", pady=5)
            self.capture_card_center_label = ctk.CTkLabel(
                center_info_frame, 
                text="Center: (0, 0)", 
                font=("Roboto", 10), 
                text_color=COLOR_TEXT_DIM
            )
            self.capture_card_center_label.pack(side="left")
            # 更新中心點顯示
            self._update_capture_card_center_display()
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "CONNECT", self._connect_capture_card).pack(side="left")

    def _on_udp_ip_changed(self, event=None):
        """實時保存 UDP IP"""
        if hasattr(self, 'udp_ip_entry') and self.udp_ip_entry.winfo_exists():
            val = self.udp_ip_entry.get()
            self.saved_udp_ip = val
            config.udp_ip = val

    def _on_udp_port_changed(self, event=None):
        """實時保存 UDP Port"""
        if hasattr(self, 'udp_port_entry') and self.udp_port_entry.winfo_exists():
            val = self.udp_port_entry.get()
            self.saved_udp_port = val
            config.udp_port = val
    
    def _on_capture_card_device_changed(self, event=None):
        """實時保存 CaptureCard Device Index"""
        if hasattr(self, 'capture_card_device_entry') and self.capture_card_device_entry.winfo_exists():
            try:
                val = int(self.capture_card_device_entry.get())
                config.capture_device_index = val
            except ValueError:
                pass
    
    def _on_capture_card_resolution_changed(self, event=None):
        """實時保存 CaptureCard Resolution"""
        if hasattr(self, 'capture_card_width_entry') and hasattr(self, 'capture_card_height_entry'):
            if self.capture_card_width_entry.winfo_exists() and self.capture_card_height_entry.winfo_exists():
                try:
                    width = int(self.capture_card_width_entry.get())
                    height = int(self.capture_card_height_entry.get())
                    config.capture_width = width
                    config.capture_height = height
                except ValueError:
                    pass
    
    def _on_capture_card_fps_changed(self, event=None):
        """實時保存 CaptureCard FPS"""
        if hasattr(self, 'capture_card_fps_entry') and self.capture_card_fps_entry.winfo_exists():
            try:
                val = float(self.capture_card_fps_entry.get())
                config.capture_fps = val
            except ValueError:
                pass
    
    def _on_capture_card_range_keyrelease(self, event=None):
        """在輸入過程中更新中心點顯示（不強制修改輸入框）"""
        if hasattr(self, 'capture_card_range_x_entry') and hasattr(self, 'capture_card_range_y_entry'):
            if self.capture_card_range_x_entry.winfo_exists() and self.capture_card_range_y_entry.winfo_exists():
                try:
                    range_x_str = self.capture_card_range_x_entry.get()
                    range_y_str = self.capture_card_range_y_entry.get()
                    
                    # 如果是空字符串，不處理（允許用戶清空輸入）
                    if not range_x_str or not range_y_str:
                        return
                    
                    range_x = int(range_x_str)
                    range_y = int(range_y_str)
                    
                    # 只更新中心點顯示，不更新配置（配置在失去焦點時更新）
                    # 允許用戶輸入任何數字，驗證在失去焦點時進行
                    # 更新中心點顯示（使用輸入的值，即使小於128也顯示）
                    self._update_capture_card_center_display_with_values(range_x, range_y)
                except ValueError:
                    # 如果輸入不是數字，不處理（允許用戶繼續輸入）
                    pass
    
    def _on_capture_card_range_focusout(self, event=None):
        """失去焦點時驗證並修正 CaptureCard Range"""
        if hasattr(self, 'capture_card_range_x_entry') and hasattr(self, 'capture_card_range_y_entry'):
            if self.capture_card_range_x_entry.winfo_exists() and self.capture_card_range_y_entry.winfo_exists():
                try:
                    range_x_str = self.capture_card_range_x_entry.get()
                    range_y_str = self.capture_card_range_y_entry.get()
                    
                    # 如果是空字符串，恢復為默認值
                    if not range_x_str:
                        range_x = 128
                        self.capture_card_range_x_entry.delete(0, "end")
                        self.capture_card_range_x_entry.insert(0, "128")
                    else:
                        range_x = int(range_x_str)
                        # 確保最低值為 128
                        if range_x < 128:
                            range_x = 128
                            self.capture_card_range_x_entry.delete(0, "end")
                            self.capture_card_range_x_entry.insert(0, "128")
                    
                    if not range_y_str:
                        range_y = 128
                        self.capture_card_range_y_entry.delete(0, "end")
                        self.capture_card_range_y_entry.insert(0, "128")
                    else:
                        range_y = int(range_y_str)
                        # 確保最低值為 128
                        if range_y < 128:
                            range_y = 128
                            self.capture_card_range_y_entry.delete(0, "end")
                            self.capture_card_range_y_entry.insert(0, "128")
                    
                    # 更新配置
                    config.capture_range_x = range_x
                    config.capture_range_y = range_y
                    # 更新中心點顯示
                    self._update_capture_card_center_display()
                except ValueError:
                    # 如果輸入不是數字，恢復為有效值
                    try:
                        current_x = int(getattr(config, "capture_range_x", 128))
                        if current_x < 128:
                            current_x = 128
                        self.capture_card_range_x_entry.delete(0, "end")
                        self.capture_card_range_x_entry.insert(0, str(current_x))
                        config.capture_range_x = current_x
                    except:
                        self.capture_card_range_x_entry.delete(0, "end")
                        self.capture_card_range_x_entry.insert(0, "128")
                        config.capture_range_x = 128
                    
                    try:
                        current_y = int(getattr(config, "capture_range_y", 128))
                        if current_y < 128:
                            current_y = 128
                        self.capture_card_range_y_entry.delete(0, "end")
                        self.capture_card_range_y_entry.insert(0, str(current_y))
                        config.capture_range_y = current_y
                    except:
                        self.capture_card_range_y_entry.delete(0, "end")
                        self.capture_card_range_y_entry.insert(0, "128")
                        config.capture_range_y = 128
                    
                    # 更新中心點顯示
                    self._update_capture_card_center_display()
    
    def _update_capture_card_center_display(self):
        """更新 CaptureCard 中心點顯示（從 config 讀取）"""
        if hasattr(self, 'capture_card_center_label') and self.capture_card_center_label.winfo_exists():
            try:
                range_x = int(getattr(config, "capture_range_x", 128))
                range_y = int(getattr(config, "capture_range_y", 128))
                
                # 確保最低值為 128
                if range_x < 128:
                    range_x = 128
                if range_y < 128:
                    range_y = 128
                
                # 如果範圍為 0 或未設置，使用默認值或分辨率
                if range_x <= 0:
                    range_x = max(128, int(getattr(config, "capture_width", 1920)))
                if range_y <= 0:
                    range_y = max(128, int(getattr(config, "capture_height", 1080)))
                
                # 計算中心點：基於 range_x 和 range_y 的 X/2, Y/2
                center_x = range_x // 2
                center_y = range_y // 2
                
                self.capture_card_center_label.configure(
                    text=f"Center: ({center_x}, {center_y}) | Range: {range_x}x{range_y}"
                )
            except (ValueError, AttributeError):
                self.capture_card_center_label.configure(text="Center: (0, 0)")
    
    def _update_capture_card_center_display_with_values(self, range_x, range_y):
        """更新 CaptureCard 中心點顯示（使用指定的值）"""
        if hasattr(self, 'capture_card_center_label') and self.capture_card_center_label.winfo_exists():
            try:
                # 使用傳入的值（即使小於128也顯示，讓用戶看到輸入的值）
                if range_x <= 0:
                    range_x = max(128, int(getattr(config, "capture_width", 1920)))
                if range_y <= 0:
                    range_y = max(128, int(getattr(config, "capture_height", 1080)))
                
                # 計算中心點：基於 range_x 和 range_y 的 X/2, Y/2
                center_x = range_x // 2
                center_y = range_y // 2
                
                self.capture_card_center_label.configure(
                    text=f"Center: ({center_x}, {center_y}) | Range: {range_x}x{range_y}"
                )
            except (ValueError, AttributeError):
                self.capture_card_center_label.configure(text="Center: (0, 0)")

    def _show_aimbot_tab(self):
        self._clear_content()
        self._add_title("Aimbot")
        
        self.var_enableaim = tk.BooleanVar(value=getattr(config, "enableaim", False))
        self._add_switch("Enable Aimbot", self.var_enableaim, self._on_enableaim_changed)
        self._checkbox_vars["enableaim"] = self.var_enableaim
        
        # Anti-Smoke Switch
        self.var_anti_smoke = tk.BooleanVar(value=getattr(config, "anti_smoke_enabled", False))
        self._add_switch("Enable Anti-Smoke", self.var_anti_smoke, self._on_anti_smoke_changed)
        self._checkbox_vars["anti_smoke_enabled"] = self.var_anti_smoke
        
        self._add_spacer()
        self._add_subtitle("SENSITIVITY")
        # 從 config 讀取當前值而不是硬編碼預設值
        self._add_slider("X-Speed", "normal_x_speed", 0.1, 2000, 
                        float(getattr(config, "normal_x_speed", 0.5)), 
                        self._on_normal_x_speed_changed)
        self._add_slider("Y-Speed", "normal_y_speed", 0.1, 2000, 
                        float(getattr(config, "normal_y_speed", 0.5)), 
                        self._on_normal_y_speed_changed)
        self._add_slider("Smoothing", "normalsmooth", 1, 30, 
                        float(getattr(config, "normalsmooth", 10)), 
                        self._on_config_normal_smooth_changed)
        
        self._add_spacer()
        self._add_subtitle("FOV")
        self._add_slider("FOV Size", "fovsize", 1, 1000, 
                        float(getattr(config, "fovsize", 300)), 
                        self._on_fovsize_changed)
        self._add_slider("FOV Smooth", "normalsmoothfov", 1, 30, 
                        float(getattr(config, "normalsmoothfov", 10)), 
                        self._on_config_normal_smoothfov_changed)
        
        self._add_spacer()
        self._add_subtitle("OFFSET")
        # X-Offset
        self._add_slider("X-Offset", "aim_offsetX", -100, 100, 
                        float(getattr(config, "aim_offsetX", 0)), 
                        self._on_aim_offsetX_changed)
        # Y-Offset
        self._add_slider("Y-Offset", "aim_offsetY", -100, 100, 
                        float(getattr(config, "aim_offsetY", 0)), 
                        self._on_aim_offsetY_changed)
        
        self._add_spacer()
        self._add_subtitle("AIM TYPE")
        # Aim Type 選項
        self.aim_type_option = self._add_option_row("Target", ["head", "body", "nearest"], self._on_aim_type_selected)
        self._option_widgets["aim_type"] = self.aim_type_option
        # 設置當前值
        current_aim_type = getattr(config, "aim_type", "head")
        self.aim_type_option.set(current_aim_type)
        
        self._add_spacer()
        self._add_subtitle("ACTIVATION")
        self.aimbot_button_option = self._add_option_row("Keybind", list(BUTTONS.values()), self._on_aimbot_button_selected)
        self._option_widgets["selected_mouse_button"] = self.aimbot_button_option
        # 設置當前值
        current_btn = getattr(config, "selected_mouse_button", 3)
        self.aimbot_button_option.set(BUTTONS.get(current_btn, BUTTONS[3]))

    def _show_sec_aimbot_tab(self):
        self._clear_content()
        self._add_title("Secondary Aimbot")
        
        self.var_enableaim_sec = tk.BooleanVar(value=getattr(config, "enableaim_sec", False))
        self._add_switch("Enable Sec Aimbot", self.var_enableaim_sec, self._on_enableaim_sec_changed)
        self._checkbox_vars["enableaim_sec"] = self.var_enableaim_sec
        
        # Anti-Smoke Switch for Sec Aimbot
        self.var_anti_smoke_sec = tk.BooleanVar(value=getattr(config, "anti_smoke_enabled_sec", False))
        self._add_switch("Enable Anti-Smoke", self.var_anti_smoke_sec, self._on_anti_smoke_sec_changed)
        self._checkbox_vars["anti_smoke_enabled_sec"] = self.var_anti_smoke_sec
        
        self._add_spacer()
        self._add_subtitle("SENSITIVITY")
        # 從 config 讀取當前值
        self._add_slider("X-Speed", "normal_x_speed_sec", 0.1, 2000, 
                        float(getattr(config, "normal_x_speed_sec", 2)), 
                        self._on_normal_x_speed_sec_changed)
        self._add_slider("Y-Speed", "normal_y_speed_sec", 0.1, 2000, 
                        float(getattr(config, "normal_y_speed_sec", 2)), 
                        self._on_normal_y_speed_sec_changed)
        self._add_slider("Smoothing", "normalsmooth_sec", 1, 30, 
                        float(getattr(config, "normalsmooth_sec", 20)), 
                        self._on_config_normal_smooth_sec_changed)
        
        self._add_spacer()
        self._add_subtitle("FOV")
        self._add_slider("FOV Size", "fovsize_sec", 1, 1000, 
                        float(getattr(config, "fovsize_sec", 150)), 
                        self._on_fovsize_sec_changed)
        self._add_slider("FOV Smooth", "normalsmoothfov_sec", 1, 30, 
                        float(getattr(config, "normalsmoothfov_sec", 20)), 
                        self._on_config_normal_smoothfov_sec_changed)
        
        self._add_spacer()
        self._add_subtitle("OFFSET")
        # X-Offset
        self._add_slider("X-Offset", "aim_offsetX_sec", -100, 100, 
                        float(getattr(config, "aim_offsetX_sec", 0)), 
                        self._on_aim_offsetX_sec_changed)
        # Y-Offset
        self._add_slider("Y-Offset", "aim_offsetY_sec", -100, 100, 
                        float(getattr(config, "aim_offsetY_sec", 0)), 
                        self._on_aim_offsetY_sec_changed)
        
        self._add_spacer()
        self._add_subtitle("AIM TYPE")
        # Aim Type 選項
        self.aim_type_option_sec = self._add_option_row("Target", ["head", "body", "nearest"], self._on_aim_type_sec_selected)
        self._option_widgets["aim_type_sec"] = self.aim_type_option_sec
        # 設置當前值
        current_aim_type_sec = getattr(config, "aim_type_sec", "head")
        self.aim_type_option_sec.set(current_aim_type_sec)
        
        self._add_spacer()
        self._add_subtitle("ACTIVATION")
        self.aimbot_button_option_sec = self._add_option_row("Keybind", list(BUTTONS.values()), self._on_aimbot_button_sec_selected)
        self._option_widgets["selected_mouse_button_sec"] = self.aimbot_button_option_sec
        # 設置當前值
        current_btn_sec = getattr(config, "selected_mouse_button_sec", 2)
        self.aimbot_button_option_sec.set(BUTTONS.get(current_btn_sec, BUTTONS[2]))

    def _show_tb_tab(self):
        self._clear_content()
        self._add_title("Triggerbot")
        
        self.var_enabletb = tk.BooleanVar(value=getattr(config, "enabletb", False))
        self._add_switch("Enable Triggerbot", self.var_enabletb, self._on_enabletb_changed)
        self._checkbox_vars["enabletb"] = self.var_enabletb
        
        self._add_spacer()
        self._add_subtitle("PARAMETERS")
        # 從 config 讀取當前值
        self._add_slider("FOV Size", "tbfovsize", 1, 300, 
                        float(getattr(config, "tbfovsize", 70)), 
                        self._on_tbfovsize_changed)
        
        # Delay Range (雙滑塊)
        self._add_range_slider(
            "Delay Range (s)", 
            "tbdelay", 
            0.0, 1.0,
            float(getattr(config, "tbdelay_min", 0.08)),
            float(getattr(config, "tbdelay_max", 0.15)),
            self._on_tbdelay_range_changed,
            is_float=True
        )
        
        # Hold Range (雙滑塊)
        self._add_range_slider(
            "Hold Range (ms)", 
            "tbhold", 
            5, 500,
            float(getattr(config, "tbhold_min", 40)),
            float(getattr(config, "tbhold_max", 60)),
            self._on_tbhold_range_changed,
            is_float=False
        )
        
        self._add_spacer()
        self._add_subtitle("BURST SETTINGS")
        
        # Cooldown Range (雙滑塊)
        self._add_range_slider(
            "Cooldown Range (s)", 
            "tbcooldown", 
            0.0, 5.0,
            float(getattr(config, "tbcooldown_min", 0.0)),
            float(getattr(config, "tbcooldown_max", 0.0)),
            self._on_tbcooldown_range_changed,
            is_float=True
        )
        
        # Burst Count Range (雙滑塊)
        self._add_range_slider(
            "Burst Count Range", 
            "tbburst_count", 
            1, 10,
            int(getattr(config, "tbburst_count_min", 1)),
            int(getattr(config, "tbburst_count_max", 1)),
            self._on_tbburst_count_range_changed,
            is_float=False
        )
        
        # Burst Interval Range (雙滑塊)
        self._add_range_slider(
            "Burst Interval Range (ms)", 
            "tbburst_interval", 
            0, 500,
            float(getattr(config, "tbburst_interval_min", 0.0)),
            float(getattr(config, "tbburst_interval_max", 0.0)),
            self._on_tbburst_interval_range_changed,
            is_float=True
        )
        
        self._add_spacer()
        self._add_subtitle("ACTIVATION")
        self.tb_button_option = self._add_option_row("Keybind", list(BUTTONS.values()), self._on_tb_button_selected)
        self._option_widgets["selected_tb_btn"] = self.tb_button_option
        # 設置當前值
        current_tb_btn = getattr(config, "selected_tb_btn", 3)
        self.tb_button_option.set(BUTTONS.get(current_tb_btn, BUTTONS[3]))

    def _show_rcs_tab(self):
        """顯示 RCS 設置標籤"""
        self._clear_content()
        self._add_title("RCS (Recoil Control System)")
        
        # RCS 開關
        self.var_enablercs = tk.BooleanVar(value=getattr(config, "enablercs", False))
        self._add_switch("Enable RCS", self.var_enablercs, self._on_enablercs_changed)
        self._checkbox_vars["enablercs"] = self.var_enablercs
        
        self._add_spacer()
        self._add_subtitle("PARAMETERS")
        
        # Pull Speed (單滑塊)
        self._add_slider(
            "Pull Speed", 
            "rcs_pull_speed", 
            1, 20,
            int(getattr(config, "rcs_pull_speed", 10)),
            self._on_rcs_pull_speed_changed,
            is_float=False
        )
        
        # Activation Delay (單滑塊)
        self._add_slider(
            "Activation Delay (ms)", 
            "rcs_activation_delay", 
            50, 500,
            int(getattr(config, "rcs_activation_delay", 100)),
            self._on_rcs_activation_delay_changed,
            is_float=False
        )
        
        # Rapid Click Threshold (單滑塊)
        self._add_slider(
            "Rapid Click Threshold (ms)", 
            "rcs_rapid_click_threshold", 
            100, 1000,
            int(getattr(config, "rcs_rapid_click_threshold", 200)),
            self._on_rcs_rapid_click_threshold_changed,
            is_float=False
        )

    def _show_config_tab(self):
        self._clear_content()
        self._add_title("Configuration")
        
        os.makedirs("configs", exist_ok=True)
        
        self.config_option = self._add_option_menu([], self._on_config_selected)
        self.config_option.pack(fill="x", pady=10)
        
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        self._add_text_button(btn_frame, "SAVE", self._save_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "LOAD", self._load_selected_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "NEW", self._save_new_config).pack(side="left")
        
        self._add_spacer()
        self.config_log = ctk.CTkTextbox(
            self.content_frame, 
            height=100, 
            fg_color=COLOR_SURFACE, 
            text_color=COLOR_TEXT_DIM,
            font=("Consolas", 10),
            corner_radius=0
        )
        self.config_log.pack(fill="x", pady=10)
        
        self._refresh_config_list()

    def _show_debug_tab(self):
        """顯示 Debug tab - 顯示滑鼠移動和點擊日誌"""
        self._clear_content()
        self._add_title("Debug")
        
        # Mouse Input Debug Section
        self._add_subtitle("MOUSE INPUT DEBUG")
        
        # Enable switch (use existing var to preserve state)
        if not hasattr(self, 'debug_mouse_input_var'):
            self.debug_mouse_input_var = tk.BooleanVar(value=False)
        debug_switch = self._add_switch(
            "Enable Mouse Input Debug",
            self.debug_mouse_input_var,
            self._on_debug_mouse_input_changed
        )
        
        # Button status display container
        self.debug_mouse_frame = ctk.CTkFrame(self.content_frame, fg_color=COLOR_SURFACE, corner_radius=0)
        self.debug_mouse_frame.pack(fill="x", pady=10)
        
        # Create button status display
        self.debug_button_widgets = {}
        button_names = {
            0: "Left Button",
            1: "Right Button",
            2: "Middle Button",
            3: "Side Button 4",
            4: "Side Button 5"
        }
        
        for idx, name in button_names.items():
            btn_frame = ctk.CTkFrame(self.debug_mouse_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=5)
            
            # Button name
            name_label = ctk.CTkLabel(
                btn_frame,
                text=name,
                font=FONT_MAIN,
                text_color=COLOR_TEXT,
                width=120,
                anchor="w"
            )
            name_label.pack(side="left", padx=5)
            
            # Status indicator (circle)
            state_indicator = ctk.CTkLabel(
                btn_frame,
                text="●",
                font=("Arial", 16),
                text_color="#CF6679",  # Red (not pressed)
                width=30
            )
            state_indicator.pack(side="left", padx=5)
            
            # Count display
            count_label = ctk.CTkLabel(
                btn_frame,
                text="Count: 0",
                font=FONT_MAIN,
                text_color=COLOR_TEXT_DIM,
                anchor="w"
            )
            count_label.pack(side="left", padx=5, fill="x", expand=True)
            
            # Reset button
            reset_btn = ctk.CTkButton(
                btn_frame,
                text="Reset",
                width=60,
                height=25,
                fg_color=COLOR_BORDER,
                hover_color=COLOR_SURFACE,
                text_color=COLOR_TEXT,
                font=("Roboto", 9),
                command=lambda i=idx: self._reset_button_count(i)
            )
            reset_btn.pack(side="right", padx=5)
            
            self.debug_button_widgets[idx] = {
                "state_indicator": state_indicator,
                "count_label": count_label
            }
            
            # Restore button count from monitor (preserve state when switching tabs)
            try:
                count = self.mouse_input_monitor.get_button_count(idx)
                count_label.configure(text=f"Count: {count}")
            except Exception:
                pass
        
        # Reset all button
        reset_all_frame = ctk.CTkFrame(self.debug_mouse_frame, fg_color="transparent")
        reset_all_frame.pack(fill="x", padx=10, pady=5)
        
        reset_all_btn = ctk.CTkButton(
            reset_all_frame,
            text="Reset All Counts",
            width=120,
            height=30,
            fg_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            command=self._reset_all_button_counts
        )
        reset_all_btn.pack(side="right", padx=5)
        
        # Restore visibility state based on switch state
        if self.debug_mouse_input_var.get():
            self.debug_mouse_frame.pack(fill="x", pady=10)
            # Ensure monitor is enabled
            self.mouse_input_monitor.enable()
        else:
            self.debug_mouse_frame.pack_forget()
        
        # Debug Log Section
        self._add_spacer()
        self._add_subtitle("DEBUG LOG")
        
        # Control button area
        control_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        control_frame.pack(fill="x", pady=10)
        
        # Clear log button
        clear_btn = self._add_text_button(control_frame, "Clear Log", self._clear_debug_log)
        clear_btn.pack(side="left", padx=(0, 10))
        
        # Log count label
        self.debug_log_count_label = ctk.CTkLabel(
            control_frame,
            text="Log Count: 0",
            font=FONT_MAIN,
            text_color=COLOR_TEXT_DIM
        )
        self.debug_log_count_label.pack(side="left", padx=10)
        
        # Log display area
        self.debug_log_textbox = ctk.CTkTextbox(
            self.content_frame,
            height=400,
            fg_color=COLOR_SURFACE,
            text_color=COLOR_TEXT,
            font=("Consolas", 10),
            corner_radius=0
        )
        self.debug_log_textbox.pack(fill="both", expand=True, pady=10)
        
        # Initialize log display
        self._update_debug_log()

    # --- 極簡組件構建器 ---

    def _add_title(self, text):
        ctk.CTkLabel(self.content_frame, text=text, font=FONT_TITLE, text_color=COLOR_TEXT).pack(anchor="w", pady=(0, 20))

    def _add_subtitle(self, text):
        ctk.CTkLabel(self.content_frame, text=text.upper(), font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(anchor="w", pady=(10, 5))

    def _add_subtitle_in_frame(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(anchor="w", pady=(10, 5))
    
    def _add_spacer_in_frame(self, parent):
        """在指定 frame 中添加間距"""
        ctk.CTkFrame(parent, height=1, fg_color="transparent").pack(pady=5)

    def _add_spacer(self):
        ctk.CTkFrame(self.content_frame, height=1, fg_color="transparent").pack(pady=5)

    def _add_switch(self, text, variable, command):
        switch = ctk.CTkSwitch(
            self.content_frame, 
            text=text, 
            variable=variable, 
            command=command,
            progress_color=COLOR_TEXT, # 黑白風格
            fg_color=COLOR_BORDER,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_TEXT,
            font=FONT_MAIN,
            text_color=COLOR_TEXT
        )
        switch.pack(anchor="w", pady=5)
        return switch

    def _add_slider(self, text, key, min_val, max_val, init_val, command, is_float=False):
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        
        # 標籤與輸入框同在一行
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=text, font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        
        # 可編輯的輸入框（替換原本的 Label）
        val_str = f"{init_val:.2f}" if is_float else f"{int(init_val)}"
        val_entry = ctk.CTkEntry(
            header, 
            width=80,
            height=25,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            justify="center"
        )
        val_entry.insert(0, val_str)
        val_entry.pack(side="right")
        
        # Slider
        slider = ctk.CTkSlider(
            frame, 
            from_=min_val, 
            to=max_val, 
            number_of_steps=100,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_ACCENT,
            height=10,
            command=lambda v: self._on_slider_changed(v, val_entry, key, command, is_float, slider, min_val, max_val)
        )
        slider.set(init_val)
        slider.pack(fill="x", pady=(2, 5))
        
        # 綁定輸入框的事件
        val_entry.bind("<Return>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        val_entry.bind("<FocusOut>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        
        # 註冊 slider（保存 entry 引用而不是 label）
        self._register_slider(key, slider, val_entry, min_val, max_val, is_float)
    
    def _add_range_slider(self, text, key, min_val, max_val, init_min, init_max, command, is_float=False):
        """添加範圍滑塊（雙滑塊）"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        
        # 標籤與兩個輸入框
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=text, font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        
        # Max 輸入框（右邊）
        max_str = f"{init_max:.2f}" if is_float else f"{int(init_max)}"
        max_entry = ctk.CTkEntry(
            header, 
            width=70,
            height=25,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=("Roboto", 10),
            justify="center"
        )
        max_entry.insert(0, max_str)
        max_entry.pack(side="right", padx=2)
        
        # 連接符號
        ctk.CTkLabel(header, text="~", font=("Roboto", 10), text_color=COLOR_TEXT_DIM).pack(side="right")
        
        # Min 輸入框（左邊）
        min_str = f"{init_min:.2f}" if is_float else f"{int(init_min)}"
        min_entry = ctk.CTkEntry(
            header, 
            width=70,
            height=25,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=("Roboto", 10),
            justify="center"
        )
        min_entry.insert(0, min_str)
        min_entry.pack(side="right", padx=2)
        
        # 滑塊容器
        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(2, 5))
        
        # Min 滑塊（上面）
        min_slider = ctk.CTkSlider(
            slider_frame, 
            from_=min_val, 
            to=max_val, 
            number_of_steps=100 if is_float else int(max_val - min_val),
            fg_color=COLOR_BORDER,
            progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_ACCENT,
            height=10,
            command=lambda v: self._on_range_slider_changed(v, "min", min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val)
        )
        min_slider.set(init_min)
        min_slider.pack(fill="x", pady=1)
        
        # Max 滑塊（下面）
        max_slider = ctk.CTkSlider(
            slider_frame, 
            from_=min_val, 
            to=max_val, 
            number_of_steps=100 if is_float else int(max_val - min_val),
            fg_color=COLOR_BORDER,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            height=10,
            command=lambda v: self._on_range_slider_changed(v, "max", min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val)
        )
        max_slider.set(init_max)
        max_slider.pack(fill="x", pady=1)
        
        # 綁定輸入框事件
        min_entry.bind("<Return>", lambda e: self._on_range_entry_changed(min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val))
        min_entry.bind("<FocusOut>", lambda e: self._on_range_entry_changed(min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val))
        max_entry.bind("<Return>", lambda e: self._on_range_entry_changed(min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val))
        max_entry.bind("<FocusOut>", lambda e: self._on_range_entry_changed(min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val))
        
        # 註冊範圍滑塊
        if not hasattr(self, '_range_slider_widgets'):
            self._range_slider_widgets = {}
        self._range_slider_widgets[key] = {
            "min_slider": min_slider,
            "max_slider": max_slider,
            "min_entry": min_entry,
            "max_entry": max_entry,
            "min_val": min_val,
            "max_val": max_val,
            "is_float": is_float
        }
    
    def _on_range_slider_changed(self, value, slider_type, min_entry, max_entry, min_slider, max_slider, key, command, is_float, range_min, range_max):
        """當範圍滑塊改變時更新"""
        val = float(value) if is_float else int(round(value))
        
        if slider_type == "min":
            # 確保 min 不大於 max
            max_val = max_slider.get()
            if is_float:
                max_val = float(max_val)
            else:
                max_val = int(round(max_val))
            
            if val > max_val:
                val = max_val
                min_slider.set(val)
            
            # 更新輸入框
            min_entry.delete(0, "end")
            min_entry.insert(0, f"{val:.2f}" if is_float else f"{val}")
        else:  # max
            # 確保 max 不小於 min
            min_val = min_slider.get()
            if is_float:
                min_val = float(min_val)
            else:
                min_val = int(round(min_val))
            
            if val < min_val:
                val = min_val
                max_slider.set(val)
            
            # 更新輸入框
            max_entry.delete(0, "end")
            max_entry.insert(0, f"{val:.2f}" if is_float else f"{val}")
        
        # 調用回調
        min_v = min_slider.get()
        max_v = max_slider.get()
        if is_float:
            command(float(min_v), float(max_v))
        else:
            command(int(round(min_v)), int(round(max_v)))
    
    def _on_range_entry_changed(self, min_entry, max_entry, min_slider, max_slider, key, command, is_float, range_min, range_max):
        """當範圍輸入框改變時更新滑塊"""
        try:
            min_val = float(min_entry.get()) if is_float else int(float(min_entry.get()))
            max_val = float(max_entry.get()) if is_float else int(float(max_entry.get()))
            
            # 限制範圍
            min_val = max(range_min, min(min_val, range_max))
            max_val = max(range_min, min(max_val, range_max))
            
            # 確保 min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            
            # 更新滑塊
            min_slider.set(min_val)
            max_slider.set(max_val)
            
            # 更新輸入框顯示
            min_entry.delete(0, "end")
            min_entry.insert(0, f"{min_val:.2f}" if is_float else f"{min_val}")
            max_entry.delete(0, "end")
            max_entry.insert(0, f"{max_val:.2f}" if is_float else f"{max_val}")
            
            # 調用回調
            command(min_val, max_val)
        except ValueError:
            # 無效輸入，恢復到當前滑塊值
            min_val = min_slider.get()
            max_val = max_slider.get()
            if is_float:
                min_val, max_val = float(min_val), float(max_val)
            else:
                min_val, max_val = int(round(min_val)), int(round(max_val))
            
            min_entry.delete(0, "end")
            min_entry.insert(0, f"{min_val:.2f}" if is_float else f"{min_val}")
            max_entry.delete(0, "end")
            max_entry.insert(0, f"{max_val:.2f}" if is_float else f"{max_val}")

    def _on_slider_changed(self, value, entry_widget, key, command, is_float, slider, min_val, max_val):
        """當滑條改變時更新輸入框"""
        val = float(value) if is_float else int(round(value))
        # 限制範圍
        val = max(min_val, min(val, max_val))
        
        # 更新輸入框
        entry_widget.delete(0, "end")
        entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")
        
        # 調用原始 command
        command(val)

    def _on_entry_changed(self, entry_widget, slider, key, command, is_float, min_val, max_val):
        """當輸入框改變時更新滑條"""
        try:
            text = entry_widget.get()
            val = float(text) if is_float else int(float(text))
            
            # 限制範圍
            val = max(min_val, min(val, max_val))
            
            # 更新滑條
            slider.set(val)
            
            # 更新輸入框顯示（格式化）
            entry_widget.delete(0, "end")
            entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")
            
            # 調用原始 command
            command(val)
        except ValueError:
            # 如果輸入無效，恢復到滑條當前值
            current_val = slider.get()
            val = float(current_val) if is_float else int(round(current_val))
            entry_widget.delete(0, "end")
            entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")

    def _add_option_menu(self, values, command, parent=None):
        """創建獨立的 OptionMenu"""
        target_parent = parent if parent else self.content_frame
        return ctk.CTkOptionMenu(
            target_parent,
            values=values,
            command=command,
            fg_color=COLOR_SURFACE,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            corner_radius=0,
            height=28,
            width=180
        )

    def _add_option_row(self, label_text, values, command):
        """創建帶標籤的行內 OptionMenu"""
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        
        # Label
        ctk.CTkLabel(frame, text=label_text, font=FONT_MAIN, text_color=COLOR_TEXT).grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # OptionMenu (Parent is row frame)
        menu = self._add_option_menu(values, command, parent=frame)
        menu.grid(row=0, column=1, sticky="e")
        return menu

    def _add_text_button(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            font=("Roboto", 10, "bold"),
            text_color=COLOR_TEXT,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            height=28,
            corner_radius=0,
            command=command
        )

    # --- 邏輯功能 ---

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = self.winfo_pointerx() - self._x
        y = self.winfo_pointery() - self._y
        self.geometry(f"+{x}+{y}")

    def _register_slider(self, key, slider, entry, vmin, vmax, is_float):
        self._slider_widgets[key] = {"slider": slider, "entry": entry, "min": vmin, "max": vmax, "is_float": is_float}

    def _set_slider_value(self, key, value):
        if key not in self._slider_widgets: return
        w = self._slider_widgets[key]
        is_float = w["is_float"]
        try:
            v = float(value) if is_float else int(round(float(value)))
        except: return
        v = max(w["min"], min(v, w["max"]))
        w["slider"].set(v)
        # 更新輸入框而不是標籤
        w["entry"].delete(0, "end")
        w["entry"].insert(0, f"{v:.2f}" if is_float else f"{v}")

    def _set_checkbox_value(self, key, value_bool):
        var = self._checkbox_vars.get(key)
        if var: var.set(bool(value_bool))

    def _set_option_value(self, key, value_str):
        menu = self._option_widgets.get(key)
        if menu and value_str: menu.set(str(value_str))

    def _set_btn_option_value(self, key, value_str):
        self._set_option_value(key, value_str)

    def _get_current_settings(self):
        """獲取當前所有設置 - 直接使用 config.to_dict() 確保一致性"""
        return config.to_dict()

    def _load_initial_config(self):
        """初始化時載入配置並應用到所有 UI 元素"""
        try:
            # 配置已經在 config.py 的 __init__ 中自動載入了
            # 現在需要將配置同步到 tracker 和 UI
            self._sync_config_to_tracker()
            
            # 重新顯示當前頁面以更新 UI 元素
            # 這會確保所有 slider、checkbox、option menu 都顯示正確的值
            self._handle_nav_click("General", self._show_general_tab)
            
            print("[UI] Configuration loaded and applied to all UI elements")
            print(f"[UI] Loaded values - Aim: {config.enableaim}, TB: {config.enabletb}, Mode: {config.mode}, Color: {config.color}")
            print(f"[UI] Display settings - OpenCV: {config.show_opencv_windows}, Mode Text: {config.show_mode_text}")
        except Exception as e:
            print(f"[UI] Init load error: {e}")
    
    def _sync_config_to_tracker(self):
        """將 config 中的值同步到 tracker"""
        try:
            # 同步所有參數
            self.tracker.normal_x_speed = config.normal_x_speed
            self.tracker.normal_y_speed = config.normal_y_speed
            self.tracker.normalsmooth = config.normalsmooth
            self.tracker.normalsmoothfov = config.normalsmoothfov
            self.tracker.mouse_dpi = config.mouse_dpi
            self.tracker.fovsize = config.fovsize
            self.tracker.tbfovsize = config.tbfovsize
            self.tracker.tbdelay_min = config.tbdelay_min
            self.tracker.tbdelay_max = config.tbdelay_max
            self.tracker.tbhold_min = config.tbhold_min
            self.tracker.tbhold_max = config.tbhold_max
            self.tracker.tbcooldown_min = config.tbcooldown_min
            self.tracker.tbcooldown_max = config.tbcooldown_max
            self.tracker.tbburst_count_min = config.tbburst_count_min
            self.tracker.tbburst_count_max = config.tbburst_count_max
            self.tracker.tbburst_interval_min = config.tbburst_interval_min
            self.tracker.tbburst_interval_max = config.tbburst_interval_max
            self.tracker.rcs_pull_speed = config.rcs_pull_speed
            self.tracker.rcs_activation_delay = config.rcs_activation_delay
            self.tracker.rcs_rapid_click_threshold = config.rcs_rapid_click_threshold
            self.tracker.in_game_sens = config.in_game_sens
            self.tracker.color = config.color
            self.tracker.mode = config.mode
            
            # Sec Aimbot
            self.tracker.normal_x_speed_sec = config.normal_x_speed_sec
            self.tracker.normal_y_speed_sec = config.normal_y_speed_sec
            self.tracker.normalsmooth_sec = config.normalsmooth_sec
            self.tracker.normalsmoothfov_sec = config.normalsmoothfov_sec
            self.tracker.fovsize_sec = config.fovsize_sec
            self.tracker.selected_mouse_button_sec = config.selected_mouse_button_sec
            
            print("[UI] Config synced to tracker")
        except Exception as e:
            print(f"[UI] Sync error: {e}")

    def _apply_settings(self, data, config_name=None):
        try:
            for k, v in data.items():
                setattr(config, k, v)
                if hasattr(self.tracker, k):
                    setattr(self.tracker, k, v)
                
                if k in self._slider_widgets: 
                    self._set_slider_value(k, v)
                if k in self._checkbox_vars: 
                    self._set_checkbox_value(k, v)
                if k in self._option_widgets: 
                    if k in ["selected_mouse_button", "selected_tb_btn", "selected_mouse_button_sec"]:
                        self._set_btn_option_value(k, BUTTONS.get(v, str(v)))
                    else:
                        self._set_option_value(k, v)
                
                # 更新 OpenCV 顯示設置的 UI 變量
                if k == "show_opencv_windows" and hasattr(self, "show_opencv_var"):
                    self.show_opencv_var.set(v)
                elif k == "show_mode_text" and hasattr(self, "show_mode_var"):
                    self.show_mode_var.set(v)
                elif k == "show_aimbot_status" and hasattr(self, "show_aimbot_status_var"):
                    self.show_aimbot_status_var.set(v)
                elif k == "show_triggerbot_status" and hasattr(self, "show_triggerbot_status_var"):
                    self.show_triggerbot_status_var.set(v)
                elif k == "show_target_count" and hasattr(self, "show_target_count_var"):
                    self.show_target_count_var.set(v)
                elif k == "show_crosshair" and hasattr(self, "show_crosshair_var"):
                    self.show_crosshair_var.set(v)
                elif k == "show_distance_text" and hasattr(self, "show_distance_var"):
                    self.show_distance_var.set(v)

            from src.utils.detection import reload_model
            self.tracker.model, self.tracker.class_names = reload_model()
            
            msg = f"Loaded: {config_name}" if config_name else "Loaded config"
            print(f"[UI] {msg}")
            try:
                self._log_config(f"{msg}")
            except:
                pass
        except Exception as e:
            print(f"[UI] Apply error: {e}")
            try:
                self._log_config(f"Apply error: {e}")
            except:
                pass

    def _save_new_config(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Config name", "Enter the config name:")
        if not name: return
        self._do_save(name)

    def _save_config(self):
        name = self.config_option.get() or "default"
        self._do_save(name)

    def _do_save(self, name):
        data = self._get_current_settings()
        path = os.path.join("configs", f"{name}.json")
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            self._refresh_config_list()
            self.config_option.set(name)
            self._log_config(f"Saved: {name}")
        except Exception as e:
            self._log_config(f"Save error: {e}")

    def _load_selected_config(self):
        name = self.config_option.get()
        path = os.path.join("configs", f"{name}.json")
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._apply_settings(data, config_name=name)
        except Exception as e:
            self._log_config(f"Load error: {e}")

    def _refresh_config_list(self):
        files = [f[:-5] for f in os.listdir("configs") if f.endswith(".json")]
        if not files: files = ["default"]
        current = self.config_option.get()
        self.config_option.configure(values=files)
        if current in files:
            self.config_option.set(current)
        else:
            self.config_option.set(files[0])

    def _on_config_selected(self, val):
        self._log_config(f"Selected config: {val}")

    def _log_config(self, msg):
        try:
            self.config_log.insert("end", f"> {msg}\n")
            self.config_log.see("end")
        except: pass

    # --- NDI & Capture Callbacks ---
    
    def _on_capture_method_changed(self, val):
        self.capture_method_var.set(val)
        self.capture.set_mode(val)
        config.capture_mode = val  # 保存到 config
        self._update_capture_ui()
        self.status_indicator.configure(text=f"● Mode: {val}", text_color=COLOR_TEXT)

    def _process_source_updates(self):
        if self.capture.mode == "NDI":
            updates = self.capture.ndi.get_pending_source_updates()
            for names in updates:
                self._apply_sources_to_ui(names)
        self.after(100, self._process_source_updates)

    def _refresh_sources(self):
        if self.capture.mode == "NDI":
            names = self.capture.ndi.refresh_sources()
            self._apply_sources_to_ui(names)
            self.status_indicator.configure(text="● Refreshing...", text_color=COLOR_TEXT)

    def _connect_to_selected(self):
        if self.capture.mode == "NDI":
            sources = self.capture.ndi.get_source_list()
            if not sources: return
            
            selected = self.source_option.get()
            if selected and selected not in ["(no sources)", "(Scanning...)"]:
                self.capture.ndi.set_selected_source(selected)
                # 保存選中的 NDI 源
                self.saved_ndi_source = selected
                config.last_ndi_source = selected
            
            success, error = self.capture.connect_ndi(selected)
            if success:
                self.status_indicator.configure(text=f"● Connected: {selected}", text_color=COLOR_TEXT)
            else:
                self.status_indicator.configure(text=f"● Error: {error}", text_color=COLOR_DANGER)
                
    def _connect_udp(self):
        if self.capture.mode == "UDP":
            ip = self.udp_ip_entry.get()
            port = self.udp_port_entry.get()
            
            # 保存到內存和 config
            self.saved_udp_ip = ip
            self.saved_udp_port = port
            config.udp_ip = ip
            config.udp_port = port
            
            print(f"[UI] Connecting to UDP {ip}:{port}...")
            success, error = self.capture.connect_udp(ip, port)
            if success:
                self.status_indicator.configure(text=f"● Connected: UDP {ip}:{port}", text_color=COLOR_TEXT)
                print(f"[UI] UDP connection successful")
                
                # 檢查連接狀態
                import time
                time.sleep(0.5)  # 等待連接穩定
                is_connected = self.capture.is_connected()
                print(f"[UI] UDP is_connected check: {is_connected}")
            else:
                self.status_indicator.configure(text=f"● Connection failed: {error}", text_color=COLOR_DANGER)
                print(f"[UI] UDP connection failed: {error}")
    
    def _connect_capture_card(self):
        """連接 CaptureCard"""
        if self.capture.mode == "CaptureCard":
            # 確保配置已更新
            if hasattr(self, 'capture_card_device_entry'):
                try:
                    device_index = int(self.capture_card_device_entry.get())
                    config.capture_device_index = device_index
                except ValueError:
                    pass
            
            if hasattr(self, 'capture_card_width_entry') and hasattr(self, 'capture_card_height_entry'):
                try:
                    width = int(self.capture_card_width_entry.get())
                    height = int(self.capture_card_height_entry.get())
                    config.capture_width = width
                    config.capture_height = height
                    # 更新中心點顯示（因為分辨率改變可能影響中心點）
                    self._update_capture_card_center_display()
                except ValueError:
                    pass
            
            if hasattr(self, 'capture_card_fps_entry'):
                try:
                    fps = float(self.capture_card_fps_entry.get())
                    config.capture_fps = fps
                except ValueError:
                    pass
            
            # 更新中心點顯示
            self._update_capture_card_center_display()
            
            print(f"[UI] Connecting to CaptureCard...")
            success, error = self.capture.connect_capture_card(config)
            if success:
                self.status_indicator.configure(text="● Connected: CaptureCard", text_color=COLOR_TEXT)
                print(f"[UI] CaptureCard connection successful")
                
                # 檢查連接狀態
                import time
                time.sleep(0.5)  # 等待連接穩定
                is_connected = self.capture.is_connected()
                print(f"[UI] CaptureCard is_connected check: {is_connected}")
            else:
                self.status_indicator.configure(text=f"● Connection failed: {error}", text_color=COLOR_DANGER)
                print(f"[UI] CaptureCard connection failed: {error}")

    def _update_connection_status_loop(self):
        is_conn = self.capture.is_connected()
        current_mode = self.capture.mode
        
        if is_conn:
            self.status_indicator.configure(text=f"● Online ({current_mode})", text_color=COLOR_TEXT)
        else:
            self.status_indicator.configure(text="● Offline", text_color=COLOR_TEXT_DIM)
        self.after(500, self._update_connection_status_loop)

    def _update_performance_stats(self):
        """更新性能統計信息（FPS 和延遲）"""
        try:
            if self.capture.mode == "UDP" and self.capture.is_connected():
                # 從 UDP receiver 獲取性能統計
                receiver = self.capture.udp_manager.get_receiver()
                if receiver:
                    stats = receiver.get_performance_stats()
                    
                    # 更新 FPS
                    current_fps = stats.get('current_fps', 0)
                    self.fps_label.configure(text=f"FPS: {current_fps:.1f}")
                    
                    # 更新解碼延遲
                    decode_delay = stats.get('decode_delay_ms', 0)
                    self.decode_delay_label.configure(text=f"Decode: {decode_delay:.1f} ms")
                    
                    # 更新總延遲（接收 + 解碼 + 處理）
                    receive_delay = stats.get('receive_delay_ms', 0)
                    processing_delay = stats.get('processing_delay_ms', 0)
                    total_delay = receive_delay + decode_delay + processing_delay
                    self.total_delay_label.configure(text=f"Delay: {total_delay:.1f} ms")
            elif self.capture.mode == "NDI" and self.capture.is_connected():
                # NDI 模式：從 tracker 獲取簡單的 FPS 信息
                if hasattr(self.tracker, '_frame_count'):
                    # 計算 FPS（基於最近的幀計數）
                    self.fps_label.configure(text=f"FPS: ~{self.tracker._target_fps}")
                    self.decode_delay_label.configure(text="Decode: N/A")
                    self.total_delay_label.configure(text="Delay: N/A")
            else:
                # 未連接時顯示 --
                self.fps_label.configure(text="FPS: --")
                self.decode_delay_label.configure(text="Decode: -- ms")
                self.total_delay_label.configure(text="Delay: -- ms")
        except Exception as e:
            print(f"[UI] Performance stats update error: {e}")
        
        # 每 500ms 更新一次
        self.after(500, self._update_performance_stats)

    def _apply_sources_to_ui(self, names):
        # Only update if we are still on NDI mode and the widget exists
        if self.capture.mode == "NDI" and hasattr(self, 'source_option') and self.source_option.winfo_exists():
            if names:
                self.source_option.configure(values=names)
                
                # 嘗試恢復之前保存的選擇
                if self.saved_ndi_source and self.saved_ndi_source in names:
                    self.source_option.set(self.saved_ndi_source)
                elif self.source_option.get() not in names:
                    self.source_option.set(names[0])
            else:
                self.source_option.configure(values=["(no sources)"])
                self.source_option.set("(no sources)")

    def _on_source_selected(self, val):
        if val and val not in ["(no sources)", "(Scanning...)"]:
            if self.capture.mode == "NDI":
                self.capture.ndi.set_selected_source(val)

    def _open_settings_window(self):
        """打開設置視窗"""
        SettingsWindow(self)
    
    def _on_close(self):
        # 從 tracker 同步最新的設置到 config（確保所有運行時的變更都被保存）
        try:
            config.normal_x_speed = self.tracker.normal_x_speed
            config.normal_y_speed = self.tracker.normal_y_speed
            config.normalsmooth = self.tracker.normalsmooth
            config.normalsmoothfov = self.tracker.normalsmoothfov
            config.fovsize = self.tracker.fovsize
            config.tbfovsize = self.tracker.tbfovsize
            config.tbdelay = self.tracker.tbdelay
            config.in_game_sens = self.tracker.in_game_sens
            config.mouse_dpi = self.tracker.mouse_dpi
            
            # Sec Aimbot
            config.normal_x_speed_sec = self.tracker.normal_x_speed_sec
            config.normal_y_speed_sec = self.tracker.normal_y_speed_sec
            config.normalsmooth_sec = self.tracker.normalsmooth_sec
            config.normalsmoothfov_sec = self.tracker.normalsmoothfov_sec
            config.fovsize_sec = self.tracker.fovsize_sec
            config.selected_mouse_button_sec = self.tracker.selected_mouse_button_sec
            
            print("[UI] Settings synced from tracker to config before save")
        except Exception as e:
            print(f"[UI] Sync before save error: {e}")
        
        # 保存當前配置
        try:
            config.save_to_file()
            print("[UI] Configuration auto-saved on exit")
        except Exception as e:
            print(f"[UI] Failed to auto-save configuration: {e}")
        
        # 停止追蹤器
        try: 
            self.tracker.stop()
        except Exception as e:
            print(f"[UI] Tracker stop error: {e}")
        
        # 清理捕獲服務
        try: 
            self.capture.cleanup()
        except Exception as e:
            print(f"[UI] Capture cleanup error: {e}")
        
        # 銷毀窗口
        self.destroy()
        
        # 關閉所有 OpenCV 窗口
        try: 
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"[UI] CV2 cleanup error: {e}")

    # Callbacks proxies
    def _on_normal_x_speed_changed(self, val): 
        config.normal_x_speed = val
        self.tracker.normal_x_speed = val
        print(f"[Config] X-Speed: {val}")
    
    def _on_normal_y_speed_changed(self, val): 
        config.normal_y_speed = val
        self.tracker.normal_y_speed = val
        print(f"[Config] Y-Speed: {val}")
    
    def _on_config_in_game_sens_changed(self, val): 
        config.in_game_sens = val
        self.tracker.in_game_sens = val
        print(f"[Config] In-Game Sensitivity: {val}")
    
    def _on_config_normal_smooth_changed(self, val): 
        config.normalsmooth = val
        self.tracker.normalsmooth = val
        print(f"[Config] Smoothing: {val}")
    
    def _on_config_normal_smoothfov_changed(self, val): 
        config.normalsmoothfov = val
        self.tracker.normalsmoothfov = val
        print(f"[Config] FOV Smooth: {val}")
    
    def _on_fovsize_changed(self, val): 
        config.fovsize = val
        self.tracker.fovsize = val
        print(f"[Config] FOV Size: {val}")
    
    def _on_aim_offsetX_changed(self, val):
        config.aim_offsetX = val
        print(f"[Config] Aim X-Offset: {val}")
    
    def _on_aim_offsetY_changed(self, val):
        config.aim_offsetY = val
        print(f"[Config] Aim Y-Offset: {val}")
    
    def _on_aim_type_selected(self, val):
        config.aim_type = val
        print(f"[Config] Aim Type: {val}")
    
    def _on_tbdelay_range_changed(self, min_val, max_val):
        """Triggerbot Delay 範圍改變"""
        config.tbdelay_min = min_val
        config.tbdelay_max = max_val
        print(f"[Config] Triggerbot Delay Range: {min_val:.2f}s ~ {max_val:.2f}s")
    
    def _on_tbhold_range_changed(self, min_val, max_val):
        """Triggerbot Hold 範圍改變"""
        config.tbhold_min = min_val
        config.tbhold_max = max_val
        print(f"[Config] Triggerbot Hold Range: {min_val}ms ~ {max_val}ms")
    
    def _on_tbcooldown_range_changed(self, min_val, max_val):
        """Triggerbot Cooldown 範圍改變"""
        config.tbcooldown_min = min_val
        config.tbcooldown_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbcooldown_min = min_val
            self.tracker.tbcooldown_max = max_val
        print(f"[Config] Triggerbot Cooldown Range: {min_val:.2f}s ~ {max_val:.2f}s")
    
    def _on_tbburst_count_range_changed(self, min_val, max_val):
        """Triggerbot Burst Count 範圍改變"""
        config.tbburst_count_min = int(min_val)
        config.tbburst_count_max = int(max_val)
        if hasattr(self, 'tracker'):
            self.tracker.tbburst_count_min = int(min_val)
            self.tracker.tbburst_count_max = int(max_val)
        print(f"[Config] Triggerbot Burst Count Range: {int(min_val)} ~ {int(max_val)}")
    
    def _on_tbburst_interval_range_changed(self, min_val, max_val):
        """Triggerbot Burst Interval 範圍改變"""
        config.tbburst_interval_min = min_val
        config.tbburst_interval_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbburst_interval_min = min_val
            self.tracker.tbburst_interval_max = max_val
        print(f"[Config] Triggerbot Burst Interval Range: {min_val:.2f}ms ~ {max_val:.2f}ms")
    
    def _on_tbfovsize_changed(self, val): 
        config.tbfovsize = val
        self.tracker.tbfovsize = val
        print(f"[Config] Triggerbot FOV Size: {val}")
    
    def _on_tbhold_changed(self, val):
        config.tbhold = val
        self.tracker.tbhold = val
        print(f"[Config] Triggerbot Hold: {val}ms")
    
    def _on_enableaim_changed(self): 
        config.enableaim = self.var_enableaim.get()
        print(f"[Config] Aimbot Enabled: {config.enableaim}")
    
    def _on_anti_smoke_changed(self):
        """Main Aimbot Anti-Smoke 開關回調"""
        config.anti_smoke_enabled = self.var_anti_smoke.get()
        # 更新 tracker 中的 anti-smoke detector
        if hasattr(self.tracker, 'anti_smoke_detector'):
            self.tracker.anti_smoke_detector.set_enabled(config.anti_smoke_enabled)
        print(f"[Config] Main Aimbot Anti-Smoke: {config.anti_smoke_enabled}")
    
    def _on_enabletb_changed(self): 
        config.enabletb = self.var_enabletb.get()
        print(f"[Config] Triggerbot Enabled: {config.enabletb}")
    
    def _on_enablercs_changed(self):
        """RCS 開關改變"""
        config.enablercs = self.var_enablercs.get()
        print(f"[Config] RCS Enabled: {config.enablercs}")
    
    def _on_rcs_pull_speed_changed(self, val):
        """RCS Pull Speed 改變"""
        config.rcs_pull_speed = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_pull_speed = int(val)
        print(f"[Config] RCS Pull Speed: {int(val)}")
    
    def _on_rcs_activation_delay_changed(self, val):
        """RCS Activation Delay 改變"""
        config.rcs_activation_delay = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_activation_delay = int(val)
        print(f"[Config] RCS Activation Delay: {int(val)}ms")
    
    def _on_rcs_rapid_click_threshold_changed(self, val):
        """RCS Rapid Click Threshold 改變"""
        config.rcs_rapid_click_threshold = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_rapid_click_threshold = int(val)
        print(f"[Config] RCS Rapid Click Threshold: {int(val)}ms")
    
    def _on_color_selected(self, val): 
        config.color = val
        self.tracker.color = val
        print(f"[Config] Target Color: {val}")
    
    def _on_mode_selected(self, val): 
        config.mode = val
        self.tracker.mode = val
        print(f"[Config] Operation Mode: {val}")
    
    # Sec Aimbot Callbacks
    def _on_normal_x_speed_sec_changed(self, val): 
        config.normal_x_speed_sec = val
        self.tracker.normal_x_speed_sec = val
        print(f"[Config] Sec X-Speed: {val}")
    
    def _on_normal_y_speed_sec_changed(self, val): 
        config.normal_y_speed_sec = val
        self.tracker.normal_y_speed_sec = val
        print(f"[Config] Sec Y-Speed: {val}")
    
    def _on_config_normal_smooth_sec_changed(self, val): 
        config.normalsmooth_sec = val
        self.tracker.normalsmooth_sec = val
        print(f"[Config] Sec Smoothing: {val}")
    
    def _on_config_normal_smoothfov_sec_changed(self, val): 
        config.normalsmoothfov_sec = val
        self.tracker.normalsmoothfov_sec = val
        print(f"[Config] Sec FOV Smooth: {val}")
    
    def _on_fovsize_sec_changed(self, val): 
        config.fovsize_sec = val
        self.tracker.fovsize_sec = val
        print(f"[Config] Sec FOV Size: {val}")
    
    def _on_aim_offsetX_sec_changed(self, val):
        config.aim_offsetX_sec = val
        print(f"[Config] Sec Aim X-Offset: {val}")
    
    def _on_aim_offsetY_sec_changed(self, val):
        config.aim_offsetY_sec = val
        print(f"[Config] Sec Aim Y-Offset: {val}")
    
    def _on_aim_type_sec_selected(self, val):
        config.aim_type_sec = val
        print(f"[Config] Sec Aim Type: {val}")
    
    def _on_enableaim_sec_changed(self): 
        config.enableaim_sec = self.var_enableaim_sec.get()
        print(f"[Config] Sec Aimbot Enabled: {config.enableaim_sec}")
    
    def _on_anti_smoke_sec_changed(self):
        """Secondary Aimbot Anti-Smoke 開關回調"""
        config.anti_smoke_enabled_sec = self.var_anti_smoke_sec.get()
        # 更新 tracker 中的 sec anti-smoke detector
        if hasattr(self.tracker, 'anti_smoke_detector_sec'):
            self.tracker.anti_smoke_detector_sec.set_enabled(config.anti_smoke_enabled_sec)
        print(f"[Config] Sec Aimbot Anti-Smoke: {config.anti_smoke_enabled_sec}")
    
    def _on_aimbot_button_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_mouse_button = k
                self._log_config(f"Aim Key: {val}")
                break

    def _on_tb_button_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_tb_btn = k
                self._log_config(f"Trigger Key: {val}")
                break
    
    # Mouse Input Debug Callbacks
    def _on_debug_mouse_input_changed(self):
        """滑鼠輸入調試開關改變"""
        enabled = self.debug_mouse_input_var.get()
        if enabled:
            self.mouse_input_monitor.enable()
            # Show debug area
            if hasattr(self, 'debug_mouse_frame'):
                try:
                    self.debug_mouse_frame.pack(fill="x", pady=10)
                except Exception:
                    pass
        else:
            self.mouse_input_monitor.disable()
            # Hide debug area
            if hasattr(self, 'debug_mouse_frame'):
                try:
                    self.debug_mouse_frame.pack_forget()
                except Exception:
                    pass
        print(f"[Debug] Mouse Input Debug: {enabled}")
    
    def _update_mouse_input_debug(self):
        """定期更新滑鼠輸入調試顯示"""
        # Only update if we're on the Debug tab and the switch is enabled
        try:
            if hasattr(self, 'debug_mouse_input_var') and self.debug_mouse_input_var.get():
                if hasattr(self, 'debug_button_widgets') and self.debug_button_widgets:
                    # Update monitor
                    self.mouse_input_monitor.update()
                    
                    # Update UI display
                    for idx, widgets in self.debug_button_widgets.items():
                        try:
                            state = self.mouse_input_monitor.get_button_state(idx)
                            count = self.mouse_input_monitor.get_button_count(idx)
                            
                            # Update status indicator color (green=pressed, red=not pressed)
                            color = "#4CAF50" if state else "#CF6679"  # Green or red
                            widgets["state_indicator"].configure(text_color=color)
                            
                            # Update count
                            widgets["count_label"].configure(text=f"Count: {count}")
                        except Exception:
                            # Widget might be destroyed, skip this update
                            pass
        except Exception:
            # Tab might have been switched, ignore
            pass
        
        # Continue periodic update (every 50ms)
        self.after(50, self._update_mouse_input_debug)
    
    def _reset_button_count(self, button_idx: int):
        """重置單個按鈕的計數"""
        if hasattr(self.mouse_input_monitor, 'button_counts'):
            self.mouse_input_monitor.button_counts[button_idx] = 0
        if hasattr(self, 'debug_button_widgets') and button_idx in self.debug_button_widgets:
            try:
                self.debug_button_widgets[button_idx]["count_label"].configure(text="Count: 0")
            except Exception:
                pass
        print(f"[Debug] Reset button {button_idx} count")
    
    def _reset_all_button_counts(self):
        """重置所有按鈕的計數"""
        self.mouse_input_monitor.reset_counts()
        if hasattr(self, 'debug_button_widgets'):
            for idx, widgets in self.debug_button_widgets.items():
                try:
                    widgets["count_label"].configure(text="Count: 0")
                except Exception:
                    pass
        print("[Debug] Reset all button counts")
    
    def _update_debug_log(self):
        """定期更新 Debug 日誌顯示"""
        try:
            if hasattr(self, 'debug_log_textbox'):
                try:
                    # Get recent logs (up to 500)
                    logs = get_recent_logs(500)
                    log_count = get_log_count()
                    
                    # Update log count
                    if hasattr(self, 'debug_log_count_label'):
                        try:
                            self.debug_log_count_label.configure(text=f"Log Count: {log_count}")
                        except Exception:
                            pass
                    
                    # Format log text
                    import datetime
                    log_text = ""
                    for log in logs:
                        timestamp = datetime.datetime.fromtimestamp(log["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
                        log_type = log["type"]
                        source = log.get("source", "Unknown")
                        
                        if log_type == "MOVE":
                            dx = log.get("dx", 0)
                            dy = log.get("dy", 0)
                            log_text += f"[{timestamp}] {log_type:8s} [{source:15s}] dx={dx:8.2f}, dy={dy:8.2f}\n"
                        else:
                            log_text += f"[{timestamp}] {log_type:8s} [{source:15s}]\n"
                    
                    # Update text box (only when content changes to avoid frequent refresh)
                    try:
                        current_text = self.debug_log_textbox.get("1.0", "end-1c")
                        if current_text != log_text:
                            self.debug_log_textbox.delete("1.0", "end")
                            self.debug_log_textbox.insert("1.0", log_text)
                            # Auto scroll to bottom
                            self.debug_log_textbox.see("end")
                    except Exception:
                        # Widget might be destroyed
                        pass
                except Exception as e:
                    # Ignore errors during tab switch
                    pass
        except Exception:
            # Tab might have been switched
            pass
        
        # Continue periodic update (every 100ms)
        self.after(100, self._update_debug_log)
    
    def _clear_debug_log(self):
        """清空 Debug 日誌"""
        clear_logs()
        if hasattr(self, 'debug_log_textbox'):
            try:
                self.debug_log_textbox.delete("1.0", "end")
            except Exception:
                pass
        if hasattr(self, 'debug_log_count_label'):
            try:
                self.debug_log_count_label.configure(text="Log Count: 0")
            except Exception:
                pass
        print("[Debug] Logs cleared")
    
    def _on_aimbot_button_sec_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_mouse_button_sec = k
                self.tracker.selected_mouse_button_sec = k
                print(f"[Config] Sec Aim Key: {val}")
                break
    
    def _on_button_mask_enabled_changed(self):
        """Button Mask 總開關回調"""
        config.button_mask_enabled = self.var_button_mask_enabled.get()
        print(f"[Config] Button Mask Enabled: {config.button_mask_enabled}")
    
    def _on_button_mask_changed(self, key, var):
        """單個按鈕 Mask 狀態改變回調"""
        value = var.get()
        setattr(config, key, value)
        button_names = {
            "mask_left_button": "Left (L)",
            "mask_right_button": "Right (R)",
            "mask_middle_button": "Middle (M)",
            "mask_side4_button": "Side 4 (S4)",
            "mask_side5_button": "Side 5 (S5)"
        }
        print(f"[Config] Button Mask - {button_names.get(key, key)}: {value}")


class SettingsWindow(ctk.CTkToplevel):
    """OpenCV 顯示設置視窗"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("display settings")
        self.geometry("400x600")
        self.resizable(False, False)
        
        # 置中顯示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.geometry(f"+{x}+{y}")
        
        # 設置為模態視窗
        self.transient(parent)
        self.grab_set()
        
        # 臨時儲存設置（用於取消）
        self.temp_settings = {
            "show_opencv_windows": getattr(config, "show_opencv_windows", True),
            "show_opencv_mask": getattr(config, "show_opencv_mask", True),
            "show_opencv_detection": getattr(config, "show_opencv_detection", True),
            "show_opencv_roi": getattr(config, "show_opencv_roi", True),
            "show_opencv_triggerbot_mask": getattr(config, "show_opencv_triggerbot_mask", True),
            "show_mode_text": getattr(config, "show_mode_text", True),
            "show_aimbot_status": getattr(config, "show_aimbot_status", True),
            "show_triggerbot_status": getattr(config, "show_triggerbot_status", True),
            "show_target_count": getattr(config, "show_target_count", True),
            "show_crosshair": getattr(config, "show_crosshair", True),
            "show_distance_text": getattr(config, "show_distance_text", True)
        }
        
        self._build_ui()
    
    def _build_ui(self):
        """構建 UI"""
        # 主容器 - 使用深色背景，填滿整個視窗
        main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 內部容器 (用於內容邊距)
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 標題
        title_label = ctk.CTkLabel(
            content_frame,
            text="DISPLAY SETTINGS",
            font=("Roboto", 16, "bold"),
            text_color=COLOR_TEXT
        )
        title_label.pack(pady=(0, 20), anchor="w")
        
        # 分組1: 全局顯示設置
        self._add_section_title(content_frame, "VISUAL SETTINGS")
        
        # OpenCV 視窗總開關 (Switch)
        self.show_opencv_var = tk.BooleanVar(value=self.temp_settings["show_opencv_windows"])
        self._add_switch(content_frame, "Show OpenCV Windows", self.show_opencv_var)

        # 分隔
        self._add_spacer(content_frame)
        
        # 分組1.5: OpenCV 視窗詳細設置
        self._add_section_title(content_frame, "OPENCV WINDOWS")
        
        # 使用 Grid 佈局來排列 OpenCV 視窗開關
        opencv_grid_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        opencv_grid_frame.pack(fill="x", pady=5)
        opencv_grid_frame.grid_columnconfigure(0, weight=1)
        opencv_grid_frame.grid_columnconfigure(1, weight=1)
        
        # 各項 OpenCV 視窗開關
        self.show_opencv_mask_var = tk.BooleanVar(value=self.temp_settings["show_opencv_mask"])
        self._add_grid_switch(opencv_grid_frame, "MASK", self.show_opencv_mask_var, 0, 0)
        
        self.show_opencv_detection_var = tk.BooleanVar(value=self.temp_settings["show_opencv_detection"])
        self._add_grid_switch(opencv_grid_frame, "Detection", self.show_opencv_detection_var, 0, 1)
        
        self.show_opencv_roi_var = tk.BooleanVar(value=self.temp_settings["show_opencv_roi"])
        self._add_grid_switch(opencv_grid_frame, "ROI", self.show_opencv_roi_var, 1, 0)
        
        self.show_opencv_triggerbot_mask_var = tk.BooleanVar(value=self.temp_settings["show_opencv_triggerbot_mask"])
        self._add_grid_switch(opencv_grid_frame, "Triggerbot Mask", self.show_opencv_triggerbot_mask_var, 1, 1)

        # 分隔
        self._add_spacer(content_frame)
        
        # 分組2: 文字資訊 (Overlay Elements)
        self._add_section_title(content_frame, "OVERLAY ELEMENTS")
        
        # 使用 Grid 佈局來排列開關，使其更整齊
        grid_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        # 各項開關 (Switch instead of Checkbox for better look)
        self.show_mode_var = tk.BooleanVar(value=self.temp_settings["show_mode_text"])
        self._add_grid_switch(grid_frame, "Mode Info", self.show_mode_var, 0, 0)
        
        self.show_aimbot_status_var = tk.BooleanVar(value=self.temp_settings["show_aimbot_status"])
        self._add_grid_switch(grid_frame, "Aim Status", self.show_aimbot_status_var, 0, 1)
        
        self.show_triggerbot_status_var = tk.BooleanVar(value=self.temp_settings["show_triggerbot_status"])
        self._add_grid_switch(grid_frame, "Trigger Status", self.show_triggerbot_status_var, 1, 0)
        
        self.show_target_count_var = tk.BooleanVar(value=self.temp_settings["show_target_count"])
        self._add_grid_switch(grid_frame, "Target Count", self.show_target_count_var, 1, 1)
        
        self.show_crosshair_var = tk.BooleanVar(value=self.temp_settings["show_crosshair"])
        self._add_grid_switch(grid_frame, "Crosshair", self.show_crosshair_var, 2, 0)
        
        self.show_distance_var = tk.BooleanVar(value=self.temp_settings["show_distance_text"])
        self._add_grid_switch(grid_frame, "Distance Text", self.show_distance_var, 2, 1)
        
        # 底部按鈕區域
        # 使用 Spacer 推到底部
        ctk.CTkFrame(content_frame, fg_color="transparent").pack(fill="both", expand=True)
        
        # 分隔線
        ctk.CTkFrame(content_frame, height=1, fg_color=COLOR_BORDER).pack(fill="x", pady=(0, 15))
        
        # 按鈕容器
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 5))
        
        # 取消按鈕 (Outlined)
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="CANCEL",
            command=self._on_cancel,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 11, "bold"),
            height=35
        )
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        # 保存按鈕 (Filled)
        save_btn = ctk.CTkButton(
            button_frame,
            text="SAVE",
            command=self._on_save,
            fg_color=COLOR_TEXT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BG,
            font=("Roboto", 11, "bold"),
            height=35
        )
        save_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

    def _add_section_title(self, parent, text):
        ctk.CTkLabel(
            parent, 
            text=text, 
            font=("Roboto", 10, "bold"), 
            text_color=COLOR_TEXT_DIM
        ).pack(anchor="w", pady=(10, 5))

    def _add_spacer(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", pady=10)

    def _add_switch(self, parent, text, variable):
        switch = ctk.CTkSwitch(
            parent,
            text=text,
            variable=variable,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=("Roboto", 12)
        )
        switch.pack(anchor="w", pady=5)

    def _add_grid_switch(self, parent, text, variable, row, col):
        switch = ctk.CTkSwitch(
            parent,
            text=text,
            variable=variable,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=("Roboto", 12)
        )
        switch.grid(row=row, column=col, sticky="w", pady=8, padx=5)
    
    def _on_save(self):
        """保存設置"""
        # 更新配置
        config.show_opencv_windows = self.show_opencv_var.get()
        config.show_opencv_mask = self.show_opencv_mask_var.get()
        config.show_opencv_detection = self.show_opencv_detection_var.get()
        config.show_opencv_roi = self.show_opencv_roi_var.get()
        config.show_opencv_triggerbot_mask = self.show_opencv_triggerbot_mask_var.get()
        config.show_mode_text = self.show_mode_var.get()
        config.show_aimbot_status = self.show_aimbot_status_var.get()
        config.show_triggerbot_status = self.show_triggerbot_status_var.get()
        config.show_target_count = self.show_target_count_var.get()
        config.show_crosshair = self.show_crosshair_var.get()
        config.show_distance_text = self.show_distance_var.get()
        
        # 保存到文件
        config.save_to_file()
        
        # 打印確認
        print(f"[Settings] OpenCV Windows: {config.show_opencv_windows}")
        print(f"[Settings] OpenCV Windows Detail - MASK:{config.show_opencv_mask} Detection:{config.show_opencv_detection} ROI:{config.show_opencv_roi} TB Mask:{config.show_opencv_triggerbot_mask}")
        print(f"[Settings] Text Info - Mode:{config.show_mode_text} Aim:{config.show_aimbot_status} TB:{config.show_triggerbot_status}")
        print(f"[Settings] Text Info - Targets:{config.show_target_count} Cross:{config.show_crosshair} Dist:{config.show_distance_text}")
        
        # 關閉視窗
        self.destroy()
    
    def _on_cancel(self):
        """取消並關閉 - 不保存任何更改，恢復原始設置"""
        # 恢復所有設置到臨時保存的值（不更新 config）
        # 這樣可以確保如果用戶再次打開設置視窗，會看到原始值
        print("[Settings] Cancelled - no changes saved, restoring original settings")
        self.destroy()
