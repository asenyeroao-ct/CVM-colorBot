"""
UI 模組 - Ultra Minimalist 風格
處理主視窗、分頁內容與設定互動 (GUI layer)
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import ctypes
from ctypes import wintypes
import os
import json
import cv2
import threading
import time
import webbrowser
from PIL import Image
from functools import partial

from src.utils.config import config
from src.capture.capture_service import CaptureService
from src.utils.mouse_input import MouseInputMonitor
from src.utils.debug_logger import get_recent_logs, clear_logs, get_log_count, log_print
from src.utils.updater import get_update_checker
from src.ui_hsv_preview import HsvPreviewWindow

# --- Theme constants (繁中 + English) ---
COLOR_BG = "#121212"          # 主背景色 Main background
COLOR_SIDEBAR = "#121212"     # 側欄背景 Sidebar background
COLOR_SURFACE = "#1E1E1E"     # 卡片/面板色 Surface color
COLOR_ACCENT = "#FFFFFF"      # 強調色 Accent color
COLOR_ACCENT_HOVER = "#E0E0E0"
COLOR_TEXT = "#E0E0E0"        # 主文字 Text
COLOR_TEXT_DIM = "#757575"    # 次要文字 Secondary text
COLOR_BORDER = "#2C2C2C"      # 邊框色 Border
COLOR_DANGER = "#CF6679"      # 危險色 Danger
COLOR_SUCCESS = "#4CAF50"

FONT_MAIN = ("Roboto", 11)
FONT_BOLD = ("Roboto", 11, "bold")
FONT_TITLE = ("Roboto", 18, "bold")

CVM_CONFIG_COMMENT_KEY = "_comment"
CVM_CONFIG_COMMENT_VALUE = "This is CVM colorBot config."
CF_HDROP = 15
DRAG_QUERY_FILE_COUNT = 0xFFFFFFFF
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT


class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


if os.name == "nt":
    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    USER32 = ctypes.WinDLL("user32", use_last_error=True)
    SHELL32 = ctypes.WinDLL("shell32", use_last_error=True)

    KERNEL32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    KERNEL32.GlobalAlloc.restype = wintypes.HANDLE
    KERNEL32.GlobalLock.argtypes = [wintypes.HANDLE]
    KERNEL32.GlobalLock.restype = wintypes.LPVOID
    KERNEL32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    KERNEL32.GlobalUnlock.restype = wintypes.BOOL
    KERNEL32.GlobalFree.argtypes = [wintypes.HANDLE]
    KERNEL32.GlobalFree.restype = wintypes.HANDLE

    USER32.OpenClipboard.argtypes = [wintypes.HWND]
    USER32.OpenClipboard.restype = wintypes.BOOL
    USER32.EmptyClipboard.argtypes = []
    USER32.EmptyClipboard.restype = wintypes.BOOL
    USER32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    USER32.SetClipboardData.restype = wintypes.HANDLE
    USER32.GetClipboardData.argtypes = [wintypes.UINT]
    USER32.GetClipboardData.restype = wintypes.HANDLE
    USER32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    USER32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    USER32.CloseClipboard.argtypes = []
    USER32.CloseClipboard.restype = wintypes.BOOL

    SHELL32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    SHELL32.DragQueryFileW.restype = wintypes.UINT
else:
    KERNEL32 = None
    USER32 = None
    SHELL32 = None

BUTTONS = {
    0: 'Left Mouse Button',
    1: 'Right Mouse Button',
    2: 'Middle Mouse Button',
    3: 'Side Mouse 4 Button',
    4: 'Side Mouse 5 Button'
}
BUTTON_NAME_TO_IDX = {name: idx for idx, name in BUTTONS.items()}

ADS_KEY_DISPLAY_TO_BINDING = {
    "Right Mouse Button": "Right Mouse Button",
    "Left Mouse Button": "Left Mouse Button",
    "Middle Mouse Button": "Middle Mouse Button",
    "Side Mouse 4 Button": "Side Mouse 4 Button",
    "Side Mouse 5 Button": "Side Mouse 5 Button",
    "Left Shift": "LSHIFT",
    "Right Shift": "RSHIFT",
    "Left Ctrl": "LCONTROL",
    "Right Ctrl": "RCONTROL",
    "Left Alt": "LMENU",
    "Right Alt": "RMENU",
    "Space": "SPACE",
    "E": "E",
    "Q": "Q",
    "F": "F",
    "R": "R",
    "C": "C",
    "V": "V",
    "X": "X",
    "Z": "Z",
    "W": "W",
    "A": "A",
    "S": "S",
    "D": "D",
}

ADS_KEY_BINDING_TO_DISPLAY = {
    str(binding).upper(): display for display, binding in ADS_KEY_DISPLAY_TO_BINDING.items()
}

BIND_CAPTURE_KEY_TOKENS = (
    ["SPACE", "TAB", "ENTER", "ESCAPE", "LSHIFT", "RSHIFT", "LCONTROL", "RCONTROL", "LMENU", "RMENU", "UP", "DOWN", "LEFT", "RIGHT"]
    + [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    + [str(num) for num in range(10)]
    + [f"F{i}" for i in range(1, 13)]
)

ADS_KEY_TYPE_DISPLAY_TO_VALUE = {
    "Hold": "hold",
    "Toggle": "toggle",
}

ADS_KEY_TYPE_VALUE_TO_DISPLAY = {
    str(value).lower(): display for display, value in ADS_KEY_TYPE_DISPLAY_TO_VALUE.items()
}

TRIGGER_TYPE_DISPLAY = {
    "current": "Classic Trigger",
    "rgb": "RGB Trigger",
}

RGB_TRIGGER_PROFILE_DISPLAY = {
    "red": "Red",
    "yellow": "Yellow",
    "purple": "Purple",
    "custom": "Custom",
}

TRIGGER_STRAFE_MODE_DISPLAY = {
    "off": "Off",
    "auto": "Auto Strafe",
    "manual_wait": "Manual Wait",
}

class ViewerApp(ctk.CTk):
    """主應用程式 UI (Ultra Minimalist)。"""
    
    def __init__(self, tracker, capture_service):
        super().__init__()
        
        # --- Window setup ---
        self.title("CVM colorBot")
        self.geometry("1280x950")
        
        # 注意: 若啟用 overrideredirect(True)，系統框線與 taskbar 行為可能不同
        # If you need normal window decorations, keep it commented out.
        # self.overrideredirect(True)
        
        self.configure(fg_color=COLOR_BG)
        
        # 預設不置頂，避免影響其他 app/focus
        self.attributes('-topmost', False)
        
        # --- Core services ---
        self.tracker = tracker
        self.capture = capture_service
        
        # --- Mouse input monitor ---
        self.mouse_input_monitor = MouseInputMonitor()
        
        # --- Update Checker ---
        self.update_checker = get_update_checker()
        self._update_check_in_progress = False
        
        # --- Debug tab state (init once to preserve tab-switch state) ---
        self.debug_mouse_input_var = tk.BooleanVar(value=False)
        
        # --- UI runtime state ---
        self._slider_widgets = {}
        self._checkbox_vars = {}
        self._option_widgets = {}
        self._active_tab_name = "General"
        self._clipboard_import_poll_interval_ms = 1200
        self._clipboard_import_last_declined_signature = None
        self._clipboard_import_last_declined_config_fingerprint = None
        self._clipboard_import_imported_signatures = set()
        self._clipboard_import_prompt_open = False
        raw_section_states = getattr(config, "ui_collapsible_states", {})
        self._collapsible_section_states = (
            dict(raw_section_states) if isinstance(raw_section_states, dict) else {}
        )
        self.current_frame = None
        
        # 啟動時使用 config.capture_mode
        init_mode = getattr(config, "capture_mode", "NDI")
        self.capture.set_mode(init_mode)
        self.capture_method_var = tk.StringVar(value=init_mode)
        
        # --- Capture control cache (restore from config) ---
        self.saved_udp_ip = getattr(config, "udp_ip", "127.0.0.1")
        self.saved_udp_port = getattr(config, "udp_port", "1234")
        self.saved_ndi_source = getattr(config, "last_ndi_source", None)
        self.saved_mouse_api = getattr(config, "mouse_api", "Serial")
        self.saved_net_ip = getattr(config, "net_ip", "192.168.2.188")
        self.saved_net_port = getattr(config, "net_port", "6234")
        self.saved_net_uuid = getattr(config, "net_uuid", getattr(config, "net_mac", ""))
        self.saved_kmboxa_vid_pid = str(
            getattr(config, "kmboxa_vid_pid", f"{getattr(config, 'kmboxa_vid', 0)}/{getattr(config, 'kmboxa_pid', 0)}")
        )
        self.saved_serial_port_mode = str(getattr(config, "serial_port_mode", "Auto"))
        self.saved_serial_port = str(getattr(config, "serial_port", ""))
        self.saved_serial_auto_switch_4m = bool(getattr(config, "serial_auto_switch_4m", False))
        self.saved_arduino_port = str(getattr(config, "arduino_port", ""))
        self.saved_arduino_baud = str(getattr(config, "arduino_baud", 115200))
        self.saved_makv2_port = getattr(config, "makv2_port", "")
        self.saved_makv2_baud = str(getattr(config, "makv2_baud", 4000000))
        self.saved_dhz_ip = getattr(config, "dhz_ip", "192.168.2.188")
        self.saved_dhz_port = str(getattr(config, "dhz_port", "5000"))
        self.saved_dhz_random = str(getattr(config, "dhz_random", 0))
        self.saved_auto_connect_mouse_api = bool(getattr(config, "auto_connect_mouse_api", False))
        self._mouse_api_connecting = False
        self._mouse_api_connect_job_id = 0
        self._mouse_api_connect_timeout_ms = 12000
        self._serial_baud_switching = False
        
        # --- Build layout ---
        self._build_layout()
        
        # --- Periodic jobs ---
        self.after(100, self._process_source_updates)
        self.after(500, self._update_connection_status_loop)
        self.after(200, self._load_initial_config)
        self.after(self._clipboard_import_poll_interval_ms, self._poll_clipboard_config_import)
        self.after(300, self._update_performance_stats)  # 更新效能統計 Performance stats
        self.after(50, self._update_mouse_input_debug)  # 更新滑鼠輸入監控 Mouse input debug
        self.after(100, self._update_debug_log)  # 更新 Debug log

    def _build_layout(self):
        """建立主版面：title bar + sidebar + content area。"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 標題列 Title bar
        self._build_title_bar()
        
        # 側欄導覽 Sidebar
        self._build_sidebar()
        
        # 內容區 Content frame
        self.content_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLOR_BORDER,
            scrollbar_button_hover_color=COLOR_SURFACE
        )
        self.content_frame.grid(row=1, column=1, sticky="nsew", padx=24, pady=20)
        
        self._show_general_tab()

    def _build_title_bar(self):
        """建立標題列 (title bar)。"""
        self.title_bar = ctk.CTkFrame(self, height=30, fg_color=COLOR_BG, corner_radius=0)
        self.title_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Title and version
        title_container = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        title_container.pack(side="left", padx=20)
        
        # Logo icon
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cvm.jpg")
        self.logo_lbl = None
        if os.path.exists(logo_path):
            try:
                logo_image = Image.open(logo_path)
                # 調整 logo 尺寸為 20x20
                logo_image = logo_image.resize((20, 20), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(20, 20))
                self.logo_lbl = ctk.CTkLabel(
                    title_container,
                    image=logo_ctk,
                    text=""
                )
                self.logo_lbl.pack(side="left", padx=(0, 10))
            except Exception as e:
                log_print(f"[UI] Failed to load logo: {e}")
        
        title_lbl = ctk.CTkLabel(
            title_container, 
            text="CVM colorBot", 
            font=("Roboto", 10, "bold"),
            text_color=COLOR_TEXT_DIM
        )
        title_lbl.pack(side="left")
        
        # Version label
        current_version = self.update_checker.get_current_version()
        self.version_lbl = ctk.CTkLabel(
            title_container,
            text=f"v{current_version}",
            font=("Roboto", 9),
            text_color=COLOR_TEXT_DIM
        )
        self.version_lbl.pack(side="left", padx=(10, 0))
        
        # Update button (only show if update available)
        self.update_btn = None
        
        # 關閉按鈕 Close button
        close_btn = ctk.CTkButton(
            self.title_bar, 
            text="X",
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
        
        # 視窗拖曳事件 Drag behavior
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        title_lbl.bind("<Button-1>", self.start_move)
        title_lbl.bind("<B1-Motion>", self.do_move)
        if self.logo_lbl:
            self.logo_lbl.bind("<Button-1>", self.start_move)
            self.logo_lbl.bind("<B1-Motion>", self.do_move)

    def _build_sidebar(self):
        """建立側邊欄：navigation + status widgets。"""
        self.sidebar = ctk.CTkFrame(self, width=165, fg_color=COLOR_BG, corner_radius=0)
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        
        # 分隔線 Separator
        sep = ctk.CTkFrame(self.sidebar, width=1, fg_color=COLOR_BORDER)
        sep.pack(side="right", fill="y")

        # 導覽容器 Navigation container
        nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_container.pack(fill="x", padx=20, pady=20)
        
        self.nav_buttons = {}
        tabs = [
            ("General", self._show_general_tab),
            ("Main Aimbot", self._show_aimbot_tab),
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
            
        # 側欄底部區塊 Bottom section
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        # 主題切換 Theme toggle
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
        
        # 效能資訊 Performance labels
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
        
        # 狀態指示器 Status indicator
        self.status_indicator = ctk.CTkLabel(
            bottom_frame,
            text="Status: Offline",
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 10),
            anchor="w",
            height=18,
        )
        self.status_indicator.pack(fill="x")

        self.hardware_type_label = ctk.CTkLabel(
            bottom_frame,
            text=f"Hardware: {getattr(config, 'mouse_api', 'Serial')}",
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 10),
            anchor="w",
        )
        self.hardware_type_label.pack(fill="x", pady=(4, 0))

        self.hardware_conn_label = ctk.CTkLabel(
            bottom_frame,
            text="Hardware Status: Disconnected",
            text_color=COLOR_DANGER,
            font=("Roboto", 10),
            anchor="w",
        )
        self.hardware_conn_label.pack(fill="x")

        self._hardware_info_expanded = False
        self.hardware_details_toggle = ctk.CTkButton(
            bottom_frame,
            text="Hardware Info",
            command=self._toggle_hardware_info_details,
            fg_color="transparent",
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 9),
            anchor="w",
            height=22,
        )
        self.hardware_details_toggle.pack(fill="x", pady=(2, 0))

        self.hardware_details_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            text_color=COLOR_TEXT_DIM,
            font=("Roboto", 9),
            anchor="w",
            justify="left",
        )
        self._update_hardware_status_ui()
        
        # 設定按鈕 Settings button
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="Settings",
            command=self._open_settings_window,
            fg_color="transparent",
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=("Roboto", 11),
            anchor="w",
            height=30
        )
        settings_btn.pack(fill="x", pady=(10, 0))

    def _set_status_indicator(self, text, text_color=COLOR_TEXT_DIM):
        if not hasattr(self, "status_indicator") or not self.status_indicator.winfo_exists():
            return
        msg = str(text).replace("\n", " ").strip()
        max_chars = 30
        if len(msg) > max_chars:
            msg = msg[: max_chars - 3] + "..."
        self.status_indicator.configure(text=msg, text_color=text_color)

    def _create_nav_btn(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            height=35,
            fg_color="transparent",
            text_color=COLOR_TEXT_DIM,
            hover_color=None, # 保持透明背景，不做 hover fill
            anchor="w",
            font=FONT_BOLD,
            command=lambda: self._handle_nav_click(text, command)
        )

    def _handle_nav_click(self, text, command):
        self._active_tab_name = str(text)
        for btn_text, btn in self.nav_buttons.items():
            if btn_text == text:
                btn.configure(text_color=COLOR_ACCENT)  # 當前 tab 只高亮文字
            else:
                btn.configure(text_color=COLOR_TEXT_DIM)
        command()

    def _clear_content(self):
        self._cancel_binding_capture()
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        # Clear widget maps to avoid stale destroyed references during config apply.
        self._option_widgets = {}
        self._slider_widgets = {}
        if hasattr(self, "_range_slider_widgets"):
            self._range_slider_widgets = {}

    def _toggle_theme(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="Light Mode")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="Dark Mode")

    # --- 各分頁內容 Tabs ---

    def _show_general_tab(self):
        self._active_tab_name = "General"
        self._clear_content()
        self._add_title("General")

        # -- HARDWARE API (collapsible) --
        sec_hardware = self._create_collapsible_section(self.content_frame, "Hardware API", initially_open=True)
        self.mouse_api_option = self._add_option_row_in_frame(
            sec_hardware,
            "Input API",
            ["Serial", "Arduino", "SendInput", "Net", "KmboxA", "MakV2", "MakV2Binary", "DHZ"],
            self._on_mouse_api_changed,
        )
        self.var_auto_connect_mouse_api = tk.BooleanVar(value=bool(getattr(config, "auto_connect_mouse_api", False)))
        self._add_switch_in_frame(
            sec_hardware,
            "Auto Connect Mouse API On Startup",
            self.var_auto_connect_mouse_api,
            self._on_auto_connect_mouse_api_changed,
        )
        current_mouse_api = getattr(config, "mouse_api", "Serial")
        current_mouse_api_norm = str(current_mouse_api).strip().lower()
        if current_mouse_api_norm == "net":
            current_mouse_api = "Net"
        elif current_mouse_api_norm in ("kmboxa", "kmboxa_api", "kmboxaapi", "kma", "kmboxa-api"):
            current_mouse_api = "KmboxA"
        elif current_mouse_api_norm == "dhz":
            current_mouse_api = "DHZ"
        elif current_mouse_api_norm in ("makv2binary", "makv2_binary", "makv2-binary", "binary"):
            current_mouse_api = "MakV2Binary"
        elif current_mouse_api_norm in ("makv2", "mak_v2", "mak-v2"):
            current_mouse_api = "MakV2"
        elif current_mouse_api_norm == "arduino":
            current_mouse_api = "Arduino"
        elif current_mouse_api_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
            current_mouse_api = "SendInput"
        else:
            current_mouse_api = "Serial"
        self.mouse_api_option.set(current_mouse_api)
        self.saved_mouse_api = current_mouse_api
        serial_mode = str(getattr(config, "serial_port_mode", self.saved_serial_port_mode)).strip().lower()
        self.saved_serial_port_mode = "Manual" if serial_mode == "manual" else "Auto"
        self.saved_serial_port = str(getattr(config, "serial_port", self.saved_serial_port))
        self.saved_serial_auto_switch_4m = bool(
            getattr(config, "serial_auto_switch_4m", self.saved_serial_auto_switch_4m)
        )
        self.saved_net_ip = getattr(config, "net_ip", self.saved_net_ip)
        self.saved_net_port = getattr(config, "net_port", self.saved_net_port)
        self.saved_net_uuid = getattr(config, "net_uuid", getattr(config, "net_mac", self.saved_net_uuid))
        self.saved_kmboxa_vid_pid = str(
            getattr(
                config,
                "kmboxa_vid_pid",
                f"{getattr(config, 'kmboxa_vid', 0)}/{getattr(config, 'kmboxa_pid', 0)}",
            )
        )
        self.saved_arduino_port = str(getattr(config, "arduino_port", self.saved_arduino_port))
        self.saved_arduino_baud = str(getattr(config, "arduino_baud", self.saved_arduino_baud))
        self.saved_makv2_port = getattr(config, "makv2_port", self.saved_makv2_port)
        self.saved_makv2_baud = str(getattr(config, "makv2_baud", self.saved_makv2_baud))
        self.saved_dhz_ip = getattr(config, "dhz_ip", self.saved_dhz_ip)
        self.saved_dhz_port = str(getattr(config, "dhz_port", self.saved_dhz_port))
        self.saved_dhz_random = str(getattr(config, "dhz_random", self.saved_dhz_random))
        self.saved_auto_connect_mouse_api = bool(getattr(config, "auto_connect_mouse_api", self.saved_auto_connect_mouse_api))

        self._add_spacer_in_frame(sec_hardware)
        self.hardware_content_frame = ctk.CTkFrame(sec_hardware, fg_color="transparent")
        self.hardware_content_frame.pack(fill="x", pady=5)
        self._update_mouse_api_ui()
        
        # 鈹€鈹€ CAPTURE CONTROLS (collapsible) 鈹€鈹€
        sec_capture = self._create_collapsible_section(self.content_frame, "Capture Controls", initially_open=True)
        
        # Capture Method Selection
        self.capture_method_var.set(self.capture.mode)
        # 鍓靛缓 option menu
        self.capture_method_option = self._add_option_row_in_frame(sec_capture, "Method", ["NDI", "UDP", "CaptureCard", "MSS"], self._on_capture_method_changed)
        # 椤紡瑷疆鐣跺墠鍊?
        self.capture_method_option.set(self.capture.mode)
        
        self._add_spacer_in_frame(sec_capture)
        
        # Dynamic Capture Content Frame
        self.capture_content_frame = ctk.CTkFrame(sec_capture, fg_color="transparent")
        self.capture_content_frame.pack(fill="x", pady=5)
        
        self._update_capture_ui()

        # 鈹€鈹€ SETTINGS (collapsible) 鈹€鈹€
        sec_settings = self._create_collapsible_section(self.content_frame, "Settings", initially_open=True)
        
        # In-Game Sensitivity (闋愯ō 0.235, 绡勫湇 0.1-20)
        self._add_slider_in_frame(sec_settings, "In-Game Sensitivity", "in_game_sens", 0.1, 20, 
                        float(getattr(config, "in_game_sens", 0.235)), 
                        self._on_config_in_game_sens_changed, is_float=True)
        
        self._add_spacer_in_frame(sec_settings)
        
        self.color_option = self._add_option_row_in_frame(
            sec_settings,
            "Target Color",
            ["yellow", "purple", "red", "custom"],
            self._on_color_selected,
        )
        self._option_widgets["color"] = self.color_option
        # 瑷疆鐣跺墠鍊?
        current_color = getattr(config, "color", "yellow")
        self.color_option.set(current_color)
        
        # 鈹€鈹€ Custom HSV Settings (collapsible, only show when custom is selected) 鈹€鈹€
        # 鍓靛缓 container 浠ヤ究鎺у埗椤ず/闅辫棌锛堜笉鑷嫊 pack锛?
        self.custom_hsv_section, self.custom_hsv_container = self._create_collapsible_section(
            self.content_frame, "Custom HSV", initially_open=True, auto_pack=False
        )
        if current_color == "custom":
            self.custom_hsv_container.pack(fill="x", pady=(5, 0))
        self._hsv_preview_btn_frame = ctk.CTkFrame(self.custom_hsv_section, fg_color="transparent")
        self._hsv_preview_btn_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            self._hsv_preview_btn_frame,
            text="HSV Filter Preview",
            height=30,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ACCENT,
            font=FONT_BOLD,
            corner_radius=4,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self._open_hsv_preview,
        ).pack(fill="x", padx=14)
        
        # HSV Min Values
        self._add_subtitle_in_frame(self.custom_hsv_section, "HSV MIN")
        self._add_slider_in_frame(self.custom_hsv_section, "H Min", "custom_hsv_min_h", 0, 179,
                                  int(getattr(config, "custom_hsv_min_h", 0)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_min_h", v))
        self._add_slider_in_frame(self.custom_hsv_section, "S Min", "custom_hsv_min_s", 0, 255,
                                  int(getattr(config, "custom_hsv_min_s", 0)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_min_s", v))
        self._add_slider_in_frame(self.custom_hsv_section, "V Min", "custom_hsv_min_v", 0, 255,
                                  int(getattr(config, "custom_hsv_min_v", 0)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_min_v", v))
        
        self._add_spacer_in_frame(self.custom_hsv_section)
        
        # HSV Max Values
        self._add_subtitle_in_frame(self.custom_hsv_section, "HSV MAX")
        self._add_slider_in_frame(self.custom_hsv_section, "H Max", "custom_hsv_max_h", 0, 179,
                                  int(getattr(config, "custom_hsv_max_h", 179)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_max_h", v))
        self._add_slider_in_frame(self.custom_hsv_section, "S Max", "custom_hsv_max_s", 0, 255,
                                  int(getattr(config, "custom_hsv_max_s", 255)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_max_s", v))
        self._add_slider_in_frame(self.custom_hsv_section, "V Max", "custom_hsv_max_v", 0, 255,
                                  int(getattr(config, "custom_hsv_max_v", 255)),
                                  lambda v: self._on_custom_hsv_changed("custom_hsv_max_v", v))
        
        # 鏍规摎鐣跺墠閬告搰椤ず/闅辫棌 Custom HSV 鍗€濉?

        self._update_custom_hsv_visibility()
        
        # 鈹€鈹€ DETECTION PARAMETERS (collapsible) 鈹€鈹€
        detection_tooltip_text = (
            "- Merge Distance: Controls the distance threshold for merging detection rectangles. "
            "Higher values merge more (may cause false merges), lower values merge less (may create multiple targets). "
            "Recommended: 200-300 (default 250)\n\n"
            "- Min Contour Points: Filters contours with too few points (usually noise). "
            "Higher values filter more strictly (may miss small targets), lower values filter more loosely (may include more noise). "
            "Recommended: 3-10 (default 5)"
        )
        sec_detection = self._create_collapsible_section(
            self.content_frame, 
            "Detection Parameters", 
            initially_open=False,
            tooltip_text=detection_tooltip_text
        )
        
        # Merge Distance
        self._add_slider_in_frame(sec_detection, "Merge Distance", "detection_merge_distance", 50, 500,
                                  int(getattr(config, "detection_merge_distance", 250)),
                                  self._on_detection_merge_distance_changed)
        
        self._add_spacer_in_frame(sec_detection)
        
        # Min Contour Points
        self._add_slider_in_frame(sec_detection, "Min Contour Points", "detection_min_contour_points", 3, 100,
                                  int(getattr(config, "detection_min_contour_points", 5)),
                                  self._on_detection_min_contour_points_changed)
        
        # MOUSE LOCK (collapsible)
        mouse_lock_tooltip_text = (
            "- Lock Main Aimbot X-Axis: Blocks physical mouse movement on X-axis when Main Aimbot is active. "
            "Only aimbot-controlled movements will be applied.\n\n"
            "- Lock Main Aimbot Y-Axis: Blocks physical mouse movement on Y-axis when Main Aimbot is active. "
            "Only aimbot-controlled movements will be applied.\n\n"
            "- Lock Sec Aimbot X-Axis: Blocks physical mouse movement on X-axis when Sec Aimbot is active. "
            "Only aimbot-controlled movements will be applied.\n\n"
            "- Lock Sec Aimbot Y-Axis: Blocks physical mouse movement on Y-axis when Sec Aimbot is active. "
            "Only aimbot-controlled movements will be applied.\n\n"
            "Note: The lock will automatically release when the aimbot button is released or aimbot stops moving."
        )
        sec_mouse_lock = self._create_collapsible_section(
            self.content_frame,
            "Mouse Lock",
            initially_open=False,
            tooltip_text=mouse_lock_tooltip_text
        )
        
        # Lock Main Aimbot X-Axis
        if not hasattr(self, 'var_mouse_lock_main_x'):
            self.var_mouse_lock_main_x = tk.BooleanVar(value=getattr(config, "mouse_lock_main_x", False))
        self._add_switch_in_frame(sec_mouse_lock, "Lock Main Aimbot X-Axis", self.var_mouse_lock_main_x, self._on_mouse_lock_main_x_changed)
        self._checkbox_vars["mouse_lock_main_x"] = self.var_mouse_lock_main_x
        
        # Lock Main Aimbot Y-Axis
        if not hasattr(self, 'var_mouse_lock_main_y'):
            self.var_mouse_lock_main_y = tk.BooleanVar(value=getattr(config, "mouse_lock_main_y", False))
        self._add_switch_in_frame(sec_mouse_lock, "Lock Main Aimbot Y-Axis", self.var_mouse_lock_main_y, self._on_mouse_lock_main_y_changed)
        self._checkbox_vars["mouse_lock_main_y"] = self.var_mouse_lock_main_y
        
        self._add_spacer_in_frame(sec_mouse_lock)
        
        # Lock Sec Aimbot X-Axis
        if not hasattr(self, 'var_mouse_lock_sec_x'):
            self.var_mouse_lock_sec_x = tk.BooleanVar(value=getattr(config, "mouse_lock_sec_x", False))
        self._add_switch_in_frame(sec_mouse_lock, "Lock Sec Aimbot X-Axis", self.var_mouse_lock_sec_x, self._on_mouse_lock_sec_x_changed)
        self._checkbox_vars["mouse_lock_sec_x"] = self.var_mouse_lock_sec_x
        
        # Lock Sec Aimbot Y-Axis
        if not hasattr(self, 'var_mouse_lock_sec_y'):
            self.var_mouse_lock_sec_y = tk.BooleanVar(value=getattr(config, "mouse_lock_sec_y", False))
        self._add_switch_in_frame(sec_mouse_lock, "Lock Sec Aimbot Y-Axis", self.var_mouse_lock_sec_y, self._on_mouse_lock_sec_y_changed)
        self._checkbox_vars["mouse_lock_sec_y"] = self.var_mouse_lock_sec_y
        
        # 鈹€鈹€ BUTTON MASK (collapsible) 鈹€鈹€
        sec_button_mask = self._create_collapsible_section(self.content_frame, "Button Mask", initially_open=False)
        
        # Button Mask 绺介枊闂?
        if not hasattr(self, 'var_button_mask_enabled'):
            self.var_button_mask_enabled = tk.BooleanVar(value=getattr(config, "button_mask_enabled", False))
        
        master_switch = ctk.CTkSwitch(
            sec_button_mask,
            text="Enable Button Mask",
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
        master_switch.pack(fill="x", pady=(5, 10))
        self._checkbox_vars["button_mask_enabled"] = self.var_button_mask_enabled
        
        # Grid for individual buttons
        grid_frame = ctk.CTkFrame(sec_button_mask, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 5))
        
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
            
            # 浣跨敤鏇寸啊绱勭殑 Switch 棰ㄦ牸
            btn_switch = ctk.CTkSwitch(
                grid_frame,
                text=label,
                variable=var,
                command=lambda k=key, v=var: self._on_button_mask_changed(k, v),
                fg_color=COLOR_BORDER,
                progress_color=COLOR_TEXT, # 绲变竴榛戠櫧棰ㄦ牸
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

    def _update_mouse_api_ui(self):
        """鏍规摎閬告搰鐨勬粦榧?API 鏇存柊 Hardware API 鍗€濉娿€?"""
        if not hasattr(self, "hardware_content_frame") or not self.hardware_content_frame.winfo_exists():
            return

        for widget in self.hardware_content_frame.winfo_children():
            widget.destroy()

        mode = "Serial"
        if hasattr(self, "mouse_api_option") and self.mouse_api_option.winfo_exists():
            mode = self.mouse_api_option.get()
        mode_norm = str(mode).strip().lower()
        if mode_norm == "net":
            mode = "Net"
        elif mode_norm in ("kmboxa", "kmboxa_api", "kmboxaapi", "kma", "kmboxa-api"):
            mode = "KmboxA"
        elif mode_norm == "dhz":
            mode = "DHZ"
        elif mode_norm in ("makv2", "mak_v2", "mak-v2"):
            mode = "MakV2"
        elif mode_norm == "arduino":
            mode = "Arduino"
        elif mode_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
            mode = "SendInput"
        else:
            mode = "Serial"
        self.saved_mouse_api = mode
        config.mouse_api = mode

        if mode == "Serial":
            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text="Serial API (MAKCU/CH34x)",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            mode_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            mode_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(mode_frame, text="COM Mode", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.serial_mode_option = self._add_option_menu(
                ["Auto", "Manual"],
                self._on_serial_mode_selected,
                parent=mode_frame,
            )
            self.serial_mode_option.pack(side="right")
            current_serial_mode = "Manual" if str(self.saved_serial_port_mode).strip().lower() == "manual" else "Auto"
            self.saved_serial_port_mode = current_serial_mode
            self.serial_mode_option.set(current_serial_mode)

            if current_serial_mode == "Manual":
                port_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
                port_frame.pack(fill="x", pady=3)
                ctk.CTkLabel(port_frame, text="COM Port", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
                self.serial_port_entry = ctk.CTkEntry(
                    port_frame,
                    fg_color=COLOR_SURFACE,
                    border_width=0,
                    text_color=COLOR_TEXT,
                    width=170,
                )
                self.serial_port_entry.pack(side="right")
                self.serial_port_entry.insert(0, self.saved_serial_port)
                self.serial_port_entry.bind("<KeyRelease>", self._on_serial_port_changed)
                self.serial_port_entry.bind("<FocusOut>", self._on_serial_port_changed)

            self.var_serial_auto_switch_4m = tk.BooleanVar(value=bool(self.saved_serial_auto_switch_4m))
            self._add_switch_in_frame(
                self.hardware_content_frame,
                "Auto Switch Serial to 4M On Startup",
                self.var_serial_auto_switch_4m,
                self._on_serial_auto_switch_4m_changed,
            )

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=5)
            self._add_text_button(btn_frame, "CONNECT SERIAL", lambda: self._connect_mouse_api("Serial")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            self._add_text_button(btn_frame, "SWITCH TO 4M", self._switch_serial_to_4m).pack(side="left")
            return

        if mode == "Arduino":
            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text="Arduino API (serial c/p/r/mX,Y newline protocol)",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            port_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            port_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(port_frame, text="COM Port (optional)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.arduino_port_entry = ctk.CTkEntry(
                port_frame,
                fg_color=COLOR_SURFACE,
                border_width=0,
                text_color=COLOR_TEXT,
                width=170,
            )
            self.arduino_port_entry.pack(side="right")
            self.arduino_port_entry.insert(0, self.saved_arduino_port)
            self.arduino_port_entry.bind("<KeyRelease>", self._on_arduino_port_changed)
            self.arduino_port_entry.bind("<FocusOut>", self._on_arduino_port_changed)

            baud_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            baud_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(baud_frame, text="Baud", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.arduino_baud_entry = ctk.CTkEntry(
                baud_frame,
                fg_color=COLOR_SURFACE,
                border_width=0,
                text_color=COLOR_TEXT,
                width=170,
            )
            self.arduino_baud_entry.pack(side="right")
            self.arduino_baud_entry.insert(0, self.saved_arduino_baud)
            self.arduino_baud_entry.bind("<KeyRelease>", self._on_arduino_baud_changed)
            self.arduino_baud_entry.bind("<FocusOut>", self._on_arduino_baud_changed)

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=8)
            self._add_text_button(btn_frame, "CONNECT ARDUINO", lambda: self._connect_mouse_api("Arduino")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            return

        if mode == "SendInput":
            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text="Win32 SendInput API (software injection, no COM needed)",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            sendinput_notice = ctk.CTkLabel(
                self.hardware_content_frame,
                text="For dual-PC streaming setups (e.g., Moonlight).",
                font=("Roboto", 10, "bold"),
                text_color=COLOR_DANGER,
            )
            sendinput_notice.pack(anchor="w", pady=(0, 8))

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=8)
            self._add_text_button(btn_frame, "ENABLE SENDINPUT", lambda: self._connect_mouse_api("SendInput")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            return

        if mode == "MakV2":
            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text="MakV2 API (ASCII km.* commands over serial)",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            port_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            port_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(port_frame, text="Port (optional)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.makv2_port_entry = ctk.CTkEntry(port_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
            self.makv2_port_entry.pack(side="right")
            self.makv2_port_entry.insert(0, self.saved_makv2_port)
            self.makv2_port_entry.bind("<KeyRelease>", self._on_makv2_port_changed)
            self.makv2_port_entry.bind("<FocusOut>", self._on_makv2_port_changed)

            baud_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            baud_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(baud_frame, text="Baud", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.makv2_baud_entry = ctk.CTkEntry(baud_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
            self.makv2_baud_entry.pack(side="right")
            self.makv2_baud_entry.insert(0, self.saved_makv2_baud)
            self.makv2_baud_entry.bind("<KeyRelease>", self._on_makv2_baud_changed)
            self.makv2_baud_entry.bind("<FocusOut>", self._on_makv2_baud_changed)

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=8)
            self._add_text_button(btn_frame, "CONNECT MAKV2", lambda: self._connect_mouse_api("MakV2")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            return

        if mode == "DHZ":
            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text="DHZ API (UDP + Caesar-shift command protocol)",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            ip_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            ip_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(ip_frame, text="IP Address", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.dhz_ip_entry = ctk.CTkEntry(ip_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
            self.dhz_ip_entry.pack(side="right")
            self.dhz_ip_entry.insert(0, self.saved_dhz_ip)
            self.dhz_ip_entry.bind("<KeyRelease>", self._on_dhz_ip_changed)
            self.dhz_ip_entry.bind("<FocusOut>", self._on_dhz_ip_changed)

            port_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            port_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(port_frame, text="Port", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.dhz_port_entry = ctk.CTkEntry(port_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
            self.dhz_port_entry.pack(side="right")
            self.dhz_port_entry.insert(0, self.saved_dhz_port)
            self.dhz_port_entry.bind("<KeyRelease>", self._on_dhz_port_changed)
            self.dhz_port_entry.bind("<FocusOut>", self._on_dhz_port_changed)

            random_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            random_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(random_frame, text="Random Shift", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.dhz_random_entry = ctk.CTkEntry(random_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
            self.dhz_random_entry.pack(side="right")
            self.dhz_random_entry.insert(0, self.saved_dhz_random)
            self.dhz_random_entry.bind("<KeyRelease>", self._on_dhz_random_changed)
            self.dhz_random_entry.bind("<FocusOut>", self._on_dhz_random_changed)

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=8)
            self._add_text_button(btn_frame, "CONNECT DHZ", lambda: self._connect_mouse_api("DHZ")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            return

        if mode == "KmboxA":
            dll_name = "kmA.pyd"
            try:
                from src.utils.mouse import get_expected_kmboxa_dll_name

                dll_name = get_expected_kmboxa_dll_name()
            except Exception:
                pass

            tip = ctk.CTkLabel(
                self.hardware_content_frame,
                text=f"KmboxA API auto DLL by Python version: {dll_name}",
                font=("Roboto", 10),
                text_color=COLOR_TEXT_DIM,
            )
            tip.pack(anchor="w", pady=(0, 8))

            vid_pid_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            vid_pid_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(vid_pid_frame, text="VID/PID", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.kmboxa_vid_pid_entry = ctk.CTkEntry(
                vid_pid_frame,
                fg_color=COLOR_SURFACE,
                border_width=0,
                text_color=COLOR_TEXT,
                width=170,
            )
            self.kmboxa_vid_pid_entry.pack(side="right")
            self.kmboxa_vid_pid_entry.insert(0, self.saved_kmboxa_vid_pid)
            self.kmboxa_vid_pid_entry.bind("<KeyRelease>", self._on_kmboxa_vid_pid_changed)
            self.kmboxa_vid_pid_entry.bind("<FocusOut>", self._on_kmboxa_vid_pid_changed)

            btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=8)
            self._add_text_button(btn_frame, "CONNECT KMBOXA", lambda: self._connect_mouse_api("KmboxA")).pack(side="left")
            self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)
            return

        # Net API controls
        dll_name = "kmNet.pyd"
        try:
            from src.utils.mouse import get_expected_kmnet_dll_name

            dll_name = get_expected_kmnet_dll_name()
        except Exception:
            pass

        tip = ctk.CTkLabel(
            self.hardware_content_frame,
            text=f"Net API auto DLL by Python version: {dll_name}",
            font=("Roboto", 10),
            text_color=COLOR_TEXT_DIM,
        )
        tip.pack(anchor="w", pady=(0, 8))

        ip_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
        ip_frame.pack(fill="x", pady=3)
        ctk.CTkLabel(ip_frame, text="IP Address", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        self.net_ip_entry = ctk.CTkEntry(ip_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
        self.net_ip_entry.pack(side="right")
        self.net_ip_entry.insert(0, self.saved_net_ip)
        self.net_ip_entry.bind("<KeyRelease>", self._on_net_ip_changed)
        self.net_ip_entry.bind("<FocusOut>", self._on_net_ip_changed)

        port_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
        port_frame.pack(fill="x", pady=3)
        ctk.CTkLabel(port_frame, text="Port", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        self.net_port_entry = ctk.CTkEntry(port_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
        self.net_port_entry.pack(side="right")
        self.net_port_entry.insert(0, self.saved_net_port)
        self.net_port_entry.bind("<KeyRelease>", self._on_net_port_changed)
        self.net_port_entry.bind("<FocusOut>", self._on_net_port_changed)

        uuid_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
        uuid_frame.pack(fill="x", pady=3)
        ctk.CTkLabel(uuid_frame, text="UUID", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        self.net_uuid_entry = ctk.CTkEntry(uuid_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=170)
        self.net_uuid_entry.pack(side="right")
        self.net_uuid_entry.insert(0, self.saved_net_uuid)
        self.net_uuid_entry.bind("<KeyRelease>", self._on_net_uuid_changed)
        self.net_uuid_entry.bind("<FocusOut>", self._on_net_uuid_changed)

        btn_frame = ctk.CTkFrame(self.hardware_content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=8)
        self._add_text_button(btn_frame, "CONNECT NET", lambda: self._connect_mouse_api("Net")).pack(side="left")
        self._add_text_button(btn_frame, "TEST MOVE", self._test_mouse_move).pack(side="left", padx=12)

    def _on_mouse_api_changed(self, val):
        mode_norm = str(val).strip().lower()
        if mode_norm == "net":
            self.saved_mouse_api = "Net"
        elif mode_norm in ("kmboxa", "kmboxa_api", "kmboxaapi", "kma", "kmboxa-api"):
            self.saved_mouse_api = "KmboxA"
        elif mode_norm == "dhz":
            self.saved_mouse_api = "DHZ"
        elif mode_norm in ("makv2binary", "makv2_binary", "makv2-binary", "binary"):
            self.saved_mouse_api = "MakV2Binary"
        elif mode_norm in ("makv2", "mak_v2", "mak-v2"):
            self.saved_mouse_api = "MakV2"
        elif mode_norm == "arduino":
            self.saved_mouse_api = "Arduino"
        elif mode_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
            self.saved_mouse_api = "SendInput"
        else:
            self.saved_mouse_api = "Serial"
        config.mouse_api = self.saved_mouse_api
        if not self._supports_trigger_strafe_ui(self.saved_mouse_api):
            config.trigger_strafe_mode = "off"
        self.saved_auto_connect_mouse_api = bool(getattr(config, "auto_connect_mouse_api", self.saved_auto_connect_mouse_api))
        self.saved_serial_auto_switch_4m = bool(
            getattr(config, "serial_auto_switch_4m", self.saved_serial_auto_switch_4m)
        )
        # Cancel any in-flight connect request to avoid stale success callback after mode switch.
        self._mouse_api_connect_job_id += 1
        self._mouse_api_connecting = False
        # Switching mode must drop current hardware connection state.
        try:
            from src.utils import mouse as mouse_backend

            mouse_backend.disconnect_all(selected_mode=self.saved_mouse_api)
        except Exception:
            pass
        self._update_mouse_api_ui()
        self._set_status_indicator(f"Status: Mouse API {self.saved_mouse_api} selected", COLOR_TEXT_DIM)
        self._update_hardware_status_ui()

        if str(getattr(self, "_active_tab_name", "")) == "Trigger":
            self._show_tb_tab()

    def _on_auto_connect_mouse_api_changed(self):
        val = bool(self.var_auto_connect_mouse_api.get())
        self.saved_auto_connect_mouse_api = val
        config.auto_connect_mouse_api = val
        try:
            config.save_to_file()
        except Exception:
            pass

    def _on_serial_auto_switch_4m_changed(self):
        val = bool(self.var_serial_auto_switch_4m.get())
        self.saved_serial_auto_switch_4m = val
        config.serial_auto_switch_4m = val
        try:
            config.save_to_file()
        except Exception:
            pass

    def _on_serial_mode_selected(self, val):
        mode_norm = str(val).strip().lower()
        self.saved_serial_port_mode = "Manual" if mode_norm == "manual" else "Auto"
        config.serial_port_mode = self.saved_serial_port_mode
        self._update_mouse_api_ui()

    def _on_serial_port_changed(self, event=None):
        if hasattr(self, "serial_port_entry") and self.serial_port_entry.winfo_exists():
            val = self.serial_port_entry.get().strip()
            self.saved_serial_port = val
            config.serial_port = val

    def _on_arduino_port_changed(self, event=None):
        if hasattr(self, "arduino_port_entry") and self.arduino_port_entry.winfo_exists():
            val = self.arduino_port_entry.get().strip()
            self.saved_arduino_port = val
            config.arduino_port = val

    def _on_arduino_baud_changed(self, event=None):
        if hasattr(self, "arduino_baud_entry") and self.arduino_baud_entry.winfo_exists():
            val = self.arduino_baud_entry.get().strip()
            self.saved_arduino_baud = val
            try:
                config.arduino_baud = int(val)
            except ValueError:
                config.arduino_baud = 115200

    def _on_net_ip_changed(self, event=None):
        if hasattr(self, "net_ip_entry") and self.net_ip_entry.winfo_exists():
            val = self.net_ip_entry.get().strip()
            self.saved_net_ip = val
            config.net_ip = val

    def _on_net_port_changed(self, event=None):
        if hasattr(self, "net_port_entry") and self.net_port_entry.winfo_exists():
            val = self.net_port_entry.get().strip()
            self.saved_net_port = val
            config.net_port = val

    def _on_net_uuid_changed(self, event=None):
        if hasattr(self, "net_uuid_entry") and self.net_uuid_entry.winfo_exists():
            val = self.net_uuid_entry.get().strip()
            self.saved_net_uuid = val
            config.net_uuid = val
            config.net_mac = val

    def _on_kmboxa_vid_pid_changed(self, event=None):
        if hasattr(self, "kmboxa_vid_pid_entry") and self.kmboxa_vid_pid_entry.winfo_exists():
            val = self.kmboxa_vid_pid_entry.get().strip()
            self.saved_kmboxa_vid_pid = val
            config.kmboxa_vid_pid = val

    def _on_makv2_port_changed(self, event=None):
        if hasattr(self, "makv2_port_entry") and self.makv2_port_entry.winfo_exists():
            val = self.makv2_port_entry.get().strip()
            self.saved_makv2_port = val
            config.makv2_port = val

    def _on_makv2_baud_changed(self, event=None):
        if hasattr(self, "makv2_baud_entry") and self.makv2_baud_entry.winfo_exists():
            val = self.makv2_baud_entry.get().strip()
            self.saved_makv2_baud = val
            try:
                config.makv2_baud = int(val)
            except ValueError:
                pass

    def _on_dhz_ip_changed(self, event=None):
        if hasattr(self, "dhz_ip_entry") and self.dhz_ip_entry.winfo_exists():
            val = self.dhz_ip_entry.get().strip()
            self.saved_dhz_ip = val
            config.dhz_ip = val

    def _on_dhz_port_changed(self, event=None):
        if hasattr(self, "dhz_port_entry") and self.dhz_port_entry.winfo_exists():
            val = self.dhz_port_entry.get().strip()
            self.saved_dhz_port = val
            config.dhz_port = val

    def _on_dhz_random_changed(self, event=None):
        if hasattr(self, "dhz_random_entry") and self.dhz_random_entry.winfo_exists():
            val = self.dhz_random_entry.get().strip()
            self.saved_dhz_random = val
            try:
                config.dhz_random = int(val)
            except ValueError:
                pass

    def _test_mouse_move(self):
        try:
            from src.utils import mouse as mouse_backend

            if not getattr(mouse_backend, "is_connected", False):
                self._set_status_indicator("Status: Mouse API not connected", COLOR_DANGER)
                return

            mouse_backend.test_move()
            backend = mouse_backend.get_active_backend()
            self._set_status_indicator(f"Status: Test move sent via {backend}", COLOR_TEXT)
        except Exception as e:
            self._set_status_indicator(f"Status: Mouse API test error: {e}", COLOR_DANGER)

    def _switch_serial_to_4m(self):
        if getattr(self, "_mouse_api_connecting", False):
            self._set_status_indicator("Status: HW connecting...", COLOR_TEXT_DIM)
            return
        if getattr(self, "_serial_baud_switching", False):
            self._set_status_indicator("Status: Serial baud switching...", COLOR_TEXT_DIM)
            return

        self._serial_baud_switching = True
        self._set_status_indicator("Status: Switching Serial to 4M", COLOR_TEXT_DIM)
        threading.Thread(target=self._switch_serial_to_4m_worker, daemon=True).start()

    def _switch_serial_to_4m_worker(self):
        success = False
        error = ""
        try:
            from src.utils import mouse as mouse_backend

            success = bool(mouse_backend.switch_to_4m())
            if not success:
                error = str(mouse_backend.get_last_connect_error() or "").strip()
        except Exception as e:
            success = False
            error = str(e)

        self.after(0, lambda: self._on_switch_serial_to_4m_done(success, error))

    def _on_switch_serial_to_4m_done(self, success, error):
        self._serial_baud_switching = False
        if success:
            self._set_status_indicator("Status: Serial switched to 4M", COLOR_TEXT)
        else:
            suffix = f": {error}" if error else ""
            self._set_status_indicator(f"Status: Switch to 4M failed{suffix}", COLOR_DANGER)
        self._update_hardware_status_ui()

    def _connect_mouse_api(self, target_mode=None):
        if getattr(self, "_mouse_api_connecting", False):
            self._set_status_indicator("Status: HW connecting...", COLOR_TEXT_DIM)
            return
        if getattr(self, "_serial_baud_switching", False):
            self._set_status_indicator("Status: Serial baud switching...", COLOR_TEXT_DIM)
            return

        mode = target_mode or getattr(config, "mouse_api", "Serial")
        mode_norm = str(mode).strip().lower()
        if mode_norm == "net":
            mode = "Net"
        elif mode_norm in ("kmboxa", "kmboxa_api", "kmboxaapi", "kma", "kmboxa-api"):
            mode = "KmboxA"
        elif mode_norm == "dhz":
            mode = "DHZ"
        elif mode_norm in ("makv2", "mak_v2", "mak-v2"):
            mode = "MakV2"
        elif mode_norm == "arduino":
            mode = "Arduino"
        elif mode_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
            mode = "SendInput"
        else:
            mode = "Serial"
        payload = {"mode": mode}

        if mode == "Serial":
            selected_serial_mode = "Manual" if str(self.saved_serial_port_mode).strip().lower() == "manual" else "Auto"
            self.saved_serial_port_mode = selected_serial_mode
            if selected_serial_mode == "Manual":
                if hasattr(self, "serial_port_entry") and self.serial_port_entry.winfo_exists():
                    self.saved_serial_port = self.serial_port_entry.get().strip()
            config.serial_port_mode = selected_serial_mode
            config.serial_port = self.saved_serial_port
            payload.update(
                {
                    "serial_port_mode": selected_serial_mode,
                    "serial_port": self.saved_serial_port,
                }
            )

        elif mode == "Arduino":
            if hasattr(self, "arduino_port_entry") and self.arduino_port_entry.winfo_exists():
                self.saved_arduino_port = self.arduino_port_entry.get().strip()
            if hasattr(self, "arduino_baud_entry") and self.arduino_baud_entry.winfo_exists():
                self.saved_arduino_baud = self.arduino_baud_entry.get().strip()

            config.arduino_port = self.saved_arduino_port
            try:
                config.arduino_baud = int(self.saved_arduino_baud)
            except ValueError:
                config.arduino_baud = 115200
            payload.update(
                {
                    "arduino_port": self.saved_arduino_port,
                    "arduino_baud": config.arduino_baud,
                }
            )

        elif mode == "Net":
            if hasattr(self, "net_ip_entry") and self.net_ip_entry.winfo_exists():
                self.saved_net_ip = self.net_ip_entry.get().strip()
            if hasattr(self, "net_port_entry") and self.net_port_entry.winfo_exists():
                self.saved_net_port = self.net_port_entry.get().strip()
            if hasattr(self, "net_uuid_entry") and self.net_uuid_entry.winfo_exists():
                self.saved_net_uuid = self.net_uuid_entry.get().strip()

            config.net_ip = self.saved_net_ip
            config.net_port = self.saved_net_port
            config.net_uuid = self.saved_net_uuid
            config.net_mac = self.saved_net_uuid
            payload.update({
                "ip": self.saved_net_ip,
                "port": self.saved_net_port,
                "uuid": self.saved_net_uuid,
            })
        elif mode == "KmboxA":
            if hasattr(self, "kmboxa_vid_pid_entry") and self.kmboxa_vid_pid_entry.winfo_exists():
                self.saved_kmboxa_vid_pid = self.kmboxa_vid_pid_entry.get().strip()
            config.kmboxa_vid_pid = self.saved_kmboxa_vid_pid
            payload.update({
                "kmboxa_vid_pid": self.saved_kmboxa_vid_pid,
            })

        elif mode == "MakV2":
            if hasattr(self, "makv2_port_entry") and self.makv2_port_entry.winfo_exists():
                self.saved_makv2_port = self.makv2_port_entry.get().strip()
            if hasattr(self, "makv2_baud_entry") and self.makv2_baud_entry.winfo_exists():
                self.saved_makv2_baud = self.makv2_baud_entry.get().strip()

            config.makv2_port = self.saved_makv2_port
            try:
                config.makv2_baud = int(self.saved_makv2_baud)
            except ValueError:
                config.makv2_baud = 4000000
            payload.update({
                "makv2_port": self.saved_makv2_port,
                "makv2_baud": config.makv2_baud,
            })
        elif mode == "DHZ":
            if hasattr(self, "dhz_ip_entry") and self.dhz_ip_entry.winfo_exists():
                self.saved_dhz_ip = self.dhz_ip_entry.get().strip()
            if hasattr(self, "dhz_port_entry") and self.dhz_port_entry.winfo_exists():
                self.saved_dhz_port = self.dhz_port_entry.get().strip()
            if hasattr(self, "dhz_random_entry") and self.dhz_random_entry.winfo_exists():
                self.saved_dhz_random = self.dhz_random_entry.get().strip()

            config.dhz_ip = self.saved_dhz_ip
            config.dhz_port = self.saved_dhz_port
            try:
                config.dhz_random = int(self.saved_dhz_random)
            except ValueError:
                config.dhz_random = 0
            payload.update({
                "dhz_ip": self.saved_dhz_ip,
                "dhz_port": self.saved_dhz_port,
                "dhz_random": config.dhz_random,
            })
        elif mode == "SendInput":
            pass

        self._mouse_api_connecting = True
        self._mouse_api_connect_job_id += 1
        job_id = self._mouse_api_connect_job_id
        self._set_status_indicator(f"Status: HW {mode} connecting", COLOR_TEXT_DIM)

        threading.Thread(
            target=self._connect_mouse_api_worker,
            args=(job_id, payload),
            daemon=True,
        ).start()
        self.after(
            self._mouse_api_connect_timeout_ms,
            lambda: self._check_mouse_api_connect_timeout(job_id, mode),
        )

    def _connect_mouse_api_worker(self, job_id, payload):
        mode = payload.get("mode", "Serial")
        success, error = False, "unknown error"
        try:
            from src.utils.mouse import switch_backend

            if mode == "Net":
                success, error = switch_backend(
                    "Net",
                    ip=payload.get("ip", ""),
                    port=payload.get("port", ""),
                    uuid=payload.get("uuid", ""),
                )
            elif mode == "KmboxA":
                success, error = switch_backend(
                    "KmboxA",
                    kmboxa_vid_pid=payload.get("kmboxa_vid_pid", ""),
                )
            elif mode == "Arduino":
                success, error = switch_backend(
                    "Arduino",
                    arduino_port=payload.get("arduino_port", ""),
                    arduino_baud=payload.get("arduino_baud", 115200),
                )
            elif mode == "SendInput":
                success, error = switch_backend("SendInput")
            elif mode == "MakV2":
                success, error = switch_backend(
                    "MakV2",
                    makv2_port=payload.get("makv2_port", ""),
                    makv2_baud=payload.get("makv2_baud", 4000000),
                )
            elif mode == "DHZ":
                success, error = switch_backend(
                    "DHZ",
                    dhz_ip=payload.get("dhz_ip", ""),
                    dhz_port=payload.get("dhz_port", ""),
                    dhz_random=payload.get("dhz_random", 0),
                )
            else:
                success, error = switch_backend(
                    "Serial",
                    serial_port_mode=payload.get("serial_port_mode", "Auto"),
                    serial_port=payload.get("serial_port", ""),
                )
        except Exception as e:
            success, error = False, str(e)

        self.after(0, lambda: self._on_mouse_api_connect_done(job_id, mode, payload, success, error))

    def _on_mouse_api_connect_done(self, job_id, mode, payload, success, error):
        # Ignore stale callback results.
        if job_id != getattr(self, "_mouse_api_connect_job_id", 0):
            return

        self._mouse_api_connecting = False
        if success:
            if mode == "Net":
                self._set_status_indicator("Status: Mouse API connected (Net)", COLOR_TEXT)
            elif mode == "KmboxA":
                self._set_status_indicator("Status: Mouse API connected (KmboxA)", COLOR_TEXT)
            elif mode == "Arduino":
                self._set_status_indicator("Status: Mouse API connected (Arduino)", COLOR_TEXT)
            elif mode == "SendInput":
                self._set_status_indicator("Status: Mouse API connected (SendInput)", COLOR_TEXT)
            elif mode == "MakV2":
                self._set_status_indicator("Status: Mouse API connected (MakV2)", COLOR_TEXT)
            elif mode == "DHZ":
                self._set_status_indicator("Status: Mouse API connected (DHZ)", COLOR_TEXT)
            else:
                self._set_status_indicator("Status: Mouse API connected (Serial)", COLOR_TEXT)
            return

        self._set_status_indicator(f"Status: Mouse API error: {error}", COLOR_DANGER)

    def _check_mouse_api_connect_timeout(self, job_id, mode):
        if not getattr(self, "_mouse_api_connecting", False):
            return
        if job_id != getattr(self, "_mouse_api_connect_job_id", 0):
            return

        # Invalidate current job, ignore late callback from blocked worker.
        self._mouse_api_connect_job_id += 1
        self._mouse_api_connecting = False
        self._set_status_indicator(f"Status: Mouse API timeout ({mode})", COLOR_DANGER)

    def _update_capture_ui(self):
        """鏍规摎閬告搰鐨勬崟鐛叉柟娉曟洿鏂?UI"""
        # 淇濆瓨鐣跺墠 UDP 杓稿叆妗嗙殑鍊硷紙濡傛灉瀛樺湪锛?
        if hasattr(self, 'udp_ip_entry') and self.udp_ip_entry.winfo_exists():
            self.saved_udp_ip = self.udp_ip_entry.get()
        if hasattr(self, 'udp_port_entry') and self.udp_port_entry.winfo_exists():
            self.saved_udp_port = self.udp_port_entry.get()
        
        # 淇濆瓨鐣跺墠 NDI 閬告搰鐨勬簮锛堝鏋滃瓨鍦級
        if hasattr(self, 'source_option') and self.source_option.winfo_exists():
            current_selection = self.source_option.get()
            if current_selection not in ["(Scanning...)", "(no sources)"]:
                self.saved_ndi_source = current_selection
        
        # 娓呴櫎鑸婄殑 UI 鍏冪礌
        for widget in self.capture_content_frame.winfo_children():
            widget.destroy()
        
        # Add FPS Limit control at the top (applies to all capture methods)
        self._add_subtitle_in_frame(self.capture_content_frame, "PROCESSING FPS LIMIT")
        
        fps_limit_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
        fps_limit_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(fps_limit_frame, text="Target FPS", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        self.fps_limit_entry = ctk.CTkEntry(fps_limit_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
        self.fps_limit_entry.pack(side="right")
        target_fps = str(getattr(config, "target_fps", 80))
        self.fps_limit_entry.insert(0, target_fps)
        self.fps_limit_entry.bind("<KeyRelease>", self._on_fps_limit_changed)
        self.fps_limit_entry.bind("<FocusOut>", self._on_fps_limit_changed)
        
        self._add_spacer_in_frame(self.capture_content_frame)
            
        method = self.capture_method_var.get()
        
        if method == "NDI":
            # NDI Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "NDI SOURCE")
            self.source_option = self._add_option_menu(["(Scanning...)"], self._on_source_selected, parent=self.capture_content_frame)
            self.source_option.pack(fill="x", pady=5)
            
            # 濡傛灉鏈変繚瀛樼殑 NDI 婧愶紝鍢楄│鎭㈠京
            if self.saved_ndi_source:
                # 绋嶅緦鍦?_apply_sources_to_ui 涓渻鏇存柊婧愬垪琛ㄤ甫鎭㈠京閬告搰
                pass
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "REFRESH", self._refresh_sources).pack(side="left")
            self._add_text_button(btn_frame, "CONNECT", self._connect_to_selected).pack(side="left", padx=15)
            
            # NDI FOV 瑁佸垏瑷畾
            self._add_spacer_in_frame(self.capture_content_frame)
            self._add_subtitle_in_frame(self.capture_content_frame, "CENTER CROP (FOV)")
            
            # Enable FOV Crop Checkbox
            if not hasattr(self, 'var_ndi_fov_enabled'):
                self.var_ndi_fov_enabled = tk.BooleanVar(value=getattr(config, "ndi_fov_enabled", False))
            
            fov_enable_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_enable_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(fov_enable_frame, text="Enable Center Crop", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            ndi_fov_switch = ctk.CTkSwitch(
                fov_enable_frame,
                text="",
                variable=self.var_ndi_fov_enabled,
                command=self._on_ndi_fov_enabled_changed,
                fg_color=COLOR_BORDER,
                progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT,
                button_hover_color=COLOR_ACCENT_HOVER,
                width=50,
                height=20
            )
            ndi_fov_switch.pack(side="right")
            
            # FOV Slider (姝ｆ柟褰㈣鍒囷紝鍙渶瑕佷竴鍊嬪€?
            fov_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_frame.pack(fill="x", pady=2)
            fov_header = ctk.CTkFrame(fov_frame, fg_color="transparent")
            fov_header.pack(fill="x")
            ctk.CTkLabel(fov_header, text="FOV (half-size, square crop)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.ndi_fov_entry = ctk.CTkEntry(
                fov_header, width=80, height=25, fg_color=COLOR_SURFACE,
                border_width=1, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, font=FONT_MAIN, justify="center"
            )
            init_fov = int(getattr(config, "ndi_fov", 320))
            self.ndi_fov_entry.insert(0, str(init_fov))
            self.ndi_fov_entry.pack(side="right")
            
            self.ndi_fov_slider = ctk.CTkSlider(
                fov_frame, from_=16, to=1920, number_of_steps=100,
                fg_color=COLOR_BORDER, progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT, button_hover_color=COLOR_ACCENT,
                height=10,
                command=self._on_ndi_fov_slider_changed
            )
            self.ndi_fov_slider.set(init_fov)
            self.ndi_fov_slider.pack(fill="x", pady=(2, 5))
            self.ndi_fov_entry.bind("<Return>", self._on_ndi_fov_entry_changed)
            self.ndi_fov_entry.bind("<FocusOut>", self._on_ndi_fov_entry_changed)
            
            # 瑁佸垏绡勫湇璩囪▕
            total_size = init_fov * 2
            self.ndi_fov_info_label = ctk.CTkLabel(
                self.capture_content_frame,
                text=f"Crop area: {total_size} x {total_size} px (square, centered on frame)",
                font=("Roboto", 9), text_color=COLOR_TEXT_DIM
            )
            self.ndi_fov_info_label.pack(anchor="w", pady=(0, 5))
            
        elif method == "UDP":
            # UDP Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "UDP SETTINGS")
            
            # IP Input - 浣跨敤淇濆瓨鐨勫€?
            ip_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            ip_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(ip_frame, text="IP Address", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.udp_ip_entry = ctk.CTkEntry(ip_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.udp_ip_entry.pack(side="right")
            self.udp_ip_entry.insert(0, self.saved_udp_ip)
            # 缍佸畾浜嬩欢浠ュ鏅備繚瀛?
            self.udp_ip_entry.bind("<KeyRelease>", self._on_udp_ip_changed)
            self.udp_ip_entry.bind("<FocusOut>", self._on_udp_ip_changed)
            
            # Port Input - 浣跨敤淇濆瓨鐨勫€?
            port_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            port_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(port_frame, text="Port", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.udp_port_entry = ctk.CTkEntry(port_frame, fg_color=COLOR_SURFACE, border_width=0, text_color=COLOR_TEXT, width=150)
            self.udp_port_entry.pack(side="right")
            self.udp_port_entry.insert(0, self.saved_udp_port)
            # 缍佸畾浜嬩欢浠ュ鏅備繚瀛?
            self.udp_port_entry.bind("<KeyRelease>", self._on_udp_port_changed)
            self.udp_port_entry.bind("<FocusOut>", self._on_udp_port_changed)
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "CONNECT", self._connect_udp).pack(side="left")
            
            # UDP FOV 瑁佸垏瑷畾
            self._add_spacer_in_frame(self.capture_content_frame)
            self._add_subtitle_in_frame(self.capture_content_frame, "CENTER CROP (FOV)")
            
            # Enable FOV Crop Checkbox
            if not hasattr(self, 'var_udp_fov_enabled'):
                self.var_udp_fov_enabled = tk.BooleanVar(value=getattr(config, "udp_fov_enabled", False))
            
            fov_enable_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_enable_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(fov_enable_frame, text="Enable Center Crop", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            udp_fov_switch = ctk.CTkSwitch(
                fov_enable_frame,
                text="",
                variable=self.var_udp_fov_enabled,
                command=self._on_udp_fov_enabled_changed,
                fg_color=COLOR_BORDER,
                progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT,
                button_hover_color=COLOR_ACCENT_HOVER,
                width=50,
                height=20
            )
            udp_fov_switch.pack(side="right")
            
            # FOV Slider (姝ｆ柟褰㈣鍒囷紝鍙渶瑕佷竴鍊嬪€?
            fov_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_frame.pack(fill="x", pady=2)
            fov_header = ctk.CTkFrame(fov_frame, fg_color="transparent")
            fov_header.pack(fill="x")
            ctk.CTkLabel(fov_header, text="FOV (half-size, square crop)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.udp_fov_entry = ctk.CTkEntry(
                fov_header, width=80, height=25, fg_color=COLOR_SURFACE,
                border_width=1, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, font=FONT_MAIN, justify="center"
            )
            init_fov = int(getattr(config, "udp_fov", 320))
            self.udp_fov_entry.insert(0, str(init_fov))
            self.udp_fov_entry.pack(side="right")
            
            self.udp_fov_slider = ctk.CTkSlider(
                fov_frame, from_=16, to=1920, number_of_steps=100,
                fg_color=COLOR_BORDER, progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT, button_hover_color=COLOR_ACCENT,
                height=10,
                command=self._on_udp_fov_slider_changed
            )
            self.udp_fov_slider.set(init_fov)
            self.udp_fov_slider.pack(fill="x", pady=(2, 5))
            self.udp_fov_entry.bind("<Return>", self._on_udp_fov_entry_changed)
            self.udp_fov_entry.bind("<FocusOut>", self._on_udp_fov_entry_changed)
            
            # 瑁佸垏绡勫湇璩囪▕
            total_size = init_fov * 2
            self.udp_fov_info_label = ctk.CTkLabel(
                self.capture_content_frame,
                text=f"Crop area: {total_size} x {total_size} px (square, centered on frame)",
                font=("Roboto", 9), text_color=COLOR_TEXT_DIM
            )
            self.udp_fov_info_label.pack(anchor="w", pady=(0, 5))
            
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
            
            # 椤ず涓績榛炰俊鎭?
            center_info_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            center_info_frame.pack(fill="x", pady=5)
            self.capture_card_center_label = ctk.CTkLabel(
                center_info_frame, 
                text="Center: (0, 0)", 
                font=("Roboto", 10), 
                text_color=COLOR_TEXT_DIM
            )
            self.capture_card_center_label.pack(side="left")
            # 鏇存柊涓績榛為’绀?
            self._update_capture_card_center_display()
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "CONNECT", self._connect_capture_card).pack(side="left")
        
        elif method == "MSS":
            # MSS Screen Capture Controls
            self._add_subtitle_in_frame(self.capture_content_frame, "MSS SCREEN CAPTURE")
            ctk.CTkLabel(
                self.capture_content_frame,
                text="For dual-PC streaming users (e.g., Moonlight), pair MSS with SendInput.",
                font=("Roboto", 10, "bold"),
                text_color=COLOR_DANGER,
            ).pack(anchor="w", pady=(0, 8))
            
            # Monitor Index
            monitor_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            monitor_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(monitor_frame, text="Monitor Index", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.mss_monitor_entry = ctk.CTkEntry(
                monitor_frame, fg_color=COLOR_SURFACE, border_width=0,
                text_color=COLOR_TEXT, width=150
            )
            self.mss_monitor_entry.pack(side="right")
            self.mss_monitor_entry.insert(0, str(getattr(config, "mss_monitor_index", 1)))
            self.mss_monitor_entry.bind("<KeyRelease>", self._on_mss_monitor_changed)
            self.mss_monitor_entry.bind("<FocusOut>", self._on_mss_monitor_changed)
            
            # 鍙敤铻㈠箷鍒楄〃璩囪▕
            try:
                from src.capture.mss_capture import MSSCapture, HAS_MSS
                if HAS_MSS:
                    temp_mss = MSSCapture()
                    monitor_list = temp_mss.get_monitor_list()
                    if monitor_list:
                        info_text = " | ".join(monitor_list)
                    else:
                        info_text = "No monitors detected"
                else:
                    info_text = "mss not installed (pip install mss)"
            except Exception:
                info_text = "Unable to detect monitors"
            
            ctk.CTkLabel(
                self.capture_content_frame, text=info_text,
                font=("Roboto", 9), text_color=COLOR_TEXT_DIM
            ).pack(anchor="w", pady=(0, 5))
            
            self._add_spacer_in_frame(self.capture_content_frame)
            self._add_subtitle_in_frame(self.capture_content_frame, "CAPTURE FOV (center-based)")
            
            # FOV X Slider
            fov_x_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_x_frame.pack(fill="x", pady=2)
            fov_x_header = ctk.CTkFrame(fov_x_frame, fg_color="transparent")
            fov_x_header.pack(fill="x")
            ctk.CTkLabel(fov_x_header, text="FOV X (half-width)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.mss_fov_x_entry = ctk.CTkEntry(
                fov_x_header, width=80, height=25, fg_color=COLOR_SURFACE,
                border_width=1, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, font=FONT_MAIN, justify="center"
            )
            init_fov_x = int(getattr(config, "mss_fov_x", 320))
            self.mss_fov_x_entry.insert(0, str(init_fov_x))
            self.mss_fov_x_entry.pack(side="right")
            
            self.mss_fov_x_slider = ctk.CTkSlider(
                fov_x_frame, from_=16, to=1920, number_of_steps=100,
                fg_color=COLOR_BORDER, progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT, button_hover_color=COLOR_ACCENT,
                height=10,
                command=self._on_mss_fov_x_slider_changed
            )
            self.mss_fov_x_slider.set(init_fov_x)
            self.mss_fov_x_slider.pack(fill="x", pady=(2, 5))
            self.mss_fov_x_entry.bind("<Return>", self._on_mss_fov_x_entry_changed)
            self.mss_fov_x_entry.bind("<FocusOut>", self._on_mss_fov_x_entry_changed)
            
            # FOV Y Slider
            fov_y_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            fov_y_frame.pack(fill="x", pady=2)
            fov_y_header = ctk.CTkFrame(fov_y_frame, fg_color="transparent")
            fov_y_header.pack(fill="x")
            ctk.CTkLabel(fov_y_header, text="FOV Y (half-height)", font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
            self.mss_fov_y_entry = ctk.CTkEntry(
                fov_y_header, width=80, height=25, fg_color=COLOR_SURFACE,
                border_width=1, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, font=FONT_MAIN, justify="center"
            )
            init_fov_y = int(getattr(config, "mss_fov_y", 320))
            self.mss_fov_y_entry.insert(0, str(init_fov_y))
            self.mss_fov_y_entry.pack(side="right")
            
            self.mss_fov_y_slider = ctk.CTkSlider(
                fov_y_frame, from_=16, to=1080, number_of_steps=100,
                fg_color=COLOR_BORDER, progress_color=COLOR_TEXT,
                button_color=COLOR_TEXT, button_hover_color=COLOR_ACCENT,
                height=10,
                command=self._on_mss_fov_y_slider_changed
            )
            self.mss_fov_y_slider.set(init_fov_y)
            self.mss_fov_y_slider.pack(fill="x", pady=(2, 5))
            self.mss_fov_y_entry.bind("<Return>", self._on_mss_fov_y_entry_changed)
            self.mss_fov_y_entry.bind("<FocusOut>", self._on_mss_fov_y_entry_changed)
            
            # 鎿峰彇绡勫湇璩囪▕
            total_w = init_fov_x * 2
            total_h = init_fov_y * 2
            self.mss_capture_info_label = ctk.CTkLabel(
                self.capture_content_frame,
                text=f"Capture area: {total_w} x {total_h} px (centered on screen)",
                font=("Roboto", 9), text_color=COLOR_TEXT_DIM
            )
            self.mss_capture_info_label.pack(anchor="w", pady=(0, 5))
            
            btn_frame = ctk.CTkFrame(self.capture_content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=10)
            self._add_text_button(btn_frame, "CONNECT", self._connect_mss).pack(side="left")

    def _on_udp_ip_changed(self, event=None):
        """瀵︽檪淇濆瓨 UDP IP"""
        if hasattr(self, 'udp_ip_entry') and self.udp_ip_entry.winfo_exists():
            val = self.udp_ip_entry.get()
            self.saved_udp_ip = val
            config.udp_ip = val

    def _on_udp_port_changed(self, event=None):
        """瀵︽檪淇濆瓨 UDP Port"""
        if hasattr(self, 'udp_port_entry') and self.udp_port_entry.winfo_exists():
            val = self.udp_port_entry.get()
            self.saved_udp_port = val
            config.udp_port = val
    
    def _on_capture_card_device_changed(self, event=None):
        """瀵︽檪淇濆瓨 CaptureCard Device Index"""
        if hasattr(self, 'capture_card_device_entry') and self.capture_card_device_entry.winfo_exists():
            try:
                val = int(self.capture_card_device_entry.get())
                config.capture_device_index = val
            except ValueError:
                pass
    
    def _on_capture_card_resolution_changed(self, event=None):
        """瀵︽檪淇濆瓨 CaptureCard Resolution"""
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
        """瀵︽檪淇濆瓨 CaptureCard FPS"""
        if hasattr(self, 'capture_card_fps_entry') and self.capture_card_fps_entry.winfo_exists():
            try:
                val = float(self.capture_card_fps_entry.get())
                config.capture_fps = val
            except ValueError:
                pass
    
    def _on_fps_limit_changed(self, event=None):
        """Handle FPS limit change"""
        try:
            if not hasattr(self, 'fps_limit_entry'):
                return
            fps = float(self.fps_limit_entry.get())
            if fps < 1 or fps > 1000:
                fps = 80
                self.fps_limit_entry.delete(0, "end")
                self.fps_limit_entry.insert(0, "80")
            config.target_fps = fps
            config.save_to_file()
            # Update tracker's target FPS dynamically
            if hasattr(self, 'tracker') and self.tracker:
                if hasattr(self.tracker, 'set_target_fps'):
                    self.tracker.set_target_fps(fps)
                else:
                    self.tracker._target_fps = float(fps)
        except ValueError:
            pass
    
    def _on_capture_card_range_keyrelease(self, event=None):
        """鍦ㄨ几鍏ラ亷绋嬩腑鏇存柊涓績榛為’绀猴紙涓嶅挤鍒朵慨鏀硅几鍏ユ锛?"""
        if hasattr(self, 'capture_card_range_x_entry') and hasattr(self, 'capture_card_range_y_entry'):
            if self.capture_card_range_x_entry.winfo_exists() and self.capture_card_range_y_entry.winfo_exists():
                try:
                    range_x_str = self.capture_card_range_x_entry.get()
                    range_y_str = self.capture_card_range_y_entry.get()
                    
                    # 濡傛灉鏄┖瀛楃涓诧紝涓嶈檿鐞嗭紙鍏佽ū鐢ㄦ埗娓呯┖杓稿叆锛?
                    if not range_x_str or not range_y_str:
                        return
                    
                    range_x = int(range_x_str)
                    range_y = int(range_y_str)
                    
                    # 鍙洿鏂颁腑蹇冮粸椤ず锛屼笉鏇存柊閰嶇疆锛堥厤缃湪澶卞幓鐒﹂粸鏅傛洿鏂帮級
                    # 鍏佽ū鐢ㄦ埗杓稿叆浠讳綍鏁稿瓧锛岄璀夊湪澶卞幓鐒﹂粸鏅傞€茶
                    # 鏇存柊涓績榛為’绀猴紙浣跨敤杓稿叆鐨勫€硷紝鍗充娇灏忔柤128涔熼’绀猴級
                    self._update_capture_card_center_display_with_values(range_x, range_y)
                except ValueError:
                    # 濡傛灉杓稿叆涓嶆槸鏁稿瓧锛屼笉铏曠悊锛堝厑瑷辩敤鎴剁辜绾岃几鍏ワ級
                    pass
    
    def _on_capture_card_range_focusout(self, event=None):
        """澶卞幓鐒﹂粸鏅傞璀変甫淇 CaptureCard Range"""
        if hasattr(self, 'capture_card_range_x_entry') and hasattr(self, 'capture_card_range_y_entry'):
            if self.capture_card_range_x_entry.winfo_exists() and self.capture_card_range_y_entry.winfo_exists():
                try:
                    range_x_str = self.capture_card_range_x_entry.get()
                    range_y_str = self.capture_card_range_y_entry.get()
                    
                    # 濡傛灉鏄┖瀛楃涓诧紝鎭㈠京鐐洪粯瑾嶅€?
                    if not range_x_str:
                        range_x = 128
                        self.capture_card_range_x_entry.delete(0, "end")
                        self.capture_card_range_x_entry.insert(0, "128")
                    else:
                        range_x = int(range_x_str)
                        # 纰轰繚鏈€浣庡€肩偤 128
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
                        # 纰轰繚鏈€浣庡€肩偤 128
                        if range_y < 128:
                            range_y = 128
                            self.capture_card_range_y_entry.delete(0, "end")
                            self.capture_card_range_y_entry.insert(0, "128")
                    
                    # 鏇存柊閰嶇疆
                    config.capture_range_x = range_x
                    config.capture_range_y = range_y
                    # 鏇存柊涓績榛為’绀?
                    self._update_capture_card_center_display()
                except ValueError:
                    # 濡傛灉杓稿叆涓嶆槸鏁稿瓧锛屾仮寰╃偤鏈夋晥鍊?
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
                    
                    # 鏇存柊涓績榛為’绀?
                    self._update_capture_card_center_display()
    
    def _update_capture_card_center_display(self):
        """鏇存柊 CaptureCard 涓績榛為’绀猴紙寰?config 璁€鍙栵級"""
        if hasattr(self, 'capture_card_center_label') and self.capture_card_center_label.winfo_exists():
            try:
                range_x = int(getattr(config, "capture_range_x", 128))
                range_y = int(getattr(config, "capture_range_y", 128))
                
                # 纰轰繚鏈€浣庡€肩偤 128
                if range_x < 128:
                    range_x = 128
                if range_y < 128:
                    range_y = 128
                
                # 濡傛灉绡勫湇鐐?0 鎴栨湭瑷疆锛屼娇鐢ㄩ粯瑾嶅€兼垨鍒嗚鲸鐜?
                if range_x <= 0:
                    range_x = max(128, int(getattr(config, "capture_width", 1920)))
                if range_y <= 0:
                    range_y = max(128, int(getattr(config, "capture_height", 1080)))
                
                # 瑷堢畻涓績榛烇細鍩烘柤 range_x 鍜?range_y 鐨?X/2, Y/2
                center_x = range_x // 2
                center_y = range_y // 2
                
                self.capture_card_center_label.configure(
                    text=f"Center: ({center_x}, {center_y}) | Range: {range_x}x{range_y}"
                )
            except (ValueError, AttributeError):
                self.capture_card_center_label.configure(text="Center: (0, 0)")
    
    def _update_capture_card_center_display_with_values(self, range_x, range_y):
        """鏇存柊 CaptureCard 涓績榛為’绀猴紙浣跨敤鎸囧畾鐨勫€硷級"""
        if hasattr(self, 'capture_card_center_label') and self.capture_card_center_label.winfo_exists():
            try:
                # 浣跨敤鍌冲叆鐨勫€硷紙鍗充娇灏忔柤128涔熼’绀猴紝璁撶敤鎴剁湅鍒拌几鍏ョ殑鍊硷級
                if range_x <= 0:
                    range_x = max(128, int(getattr(config, "capture_width", 1920)))
                if range_y <= 0:
                    range_y = max(128, int(getattr(config, "capture_height", 1080)))
                
                # 瑷堢畻涓績榛烇細鍩烘柤 range_x 鍜?range_y 鐨?X/2, Y/2
                center_x = range_x // 2
                center_y = range_y // 2
                
                self.capture_card_center_label.configure(
                    text=f"Center: ({center_x}, {center_y}) | Range: {range_x}x{range_y}"
                )
            except (ValueError, AttributeError):
                self.capture_card_center_label.configure(text="Center: (0, 0)")

    def _show_aimbot_tab(self):
        self._active_tab_name = "Main Aimbot"
        self._clear_content()
        self._add_title("Main Aimbot")
        
        self.var_enableaim = tk.BooleanVar(value=getattr(config, "enableaim", False))
        self._add_switch("Enable Aimbot", self.var_enableaim, self._on_enableaim_changed)
        self._checkbox_vars["enableaim"] = self.var_enableaim
        
        # Anti-Smoke Switch
        self.var_anti_smoke = tk.BooleanVar(value=getattr(config, "anti_smoke_enabled", False))
        self._add_switch("Enable Anti-Smoke", self.var_anti_smoke, self._on_anti_smoke_changed)
        self._checkbox_vars["anti_smoke_enabled"] = self.var_anti_smoke
        
        # 鈹€鈹€ OPERATION MODE (collapsible) 鈹€鈹€
        sec_mode = self._create_collapsible_section(self.content_frame, "Operation Mode", initially_open=True)
        self.mode_option = self._add_option_row_in_frame(sec_mode, "Mode", ["Normal", "Silent", "NCAF", "WindMouse", "Bezier"], self._on_mode_selected)
        self._option_widgets["mode"] = self.mode_option
        current_mode = getattr(config, "mode", "Normal")
        self.mode_option.set(current_mode)
        
        # 鈹€鈹€ MODE PARAMETERS (collapsible) 鈹€鈹€
        sec_params = self._create_collapsible_section(
            self.content_frame,
            f"{current_mode} Parameters",
            initially_open=True,
            state_key="mode_parameters",
        )
        
        if current_mode == "Normal":
            self._add_subtitle_in_frame(sec_params, "SENSITIVITY")
            self._add_slider_in_frame(sec_params, "X-Speed", "normal_x_speed", 0.1, 2000,
                                      float(getattr(config, "normal_x_speed", 0.5)),
                                      self._on_normal_x_speed_changed)
            self._add_slider_in_frame(sec_params, "Y-Speed", "normal_y_speed", 0.1, 2000,
                                      float(getattr(config, "normal_y_speed", 0.5)),
                                      self._on_normal_y_speed_changed)
            self._add_slider_in_frame(sec_params, "Smoothing", "normalsmooth", 1, 30,
                                      float(getattr(config, "normalsmooth", 10)),
                                      self._on_config_normal_smooth_changed)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize", 1, 1000,
                                      float(getattr(config, "fovsize", 300)),
                                      self._on_fovsize_changed)
            self._add_slider_in_frame(sec_params, "FOV Smooth", "normalsmoothfov", 1, 30,
                                      float(getattr(config, "normalsmoothfov", 10)),
                                      self._on_config_normal_smoothfov_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=False)
        
        elif current_mode == "Silent":
            self._add_subtitle_in_frame(sec_params, "SILENT PARAMETERS")
            self._add_slider_in_frame(sec_params, "Distance (Multiplier)", "silent_distance", 0.1, 10.0,
                                      float(getattr(config, "silent_distance", 1.0)),
                                      self._on_silent_distance_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Delay (ms)", "silent_delay", 0.001, 300.0,
                                      float(getattr(config, "silent_delay", 100.0)),
                                      self._on_silent_delay_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Move Delay (ms)", "silent_move_delay", 0.001, 300.0,
                                      float(getattr(config, "silent_move_delay", 500.0)),
                                      self._on_silent_move_delay_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Return Delay (ms)", "silent_return_delay", 0.001, 300.0,
                                      float(getattr(config, "silent_return_delay", 500.0)),
                                      self._on_silent_return_delay_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize", 1, 1000,
                                      float(getattr(config, "fovsize", 300)),
                                      self._on_fovsize_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=False)
        
        elif current_mode == "NCAF":
            self._add_subtitle_in_frame(sec_params, "NCAF PARAMETERS")
            self._add_slider_in_frame(sec_params, "Alpha (Speed Curve)", "ncaf_alpha", 0.1, 5.0,
                                      float(getattr(config, "ncaf_alpha", 1.5)),
                                      self._on_ncaf_alpha_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Snap Boost Factor", "ncaf_snap_boost", 0.01, 2.0,
                                      float(getattr(config, "ncaf_snap_boost", 0.3)),
                                      self._on_ncaf_snap_boost_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Step", "ncaf_max_step", 1, 200,
                                      float(getattr(config, "ncaf_max_step", 50)),
                                      self._on_ncaf_max_step_changed)
            self._add_slider_in_frame(sec_params, "Min Speed Multiplier", "ncaf_min_speed_multiplier", 0.01, 1.0,
                                      float(getattr(config, "ncaf_min_speed_multiplier", 0.01)),
                                      self._on_ncaf_min_speed_multiplier_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Speed Multiplier", "ncaf_max_speed_multiplier", 1.0, 20.0,
                                      float(getattr(config, "ncaf_max_speed_multiplier", 10.0)),
                                      self._on_ncaf_max_speed_multiplier_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Prediction Interval (ms)", "ncaf_prediction_interval", 1, 100,
                                      float(getattr(config, "ncaf_prediction_interval", 0.016)) * 1000,
                                      self._on_ncaf_prediction_interval_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "Snap Radius (Outer)", "ncaf_snap_radius", 10, 500,
                                      float(getattr(config, "ncaf_snap_radius", 150)),
                                      self._on_ncaf_snap_radius_changed)
            self._add_slider_in_frame(sec_params, "Near Radius (Inner)", "ncaf_near_radius", 5, 400,
                                      float(getattr(config, "ncaf_near_radius", 50)),
                                      self._on_ncaf_near_radius_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=False)
        
        elif current_mode == "WindMouse":
            self._add_subtitle_in_frame(sec_params, "WINDMOUSE PARAMETERS")
            self._add_slider_in_frame(sec_params, "Gravity", "wm_gravity", 0.1, 30.0,
                                      float(getattr(config, "wm_gravity", 9.0)),
                                      self._on_wm_gravity_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Wind", "wm_wind", 0.1, 20.0,
                                      float(getattr(config, "wm_wind", 3.0)),
                                      self._on_wm_wind_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Step", "wm_max_step", 1, 100,
                                      float(getattr(config, "wm_max_step", 15)),
                                      self._on_wm_max_step_changed)
            self._add_slider_in_frame(sec_params, "Min Step", "wm_min_step", 0.1, 20,
                                      float(getattr(config, "wm_min_step", 2)),
                                      self._on_wm_min_step_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Min Delay (ms)", "wm_min_delay", 0.1, 50,
                                      float(getattr(config, "wm_min_delay", 0.001)) * 1000,
                                      self._on_wm_min_delay_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Delay (ms)", "wm_max_delay", 0.1, 50,
                                      float(getattr(config, "wm_max_delay", 0.003)) * 1000,
                                      self._on_wm_max_delay_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Distance Threshold", "wm_distance_threshold", 10, 200,
                                      float(getattr(config, "wm_distance_threshold", 50)),
                                      self._on_wm_distance_threshold_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize", 1, 1000,
                                      float(getattr(config, "fovsize", 300)),
                                      self._on_fovsize_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=False)
        
        elif current_mode == "Bezier":
            self._add_subtitle_in_frame(sec_params, "BEZIER PARAMETERS")
            self._add_slider_in_frame(sec_params, "Segments", "bezier_segments", 1, 30,
                                      float(getattr(config, "bezier_segments", 8)),
                                      self._on_bezier_segments_changed)
            self._add_slider_in_frame(sec_params, "Ctrl X", "bezier_ctrl_x", 0.0, 100.0,
                                      float(getattr(config, "bezier_ctrl_x", 16.0)),
                                      self._on_bezier_ctrl_x_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Ctrl Y", "bezier_ctrl_y", 0.0, 100.0,
                                      float(getattr(config, "bezier_ctrl_y", 16.0)),
                                      self._on_bezier_ctrl_y_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Speed", "bezier_speed", 0.1, 20.0,
                                      float(getattr(config, "bezier_speed", 1.0)),
                                      self._on_bezier_speed_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Delay (ms)", "bezier_delay", 0.1, 50.0,
                                      float(getattr(config, "bezier_delay", 0.002)) * 1000,
                                      self._on_bezier_delay_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize", 1, 1000,
                                      float(getattr(config, "fovsize", 300)),
                                      self._on_fovsize_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=False)
        
        # 鈹€鈹€ OFFSET (collapsible) 鈹€鈹€
        sec_offset = self._create_collapsible_section(self.content_frame, "Offset", initially_open=False)
        self._add_slider_in_frame(sec_offset, "X-Offset", "aim_offsetX", -100, 100,
                                  float(getattr(config, "aim_offsetX", 0)),
                                  self._on_aim_offsetX_changed)
        self._add_slider_in_frame(sec_offset, "Y-Offset", "aim_offsetY", -100, 100,
                                  float(getattr(config, "aim_offsetY", 0)),
                                  self._on_aim_offsetY_changed)
        
        # 鈹€鈹€ AIM TYPE (collapsible) 鈹€鈹€
        sec_aim_type = self._create_collapsible_section(self.content_frame, "Aim Type", initially_open=False)
        self.aim_type_option = self._add_option_row_in_frame(sec_aim_type, "Target", ["head", "body", "nearest"], self._on_aim_type_selected)
        self._option_widgets["aim_type"] = self.aim_type_option
        current_aim_type = getattr(config, "aim_type", "head")
        self.aim_type_option.set(current_aim_type)
        
        # 鈹€鈹€ ACTIVATION (collapsible) 鈹€鈹€
        sec_activation = self._create_collapsible_section(self.content_frame, "Activation", initially_open=False)
        current_btn = self._ads_binding_to_display(getattr(config, "selected_mouse_button", 3))
        self.aim_key_bind_button = self._add_bind_capture_row_in_frame(
            sec_activation,
            "Keybind",
            current_btn,
            lambda: self._start_aim_key_capture(is_sec=False),
        )
        
        # Activation Type
        activation_types = ["Hold to Enable", "Hold to Disable", "Toggle", "Press to Enable"]
        activation_type_map = {
            "Hold to Enable": "hold_enable",
            "Hold to Disable": "hold_disable",
            "Toggle": "toggle",
            "Press to Enable": "use_enable"
        }
        self.aimbot_activation_type_option = self._add_option_row_in_frame(sec_activation, "Type", activation_types, self._on_aimbot_activation_type_selected)
        self._option_widgets["aimbot_activation_type"] = self.aimbot_activation_type_option
        current_activation_type = getattr(config, "aimbot_activation_type", "hold_enable")
        # 鍙嶅悜鏄犲皠锛氬緸閰嶇疆鍊兼壘鍒伴’绀哄悕绋?
        for display_name, config_value in activation_type_map.items():
            if config_value == current_activation_type:
                self.aimbot_activation_type_option.set(display_name)
                break
        else:
            self.aimbot_activation_type_option.set("Hold to Enable")

        current_ads_key = self._ads_binding_to_display(getattr(config, "ads_key", "Right Mouse Button"))
        self.ads_key_bind_button = self._add_bind_capture_row_in_frame(
            sec_activation,
            "ADS Keybind",
            current_ads_key,
            lambda: self._start_ads_key_capture(is_sec=False),
        )
        self.ads_key_type_option = self._add_option_row_in_frame(
            sec_activation,
            "ADS Key Type",
            list(ADS_KEY_TYPE_DISPLAY_TO_VALUE.keys()),
            self._on_ads_key_type_selected,
        )
        self._option_widgets["ads_key_type"] = self.ads_key_type_option
        current_ads_key_type = str(getattr(config, "ads_key_type", "hold")).strip().lower()
        self.ads_key_type_option.set(ADS_KEY_TYPE_VALUE_TO_DISPLAY.get(current_ads_key_type, "Hold"))

    def _show_sec_aimbot_tab(self):
        self._active_tab_name = "Sec Aimbot"
        self._clear_content()
        self._add_title("Secondary Aimbot")
        
        self.var_enableaim_sec = tk.BooleanVar(value=getattr(config, "enableaim_sec", False))
        self._add_switch("Enable Sec Aimbot", self.var_enableaim_sec, self._on_enableaim_sec_changed)
        self._checkbox_vars["enableaim_sec"] = self.var_enableaim_sec
        
        # Anti-Smoke Switch for Sec Aimbot
        self.var_anti_smoke_sec = tk.BooleanVar(value=getattr(config, "anti_smoke_enabled_sec", False))
        self._add_switch("Enable Anti-Smoke", self.var_anti_smoke_sec, self._on_anti_smoke_sec_changed)
        self._checkbox_vars["anti_smoke_enabled_sec"] = self.var_anti_smoke_sec
        
        # 鈹€鈹€ OPERATION MODE (collapsible) 鈹€鈹€
        sec_mode = self._create_collapsible_section(self.content_frame, "Operation Mode", initially_open=True)
        self.mode_option_sec = self._add_option_row_in_frame(sec_mode, "Mode", ["Normal", "Silent", "NCAF", "WindMouse", "Bezier"], self._on_mode_sec_selected)
        self._option_widgets["mode_sec"] = self.mode_option_sec
        current_mode_sec = getattr(config, "mode_sec", "Normal")
        self.mode_option_sec.set(current_mode_sec)
        
        # 鈹€鈹€ MODE PARAMETERS (collapsible) 鈹€鈹€
        sec_params = self._create_collapsible_section(
            self.content_frame,
            f"{current_mode_sec} Parameters",
            initially_open=True,
            state_key="mode_parameters",
        )
        
        if current_mode_sec == "Normal":
            self._add_subtitle_in_frame(sec_params, "SENSITIVITY")
            self._add_slider_in_frame(sec_params, "X-Speed", "normal_x_speed_sec", 0.1, 2000,
                                      float(getattr(config, "normal_x_speed_sec", 2)),
                                      self._on_normal_x_speed_sec_changed)
            self._add_slider_in_frame(sec_params, "Y-Speed", "normal_y_speed_sec", 0.1, 2000,
                                      float(getattr(config, "normal_y_speed_sec", 2)),
                                      self._on_normal_y_speed_sec_changed)
            self._add_slider_in_frame(sec_params, "Smoothing", "normalsmooth_sec", 1, 30,
                                      float(getattr(config, "normalsmooth_sec", 20)),
                                      self._on_config_normal_smooth_sec_changed)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize_sec", 1, 1000,
                                      float(getattr(config, "fovsize_sec", 150)),
                                      self._on_fovsize_sec_changed)
            self._add_slider_in_frame(sec_params, "FOV Smooth", "normalsmoothfov_sec", 1, 30,
                                      float(getattr(config, "normalsmoothfov_sec", 20)),
                                      self._on_config_normal_smoothfov_sec_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=True)
        
        elif current_mode_sec == "Silent":
            self._add_subtitle_in_frame(sec_params, "SENSITIVITY")
            self._add_slider_in_frame(sec_params, "X-Speed", "normal_x_speed_sec", 0.1, 2000,
                                      float(getattr(config, "normal_x_speed_sec", 2)),
                                      self._on_normal_x_speed_sec_changed)
            self._add_slider_in_frame(sec_params, "Y-Speed", "normal_y_speed_sec", 0.1, 2000,
                                      float(getattr(config, "normal_y_speed_sec", 2)),
                                      self._on_normal_y_speed_sec_changed)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize_sec", 1, 1000,
                                      float(getattr(config, "fovsize_sec", 150)),
                                      self._on_fovsize_sec_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=True)
        
        elif current_mode_sec == "NCAF":
            self._add_subtitle_in_frame(sec_params, "NCAF PARAMETERS")
            self._add_slider_in_frame(sec_params, "Alpha (Speed Curve)", "ncaf_alpha_sec", 0.1, 5.0,
                                      float(getattr(config, "ncaf_alpha_sec", 1.5)),
                                      self._on_ncaf_alpha_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Snap Boost Factor", "ncaf_snap_boost_sec", 0.01, 2.0,
                                      float(getattr(config, "ncaf_snap_boost_sec", 0.3)),
                                      self._on_ncaf_snap_boost_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Step", "ncaf_max_step_sec", 1, 200,
                                      float(getattr(config, "ncaf_max_step_sec", 50)),
                                      self._on_ncaf_max_step_sec_changed)
            self._add_slider_in_frame(sec_params, "Min Speed Multiplier", "ncaf_min_speed_multiplier_sec", 0.01, 1.0,
                                      float(getattr(config, "ncaf_min_speed_multiplier_sec", 0.01)),
                                      self._on_ncaf_min_speed_multiplier_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Speed Multiplier", "ncaf_max_speed_multiplier_sec", 1.0, 20.0,
                                      float(getattr(config, "ncaf_max_speed_multiplier_sec", 10.0)),
                                      self._on_ncaf_max_speed_multiplier_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Prediction Interval (ms)", "ncaf_prediction_interval_sec", 1, 100,
                                      float(getattr(config, "ncaf_prediction_interval_sec", 0.016)) * 1000,
                                      self._on_ncaf_prediction_interval_sec_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "Snap Radius (Outer)", "ncaf_snap_radius_sec", 10, 500,
                                      float(getattr(config, "ncaf_snap_radius_sec", 150)),
                                      self._on_ncaf_snap_radius_sec_changed)
            self._add_slider_in_frame(sec_params, "Near Radius (Inner)", "ncaf_near_radius_sec", 5, 400,
                                      float(getattr(config, "ncaf_near_radius_sec", 50)),
                                      self._on_ncaf_near_radius_sec_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=True)
        
        elif current_mode_sec == "WindMouse":
            self._add_subtitle_in_frame(sec_params, "WINDMOUSE PARAMETERS")
            self._add_slider_in_frame(sec_params, "Gravity", "wm_gravity_sec", 0.1, 30.0,
                                      float(getattr(config, "wm_gravity_sec", 9.0)),
                                      self._on_wm_gravity_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Wind", "wm_wind_sec", 0.1, 20.0,
                                      float(getattr(config, "wm_wind_sec", 3.0)),
                                      self._on_wm_wind_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Step", "wm_max_step_sec", 1, 100,
                                      float(getattr(config, "wm_max_step_sec", 15)),
                                      self._on_wm_max_step_sec_changed)
            self._add_slider_in_frame(sec_params, "Min Step", "wm_min_step_sec", 0.1, 20,
                                      float(getattr(config, "wm_min_step_sec", 2)),
                                      self._on_wm_min_step_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Min Delay (ms)", "wm_min_delay_sec", 0.1, 50,
                                      float(getattr(config, "wm_min_delay_sec", 0.001)) * 1000,
                                      self._on_wm_min_delay_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Max Delay (ms)", "wm_max_delay_sec", 0.1, 50,
                                      float(getattr(config, "wm_max_delay_sec", 0.003)) * 1000,
                                      self._on_wm_max_delay_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Distance Threshold", "wm_distance_threshold_sec", 10, 200,
                                      float(getattr(config, "wm_distance_threshold_sec", 50)),
                                      self._on_wm_distance_threshold_sec_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize_sec", 1, 1000,
                                      float(getattr(config, "fovsize_sec", 150)),
                                      self._on_fovsize_sec_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=True)
        
        elif current_mode_sec == "Bezier":
            self._add_subtitle_in_frame(sec_params, "BEZIER PARAMETERS")
            self._add_slider_in_frame(sec_params, "Segments", "bezier_segments_sec", 1, 30,
                                      float(getattr(config, "bezier_segments_sec", 8)),
                                      self._on_bezier_segments_sec_changed)
            self._add_slider_in_frame(sec_params, "Ctrl X", "bezier_ctrl_x_sec", 0.0, 100.0,
                                      float(getattr(config, "bezier_ctrl_x_sec", 16.0)),
                                      self._on_bezier_ctrl_x_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Ctrl Y", "bezier_ctrl_y_sec", 0.0, 100.0,
                                      float(getattr(config, "bezier_ctrl_y_sec", 16.0)),
                                      self._on_bezier_ctrl_y_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Speed", "bezier_speed_sec", 0.1, 20.0,
                                      float(getattr(config, "bezier_speed_sec", 1.0)),
                                      self._on_bezier_speed_sec_changed, is_float=True)
            self._add_slider_in_frame(sec_params, "Delay (ms)", "bezier_delay_sec", 0.1, 50.0,
                                      float(getattr(config, "bezier_delay_sec", 0.002)) * 1000,
                                      self._on_bezier_delay_sec_changed, is_float=True)
            self._add_spacer_in_frame(sec_params)
            self._add_subtitle_in_frame(sec_params, "FOV")
            self._add_slider_in_frame(sec_params, "FOV Size", "fovsize_sec", 1, 1000,
                                      float(getattr(config, "fovsize_sec", 150)),
                                      self._on_fovsize_sec_changed)
            self._add_ads_fov_controls_in_frame(sec_params, is_sec=True)
        
        # 鈹€鈹€ OFFSET (collapsible) 鈹€鈹€
        sec_offset = self._create_collapsible_section(self.content_frame, "Offset", initially_open=False)
        self._add_slider_in_frame(sec_offset, "X-Offset", "aim_offsetX_sec", -100, 100,
                                  float(getattr(config, "aim_offsetX_sec", 0)),
                                  self._on_aim_offsetX_sec_changed)
        self._add_slider_in_frame(sec_offset, "Y-Offset", "aim_offsetY_sec", -100, 100,
                                  float(getattr(config, "aim_offsetY_sec", 0)),
                                  self._on_aim_offsetY_sec_changed)
        
        # 鈹€鈹€ AIM TYPE (collapsible) 鈹€鈹€
        sec_aim_type = self._create_collapsible_section(self.content_frame, "Aim Type", initially_open=False)
        self.aim_type_option_sec = self._add_option_row_in_frame(sec_aim_type, "Target", ["head", "body", "nearest"], self._on_aim_type_sec_selected)
        self._option_widgets["aim_type_sec"] = self.aim_type_option_sec
        current_aim_type_sec = getattr(config, "aim_type_sec", "head")
        self.aim_type_option_sec.set(current_aim_type_sec)
        
        # 鈹€鈹€ ACTIVATION (collapsible) 鈹€鈹€
        sec_activation = self._create_collapsible_section(self.content_frame, "Activation", initially_open=False)
        current_btn_sec = self._ads_binding_to_display(getattr(config, "selected_mouse_button_sec", 2))
        self.aim_key_bind_button_sec = self._add_bind_capture_row_in_frame(
            sec_activation,
            "Keybind",
            current_btn_sec,
            lambda: self._start_aim_key_capture(is_sec=True),
        )
        
        # Activation Type
        activation_types = ["Hold to Enable", "Hold to Disable", "Toggle", "Press to Enable"]
        activation_type_map = {
            "Hold to Enable": "hold_enable",
            "Hold to Disable": "hold_disable",
            "Toggle": "toggle",
            "Press to Enable": "use_enable"
        }
        self.aimbot_activation_type_option_sec = self._add_option_row_in_frame(sec_activation, "Type", activation_types, self._on_aimbot_activation_type_sec_selected)
        self._option_widgets["aimbot_activation_type_sec"] = self.aimbot_activation_type_option_sec
        current_activation_type_sec = getattr(config, "aimbot_activation_type_sec", "hold_enable")
        # 鍙嶅悜鏄犲皠锛氬緸閰嶇疆鍊兼壘鍒伴’绀哄悕绋?
        for display_name, config_value in activation_type_map.items():
            if config_value == current_activation_type_sec:
                self.aimbot_activation_type_option_sec.set(display_name)
                break
        else:
            self.aimbot_activation_type_option_sec.set("Hold to Enable")

        current_ads_key_sec = self._ads_binding_to_display(getattr(config, "ads_key_sec", "Right Mouse Button"))
        self.ads_key_bind_button_sec = self._add_bind_capture_row_in_frame(
            sec_activation,
            "ADS Keybind",
            current_ads_key_sec,
            lambda: self._start_ads_key_capture(is_sec=True),
        )
        self.ads_key_type_option_sec = self._add_option_row_in_frame(
            sec_activation,
            "ADS Key Type",
            list(ADS_KEY_TYPE_DISPLAY_TO_VALUE.keys()),
            self._on_ads_key_type_sec_selected,
        )
        self._option_widgets["ads_key_type_sec"] = self.ads_key_type_option_sec
        current_ads_key_type_sec = str(getattr(config, "ads_key_type_sec", "hold")).strip().lower()
        self.ads_key_type_option_sec.set(
            ADS_KEY_TYPE_VALUE_TO_DISPLAY.get(current_ads_key_type_sec, "Hold")
        )

    def _show_tb_tab(self):
        self._active_tab_name = "Trigger"
        self._clear_content()
        self._add_title("Triggerbot")

        current_trigger_type = str(getattr(config, "trigger_type", "current")).strip().lower()
        if current_trigger_type not in TRIGGER_TYPE_DISPLAY:
            current_trigger_type = "current"
            config.trigger_type = current_trigger_type

        sec_core = self._create_collapsible_section(self.content_frame, "Core", initially_open=True)
        self.var_enabletb = tk.BooleanVar(value=getattr(config, "enabletb", False))
        self._add_switch_in_frame(sec_core, "Enable Triggerbot", self.var_enabletb, self._on_enabletb_changed)
        self._checkbox_vars["enabletb"] = self.var_enabletb

        self.trigger_type_option = self._add_option_row_in_frame(
            sec_core,
            "Trigger Type",
            list(TRIGGER_TYPE_DISPLAY.values()),
            self._on_trigger_type_selected,
        )
        self._option_widgets["trigger_type"] = self.trigger_type_option
        self.trigger_type_option.set(TRIGGER_TYPE_DISPLAY.get(current_trigger_type, "Classic Trigger"))

        if current_trigger_type == "rgb":
            sec_rgb = self._create_collapsible_section(self.content_frame, "RGB Parameters", initially_open=True)

            self._add_slider_in_frame(
                sec_rgb,
                "FOV Size",
                "tbfovsize",
                1,
                300,
                float(getattr(config, "tbfovsize", 70)),
                self._on_tbfovsize_changed,
            )
            self._add_trigger_ads_fov_controls_in_frame(sec_rgb)

            self.rgb_color_profile_option = self._add_option_row_in_frame(
                sec_rgb,
                "RGB Preset",
                list(RGB_TRIGGER_PROFILE_DISPLAY.values()),
                self._on_rgb_color_profile_selected,
            )
            self._option_widgets["rgb_color_profile"] = self.rgb_color_profile_option
            current_rgb_profile = str(getattr(config, "rgb_color_profile", "purple")).strip().lower()
            if current_rgb_profile not in RGB_TRIGGER_PROFILE_DISPLAY:
                current_rgb_profile = "purple"
                config.rgb_color_profile = "purple"
            self.rgb_color_profile_option.set(
                RGB_TRIGGER_PROFILE_DISPLAY.get(current_rgb_profile, "Purple")
            )

            self._add_range_slider_in_frame(
                sec_rgb,
                "Delay Range (s)",
                "rgb_tbdelay",
                0.0,
                1.0,
                float(getattr(config, "rgb_tbdelay_min", 0.08)),
                float(getattr(config, "rgb_tbdelay_max", 0.15)),
                self._on_rgb_tbdelay_range_changed,
                is_float=True,
            )
            self._add_range_slider_in_frame(
                sec_rgb,
                "Hold Range (ms)",
                "rgb_tbhold",
                5,
                500,
                float(getattr(config, "rgb_tbhold_min", 40)),
                float(getattr(config, "rgb_tbhold_max", 60)),
                self._on_rgb_tbhold_range_changed,
                is_float=False,
            )
            self._add_range_slider_in_frame(
                sec_rgb,
                "Cooldown Range (s)",
                "rgb_tbcooldown",
                0.0,
                5.0,
                float(getattr(config, "rgb_tbcooldown_min", 0.0)),
                float(getattr(config, "rgb_tbcooldown_max", 0.0)),
                self._on_rgb_tbcooldown_range_changed,
                is_float=True,
            )
        else:
            sec_params = self._create_collapsible_section(self.content_frame, "Parameters", initially_open=True)
            self._add_slider_in_frame(
                sec_params,
                "FOV Size",
                "tbfovsize",
                1,
                300,
                float(getattr(config, "tbfovsize", 70)),
                self._on_tbfovsize_changed,
            )
            self._add_trigger_ads_fov_controls_in_frame(sec_params)
            self._add_range_slider_in_frame(
                sec_params,
                "Delay Range (s)",
                "tbdelay",
                0.0,
                1.0,
                float(getattr(config, "tbdelay_min", 0.08)),
                float(getattr(config, "tbdelay_max", 0.15)),
                self._on_tbdelay_range_changed,
                is_float=True,
            )
            self._add_range_slider_in_frame(
                sec_params,
                "Hold Range (ms)",
                "tbhold",
                5,
                500,
                float(getattr(config, "tbhold_min", 40)),
                float(getattr(config, "tbhold_max", 60)),
                self._on_tbhold_range_changed,
                is_float=False,
            )

            sec_conditions = self._create_collapsible_section(
                self.content_frame,
                "Trigger Conditions",
                initially_open=False,
            )
            self._add_slider_in_frame(
                sec_conditions,
                "Min Pixels",
                "trigger_min_pixels",
                1,
                200,
                int(getattr(config, "trigger_min_pixels", 4)),
                self._on_trigger_min_pixels_changed,
                is_float=False,
            )
            self._add_slider_in_frame(
                sec_conditions,
                "Min Ratio",
                "trigger_min_ratio",
                0.0,
                1.0,
                float(getattr(config, "trigger_min_ratio", 0.03)),
                self._on_trigger_min_ratio_changed,
                is_float=True,
            )
            self._add_slider_in_frame(
                sec_conditions,
                "Confirm Frames",
                "trigger_confirm_frames",
                1,
                10,
                int(getattr(config, "trigger_confirm_frames", 2)),
                self._on_trigger_confirm_frames_changed,
                is_float=False,
            )

            sec_burst = self._create_collapsible_section(self.content_frame, "Burst Settings", initially_open=False)
            self._add_range_slider_in_frame(
                sec_burst,
                "Cooldown Range (s)",
                "tbcooldown",
                0.0,
                5.0,
                float(getattr(config, "tbcooldown_min", 0.0)),
                float(getattr(config, "tbcooldown_max", 0.0)),
                self._on_tbcooldown_range_changed,
                is_float=True,
            )
            self._add_range_slider_in_frame(
                sec_burst,
                "Burst Count Range",
                "tbburst_count",
                1,
                10,
                int(getattr(config, "tbburst_count_min", 1)),
                int(getattr(config, "tbburst_count_max", 1)),
                self._on_tbburst_count_range_changed,
                is_float=False,
            )
            self._add_range_slider_in_frame(
                sec_burst,
                "Burst Interval Range (ms)",
                "tbburst_interval",
                0,
                500,
                float(getattr(config, "tbburst_interval_min", 0.0)),
                float(getattr(config, "tbburst_interval_max", 0.0)),
                self._on_tbburst_interval_range_changed,
                is_float=True,
            )

        sec_activation = self._create_collapsible_section(self.content_frame, "Activation", initially_open=False)
        current_tb_btn = self._ads_binding_to_display(getattr(config, "selected_tb_btn", 3))
        self.tb_key_bind_button = self._add_bind_capture_row_in_frame(
            sec_activation,
            "Keybind",
            current_tb_btn,
            self._start_trigger_key_capture,
        )

        trigger_activation_types = ["Hold to Enable", "Hold to Disable", "Toggle"]
        self.trigger_activation_type_option = self._add_option_row_in_frame(
            sec_activation,
            "Trigger Mode",
            trigger_activation_types,
            self._on_trigger_activation_type_selected,
        )
        self._option_widgets["trigger_activation_type"] = self.trigger_activation_type_option
        current_trigger_activation_type = str(
            getattr(config, "trigger_activation_type", "hold_enable")
        ).strip().lower()
        trigger_activation_display = {
            "hold_enable": "Hold to Enable",
            "hold_disable": "Hold to Disable",
            "toggle": "Toggle",
        }
        self.trigger_activation_type_option.set(
            trigger_activation_display.get(current_trigger_activation_type, "Hold to Enable")
        )

        current_trigger_ads_key = self._ads_binding_to_display(
            getattr(config, "trigger_ads_key", "Right Mouse Button")
        )
        self.trigger_ads_key_bind_button = self._add_bind_capture_row_in_frame(
            sec_activation,
            "ADS Keybind",
            current_trigger_ads_key,
            self._start_trigger_ads_key_capture,
        )
        self.trigger_ads_key_type_option = self._add_option_row_in_frame(
            sec_activation,
            "ADS Key Type",
            list(ADS_KEY_TYPE_DISPLAY_TO_VALUE.keys()),
            self._on_trigger_ads_key_type_selected,
        )
        self._option_widgets["trigger_ads_key_type"] = self.trigger_ads_key_type_option
        current_trigger_ads_key_type = str(
            getattr(config, "trigger_ads_key_type", "hold")
        ).strip().lower()
        self.trigger_ads_key_type_option.set(
            ADS_KEY_TYPE_VALUE_TO_DISPLAY.get(current_trigger_ads_key_type, "Hold")
        )

        if self._supports_trigger_strafe_ui():
            sec_strafe_helper = self._create_collapsible_section(
                self.content_frame,
                "Strafe Helper",
                initially_open=False,
            )
            self.trigger_strafe_mode_option = self._add_option_row_in_frame(
                sec_strafe_helper,
                "Mode",
                list(TRIGGER_STRAFE_MODE_DISPLAY.values()),
                self._on_trigger_strafe_mode_selected,
            )
            self._option_widgets["trigger_strafe_mode"] = self.trigger_strafe_mode_option
            current_strafe_mode = str(getattr(config, "trigger_strafe_mode", "off")).strip().lower()
            if current_strafe_mode not in TRIGGER_STRAFE_MODE_DISPLAY:
                current_strafe_mode = "off"
                config.trigger_strafe_mode = "off"
            self.trigger_strafe_mode_option.set(
                TRIGGER_STRAFE_MODE_DISPLAY.get(current_strafe_mode, "Off")
            )

            if current_strafe_mode == "auto":
                self._add_slider_in_frame(
                    sec_strafe_helper,
                    "Auto Lead (ms)",
                    "trigger_strafe_auto_lead_ms",
                    0,
                    50,
                    int(getattr(config, "trigger_strafe_auto_lead_ms", 8)),
                    self._on_trigger_strafe_auto_lead_ms_changed,
                    is_float=False,
                )
            elif current_strafe_mode == "manual_wait":
                self._add_slider_in_frame(
                    sec_strafe_helper,
                    "Neutral Wait (ms)",
                    "trigger_strafe_manual_neutral_ms",
                    0,
                    300,
                    int(getattr(config, "trigger_strafe_manual_neutral_ms", 0)),
                    self._on_trigger_strafe_manual_neutral_ms_changed,
                    is_float=False,
                )
        else:
            config.trigger_strafe_mode = "off"

    def _show_rcs_tab(self):
        """椤ず RCS 瑷疆妯欑堡"""
        self._active_tab_name = "RCS"
        self._clear_content()
        self._add_title("RCS (Recoil Control System)")
        
        # RCS 闁嬮棞
        self.var_enablercs = tk.BooleanVar(value=getattr(config, "enablercs", False))
        self._add_switch("Enable RCS", self.var_enablercs, self._on_enablercs_changed)
        self._checkbox_vars["enablercs"] = self.var_enablercs
        
        self._add_spacer()
        self._add_subtitle("PARAMETERS")
        
        # Pull Speed (鍠粦濉?
        self._add_slider(
            "Pull Speed", 
            "rcs_pull_speed", 
            1, 20,
            int(getattr(config, "rcs_pull_speed", 10)),
            self._on_rcs_pull_speed_changed,
            is_float=False
        )
        
        # Activation Delay (鍠粦濉?
        self._add_slider(
            "Activation Delay (ms)", 
            "rcs_activation_delay", 
            50, 500,
            int(getattr(config, "rcs_activation_delay", 100)),
            self._on_rcs_activation_delay_changed,
            is_float=False
        )
        
        # Rapid Click Threshold (鍠粦濉?
        self._add_slider(
            "Rapid Click Threshold (ms)", 
            "rcs_rapid_click_threshold", 
            100, 1000,
            int(getattr(config, "rcs_rapid_click_threshold", 200)),
            self._on_rcs_rapid_click_threshold_changed,
            is_float=False
        )
        
        self._add_spacer()
        self._add_subtitle("Y-AXIS RELEASE")
        
        # Release Y-Axis on Fire 闁嬮棞
        self.var_rcs_release_y_enabled = tk.BooleanVar(value=getattr(config, "rcs_release_y_enabled", False))
        self._add_switch("Release Y-Axis on Fire", self.var_rcs_release_y_enabled, self._on_rcs_release_y_enabled_changed)
        self._checkbox_vars["rcs_release_y_enabled"] = self.var_rcs_release_y_enabled
        
        # Release Duration (鍠粦濉?
        self._add_slider(
            "Release Duration (s)", 
            "rcs_release_y_duration", 
            0.1, 5.0,
            float(getattr(config, "rcs_release_y_duration", 1.0)),
            self._on_rcs_release_y_duration_changed,
            is_float=True
        )

    def _show_config_tab(self):
        self._active_tab_name = "Config"
        self._clear_content()
        self._add_title("Configuration")
        
        os.makedirs("configs", exist_ok=True)
        
        self.config_option = self._add_option_menu([], self._on_config_selected)
        self.config_option.pack(fill="x", pady=10)
        
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        self._add_text_button(btn_frame, "SAVE", self._save_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "LOAD", self._load_selected_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "DEL", self._delete_selected_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "NEW", self._save_new_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "EXPORT", self._export_selected_config).pack(side="left", padx=(0, 10))
        self._add_text_button(btn_frame, "IMPORT", self._import_config_file).pack(side="left")
        
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
        self.after(100, self._maybe_prompt_clipboard_config_import)

    def _show_debug_tab(self):
        """椤ず Debug tab - 椤ず婊戦紶绉诲嫊鍜岄粸鎿婃棩瑾?"""
        self._active_tab_name = "Debug"
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

    # --- 妤电啊绲勪欢妲嬪缓鍣?---

    def _add_title(self, text):
        ctk.CTkLabel(self.content_frame, text=text, font=FONT_TITLE, text_color=COLOR_TEXT).pack(anchor="w", pady=(0, 20))

    def _add_subtitle(self, text):
        ctk.CTkLabel(self.content_frame, text=text.upper(), font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(anchor="w", pady=(10, 5))

    def _add_subtitle_in_frame(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(anchor="w", pady=(10, 5))
    
    def _add_spacer_in_frame(self, parent):
        """鍦ㄦ寚瀹?frame 涓坊鍔犻枔璺?"""
        ctk.CTkFrame(parent, height=1, fg_color="transparent").pack(pady=5)
    
    def _create_tooltip(self, widget, text):
        """
        鐐?widget 鍓靛缓 tooltip
        
        Args:
            widget: 瑕佺秮瀹?tooltip 鐨?widget
            text: tooltip 鏂囧瓧鍏у
        """
        tooltip_window = [None]  # 浣跨敤鍒楄〃浠ヤ究鍦ㄥ祵濂楀嚱鏁镐腑淇敼
        
        def show_tooltip(event):
            if tooltip_window[0] is not None:
                return
            
            # 鐛插彇榧犳浣嶇疆
            x = event.x_root + 10
            y = event.y_root + 10
            
            # 鍓靛缓 tooltip 绐楀彛
            tooltip_win = ctk.CTkToplevel(widget)
            tooltip_win.overrideredirect(True)
            tooltip_win.attributes("-topmost", True)
            tooltip_win.configure(fg_color=COLOR_BG)
            
            # 鍓靛缓 tooltip 鍏у
            tooltip_frame = ctk.CTkFrame(tooltip_win, fg_color=COLOR_SURFACE, corner_radius=4)
            tooltip_frame.pack(fill="both", expand=True, padx=1, pady=1)
            
            tooltip_label = ctk.CTkLabel(
                tooltip_frame,
                text=text,
                font=("Roboto", 12.5),
                text_color=COLOR_TEXT,
                justify="left",
                anchor="w",
                wraplength=400
            )
            tooltip_label.pack(anchor="w", padx=12, pady=10)
            
            # 鏇存柊绐楀彛澶у皬涓﹁ō缃綅缃?
            tooltip_win.update_idletasks()
            tooltip_win.geometry(f"+{x}+{y}")
            
            tooltip_window[0] = tooltip_win
        
        def hide_tooltip(event):
            if tooltip_window[0] is not None:
                try:
                    tooltip_window[0].destroy()
                except:
                    pass
                tooltip_window[0] = None
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def _get_collapsible_state_key(self, title, state_key=None):
        tab_key = str(getattr(self, "_active_tab_name", "General")).strip().lower().replace(" ", "_")
        section_key = str(state_key or title).strip().lower().replace(" ", "_")
        return f"{tab_key}:{section_key}"

    def _set_collapsible_state(self, cache_key, is_open):
        self._collapsible_section_states[str(cache_key)] = bool(is_open)
        config.ui_collapsible_states = dict(self._collapsible_section_states)

    def _create_collapsible_section(self, parent, title, initially_open=True, auto_pack=True, tooltip_text=None, state_key=None):
        """
        寤虹珛鍙睍闁?鏀惰捣鐨?section銆?
        
        Args:
            parent: 鐖跺鍣?
            title: section 妯欓
            initially_open: 鏄惁闋愯ō灞曢枊
            auto_pack: 鏄惁鑷嫊 pack container锛團alse 鏅傜敱瑾跨敤鑰呮帶鍒讹級
            tooltip_text: 鍙伕鐨?tooltip 鏂囧瓧锛堝鏋滄彁渚涳紝鏈冨湪妯欓鏃侀’绀哄晱铏熷湒妯欙級
            
        Returns:
            tuple: (content_frame, container) 濡傛灉 auto_pack=False锛屽惁鍓囧彧杩斿洖 content_frame
        """
        container = ctk.CTkFrame(parent, fg_color="transparent")
        if auto_pack:
            container.pack(fill="x", pady=(5, 0))
        
        content = ctk.CTkFrame(container, fg_color="transparent")

        cache_key = self._get_collapsible_state_key(title, state_key=state_key)
        initial_open_state = self._collapsible_section_states.get(cache_key, initially_open)
        initial_open_state = bool(initial_open_state)
        is_open = [initial_open_state]
        arrow_text = "▼" if initial_open_state else "▶"
        
        header = ctk.CTkFrame(container, fg_color=COLOR_SURFACE, corner_radius=4, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        arrow_label = ctk.CTkLabel(
            header, text=arrow_text, font=("Roboto", 10), text_color=COLOR_TEXT_DIM,
            width=20
        )
        arrow_label.pack(side="left", padx=(8, 0))
        
        title_label = ctk.CTkLabel(
            header, text=title.upper(), font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM
        )
        title_label.pack(side="left", padx=(4, 0))
        
        # 濡傛灉鏈?tooltip 鏂囧瓧锛屾坊鍔犲晱铏熷湒妯?
        if tooltip_text:
            tooltip_icon = ctk.CTkLabel(
                header, text="?", font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM,
                width=20, cursor="hand2"
            )
            tooltip_icon.pack(side="left", padx=(8, 0))
            self._create_tooltip(tooltip_icon, tooltip_text)
        
        def toggle(_event=None):
            if is_open[0]:
                content.pack_forget()
                arrow_label.configure(text="▶")
                is_open[0] = False
                self._set_collapsible_state(cache_key, False)
            else:
                content.pack(fill="x", padx=(8, 0), pady=(2, 0))
                arrow_label.configure(text="▼")
                is_open[0] = True
                self._set_collapsible_state(cache_key, True)
        
        header.bind("<Button-1>", toggle)
        arrow_label.bind("<Button-1>", toggle)
        title_label.bind("<Button-1>", toggle)
        
        if initial_open_state:
            content.pack(fill="x", padx=(8, 0), pady=(2, 0))
        self._set_collapsible_state(cache_key, initial_open_state)
        
        if auto_pack:
            return content
        else:
            return content, container

    def _add_slider_in_frame(self, parent, text, key, min_val, max_val, init_val, command, is_float=False):
        """鍦ㄦ寚瀹?parent frame 涓坊鍔?slider锛堣垏 _add_slider 閭忚集涓€鑷达級"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=text, font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        
        val_str = f"{init_val:.2f}" if is_float else f"{int(init_val)}"
        val_entry = ctk.CTkEntry(
            header, width=80, height=25, fg_color=COLOR_SURFACE,
            border_width=1, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, font=FONT_MAIN, justify="center"
        )
        val_entry.insert(0, val_str)
        val_entry.pack(side="right")
        
        slider = ctk.CTkSlider(
            frame, from_=min_val, to=max_val, number_of_steps=100,
            fg_color=COLOR_BORDER, progress_color=COLOR_TEXT,
            button_color=COLOR_TEXT, button_hover_color=COLOR_ACCENT,
            height=10,
            command=lambda v: self._on_slider_changed(v, val_entry, key, command, is_float, slider, min_val, max_val)
        )
        slider.set(init_val)
        slider.pack(fill="x", pady=(2, 5))
        
        val_entry.bind("<Return>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        val_entry.bind("<FocusOut>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        
        self._register_slider(key, slider, val_entry, min_val, max_val, is_float)

    def _add_option_row_in_frame(self, parent, label_text, values, command):
        """鍦ㄦ寚瀹?parent frame 涓坊鍔?OptionMenu锛堣垏 _add_option_row 閭忚集涓€鑷达級"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(frame, text=label_text, font=FONT_MAIN, text_color=COLOR_TEXT).grid(row=0, column=0, sticky="w", padx=(0, 10))
        menu = self._add_option_menu(values, command, parent=frame)
        menu.grid(row=0, column=1, sticky="e")
        return menu

    def _add_bind_capture_row_in_frame(self, parent, label_text, button_text, command):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(frame, text=label_text, font=FONT_MAIN, text_color=COLOR_TEXT).grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        button = ctk.CTkButton(
            frame,
            text=str(button_text),
            command=command,
            font=FONT_MAIN,
            text_color=COLOR_TEXT,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=0,
            height=28,
            width=180,
        )
        button.grid(row=0, column=1, sticky="e")
        return button

    def _add_switch_in_frame(self, parent, text, variable, command):
        """鍦ㄦ寚瀹?parent frame 涓坊鍔?Switch"""
        switch = ctk.CTkSwitch(
            parent, text=text, variable=variable, command=command,
            progress_color=COLOR_TEXT, fg_color=COLOR_BORDER,
            button_color=COLOR_TEXT, button_hover_color=COLOR_TEXT,
            font=FONT_MAIN, text_color=COLOR_TEXT
        )
        switch.pack(anchor="w", pady=5)
        return switch

    def _add_spacer(self):
        ctk.CTkFrame(self.content_frame, height=1, fg_color="transparent").pack(pady=5)

    def _add_switch(self, text, variable, command):
        switch = ctk.CTkSwitch(
            self.content_frame, 
            text=text, 
            variable=variable, 
            command=command,
            progress_color=COLOR_TEXT, # 榛戠櫧棰ㄦ牸
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
        
        # 妯欑堡鑸囪几鍏ユ鍚屽湪涓€琛?
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=text, font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")
        
        # 鍙法杓殑杓稿叆妗嗭紙鏇挎彌鍘熸湰鐨?Label锛?
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
        
        # 缍佸畾杓稿叆妗嗙殑浜嬩欢
        val_entry.bind("<Return>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        val_entry.bind("<FocusOut>", lambda e: self._on_entry_changed(val_entry, slider, key, command, is_float, min_val, max_val))
        
        # 瑷诲唺 slider锛堜繚瀛?entry 寮曠敤鑰屼笉鏄?label锛?
        self._register_slider(key, slider, val_entry, min_val, max_val, is_float)
    
    def _add_range_slider_in_frame(self, parent, text, key, min_val, max_val, init_min, init_max, command, is_float=False):
        self._add_range_slider_to_parent(
            parent,
            text,
            key,
            min_val,
            max_val,
            init_min,
            init_max,
            command,
            is_float=is_float,
        )

    def _add_range_slider(self, text, key, min_val, max_val, init_min, init_max, command, is_float=False):
        self._add_range_slider_to_parent(
            self.content_frame,
            text,
            key,
            min_val,
            max_val,
            init_min,
            init_max,
            command,
            is_float=is_float,
        )

    def _add_range_slider_to_parent(
        self,
        parent,
        text,
        key,
        min_val,
        max_val,
        init_min,
        init_max,
        command,
        is_float=False,
    ):
        """Add a dual-range slider in the given parent frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=text, font=FONT_MAIN, text_color=COLOR_TEXT).pack(side="left")

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
            justify="center",
        )
        max_entry.insert(0, max_str)
        max_entry.pack(side="right", padx=2)

        ctk.CTkLabel(header, text="~", font=("Roboto", 10), text_color=COLOR_TEXT_DIM).pack(side="right")

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
            justify="center",
        )
        min_entry.insert(0, min_str)
        min_entry.pack(side="right", padx=2)

        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(2, 5))

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
            command=lambda v: self._on_range_slider_changed(
                v, "min", min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )
        min_slider.set(init_min)
        min_slider.pack(fill="x", pady=1)

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
            command=lambda v: self._on_range_slider_changed(
                v, "max", min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )
        max_slider.set(init_max)
        max_slider.pack(fill="x", pady=1)

        min_entry.bind(
            "<Return>",
            lambda e: self._on_range_entry_changed(
                min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )
        min_entry.bind(
            "<FocusOut>",
            lambda e: self._on_range_entry_changed(
                min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )
        max_entry.bind(
            "<Return>",
            lambda e: self._on_range_entry_changed(
                min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )
        max_entry.bind(
            "<FocusOut>",
            lambda e: self._on_range_entry_changed(
                min_entry, max_entry, min_slider, max_slider, key, command, is_float, min_val, max_val
            ),
        )

        if not hasattr(self, "_range_slider_widgets"):
            self._range_slider_widgets = {}
        self._range_slider_widgets[key] = {
            "min_slider": min_slider,
            "max_slider": max_slider,
            "min_entry": min_entry,
            "max_entry": max_entry,
            "min_val": min_val,
            "max_val": max_val,
            "is_float": is_float,
        }
    
    def _on_range_slider_changed(self, value, slider_type, min_entry, max_entry, min_slider, max_slider, key, command, is_float, range_min, range_max):
        """鐣剁瘎鍦嶆粦濉婃敼璁婃檪鏇存柊"""
        val = float(value) if is_float else int(round(value))
        
        if slider_type == "min":
            # 纰轰繚 min 涓嶅ぇ鏂?max
            max_val = max_slider.get()
            if is_float:
                max_val = float(max_val)
            else:
                max_val = int(round(max_val))
            
            if val > max_val:
                val = max_val
                min_slider.set(val)
            
            # 鏇存柊杓稿叆妗?
            min_entry.delete(0, "end")
            min_entry.insert(0, f"{val:.2f}" if is_float else f"{val}")
        else:  # max
            # 纰轰繚 max 涓嶅皬鏂?min
            min_val = min_slider.get()
            if is_float:
                min_val = float(min_val)
            else:
                min_val = int(round(min_val))
            
            if val < min_val:
                val = min_val
                max_slider.set(val)
            
            # 鏇存柊杓稿叆妗?
            max_entry.delete(0, "end")
            max_entry.insert(0, f"{val:.2f}" if is_float else f"{val}")
        
        # 瑾跨敤鍥炶
        min_v = min_slider.get()
        max_v = max_slider.get()
        if is_float:
            command(float(min_v), float(max_v))
        else:
            command(int(round(min_v)), int(round(max_v)))
    
    def _on_range_entry_changed(self, min_entry, max_entry, min_slider, max_slider, key, command, is_float, range_min, range_max):
        """鐣剁瘎鍦嶈几鍏ユ鏀硅畩鏅傛洿鏂版粦濉?"""
        try:
            min_val = float(min_entry.get()) if is_float else int(float(min_entry.get()))
            max_val = float(max_entry.get()) if is_float else int(float(max_entry.get()))
            
            # 闄愬埗绡勫湇
            min_val = max(range_min, min(min_val, range_max))
            max_val = max(range_min, min(max_val, range_max))
            
            # 纰轰繚 min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            
            # 鏇存柊婊戝
            min_slider.set(min_val)
            max_slider.set(max_val)
            
            # 鏇存柊杓稿叆妗嗛’绀?
            min_entry.delete(0, "end")
            min_entry.insert(0, f"{min_val:.2f}" if is_float else f"{min_val}")
            max_entry.delete(0, "end")
            max_entry.insert(0, f"{max_val:.2f}" if is_float else f"{max_val}")
            
            # 瑾跨敤鍥炶
            command(min_val, max_val)
        except ValueError:
            # 鐒℃晥杓稿叆锛屾仮寰╁埌鐣跺墠婊戝鍊?
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
        """鐣舵粦姊濇敼璁婃檪鏇存柊杓稿叆妗?"""
        val = float(value) if is_float else int(round(value))
        # 闄愬埗绡勫湇
        val = max(min_val, min(val, max_val))
        
        # 鏇存柊杓稿叆妗?
        entry_widget.delete(0, "end")
        entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")
        
        # 瑾跨敤鍘熷 command
        command(val)

    def _on_entry_changed(self, entry_widget, slider, key, command, is_float, min_val, max_val):
        """鐣惰几鍏ユ鏀硅畩鏅傛洿鏂版粦姊?"""
        try:
            text = entry_widget.get()
            val = float(text) if is_float else int(float(text))
            
            # 闄愬埗绡勫湇
            val = max(min_val, min(val, max_val))
            
            # 鏇存柊婊戞
            slider.set(val)
            
            # 鏇存柊杓稿叆妗嗛’绀猴紙鏍煎紡鍖栵級
            entry_widget.delete(0, "end")
            entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")
            
            # 瑾跨敤鍘熷 command
            command(val)
        except ValueError:
            # 濡傛灉杓稿叆鐒℃晥锛屾仮寰╁埌婊戞鐣跺墠鍊?
            current_val = slider.get()
            val = float(current_val) if is_float else int(round(current_val))
            entry_widget.delete(0, "end")
            entry_widget.insert(0, f"{val:.2f}" if is_float else f"{val}")

    def _add_option_menu(self, values, command, parent=None):
        """鍓靛缓鐛ㄧ珛鐨?OptionMenu"""
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
        """鍓靛缓甯舵绫ょ殑琛屽収 OptionMenu"""
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

    # --- 閭忚集鍔熻兘 ---

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
        # 鏇存柊杓稿叆妗嗚€屼笉鏄绫?
        w["entry"].delete(0, "end")
        w["entry"].insert(0, f"{v:.2f}" if is_float else f"{v}")

    def _set_checkbox_value(self, key, value_bool):
        var = self._checkbox_vars.get(key)
        if var: var.set(bool(value_bool))

    def _set_option_value(self, key, value_str):
        menu = self._option_widgets.get(key)
        if not menu or value_str is None:
            return
        try:
            if hasattr(menu, "winfo_exists") and not bool(menu.winfo_exists()):
                self._option_widgets.pop(key, None)
                return
            menu.set(str(value_str))
        except Exception:
            # Widget was likely destroyed while switching tabs.
            self._option_widgets.pop(key, None)

    def _set_btn_option_value(self, key, value_str):
        self._set_option_value(key, value_str)

    def _add_ads_fov_controls_in_frame(self, parent, is_sec=False):
        if is_sec:
            enabled_key = "ads_fov_enabled_sec"
            slider_key = "ads_fovsize_sec"
            fallback_fov = getattr(config, "fovsize_sec", 150)
            callback_enabled = self._on_ads_fov_enabled_sec_changed
            callback_slider = self._on_ads_fovsize_sec_changed
        else:
            enabled_key = "ads_fov_enabled"
            slider_key = "ads_fovsize"
            fallback_fov = getattr(config, "fovsize", 300)
            callback_enabled = self._on_ads_fov_enabled_changed
            callback_slider = self._on_ads_fovsize_changed

        var = tk.BooleanVar(value=bool(getattr(config, enabled_key, False)))
        if is_sec:
            self.var_ads_fov_enabled_sec = var
        else:
            self.var_ads_fov_enabled = var

        self._add_switch_in_frame(parent, "Enable ADS FOV", var, callback_enabled)
        self._checkbox_vars[enabled_key] = var

        if var.get():
            self._add_slider_in_frame(
                parent,
                "ADS FOV Size",
                slider_key,
                1,
                1000,
                float(getattr(config, slider_key, fallback_fov)),
                callback_slider,
            )

    def _add_trigger_ads_fov_controls_in_frame(self, parent):
        enabled_key = "trigger_ads_fov_enabled"
        slider_key = "trigger_ads_fovsize"
        fallback_fov = getattr(config, "tbfovsize", 70)

        self.var_trigger_ads_fov_enabled = tk.BooleanVar(
            value=bool(getattr(config, enabled_key, False))
        )
        self._add_switch_in_frame(
            parent,
            "Enable Trigger ADS FOV",
            self.var_trigger_ads_fov_enabled,
            self._on_trigger_ads_fov_enabled_changed,
        )
        self._checkbox_vars[enabled_key] = self.var_trigger_ads_fov_enabled

        if self.var_trigger_ads_fov_enabled.get():
            self._add_slider_in_frame(
                parent,
                "Trigger ADS FOV Size",
                slider_key,
                1,
                300,
                float(getattr(config, slider_key, fallback_fov)),
                self._on_trigger_ads_fovsize_changed,
            )

    def _ads_binding_to_display(self, binding_value):
        if binding_value is None:
            return "Right Mouse Button"
        try:
            idx = int(binding_value)
            if idx in BUTTONS:
                return BUTTONS[idx]
        except Exception:
            pass
        raw = str(binding_value).strip()
        if not raw:
            return "Right Mouse Button"
        if raw in BUTTON_NAME_TO_IDX:
            return raw
        if raw.isdigit():
            idx = int(raw)
            if idx in BUTTONS:
                return BUTTONS[idx]
        if raw in ADS_KEY_DISPLAY_TO_BINDING:
            return raw
        token = raw.upper()
        pretty_map = {
            "SPACE": "Space",
            "TAB": "Tab",
            "ENTER": "Enter",
            "ESCAPE": "Esc",
            "LSHIFT": "Left Shift",
            "RSHIFT": "Right Shift",
            "LCONTROL": "Left Ctrl",
            "RCONTROL": "Right Ctrl",
            "LMENU": "Left Alt",
            "RMENU": "Right Alt",
            "UP": "Up Arrow",
            "DOWN": "Down Arrow",
            "LEFT": "Left Arrow",
            "RIGHT": "Right Arrow",
        }
        if token in ADS_KEY_BINDING_TO_DISPLAY:
            return ADS_KEY_BINDING_TO_DISPLAY[token]
        if token in pretty_map:
            return pretty_map[token]
        if len(token) == 1 and token.isalnum():
            return token
        if token.startswith("F") and token[1:].isdigit():
            return token
        return raw

    def _ads_display_to_binding(self, display_value):
        return ADS_KEY_DISPLAY_TO_BINDING.get(str(display_value), "Right Mouse Button")

    def _set_bind_button_text(self, button, text):
        try:
            if button is not None and hasattr(button, "winfo_exists") and bool(button.winfo_exists()):
                button.configure(text=str(text))
        except Exception:
            pass

    def _cancel_binding_capture(self):
        ctx = getattr(self, "_binding_capture_ctx", None)
        if not isinstance(ctx, dict):
            self._binding_capture_ctx = None
            return
        button = ctx.get("button")
        self._set_bind_button_text(button, ctx.get("restore_text", "Set"))
        self._binding_capture_ctx = None

    def _is_binding_pressed_by_backend(self, binding):
        try:
            from src.utils import mouse as mouse_backend
        except Exception:
            return False

        mouse_idx = BUTTON_NAME_TO_IDX.get(str(binding), None)
        try:
            if mouse_idx is not None:
                return bool(mouse_backend.is_button_pressed(int(mouse_idx)))
            return bool(mouse_backend.is_key_pressed(binding))
        except Exception:
            return False

    def _is_input_backend_connected(self):
        try:
            from src.utils import mouse as mouse_backend

            return bool(getattr(mouse_backend, "is_connected", False))
        except Exception:
            return False

    def _get_binding_capture_candidates(self):
        mode = getattr(config, "mouse_api", "Serial")
        keyboard_supported = self._supports_keyboard_state(mode)

        # Keep deterministic order: mouse first, then keyboard.
        candidates = list(BUTTONS.values())
        if keyboard_supported:
            for _, binding in ADS_KEY_DISPLAY_TO_BINDING.items():
                if binding not in candidates:
                    candidates.append(binding)
            for binding in BIND_CAPTURE_KEY_TOKENS:
                if binding not in candidates:
                    candidates.append(binding)
        return candidates, keyboard_supported

    def _normalize_aim_binding_for_config(self, binding):
        if binding is None:
            return 3
        idx = BUTTON_NAME_TO_IDX.get(str(binding), None)
        if idx is not None:
            return int(idx)
        try:
            parsed = int(binding)
            if parsed in BUTTONS:
                return int(parsed)
        except Exception:
            pass
        return str(binding)

    def _start_aim_key_capture(self, is_sec=False):
        config_key = "selected_mouse_button_sec" if is_sec else "selected_mouse_button"
        tracker_key = "selected_mouse_button_sec" if is_sec else "selected_mouse_button"
        button = getattr(self, "aim_key_bind_button_sec" if is_sec else "aim_key_bind_button", None)
        if button is None:
            return

        self._cancel_binding_capture()

        candidates, keyboard_supported = self._get_binding_capture_candidates()
        if not keyboard_supported:
            self._log_config("Current Input API does not expose keyboard state; capture supports mouse buttons only.")
        if not self._is_input_backend_connected():
            self._log_config("Input API is not connected; key capture may timeout.")

        prev_states = {binding: bool(self._is_binding_pressed_by_backend(binding)) for binding in candidates}
        restore_binding = getattr(config, config_key, 2 if is_sec else 3)
        restore_text = self._ads_binding_to_display(restore_binding)

        ctx = {
            "id": int(getattr(self, "_binding_capture_id", 0)) + 1,
            "config_key": config_key,
            "tracker_key": tracker_key,
            "binding_kind": "aim",
            "log_label": "Sec Aim Key" if is_sec else "Aim Key",
            "button": button,
            "restore_text": restore_text,
            "candidates": candidates,
            "prev_states": prev_states,
            "started_at": time.monotonic(),
            "arm_at": time.monotonic() + 0.35,
            "timeout_sec": 10.0,
        }
        self._binding_capture_id = ctx["id"]
        self._binding_capture_ctx = ctx
        self._set_bind_button_text(button, "Press key...")
        self.after(30, lambda capture_id=ctx["id"]: self._poll_binding_capture(capture_id))

    def _start_trigger_key_capture(self):
        config_key = "selected_tb_btn"
        tracker_key = "selected_tb_btn"
        button = getattr(self, "tb_key_bind_button", None)
        if button is None:
            return

        self._cancel_binding_capture()

        candidates, keyboard_supported = self._get_binding_capture_candidates()
        if not keyboard_supported:
            self._log_config("Current Input API does not expose keyboard state; capture supports mouse buttons only.")
        if not self._is_input_backend_connected():
            self._log_config("Input API is not connected; key capture may timeout.")

        prev_states = {binding: bool(self._is_binding_pressed_by_backend(binding)) for binding in candidates}
        restore_binding = getattr(config, config_key, 3)
        restore_text = self._ads_binding_to_display(restore_binding)

        ctx = {
            "id": int(getattr(self, "_binding_capture_id", 0)) + 1,
            "config_key": config_key,
            "tracker_key": tracker_key,
            "binding_kind": "trigger",
            "log_label": "Trigger Key",
            "button": button,
            "restore_text": restore_text,
            "candidates": candidates,
            "prev_states": prev_states,
            "started_at": time.monotonic(),
            "arm_at": time.monotonic() + 0.35,
            "timeout_sec": 10.0,
        }
        self._binding_capture_id = ctx["id"]
        self._binding_capture_ctx = ctx
        self._set_bind_button_text(button, "Press key...")
        self.after(30, lambda capture_id=ctx["id"]: self._poll_binding_capture(capture_id))

    def _start_ads_key_capture(self, is_sec=False):
        key_name = "ads_key_sec" if is_sec else "ads_key"
        tracker_attr = "ads_key_sec" if is_sec else "ads_key"
        button = getattr(self, "ads_key_bind_button_sec" if is_sec else "ads_key_bind_button", None)
        if button is None:
            return

        self._cancel_binding_capture()

        candidates, keyboard_supported = self._get_binding_capture_candidates()
        if not keyboard_supported:
            self._log_config("Current Input API does not expose keyboard state; capture supports mouse buttons only.")
        if not self._is_input_backend_connected():
            self._log_config("Input API is not connected; key capture may timeout.")

        prev_states = {binding: bool(self._is_binding_pressed_by_backend(binding)) for binding in candidates}
        restore_binding = getattr(config, key_name, "Right Mouse Button")
        restore_text = self._ads_binding_to_display(restore_binding)

        ctx = {
            "id": int(getattr(self, "_binding_capture_id", 0)) + 1,
            "config_key": key_name,
            "tracker_key": tracker_attr,
            "binding_kind": "ads",
            "log_label": "Sec ADS Key" if is_sec else "ADS Key",
            "button": button,
            "restore_text": restore_text,
            "candidates": candidates,
            "prev_states": prev_states,
            "started_at": time.monotonic(),
            "arm_at": time.monotonic() + 0.35,
            "timeout_sec": 10.0,
        }
        self._binding_capture_id = ctx["id"]
        self._binding_capture_ctx = ctx
        self._set_bind_button_text(button, "Press key...")
        self.after(30, lambda capture_id=ctx["id"]: self._poll_binding_capture(capture_id))

    def _start_trigger_ads_key_capture(self):
        config_key = "trigger_ads_key"
        tracker_key = "trigger_ads_key"
        button = getattr(self, "trigger_ads_key_bind_button", None)
        if button is None:
            return

        self._cancel_binding_capture()

        candidates, keyboard_supported = self._get_binding_capture_candidates()
        if not keyboard_supported:
            self._log_config("Current Input API does not expose keyboard state; capture supports mouse buttons only.")
        if not self._is_input_backend_connected():
            self._log_config("Input API is not connected; key capture may timeout.")

        prev_states = {binding: bool(self._is_binding_pressed_by_backend(binding)) for binding in candidates}
        restore_binding = getattr(config, config_key, "Right Mouse Button")
        restore_text = self._ads_binding_to_display(restore_binding)

        ctx = {
            "id": int(getattr(self, "_binding_capture_id", 0)) + 1,
            "config_key": config_key,
            "tracker_key": tracker_key,
            "binding_kind": "trigger_ads",
            "log_label": "Trigger ADS Key",
            "button": button,
            "restore_text": restore_text,
            "candidates": candidates,
            "prev_states": prev_states,
            "started_at": time.monotonic(),
            "arm_at": time.monotonic() + 0.35,
            "timeout_sec": 10.0,
        }
        self._binding_capture_id = ctx["id"]
        self._binding_capture_ctx = ctx
        self._set_bind_button_text(button, "Press key...")
        self.after(30, lambda capture_id=ctx["id"]: self._poll_binding_capture(capture_id))

    def _poll_binding_capture(self, capture_id):
        ctx = getattr(self, "_binding_capture_ctx", None)
        if not isinstance(ctx, dict):
            return
        if int(ctx.get("id", -1)) != int(capture_id):
            return

        now = time.monotonic()
        if now - float(ctx.get("started_at", now)) > float(ctx.get("timeout_sec", 10.0)):
            self._set_bind_button_text(ctx.get("button"), ctx.get("restore_text", "Set"))
            self._binding_capture_ctx = None
            label = str(ctx.get("log_label", "Key")).strip()
            self._log_config(f"{label} capture timed out.")
            return

        candidates = list(ctx.get("candidates", []))
        prev_states = dict(ctx.get("prev_states", {}))
        selected_binding = None
        for binding in candidates:
            current_pressed = bool(self._is_binding_pressed_by_backend(binding))
            prev_pressed = bool(prev_states.get(binding, False))
            if now >= float(ctx.get("arm_at", now)) and current_pressed and not prev_pressed:
                selected_binding = binding
                prev_states[binding] = current_pressed
                break
            prev_states[binding] = current_pressed
        ctx["prev_states"] = prev_states

        if selected_binding is not None:
            config_key = str(ctx.get("config_key", "ads_key"))
            tracker_key = str(ctx.get("tracker_key", "ads_key"))
            binding_kind = str(ctx.get("binding_kind", "ads")).strip().lower()
            if binding_kind in {"aim", "trigger"}:
                stored_value = self._normalize_aim_binding_for_config(selected_binding)
            else:
                stored_value = selected_binding

            setattr(config, config_key, stored_value)
            if hasattr(self, "tracker"):
                setattr(self.tracker, tracker_key, stored_value)

            display_name = self._ads_binding_to_display(stored_value)
            self._set_bind_button_text(ctx.get("button"), display_name)
            label = str(ctx.get("log_label", "Key")).strip()
            self._log_config(f"{label}: {display_name}")
            self._binding_capture_ctx = None
            return

        self._binding_capture_ctx = ctx
        self.after(30, lambda: self._poll_binding_capture(capture_id))

    def _get_current_settings(self):
        """鐛插彇鐣跺墠鎵€鏈夎ō缃?- 鐩存帴浣跨敤 config.to_dict() 纰轰繚涓€鑷存€?"""
        return config.to_dict()

    def _load_initial_config(self):
        """鍒濆鍖栨檪杓夊叆閰嶇疆涓︽噳鐢ㄥ埌鎵€鏈?UI 鍏冪礌"""
        try:
            # 閰嶇疆宸茬稉鍦?config.py 鐨?__init__ 涓嚜鍕曡級鍏ヤ簡
            # 鐝惧湪闇€瑕佸皣閰嶇疆鍚屾鍒?tracker 鍜?UI
            self._sync_config_to_tracker()
            
            # 閲嶆柊椤ず鐣跺墠闋侀潰浠ユ洿鏂?UI 鍏冪礌
            # 閫欐渻纰轰繚鎵€鏈?slider銆乧heckbox銆乷ption menu 閮介’绀烘纰虹殑鍊?
            self._handle_nav_click("General", self._show_general_tab)
            
            log_print("[UI] Configuration loaded")
        except Exception as e:
            log_print(f"[UI] Init load error: {e}")
    
    def _sync_config_to_tracker(self):
        """灏?config 涓殑鍊煎悓姝ュ埌 tracker"""
        try:
            # 鍚屾鎵€鏈夊弮鏁?
            self.tracker.normal_x_speed = config.normal_x_speed
            self.tracker.normal_y_speed = config.normal_y_speed
            self.tracker.normalsmooth = config.normalsmooth
            self.tracker.normalsmoothfov = config.normalsmoothfov
            self.tracker.mouse_dpi = config.mouse_dpi
            self.tracker.fovsize = config.fovsize
            self.tracker.ads_fov_enabled = getattr(config, "ads_fov_enabled", False)
            self.tracker.ads_fovsize = getattr(config, "ads_fovsize", config.fovsize)
            self.tracker.ads_key = getattr(config, "ads_key", "Right Mouse Button")
            self.tracker.tbfovsize = config.tbfovsize
            self.tracker.trigger_ads_fov_enabled = getattr(config, "trigger_ads_fov_enabled", False)
            self.tracker.trigger_ads_fovsize = getattr(config, "trigger_ads_fovsize", config.tbfovsize)
            self.tracker.trigger_ads_key = getattr(config, "trigger_ads_key", "Right Mouse Button")
            self.tracker.trigger_ads_key_type = getattr(config, "trigger_ads_key_type", "hold")
            self.tracker.selected_tb_btn = config.selected_tb_btn
            self.tracker.trigger_type = getattr(config, "trigger_type", "current")
            self.tracker.tbdelay_min = config.tbdelay_min
            self.tracker.tbdelay_max = config.tbdelay_max
            self.tracker.tbhold_min = config.tbhold_min
            self.tracker.tbhold_max = config.tbhold_max
            self.tracker.tbcooldown_min = config.tbcooldown_min
            self.tracker.tbcooldown_max = config.tbcooldown_max
            self.tracker.rgb_tbdelay_min = getattr(config, "rgb_tbdelay_min", 0.08)
            self.tracker.rgb_tbdelay_max = getattr(config, "rgb_tbdelay_max", 0.15)
            self.tracker.rgb_tbhold_min = getattr(config, "rgb_tbhold_min", 40)
            self.tracker.rgb_tbhold_max = getattr(config, "rgb_tbhold_max", 60)
            self.tracker.rgb_tbcooldown_min = getattr(config, "rgb_tbcooldown_min", 0.0)
            self.tracker.rgb_tbcooldown_max = getattr(config, "rgb_tbcooldown_max", 0.0)
            self.tracker.rgb_color_profile = getattr(config, "rgb_color_profile", "purple")
            self.tracker.tbburst_count_min = config.tbburst_count_min
            self.tracker.tbburst_count_max = config.tbburst_count_max
            self.tracker.tbburst_interval_min = config.tbburst_interval_min
            self.tracker.tbburst_interval_max = config.tbburst_interval_max
            self.tracker.trigger_roi_size = getattr(config, "trigger_roi_size", 8)
            self.tracker.trigger_min_pixels = getattr(config, "trigger_min_pixels", 4)
            self.tracker.trigger_min_ratio = getattr(config, "trigger_min_ratio", 0.03)
            self.tracker.trigger_confirm_frames = getattr(config, "trigger_confirm_frames", 2)
            self.tracker.switch_confirm_frames = getattr(config, "switch_confirm_frames", 3)
            self.tracker.ema_alpha = getattr(config, "ema_alpha", 0.35)
            if hasattr(self.tracker, "_target_smoother"):
                self.tracker._target_smoother.switch_confirm_frames = int(self.tracker.switch_confirm_frames)
                self.tracker._target_smoother.ema_alpha = float(self.tracker.ema_alpha)
            self.tracker.rcs_pull_speed = config.rcs_pull_speed
            self.tracker.rcs_activation_delay = config.rcs_activation_delay
            self.tracker.rcs_rapid_click_threshold = config.rcs_rapid_click_threshold
            # Silent Mode
            self.tracker.silent_distance = getattr(config, "silent_distance", 1.0)
            self.tracker.silent_delay = getattr(config, "silent_delay", 100.0)
            self.tracker.silent_move_delay = getattr(config, "silent_move_delay", 500.0)
            self.tracker.silent_return_delay = getattr(config, "silent_return_delay", 500.0)
            self.tracker.in_game_sens = config.in_game_sens
            self.tracker.color = config.color
            self.tracker.mode = config.mode
            self.tracker.mode_sec = getattr(config, "mode_sec", "Normal")
            self.tracker.selected_mouse_button = config.selected_mouse_button
            self.tracker.selected_mouse_button_sec = config.selected_mouse_button_sec
            
            # Update target FPS
            target_fps = getattr(config, "target_fps", 80)
            if hasattr(self.tracker, 'set_target_fps'):
                self.tracker.set_target_fps(target_fps)
            else:
                self.tracker._target_fps = float(target_fps)
            
            # Sec Aimbot
            self.tracker.normal_x_speed_sec = config.normal_x_speed_sec
            self.tracker.normal_y_speed_sec = config.normal_y_speed_sec
            self.tracker.normalsmooth_sec = config.normalsmooth_sec
            self.tracker.normalsmoothfov_sec = config.normalsmoothfov_sec
            self.tracker.fovsize_sec = config.fovsize_sec
            self.tracker.ads_fov_enabled_sec = getattr(config, "ads_fov_enabled_sec", False)
            self.tracker.ads_fovsize_sec = getattr(config, "ads_fovsize_sec", config.fovsize_sec)
            self.tracker.ads_key_sec = getattr(config, "ads_key_sec", "Right Mouse Button")
            self.tracker.selected_mouse_button_sec = config.selected_mouse_button_sec
            
        except Exception as e:
            log_print(f"[UI] Sync error: {e}")

    def _apply_settings(self, data, config_name=None):
        try:
            data = self._strip_config_metadata(data)
            for k, v in data.items():
                setattr(config, k, v)
                if hasattr(self.tracker, k):
                    setattr(self.tracker, k, v)
                
                if k in self._slider_widgets: 
                    self._set_slider_value(k, v)
                if k in self._checkbox_vars: 
                    self._set_checkbox_value(k, v)
                if k in self._option_widgets: 
                    if k in ["selected_mouse_button", "selected_mouse_button_sec"]:
                        self._set_btn_option_value(k, BUTTONS.get(v, str(v)))
                    elif k in ("ads_key", "ads_key_sec"):
                        self._set_option_value(k, self._ads_binding_to_display(v))
                    elif k in ("ads_key_type", "ads_key_type_sec"):
                        self._set_option_value(
                            k,
                            ADS_KEY_TYPE_VALUE_TO_DISPLAY.get(str(v).strip().lower(), "Hold"),
                        )
                    elif k == "trigger_ads_key_type":
                        self._set_option_value(
                            k,
                            ADS_KEY_TYPE_VALUE_TO_DISPLAY.get(str(v).strip().lower(), "Hold"),
                        )
                    elif k == "trigger_type":
                        trigger_type_display = {
                            "current": "Classic Trigger",
                            "rgb": "RGB Trigger",
                        }
                        self._set_option_value(k, trigger_type_display.get(str(v).lower(), "Classic Trigger"))
                    elif k == "rgb_color_profile":
                        rgb_profile_display = {
                            "red": "Red",
                            "yellow": "Yellow",
                            "purple": "Purple",
                            "custom": "Custom",
                        }
                        self._set_option_value(k, rgb_profile_display.get(str(v).lower(), "Purple"))
                    elif k == "trigger_activation_type":
                        trigger_activation_display = {
                            "hold_enable": "Hold to Enable",
                            "hold_disable": "Hold to Disable",
                            "toggle": "Toggle",
                        }
                        self._set_option_value(k, trigger_activation_display.get(str(v), "Hold to Enable"))
                    elif k == "trigger_strafe_mode":
                        strafe_mode_display = {
                            "off": "Off",
                            "auto": "Auto Strafe",
                            "manual_wait": "Manual Wait",
                        }
                        self._set_option_value(k, strafe_mode_display.get(str(v), "Off"))
                    else:
                        self._set_option_value(k, v)

                if k == "selected_mouse_button" and hasattr(self, "aim_key_bind_button"):
                    self._set_bind_button_text(self.aim_key_bind_button, self._ads_binding_to_display(v))
                elif k == "selected_mouse_button_sec" and hasattr(self, "aim_key_bind_button_sec"):
                    self._set_bind_button_text(self.aim_key_bind_button_sec, self._ads_binding_to_display(v))
                elif k == "selected_tb_btn" and hasattr(self, "tb_key_bind_button"):
                    self._set_bind_button_text(self.tb_key_bind_button, self._ads_binding_to_display(v))
                elif k == "ads_key" and hasattr(self, "ads_key_bind_button"):
                    self._set_bind_button_text(self.ads_key_bind_button, self._ads_binding_to_display(v))
                elif k == "ads_key_sec" and hasattr(self, "ads_key_bind_button_sec"):
                    self._set_bind_button_text(self.ads_key_bind_button_sec, self._ads_binding_to_display(v))
                elif k == "trigger_ads_key" and hasattr(self, "trigger_ads_key_bind_button"):
                    self._set_bind_button_text(self.trigger_ads_key_bind_button, self._ads_binding_to_display(v))

                if k == "serial_auto_switch_4m":
                    self.saved_serial_auto_switch_4m = bool(v)
                    if hasattr(self, "var_serial_auto_switch_4m"):
                        self.var_serial_auto_switch_4m.set(bool(v))
                
                # 鏇存柊 OpenCV 椤ず瑷疆鐨?UI 璁婇噺
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
                # 鏇存柊 NDI FOV 瑷疆
                elif k == "ndi_fov_enabled" and hasattr(self, "var_ndi_fov_enabled"):
                    self.var_ndi_fov_enabled.set(v)
                elif k == "ndi_fov" and hasattr(self, "ndi_fov_entry") and self.ndi_fov_entry.winfo_exists():
                    self.ndi_fov_entry.delete(0, "end")
                    self.ndi_fov_entry.insert(0, str(v))
                    if hasattr(self, "ndi_fov_slider"):
                        self.ndi_fov_slider.set(v)
                    self._update_ndi_fov_info()
                # 鏇存柊 UDP FOV 瑷疆
                elif k == "udp_fov_enabled" and hasattr(self, "var_udp_fov_enabled"):
                    self.var_udp_fov_enabled.set(v)
                elif k == "udp_fov" and hasattr(self, "udp_fov_entry") and self.udp_fov_entry.winfo_exists():
                    self.udp_fov_entry.delete(0, "end")
                    self.udp_fov_entry.insert(0, str(v))
                    if hasattr(self, "udp_fov_slider"):
                        self.udp_fov_slider.set(v)
                    self._update_udp_fov_info()

            if str(getattr(self, "_active_tab_name", "")) == "Trigger":
                if (
                    "trigger_type" in data
                    or "trigger_strafe_mode" in data
                    or "mouse_api" in data
                    or "selected_tb_btn" in data
                    or "trigger_ads_fov_enabled" in data
                    or "trigger_ads_key" in data
                    or "trigger_ads_key_type" in data
                ):
                    if not self._supports_trigger_strafe_ui(getattr(config, "mouse_api", "Serial")):
                        config.trigger_strafe_mode = "off"
                    self._show_tb_tab()
            if str(getattr(self, "_active_tab_name", "")) == "Main Aimbot":
                if (
                    "mode" in data
                    or "mouse_api" in data
                    or "selected_mouse_button" in data
                    or "ads_fov_enabled" in data
                    or "ads_key" in data
                    or "ads_key_type" in data
                ):
                    self._show_aimbot_tab()
            if str(getattr(self, "_active_tab_name", "")) == "Sec Aimbot":
                if (
                    "mode_sec" in data
                    or "mouse_api" in data
                    or "selected_mouse_button_sec" in data
                    or "ads_fov_enabled_sec" in data
                    or "ads_key_sec" in data
                    or "ads_key_type_sec" in data
                ):
                    self._show_sec_aimbot_tab()

            from src.utils.detection import reload_model
            self.tracker.model, self.tracker.class_names = reload_model()
            
            msg = f"Loaded: {config_name}" if config_name else "Loaded config"
            try:
                self._log_config(f"{msg}")
            except:
                pass
        except Exception as e:
            log_print(f"[UI] Apply error: {e}")
            try:
                self._log_config(f"Apply error: {e}")
            except:
                pass

    def _save_new_config(self):
        name = simpledialog.askstring("Config name", "Enter the config name:")
        if not name:
            return
        self._do_save(name)

    def _save_config(self):
        name = self.config_option.get() or "default"
        self._do_save(name)

    def _normalize_config_display_name(self, name):
        normalized = str(name or "").strip()
        if normalized.lower().endswith(".json"):
            normalized = normalized[:-5]
        if normalized.lower().endswith("_cvm"):
            normalized = normalized[:-4]
        normalized = normalized.strip()
        return normalized or "default"

    def _config_display_name_from_filename(self, filename):
        base_name = str(filename or "").strip()
        if base_name.lower().endswith(".json"):
            base_name = base_name[:-5]
        if base_name.lower().endswith("_cvm"):
            base_name = base_name[:-4]
        base_name = base_name.strip()
        return base_name or "default"

    def _config_filename_from_display_name(self, display_name):
        normalized = self._normalize_config_display_name(display_name)
        return f"{normalized}_cvm.json"

    def _resolve_config_path(self, display_name, force_new_suffix=False):
        normalized = self._normalize_config_display_name(display_name)
        if force_new_suffix:
            filename = self._config_filename_from_display_name(normalized)
        else:
            file_map = getattr(self, "_config_file_map", {})
            filename = file_map.get(normalized) or self._config_filename_from_display_name(normalized)
        return os.path.join("configs", filename), normalized

    def _build_config_payload(self, data):
        payload = {CVM_CONFIG_COMMENT_KEY: CVM_CONFIG_COMMENT_VALUE}
        payload.update(dict(data or {}))
        return payload

    def _strip_config_metadata(self, data):
        if not isinstance(data, dict):
            return {}
        cleaned = dict(data)
        cleaned.pop(CVM_CONFIG_COMMENT_KEY, None)
        return cleaned

    def _has_valid_config_comment(self, data):
        if not isinstance(data, dict):
            return False
        comment = str(data.get(CVM_CONFIG_COMMENT_KEY, "")).strip()
        return comment == CVM_CONFIG_COMMENT_VALUE

    def _config_fingerprint(self, data):
        normalized = self._strip_config_metadata(data)
        try:
            return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            fallback = {str(k): str(v) for k, v in dict(normalized).items()}
            return json.dumps(fallback, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def _load_importable_settings_from_json_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if not isinstance(raw_data, dict):
            raise ValueError("Imported file must contain a JSON object.")
        if not self._has_valid_config_comment(raw_data):
            raise ValueError("Invalid config file: missing CVM colorBot comment marker.")
        settings = self._strip_config_metadata(raw_data)
        if not isinstance(settings, dict):
            raise ValueError("Imported config payload is invalid.")
        return settings

    def _center_modal_window(self, window, width, height):
        try:
            window.update_idletasks()
            if self.winfo_exists():
                x = self.winfo_x() + max(0, (self.winfo_width() - width) // 2)
                y = self.winfo_y() + max(0, (self.winfo_height() - height) // 2)
            else:
                x = max(0, (window.winfo_screenwidth() - width) // 2)
                y = max(0, (window.winfo_screenheight() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            window.geometry(f"{width}x{height}")

    def _ask_dark_yes_no(self, title, message, yes_text="Yes", no_text="No"):
        result = {"value": False}
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLOR_BG)
        dialog.transient(self)
        dialog.grab_set()
        self._center_modal_window(dialog, 460, 190)

        def _close_with(value):
            result["value"] = bool(value)
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", lambda: _close_with(False))

        frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=16, pady=14)

        ctk.CTkLabel(
            frame,
            text=message,
            text_color=COLOR_TEXT,
            font=("Roboto", 12),
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(8, 18))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        ctk.CTkButton(
            btn_row,
            text=no_text,
            command=lambda: _close_with(False),
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            width=100,
        ).pack(side="right")

        ctk.CTkButton(
            btn_row,
            text=yes_text,
            command=lambda: _close_with(True),
            fg_color=COLOR_TEXT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BG,
            width=100,
        ).pack(side="right", padx=(0, 10))

        dialog.wait_window()
        return result["value"]

    def _ask_dark_string(self, title, prompt, initialvalue=""):
        result = {"value": None}
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLOR_BG)
        dialog.transient(self)
        dialog.grab_set()
        self._center_modal_window(dialog, 500, 210)

        def _close_with(value):
            result["value"] = value
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", lambda: _close_with(None))

        frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=16, pady=14)

        ctk.CTkLabel(
            frame,
            text=prompt,
            text_color=COLOR_TEXT,
            font=("Roboto", 12),
            anchor="w",
            justify="left",
            wraplength=460,
        ).pack(fill="x", pady=(8, 10))

        entry = ctk.CTkEntry(
            frame,
            fg_color=COLOR_SURFACE,
            text_color=COLOR_TEXT,
            border_color=COLOR_BORDER,
        )
        entry.pack(fill="x", pady=(0, 18))
        entry.insert(0, str(initialvalue or ""))
        entry.focus_set()
        entry.select_range(0, "end")

        def _confirm():
            _close_with(entry.get().strip())

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=lambda: _close_with(None),
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            width=100,
        ).pack(side="right")

        ctk.CTkButton(
            btn_row,
            text="OK",
            command=_confirm,
            fg_color=COLOR_TEXT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BG,
            width=100,
        ).pack(side="right", padx=(0, 10))

        dialog.bind("<Return>", lambda _evt: _confirm())
        dialog.bind("<Escape>", lambda _evt: _close_with(None))
        dialog.wait_window()
        return result["value"]

    def _import_config_settings(self, settings, source_name, import_title="Import", source_path=None, use_dark_dialog=False):
        data = self._build_config_payload(settings)
        target_path, normalized_name = self._resolve_config_path(source_name, force_new_suffix=True)

        if os.path.exists(target_path):
            same_source = False
            if source_path:
                try:
                    same_source = os.path.abspath(target_path) == os.path.abspath(source_path)
                except Exception:
                    same_source = False
            if not same_source:
                prompt_text = f"Profile '{normalized_name}' already exists. Overwrite it?"
                if use_dark_dialog:
                    should_overwrite = self._ask_dark_yes_no(import_title, prompt_text)
                else:
                    should_overwrite = messagebox.askyesno(import_title, prompt_text)
                if not should_overwrite:
                    self._log_config(f"{import_title} canceled: {normalized_name}")
                    return False, normalized_name

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        self._refresh_config_list()
        if hasattr(self, "config_option") and self.config_option.winfo_exists():
            self.config_option.set(normalized_name)
        self._apply_settings(settings, config_name=normalized_name)
        self._log_config(f"Imported: {normalized_name}")
        return True, normalized_name

    def _get_clipboard_file_paths(self):
        if os.name != "nt" or USER32 is None or SHELL32 is None:
            return []

        if not USER32.OpenClipboard(None):
            return []

        try:
            if not USER32.IsClipboardFormatAvailable(CF_HDROP):
                return []
            h_drop = USER32.GetClipboardData(CF_HDROP)
            if not h_drop:
                return []

            file_paths = []
            count = int(SHELL32.DragQueryFileW(h_drop, DRAG_QUERY_FILE_COUNT, None, 0))
            for idx in range(count):
                length = int(SHELL32.DragQueryFileW(h_drop, idx, None, 0))
                if length <= 0:
                    continue
                buffer = ctypes.create_unicode_buffer(length + 1)
                copied = int(SHELL32.DragQueryFileW(h_drop, idx, buffer, length + 1))
                if copied <= 0:
                    continue
                path = str(buffer.value).strip()
                if path:
                    file_paths.append(path)
            return file_paths
        finally:
            USER32.CloseClipboard()

    def _get_clipboard_import_candidate(self):
        try:
            clipboard_text = str(self.clipboard_get() or "").strip()
        except tk.TclError:
            clipboard_text = ""
        except Exception:
            clipboard_text = ""

        if clipboard_text:
            try:
                raw_data = json.loads(clipboard_text)
                if isinstance(raw_data, dict) and self._has_valid_config_comment(raw_data):
                    settings = self._strip_config_metadata(raw_data)
                    return settings, "clipboard", "clipboard text"
            except Exception:
                pass

            potential_path = clipboard_text.strip().strip("\"'")
            if os.path.isfile(potential_path) and str(potential_path).lower().endswith(".json"):
                try:
                    settings = self._load_importable_settings_from_json_file(potential_path)
                    source_name = self._normalize_config_display_name(
                        os.path.splitext(os.path.basename(potential_path))[0]
                    )
                    return settings, source_name, f"clipboard path: {potential_path}"
                except Exception:
                    pass

        for file_path in self._get_clipboard_file_paths():
            if not str(file_path).lower().endswith(".json"):
                continue
            try:
                settings = self._load_importable_settings_from_json_file(file_path)
                source_name = self._normalize_config_display_name(
                    os.path.splitext(os.path.basename(file_path))[0]
                )
                return settings, source_name, f"clipboard file: {file_path}"
            except Exception:
                continue

        return None

    def _poll_clipboard_config_import(self):
        try:
            self._maybe_prompt_clipboard_config_import()
        except Exception as e:
            log_print(f"[UI] Clipboard config poll error: {e}")
        finally:
            try:
                if self.winfo_exists():
                    self.after(self._clipboard_import_poll_interval_ms, self._poll_clipboard_config_import)
            except Exception:
                pass

    def _maybe_prompt_clipboard_config_import(self):
        if str(getattr(self, "_active_tab_name", "")) != "Config":
            return
        if not hasattr(self, "config_option") or not self.config_option.winfo_exists():
            return
        if self._clipboard_import_prompt_open:
            return

        candidate = self._get_clipboard_import_candidate()
        if not candidate:
            return

        settings, suggested_name, source_label = candidate
        current_settings = self._strip_config_metadata(self._get_current_settings())
        current_fingerprint = self._config_fingerprint(current_settings)
        incoming_fingerprint = self._config_fingerprint(settings)

        if incoming_fingerprint in self._clipboard_import_imported_signatures:
            return

        if incoming_fingerprint == current_fingerprint:
            return

        if (
            incoming_fingerprint == self._clipboard_import_last_declined_signature
            and current_fingerprint == self._clipboard_import_last_declined_config_fingerprint
        ):
            return

        self._clipboard_import_prompt_open = True
        try:
            should_import = self._ask_dark_yes_no(
                "Import",
                "Detected a CVM config in clipboard. Do you want to import it?",
            )
            if not should_import:
                self._clipboard_import_last_declined_signature = incoming_fingerprint
                self._clipboard_import_last_declined_config_fingerprint = current_fingerprint
                self._log_config(f"Clipboard import skipped: {source_label}")
                return

            default_name = self._normalize_config_display_name(suggested_name or "clipboard")
            entered_name = self._ask_dark_string(
                "Config name",
                "Enter the config name:",
                initialvalue=default_name,
            )
            if not entered_name:
                self._clipboard_import_last_declined_signature = incoming_fingerprint
                self._clipboard_import_last_declined_config_fingerprint = current_fingerprint
                self._log_config("Clipboard import canceled: no config name.")
                return

            success, normalized_name = self._import_config_settings(
                settings,
                source_name=entered_name,
                import_title="Import",
                use_dark_dialog=True,
            )
            if success:
                self._clipboard_import_last_declined_signature = None
                self._clipboard_import_last_declined_config_fingerprint = None
                self._clipboard_import_imported_signatures.add(incoming_fingerprint)
                messagebox.showinfo("Import", f"Imported config: {normalized_name}")
            else:
                self._clipboard_import_last_declined_signature = incoming_fingerprint
                self._clipboard_import_last_declined_config_fingerprint = current_fingerprint
        finally:
            self._clipboard_import_prompt_open = False

    def _copy_file_to_clipboard(self, file_path):
        if os.name != "nt" or USER32 is None or KERNEL32 is None:
            raise RuntimeError("File clipboard export is only supported on Windows.")

        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(abs_path)

        file_list_bytes = f"{abs_path}\0\0".encode("utf-16-le")
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)
        dropfiles.pt_x = 0
        dropfiles.pt_y = 0
        dropfiles.fNC = False
        dropfiles.fWide = True

        total_size = ctypes.sizeof(DROPFILES) + len(file_list_bytes)
        h_global = KERNEL32.GlobalAlloc(GHND, total_size)
        if not h_global:
            raise OSError("Failed to allocate clipboard memory.")

        locked_mem = KERNEL32.GlobalLock(h_global)
        if not locked_mem:
            KERNEL32.GlobalFree(h_global)
            raise OSError("Failed to lock clipboard memory.")

        try:
            ctypes.memmove(locked_mem, ctypes.byref(dropfiles), ctypes.sizeof(DROPFILES))
            ctypes.memmove(int(locked_mem) + ctypes.sizeof(DROPFILES), file_list_bytes, len(file_list_bytes))
        finally:
            KERNEL32.GlobalUnlock(h_global)

        if not USER32.OpenClipboard(None):
            KERNEL32.GlobalFree(h_global)
            raise OSError("Failed to open clipboard.")

        try:
            if not USER32.EmptyClipboard():
                KERNEL32.GlobalFree(h_global)
                raise OSError("Failed to empty clipboard.")
            if not USER32.SetClipboardData(CF_HDROP, h_global):
                KERNEL32.GlobalFree(h_global)
                raise OSError("Failed to set clipboard data.")
            h_global = None
        finally:
            USER32.CloseClipboard()

    def _do_save(self, name):
        path, normalized_name = self._resolve_config_path(name, force_new_suffix=True)
        settings = self._get_current_settings()
        data = self._build_config_payload(settings)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self._refresh_config_list()
            self.config_option.set(normalized_name)
            self._log_config(f"Saved: {normalized_name}")
        except Exception as e:
            self._log_config(f"Save error: {e}")

    def _load_selected_config(self):
        path, normalized_name = self._resolve_config_path(self.config_option.get())
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Config file must contain a JSON object.")
            settings = self._strip_config_metadata(data)
            self._apply_settings(settings, config_name=normalized_name)
        except Exception as e:
            self._log_config(f"Load error: {e}")

    def _export_selected_config(self):
        path, normalized_name = self._resolve_config_path(self.config_option.get())
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                raise ValueError("Config file must contain a JSON object.")

            settings = self._strip_config_metadata(raw_data)
            export_payload = self._build_config_payload(settings)
            if raw_data != export_payload:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(export_payload, f, indent=4, ensure_ascii=False)

            self._copy_file_to_clipboard(path)
            self._log_config(f"Exported file to clipboard: {normalized_name}")
            messagebox.showinfo("Export", "Config file copied to clipboard. You can now paste it elsewhere.")
        except Exception as e:
            self._log_config(f"Export error: {e}")
            messagebox.showerror("Export", f"Export failed:\n{e}")

    def _import_config_file(self):
        file_path = filedialog.askopenfilename(
            title="Import config file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            settings = self._load_importable_settings_from_json_file(file_path)
            source_name = self._normalize_config_display_name(os.path.splitext(os.path.basename(file_path))[0])
            success, normalized_name = self._import_config_settings(
                settings,
                source_name=source_name,
                import_title="Import",
                source_path=file_path,
                use_dark_dialog=True,
            )
            if success:
                messagebox.showinfo("Import", f"Imported config: {normalized_name}")
        except Exception as e:
            self._log_config(f"Import error: {e}")
            messagebox.showerror("Import", f"Import failed:\n{e}")

    def _delete_selected_config(self):
        try:
            self._refresh_config_list()
            file_map = dict(getattr(self, "_config_file_map", {}))
            display_names = sorted(file_map.keys(), key=lambda item: str(item).lower())

            if len(display_names) <= 1:
                self._log_config("Delete blocked: at least one config must remain.")
                messagebox.showwarning("Delete", "At least one config must remain.")
                return

            selected = self._normalize_config_display_name(self.config_option.get())
            if selected not in file_map:
                selected = display_names[0]

            filename = file_map.get(selected)
            if not filename:
                self._log_config("Delete error: no config selected.")
                return

            target_path = os.path.join("configs", filename)
            if not os.path.isfile(target_path):
                self._log_config(f"Delete error: file not found ({selected})")
                messagebox.showerror("Delete", f"Config file not found:\n{target_path}")
                return

            should_delete = self._ask_dark_yes_no(
                "Delete",
                f"Delete config '{selected}'?\nThis action cannot be undone.",
                yes_text="Delete",
                no_text="Cancel",
            )
            if not should_delete:
                self._log_config(f"Delete canceled: {selected}")
                return

            os.remove(target_path)
            self._log_config(f"Deleted: {selected}")
            self._refresh_config_list()
        except Exception as e:
            self._log_config(f"Delete error: {e}")
            messagebox.showerror("Delete", f"Delete failed:\n{e}")

    def _refresh_config_list(self):
        raw_files = [f for f in os.listdir("configs") if str(f).lower().endswith(".json")]
        file_map = {}
        for filename in sorted(raw_files, key=lambda item: str(item).lower()):
            display_name = self._config_display_name_from_filename(filename)
            existing = file_map.get(display_name)
            if existing:
                existing_is_new = str(existing).lower().endswith("_cvm.json")
                current_is_new = str(filename).lower().endswith("_cvm.json")
                if existing_is_new and not current_is_new:
                    continue
                if current_is_new and not existing_is_new:
                    file_map[display_name] = filename
                continue
            file_map[display_name] = filename

        if not file_map:
            file_map = {"default": self._config_filename_from_display_name("default")}

        self._config_file_map = file_map
        display_names = sorted(file_map.keys(), key=lambda item: str(item).lower())
        current = self._normalize_config_display_name(self.config_option.get())

        self.config_option.configure(values=display_names)
        if current in display_names:
            self.config_option.set(current)
        else:
            self.config_option.set(display_names[0])

    def _on_config_selected(self, val):
        self._log_config(f"Selected config: {self._normalize_config_display_name(val)}")

    def _log_config(self, msg):
        try:
            self.config_log.insert("end", f"> {msg}\n")
            self.config_log.see("end")
        except: pass

    # --- NDI & Capture Callbacks ---
    
    def _on_capture_method_changed(self, val):
        self.capture_method_var.set(val)
        self.capture.set_mode(val)
        config.capture_mode = val  # 淇濆瓨鍒?config
        self._update_capture_ui()
        self._set_status_indicator(f"Status: Mode {val}", COLOR_TEXT)

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
            self._set_status_indicator("Status: Refreshing NDI", COLOR_TEXT)

    def _update_ndi_fov_slider_max(self, width, height):
        """鏇存柊 NDI FOV 婊戞鐨勬渶澶у€硷紙姝ｆ柟褰㈣鍒囷紝浣跨敤杓冨皬鐨勫昂瀵革級"""
        if hasattr(self, 'ndi_fov_slider') and self.ndi_fov_slider.winfo_exists():
            # 姝ｆ柟褰㈣鍒囷紝鏈€澶у€艰ō鐐哄搴﹀拰楂樺害涓純灏忕殑涓€鍗?
            max_fov = max(16, min(width, height) // 2) if (width and height) else 1920
            self.ndi_fov_slider.configure(to=max_fov)
            # 濡傛灉鐣跺墠鍊艰秴閬庢柊鐨勬渶澶у€硷紝瑾挎暣鐐烘渶澶у€?
            current_val = int(getattr(config, "ndi_fov", 320))
            if current_val > max_fov:
                config.ndi_fov = max_fov
                self.ndi_fov_slider.set(max_fov)
                if hasattr(self, 'ndi_fov_entry') and self.ndi_fov_entry.winfo_exists():
                    self.ndi_fov_entry.delete(0, "end")
                    self.ndi_fov_entry.insert(0, str(max_fov))
            # 鏇存柊璩囪▕椤ず
            self._update_ndi_fov_info()
    
    def _update_udp_fov_slider_max(self, width, height):
        """鏇存柊 UDP FOV 婊戞鐨勬渶澶у€硷紙姝ｆ柟褰㈣鍒囷紝浣跨敤杓冨皬鐨勫昂瀵革級"""
        if hasattr(self, 'udp_fov_slider') and self.udp_fov_slider.winfo_exists():
            # 姝ｆ柟褰㈣鍒囷紝鏈€澶у€艰ō鐐哄搴﹀拰楂樺害涓純灏忕殑涓€鍗?
            max_fov = max(16, min(width, height) // 2) if (width and height) else 1920
            self.udp_fov_slider.configure(to=max_fov)
            # 濡傛灉鐣跺墠鍊艰秴閬庢柊鐨勬渶澶у€硷紝瑾挎暣鐐烘渶澶у€?
            current_val = int(getattr(config, "udp_fov", 320))
            if current_val > max_fov:
                config.udp_fov = max_fov
                self.udp_fov_slider.set(max_fov)
                if hasattr(self, 'udp_fov_entry') and self.udp_fov_entry.winfo_exists():
                    self.udp_fov_entry.delete(0, "end")
                    self.udp_fov_entry.insert(0, str(max_fov))
            # 鏇存柊璩囪▕椤ず
            self._update_udp_fov_info()
    
    def _connect_to_selected(self):
        if self.capture.mode == "NDI":
            sources = self.capture.ndi.get_source_list()
            if not sources: return
            
            selected = self.source_option.get()
            if selected and selected not in ["(no sources)", "(Scanning...)"]:
                self.capture.ndi.set_selected_source(selected)
                # 淇濆瓨閬镐腑鐨?NDI 婧?
                self.saved_ndi_source = selected
                config.last_ndi_source = selected
            
            success, error = self.capture.connect_ndi(selected)
            if success:
                self._set_status_indicator("Status: NDI connected", COLOR_TEXT)
                # 閫ｆ帴鎴愬姛寰岋紝鍢楄│鐛插彇鐣潰灏哄涓︽洿鏂版粦姊濇渶澶у€?
                self.after(500, self._update_ndi_fov_sliders_after_connect)  # 寤堕伈涓€榛炰互纰轰繚鐣潰宸叉簴鍌欏ソ
            else:
                self._set_status_indicator(f"Status: NDI error: {error}", COLOR_DANGER)
    
    def _update_ndi_fov_sliders_after_connect(self):
        """閫ｆ帴鎴愬姛寰屾洿鏂?NDI FOV 婊戞鐨勬渶澶у€?"""
        width, height = self.capture.get_frame_dimensions()
        if width and height:
            self._update_ndi_fov_slider_max(width, height)
            log_print(f"[UI] NDI frame dimensions: {width}x{height}, updated FOV slider max values")
            if hasattr(self, '_ndi_retry_count'):
                self._ndi_retry_count = 0
        else:
            # 濡傛灉绗竴娆＄嵅鍙栧け鏁楋紝鍐嶈│涓€娆★紙鏈€澶氳│3娆★級
            if not hasattr(self, '_ndi_retry_count'):
                self._ndi_retry_count = 0
            self._ndi_retry_count += 1
            if self._ndi_retry_count < 3:
                self.after(500, self._update_ndi_fov_sliders_after_connect)
            else:
                self._ndi_retry_count = 0
                
    def _connect_udp(self):
        if self.capture.mode == "UDP":
            ip = self.udp_ip_entry.get()
            port = self.udp_port_entry.get()
            
            # 淇濆瓨鍒板収瀛樺拰 config
            self.saved_udp_ip = ip
            self.saved_udp_port = port
            config.udp_ip = ip
            config.udp_port = port
            
            success, error = self.capture.connect_udp(ip, port)
            if success:
                self._set_status_indicator("Status: UDP connected", COLOR_TEXT)
                # 閫ｆ帴鎴愬姛寰岋紝鍢楄│鐛插彇鐣潰灏哄涓︽洿鏂版粦姊濇渶澶у€?
                self.after(500, self._update_udp_fov_sliders_after_connect)  # 寤堕伈涓€榛炰互纰轰繚鐣潰宸叉簴鍌欏ソ
            else:
                self._set_status_indicator(f"Status: UDP connect failed: {error}", COLOR_DANGER)
                log_print(f"[UI] UDP connection failed: {error}")
    
    def _update_udp_fov_sliders_after_connect(self):
        """閫ｆ帴鎴愬姛寰屾洿鏂?UDP FOV 婊戞鐨勬渶澶у€?"""
        width, height = self.capture.get_frame_dimensions()
        if width and height:
            self._update_udp_fov_slider_max(width, height)
            log_print(f"[UI] UDP frame dimensions: {width}x{height}, updated FOV slider max values")
        else:
            # 濡傛灉绗竴娆＄嵅鍙栧け鏁楋紝鍐嶈│涓€娆★紙鏈€澶氳│3娆★級
            if not hasattr(self, '_udp_retry_count'):
                self._udp_retry_count = 0
            self._udp_retry_count += 1
            if self._udp_retry_count < 3:
                self.after(500, self._update_udp_fov_sliders_after_connect)
            else:
                self._udp_retry_count = 0
    
    def _connect_capture_card(self):
        """閫ｆ帴 CaptureCard"""
        if self.capture.mode == "CaptureCard":
            # 纰轰繚閰嶇疆宸叉洿鏂?
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
                    # 鏇存柊涓績榛為’绀猴紙鍥犵偤鍒嗚鲸鐜囨敼璁婂彲鑳藉奖闊夸腑蹇冮粸锛?
                    self._update_capture_card_center_display()
                except ValueError:
                    pass
            
            if hasattr(self, 'capture_card_fps_entry'):
                try:
                    fps = float(self.capture_card_fps_entry.get())
                    config.capture_fps = fps
                except ValueError:
                    pass
            
            # 鏇存柊涓績榛為’绀?
            self._update_capture_card_center_display()
            
            success, error = self.capture.connect_capture_card(config)
            if success:
                self._set_status_indicator("Status: CaptureCard connected", COLOR_TEXT)
            else:
                self._set_status_indicator(f"Status: CaptureCard connect failed: {error}", COLOR_DANGER)
                log_print(f"[UI] CaptureCard connection failed: {error}")

    # --- MSS Callbacks ---
    def _on_mss_monitor_changed(self, event=None):
        """MSS Monitor Index 鏀硅畩"""
        if hasattr(self, 'mss_monitor_entry') and self.mss_monitor_entry.winfo_exists():
            try:
                val = int(self.mss_monitor_entry.get())
                config.mss_monitor_index = val
            except ValueError:
                pass
    
    def _on_mss_fov_x_slider_changed(self, val):
        """MSS FOV X 婊戞鏀硅畩"""
        int_val = int(round(val))
        config.mss_fov_x = int_val
        if hasattr(self, 'mss_fov_x_entry') and self.mss_fov_x_entry.winfo_exists():
            self.mss_fov_x_entry.delete(0, "end")
            self.mss_fov_x_entry.insert(0, str(int_val))
        self._update_mss_capture_info()
        # 鍗虫檪鏇存柊宸查€ｆ帴鐨?MSS 鎿峰彇鍣?
        if self.capture.mss_capture and self.capture.mss_capture.is_connected():
            fov_y = int(getattr(config, "mss_fov_y", 320))
            self.capture.mss_capture.set_fov(int_val, fov_y)
    
    def _on_mss_fov_x_entry_changed(self, event=None):
        """MSS FOV X 杓稿叆妗嗘敼璁?"""
        if hasattr(self, 'mss_fov_x_entry') and self.mss_fov_x_entry.winfo_exists():
            try:
                val = int(self.mss_fov_x_entry.get())
                val = max(16, min(1920, val))
                config.mss_fov_x = val
                if hasattr(self, 'mss_fov_x_slider'):
                    self.mss_fov_x_slider.set(val)
                self._update_mss_capture_info()
                if self.capture.mss_capture and self.capture.mss_capture.is_connected():
                    fov_y = int(getattr(config, "mss_fov_y", 320))
                    self.capture.mss_capture.set_fov(val, fov_y)
            except ValueError:
                pass
    
    def _on_mss_fov_y_slider_changed(self, val):
        """MSS FOV Y 婊戞鏀硅畩"""
        int_val = int(round(val))
        config.mss_fov_y = int_val
        if hasattr(self, 'mss_fov_y_entry') and self.mss_fov_y_entry.winfo_exists():
            self.mss_fov_y_entry.delete(0, "end")
            self.mss_fov_y_entry.insert(0, str(int_val))
        self._update_mss_capture_info()
        if self.capture.mss_capture and self.capture.mss_capture.is_connected():
            fov_x = int(getattr(config, "mss_fov_x", 320))
            self.capture.mss_capture.set_fov(fov_x, int_val)
    
    def _on_mss_fov_y_entry_changed(self, event=None):
        """MSS FOV Y 杓稿叆妗嗘敼璁?"""
        if hasattr(self, 'mss_fov_y_entry') and self.mss_fov_y_entry.winfo_exists():
            try:
                val = int(self.mss_fov_y_entry.get())
                val = max(16, min(1080, val))
                config.mss_fov_y = val
                if hasattr(self, 'mss_fov_y_slider'):
                    self.mss_fov_y_slider.set(val)
                self._update_mss_capture_info()
                if self.capture.mss_capture and self.capture.mss_capture.is_connected():
                    fov_x = int(getattr(config, "mss_fov_x", 320))
                    self.capture.mss_capture.set_fov(fov_x, val)
            except ValueError:
                pass
    
    def _update_mss_capture_info(self):
        """鏇存柊 MSS 鎿峰彇绡勫湇璩囪▕椤ず"""
        if hasattr(self, 'mss_capture_info_label') and self.mss_capture_info_label.winfo_exists():
            fov_x = int(getattr(config, "mss_fov_x", 320))
            fov_y = int(getattr(config, "mss_fov_y", 320))
            total_w = fov_x * 2
            total_h = fov_y * 2
            self.mss_capture_info_label.configure(
                text=f"Capture area: {total_w} x {total_h} px (centered on screen)"
            )
    
    def _connect_mss(self):
        """閫ｆ帴 MSS 铻㈠箷鎿峰彇"""
        if self.capture.mode == "MSS":
            monitor_index = int(getattr(config, "mss_monitor_index", 1))
            fov_x = int(getattr(config, "mss_fov_x", 320))
            fov_y = int(getattr(config, "mss_fov_y", 320))
            
            # 寰炶几鍏ユ鏇存柊
            if hasattr(self, 'mss_monitor_entry') and self.mss_monitor_entry.winfo_exists():
                try:
                    monitor_index = int(self.mss_monitor_entry.get())
                    config.mss_monitor_index = monitor_index
                except ValueError:
                    pass
            
            success, error = self.capture.connect_mss(monitor_index, fov_x, fov_y)
            if success:
                self._set_status_indicator(f"Status: MSS connected (Monitor {monitor_index})", COLOR_TEXT)
            else:
                self._set_status_indicator(f"Status: MSS connect failed: {error}", COLOR_DANGER)
                log_print(f"[UI] MSS connection failed: {error}")
    
    # --- NDI FOV Callbacks ---
    def _on_ndi_fov_enabled_changed(self):
        """NDI FOV 鍟熺敤鐙€鎱嬫敼璁?"""
        if hasattr(self, 'var_ndi_fov_enabled'):
            config.ndi_fov_enabled = self.var_ndi_fov_enabled.get()
    
    def _on_ndi_fov_slider_changed(self, val):
        """NDI FOV 婊戞鏀硅畩"""
        int_val = int(round(val))
        config.ndi_fov = int_val
        if hasattr(self, 'ndi_fov_entry') and self.ndi_fov_entry.winfo_exists():
            self.ndi_fov_entry.delete(0, "end")
            self.ndi_fov_entry.insert(0, str(int_val))
        self._update_ndi_fov_info()
    
    def _on_ndi_fov_entry_changed(self, event=None):
        """NDI FOV 杓稿叆妗嗘敼璁?"""
        if hasattr(self, 'ndi_fov_entry') and self.ndi_fov_entry.winfo_exists():
            try:
                val = int(self.ndi_fov_entry.get())
                val = max(16, min(1920, val))
                config.ndi_fov = val
                if hasattr(self, 'ndi_fov_slider'):
                    self.ndi_fov_slider.set(val)
                self._update_ndi_fov_info()
            except ValueError:
                pass
    
    def _update_ndi_fov_info(self):
        """鏇存柊 NDI 瑁佸垏绡勫湇璩囪▕椤ず"""
        if hasattr(self, 'ndi_fov_info_label') and self.ndi_fov_info_label.winfo_exists():
            fov = int(getattr(config, "ndi_fov", 320))
            total_size = fov * 2
            self.ndi_fov_info_label.configure(
                text=f"Crop area: {total_size} x {total_size} px (square, centered on frame)"
            )
    
    # --- UDP FOV Callbacks ---
    def _on_udp_fov_enabled_changed(self):
        """UDP FOV 鍟熺敤鐙€鎱嬫敼璁?"""
        if hasattr(self, 'var_udp_fov_enabled'):
            config.udp_fov_enabled = self.var_udp_fov_enabled.get()
    
    def _on_udp_fov_slider_changed(self, val):
        """UDP FOV 婊戞鏀硅畩"""
        int_val = int(round(val))
        config.udp_fov = int_val
        if hasattr(self, 'udp_fov_entry') and self.udp_fov_entry.winfo_exists():
            self.udp_fov_entry.delete(0, "end")
            self.udp_fov_entry.insert(0, str(int_val))
        self._update_udp_fov_info()
    
    def _on_udp_fov_entry_changed(self, event=None):
        """UDP FOV 杓稿叆妗嗘敼璁?"""
        if hasattr(self, 'udp_fov_entry') and self.udp_fov_entry.winfo_exists():
            try:
                val = int(self.udp_fov_entry.get())
                val = max(16, min(1920, val))
                config.udp_fov = val
                if hasattr(self, 'udp_fov_slider'):
                    self.udp_fov_slider.set(val)
                self._update_udp_fov_info()
            except ValueError:
                pass
    
    def _update_udp_fov_info(self):
        """鏇存柊 UDP 瑁佸垏绡勫湇璩囪▕椤ず"""
        if hasattr(self, 'udp_fov_info_label') and self.udp_fov_info_label.winfo_exists():
            fov = int(getattr(config, "udp_fov", 320))
            total_size = fov * 2
            self.udp_fov_info_label.configure(
                text=f"Crop area: {total_size} x {total_size} px (square, centered on frame)"
            )

    def _normalize_mouse_api_name(self, mode):
        mode_norm = str(mode).strip().lower()
        if mode_norm == "net":
            return "Net"
        if mode_norm in ("kmboxa", "kmboxa_api", "kmboxaapi", "kma", "kmboxa-api"):
            return "KmboxA"
        if mode_norm == "dhz":
            return "DHZ"
        if mode_norm in ("makv2binary", "makv2_binary", "makv2-binary", "binary"):
            return "MakV2Binary"
        if mode_norm in ("makv2", "mak_v2", "mak-v2"):
            return "MakV2"
        if mode_norm == "arduino":
            return "Arduino"
        if mode_norm in ("sendinput", "win32", "win32api", "win32_sendinput", "win32-sendinput"):
            return "SendInput"
        return "Serial"

    def _supports_trigger_strafe_ui(self, mode=None) -> bool:
        selected_mode = mode if mode is not None else getattr(config, "mouse_api", "Serial")
        try:
            from src.utils import mouse as mouse_backend

            return bool(mouse_backend.supports_trigger_strafe_ui(selected_mode))
        except Exception:
            normalized = self._normalize_mouse_api_name(selected_mode)
            return normalized in {"SendInput", "Net", "KmboxA", "DHZ"}

    def _supports_keyboard_state(self, mode=None) -> bool:
        selected_mode = mode if mode is not None else getattr(config, "mouse_api", "Serial")
        try:
            from src.utils import mouse as mouse_backend

            return bool(mouse_backend.supports_keyboard_state(selected_mode))
        except Exception:
            normalized = self._normalize_mouse_api_name(selected_mode)
            return normalized in {"SendInput", "Net", "KmboxA", "DHZ"}

    def _toggle_hardware_info_details(self):
        self._hardware_info_expanded = not bool(getattr(self, "_hardware_info_expanded", False))

        if hasattr(self, "hardware_details_toggle") and self.hardware_details_toggle.winfo_exists():
            self.hardware_details_toggle.configure(
                text="Hardware Info ▼" if self._hardware_info_expanded else "Hardware Info ▶"
            )

        if hasattr(self, "hardware_details_label") and self.hardware_details_label.winfo_exists():
            if self._hardware_info_expanded:
                self.hardware_details_label.pack(fill="x", pady=(2, 0))
                self._update_hardware_status_ui()
            else:
                self.hardware_details_label.pack_forget()

    def _build_hardware_details_text(self, mode: str, connected: bool) -> str:
        auto_connect = bool(getattr(config, "auto_connect_mouse_api", False))
        details = [
            f"Backend: {mode}",
            f"Connected: {'Yes' if connected else 'No'}",
            f"Auto Connect On Startup: {'Yes' if auto_connect else 'No'}",
        ]

        mouse_backend = None
        mouse_state = None
        net_api_module = None
        kmboxa_api_module = None
        try:
            from src.utils import mouse as mouse_backend
            from src.utils.mouse import NetAPI as net_api_module
            from src.utils.mouse import KmboxAAPI as kmboxa_api_module
            from src.utils.mouse import state as mouse_state
        except Exception:
            pass

        if mode == "Net":
            ip = str(getattr(config, "net_ip", ""))
            port = str(getattr(config, "net_port", ""))
            uuid = str(getattr(config, "net_uuid", getattr(config, "net_mac", "")))
            details.append(f"IP/Port: {ip}:{port}")
            details.append(f"UUID: {uuid or '(empty)'}")
            try:
                if mouse_backend is not None:
                    details.append(f"DLL: {mouse_backend.get_expected_kmnet_dll_name()}")
                loaded_path = getattr(net_api_module, "_loaded_module_path", "")
                if loaded_path:
                    details.append(f"Loaded: {os.path.basename(loaded_path)}")
            except Exception:
                pass
        elif mode == "DHZ":
            ip = str(getattr(config, "dhz_ip", ""))
            port = str(getattr(config, "dhz_port", ""))
            random_shift = str(getattr(config, "dhz_random", 0))
            details.append(f"IP/Port: {ip}:{port}")
            details.append(f"Random Shift: {random_shift}")
            try:
                dhz_client = getattr(mouse_state, "dhz_client", None)
                if dhz_client is not None and hasattr(dhz_client, "addr"):
                    details.append(f"Active Target: {dhz_client.addr[0]}:{dhz_client.addr[1]}")
            except Exception:
                pass
        elif mode == "KmboxA":
            vid_pid = str(getattr(config, "kmboxa_vid_pid", "")).strip()
            vid = int(getattr(config, "kmboxa_vid", 0))
            pid = int(getattr(config, "kmboxa_pid", 0))
            details.append(f"VID/PID Input: {vid_pid or '(empty)'}")
            details.append(f"VID/PID Parsed: {vid}/{pid}")
            try:
                if mouse_backend is not None:
                    details.append(f"DLL: {mouse_backend.get_expected_kmboxa_dll_name()}")
                loaded_path = getattr(kmboxa_api_module, "_loaded_module_path", "")
                if loaded_path:
                    details.append(f"Loaded: {os.path.basename(loaded_path)}")
            except Exception:
                pass
        elif mode == "MakV2":
            cfg_port = str(getattr(config, "makv2_port", "") or "auto")
            cfg_baud = str(getattr(config, "makv2_baud", 4000000))
            details.append(f"Port: {cfg_port}")
            details.append(f"Baud: {cfg_baud}")
            try:
                serial_dev = getattr(mouse_state, "makcu", None)
                if serial_dev is not None:
                    details.append(f"Active Port: {getattr(serial_dev, 'port', cfg_port)}")
                    details.append(f"Active Baud: {getattr(serial_dev, 'baudrate', cfg_baud)}")
            except Exception:
                pass
        elif mode == "Arduino":
            cfg_port = str(getattr(config, "arduino_port", "") or "auto")
            cfg_baud = str(getattr(config, "arduino_baud", 115200))
            details.append(f"Port: {cfg_port}")
            details.append(f"Baud: {cfg_baud}")
            details.append(f"16-bit Move: {'Yes' if bool(getattr(config, 'arduino_16_bit_mouse', True)) else 'No'}")
            try:
                serial_dev = getattr(mouse_state, "makcu", None)
                if serial_dev is not None:
                    details.append(f"Active Port: {getattr(serial_dev, 'port', cfg_port)}")
                    details.append(f"Active Baud: {getattr(serial_dev, 'baudrate', cfg_baud)}")
            except Exception:
                pass
        elif mode == "SendInput":
            details.append("Injection: Win32 SendInput")
            details.append("Transport: Local OS API")
        else:
            serial_mode = str(getattr(config, "serial_port_mode", "Auto")).strip().lower()
            serial_mode_label = "Manual" if serial_mode == "manual" else "Auto"
            configured_port = str(getattr(config, "serial_port", "")).strip()
            auto_switch_4m = bool(getattr(config, "serial_auto_switch_4m", False))
            details.append(f"COM Mode: {serial_mode_label}")
            details.append(f"Auto Switch 4M On Startup: {'Yes' if auto_switch_4m else 'No'}")
            if serial_mode_label == "Manual":
                details.append(f"Configured Port: {configured_port or '(empty)'}")
            else:
                details.append("Configured Port: auto-detect")
            try:
                serial_dev = getattr(mouse_state, "makcu", None)
                if serial_dev is not None:
                    details.append(f"Active Port: {getattr(serial_dev, 'port', 'unknown')}")
                    details.append(f"Active Baud: {getattr(serial_dev, 'baudrate', 'unknown')}")
            except Exception:
                pass

        try:
            if mouse_backend is not None:
                last_error = str(mouse_backend.get_last_connect_error() or "").strip()
                if last_error and not connected:
                    details.append(f"Last Error: {last_error}")
        except Exception:
            pass

        return "\n".join(details)

    def _update_hardware_status_ui(self):
        mode = self._normalize_mouse_api_name(getattr(config, "mouse_api", "Serial"))
        connected = False

        try:
            from src.utils import mouse as mouse_backend

            connected = bool(getattr(mouse_backend, "is_connected", False))
            if connected:
                active_mode = self._normalize_mouse_api_name(mouse_backend.get_active_backend())
                if active_mode:
                    mode = active_mode
        except Exception:
            connected = False

        if hasattr(self, "hardware_type_label") and self.hardware_type_label.winfo_exists():
            self.hardware_type_label.configure(text=f"Hardware: {mode}")

        if hasattr(self, "hardware_conn_label") and self.hardware_conn_label.winfo_exists():
            if connected:
                self.hardware_conn_label.configure(text="Hardware Status: Connected", text_color=COLOR_SUCCESS)
            else:
                self.hardware_conn_label.configure(text="Hardware Status: Disconnected", text_color=COLOR_DANGER)

        if (
            getattr(self, "_hardware_info_expanded", False)
            and hasattr(self, "hardware_details_label")
            and self.hardware_details_label.winfo_exists()
        ):
            self.hardware_details_label.configure(text=self._build_hardware_details_text(mode, connected))

    def _update_connection_status_loop(self):
        is_conn = self.capture.is_connected()
        current_mode = self.capture.mode
        
        if is_conn:
            self._set_status_indicator(f"Status: Online ({current_mode})", COLOR_TEXT)
        else:
            self._set_status_indicator("Status: Offline", COLOR_TEXT_DIM)
        self._update_hardware_status_ui()
        self.after(500, self._update_connection_status_loop)

    def _update_performance_stats(self):
        """鏇存柊鎬ц兘绲辫▓淇℃伅锛團PS 鍜屽欢閬诧級"""
        try:
            if self.capture.mode == "UDP" and self.capture.is_connected():
                # 寰?UDP receiver 鐛插彇鎬ц兘绲辫▓
                receiver = self.capture.udp_manager.get_receiver()
                if receiver:
                    stats = receiver.get_performance_stats()
                    
                    # 鏇存柊 FPS
                    current_fps = stats.get('current_fps', 0)
                    self.fps_label.configure(text=f"FPS: {current_fps:.1f}")
                    
                    # 鏇存柊瑙ｇ⒓寤堕伈
                    decode_delay = stats.get('decode_delay_ms', 0)
                    self.decode_delay_label.configure(text=f"Decode: {decode_delay:.1f} ms")
                    
                    # 鏇存柊绺藉欢閬诧紙鎺ユ敹 + 瑙ｇ⒓ + 铏曠悊锛?
                    receive_delay = stats.get('receive_delay_ms', 0)
                    processing_delay = stats.get('processing_delay_ms', 0)
                    total_delay = receive_delay + decode_delay + processing_delay
                    self.total_delay_label.configure(text=f"Delay: {total_delay:.1f} ms")
            elif self.capture.mode == "NDI" and self.capture.is_connected():
                # NDI 妯″紡锛氬緸 tracker 鐛插彇绨″柈鐨?FPS 淇℃伅
                if hasattr(self.tracker, '_frame_count'):
                    self.fps_label.configure(text=f"FPS: ~{self.tracker._target_fps}")
                    self.decode_delay_label.configure(text="Decode: N/A")
                    self.total_delay_label.configure(text="Delay: N/A")
            elif self.capture.mode == "MSS" and self.capture.is_connected():
                # MSS 妯″紡锛氬緸 mss_capture 鐛插彇鏁堣兘绲辫▓
                if self.capture.mss_capture:
                    stats = self.capture.mss_capture.get_performance_stats()
                    fps = stats.get('current_fps', 0)
                    grab_delay = stats.get('grab_delay_ms', 0)
                    self.fps_label.configure(text=f"FPS: {fps:.1f}")
                    self.decode_delay_label.configure(text=f"Grab: {grab_delay:.1f} ms")
                    self.total_delay_label.configure(text=f"Delay: {grab_delay:.1f} ms")
                else:
                    self.fps_label.configure(text="FPS: --")
                    self.decode_delay_label.configure(text="Grab: -- ms")
                    self.total_delay_label.configure(text="Delay: -- ms")
            elif self.capture.mode == "CaptureCard" and self.capture.is_connected():
                # CaptureCard 妯″紡锛氶’绀哄熀鏈?FPS 淇℃伅
                if hasattr(self.tracker, '_frame_count'):
                    self.fps_label.configure(text=f"FPS: ~{self.tracker._target_fps}")
                    self.decode_delay_label.configure(text="Decode: N/A")
                    self.total_delay_label.configure(text="Delay: N/A")
            else:
                # 鏈€ｆ帴鏅傞’绀?--
                self.fps_label.configure(text="FPS: --")
                self.decode_delay_label.configure(text="Decode: -- ms")
                self.total_delay_label.configure(text="Delay: -- ms")
        except Exception as e:
            log_print(f"[UI] Performance stats update error: {e}")
        
        # 姣?500ms 鏇存柊涓€娆?
        self.after(500, self._update_performance_stats)

    def _apply_sources_to_ui(self, names):
        # Only update if we are still on NDI mode and the widget exists
        if self.capture.mode == "NDI" and hasattr(self, 'source_option') and self.source_option.winfo_exists():
            if names:
                self.source_option.configure(values=names)
                
                # 鍢楄│鎭㈠京涔嬪墠淇濆瓨鐨勯伕鎿?
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
        """鎵撻枊瑷疆瑕栫獥"""
        SettingsWindow(self)
    
    def _on_close(self):
        # 寰?tracker 鍚屾鏈€鏂扮殑瑷疆鍒?config锛堢⒑淇濇墍鏈夐亱琛屾檪鐨勮畩鏇撮兘琚繚瀛橈級
        try:
            config.normal_x_speed = self.tracker.normal_x_speed
            config.normal_y_speed = self.tracker.normal_y_speed
            config.normalsmooth = self.tracker.normalsmooth
            config.normalsmoothfov = self.tracker.normalsmoothfov
            config.fovsize = self.tracker.fovsize
            config.ads_fov_enabled = getattr(self.tracker, "ads_fov_enabled", getattr(config, "ads_fov_enabled", False))
            config.ads_fovsize = getattr(self.tracker, "ads_fovsize", getattr(config, "ads_fovsize", config.fovsize))
            config.ads_key = getattr(self.tracker, "ads_key", getattr(config, "ads_key", "Right Mouse Button"))
            config.tbfovsize = self.tracker.tbfovsize
            config.trigger_ads_fov_enabled = getattr(
                self.tracker, "trigger_ads_fov_enabled", getattr(config, "trigger_ads_fov_enabled", False)
            )
            config.trigger_ads_fovsize = getattr(
                self.tracker, "trigger_ads_fovsize", getattr(config, "trigger_ads_fovsize", config.tbfovsize)
            )
            config.trigger_ads_key = getattr(
                self.tracker, "trigger_ads_key", getattr(config, "trigger_ads_key", "Right Mouse Button")
            )
            config.trigger_ads_key_type = getattr(
                self.tracker, "trigger_ads_key_type", getattr(config, "trigger_ads_key_type", "hold")
            )
            config.selected_tb_btn = getattr(self.tracker, "selected_tb_btn", getattr(config, "selected_tb_btn", 3))
            config.tbdelay_min = self.tracker.tbdelay_min
            config.tbdelay_max = self.tracker.tbdelay_max
            config.tbhold_min = self.tracker.tbhold_min
            config.tbhold_max = self.tracker.tbhold_max
            config.in_game_sens = self.tracker.in_game_sens
            config.mouse_dpi = self.tracker.mouse_dpi
            
            # Sec Aimbot
            config.normal_x_speed_sec = self.tracker.normal_x_speed_sec
            config.normal_y_speed_sec = self.tracker.normal_y_speed_sec
            config.normalsmooth_sec = self.tracker.normalsmooth_sec
            config.normalsmoothfov_sec = self.tracker.normalsmoothfov_sec
            config.fovsize_sec = self.tracker.fovsize_sec
            config.ads_fov_enabled_sec = getattr(self.tracker, "ads_fov_enabled_sec", getattr(config, "ads_fov_enabled_sec", False))
            config.ads_fovsize_sec = getattr(self.tracker, "ads_fovsize_sec", getattr(config, "ads_fovsize_sec", config.fovsize_sec))
            config.ads_key_sec = getattr(self.tracker, "ads_key_sec", getattr(config, "ads_key_sec", "Right Mouse Button"))
            config.selected_mouse_button_sec = self.tracker.selected_mouse_button_sec
            
        except Exception as e:
            log_print(f"[UI] Sync before save error: {e}")
        
        # 淇濆瓨鐣跺墠閰嶇疆
        try:
            config.save_to_file()
        except Exception as e:
            log_print(f"[UI] Failed to auto-save configuration: {e}")
        
        # 鍋滄杩借工鍣?
        try: 
            self.tracker.stop()
        except Exception as e:
            log_print(f"[UI] Tracker stop error: {e}")
        
        # 娓呯悊鎹曠嵅鏈嶅嫏
        try: 
            self.capture.cleanup()
        except Exception as e:
            log_print(f"[UI] Capture cleanup error: {e}")
        
        # 閵锋瘈绐楀彛
        self.destroy()
        
        # 闂滈枆鎵€鏈?OpenCV 绐楀彛
        try: 
            cv2.destroyAllWindows()
        except Exception as e:
            log_print(f"[UI] CV2 cleanup error: {e}")

    # Callbacks proxies
    def _on_normal_x_speed_changed(self, val): 
        config.normal_x_speed = val
        self.tracker.normal_x_speed = val
    
    def _on_normal_y_speed_changed(self, val): 
        config.normal_y_speed = val
        self.tracker.normal_y_speed = val
    
    def _on_silent_distance_changed(self, val):
        config.silent_distance = val
        self.tracker.silent_distance = val
    
    def _on_silent_delay_changed(self, val):
        config.silent_delay = val
        self.tracker.silent_delay = val
    
    def _on_silent_move_delay_changed(self, val):
        config.silent_move_delay = val
        self.tracker.silent_move_delay = val
    
    def _on_silent_return_delay_changed(self, val):
        config.silent_return_delay = val
        self.tracker.silent_return_delay = val
    
    def _on_config_in_game_sens_changed(self, val): 
        config.in_game_sens = val
        self.tracker.in_game_sens = val
    
    def _on_config_normal_smooth_changed(self, val): 
        config.normalsmooth = val
        self.tracker.normalsmooth = val
    
    def _on_config_normal_smoothfov_changed(self, val): 
        config.normalsmoothfov = val
        self.tracker.normalsmoothfov = val
    
    def _on_fovsize_changed(self, val): 
        config.fovsize = val
        self.tracker.fovsize = val
    
    def _on_aim_offsetX_changed(self, val):
        config.aim_offsetX = val
    
    def _on_aim_offsetY_changed(self, val):
        config.aim_offsetY = val
    
    def _on_aim_type_selected(self, val):
        config.aim_type = val
    
    def _on_tbdelay_range_changed(self, min_val, max_val):
        """Triggerbot Delay 绡勫湇鏀硅畩"""
        config.tbdelay_min = min_val
        config.tbdelay_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbdelay_min = min_val
            self.tracker.tbdelay_max = max_val
    
    def _on_tbhold_range_changed(self, min_val, max_val):
        """Triggerbot Hold 绡勫湇鏀硅畩"""
        config.tbhold_min = min_val
        config.tbhold_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbhold_min = min_val
            self.tracker.tbhold_max = max_val

    def _on_rgb_tbdelay_range_changed(self, min_val, max_val):
        config.rgb_tbdelay_min = min_val
        config.rgb_tbdelay_max = max_val
        if hasattr(self, "tracker"):
            self.tracker.rgb_tbdelay_min = min_val
            self.tracker.rgb_tbdelay_max = max_val

    def _on_rgb_tbhold_range_changed(self, min_val, max_val):
        config.rgb_tbhold_min = min_val
        config.rgb_tbhold_max = max_val
        if hasattr(self, "tracker"):
            self.tracker.rgb_tbhold_min = min_val
            self.tracker.rgb_tbhold_max = max_val

    def _on_rgb_tbcooldown_range_changed(self, min_val, max_val):
        config.rgb_tbcooldown_min = min_val
        config.rgb_tbcooldown_max = max_val
        if hasattr(self, "tracker"):
            self.tracker.rgb_tbcooldown_min = min_val
            self.tracker.rgb_tbcooldown_max = max_val
    

    def _on_trigger_roi_size_changed(self, val):
        config.trigger_roi_size = int(val)
        if hasattr(self, "tracker"):
            self.tracker.trigger_roi_size = int(val)

    def _on_trigger_min_pixels_changed(self, val):
        config.trigger_min_pixels = int(val)
        if hasattr(self, "tracker"):
            self.tracker.trigger_min_pixels = int(val)

    def _on_trigger_min_ratio_changed(self, val):
        config.trigger_min_ratio = float(val)
        if hasattr(self, "tracker"):
            self.tracker.trigger_min_ratio = float(val)

    def _on_trigger_confirm_frames_changed(self, val):
        config.trigger_confirm_frames = int(val)
        if hasattr(self, "tracker"):
            self.tracker.trigger_confirm_frames = int(val)

    def _on_tbcooldown_range_changed(self, min_val, max_val):
        """Triggerbot Cooldown 绡勫湇鏀硅畩"""
        config.tbcooldown_min = min_val
        config.tbcooldown_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbcooldown_min = min_val
            self.tracker.tbcooldown_max = max_val
    
    def _on_tbburst_count_range_changed(self, min_val, max_val):
        """Triggerbot Burst Count 绡勫湇鏀硅畩"""
        config.tbburst_count_min = int(min_val)
        config.tbburst_count_max = int(max_val)
        if hasattr(self, 'tracker'):
            self.tracker.tbburst_count_min = int(min_val)
            self.tracker.tbburst_count_max = int(max_val)
    
    def _on_tbburst_interval_range_changed(self, min_val, max_val):
        """Triggerbot Burst Interval 绡勫湇鏀硅畩"""
        config.tbburst_interval_min = min_val
        config.tbburst_interval_max = max_val
        if hasattr(self, 'tracker'):
            self.tracker.tbburst_interval_min = min_val
            self.tracker.tbburst_interval_max = max_val
    
    def _on_tbfovsize_changed(self, val): 
        config.tbfovsize = val
        self.tracker.tbfovsize = val

    def _on_trigger_ads_fov_enabled_changed(self):
        config.trigger_ads_fov_enabled = self.var_trigger_ads_fov_enabled.get()
        if hasattr(self, "tracker"):
            self.tracker.trigger_ads_fov_enabled = config.trigger_ads_fov_enabled
        if str(getattr(self, "_active_tab_name", "")) == "Trigger":
            self._show_tb_tab()

    def _on_trigger_ads_fovsize_changed(self, val):
        config.trigger_ads_fovsize = val
        if hasattr(self, "tracker"):
            self.tracker.trigger_ads_fovsize = val

    def _on_trigger_ads_key_type_selected(self, val):
        config.trigger_ads_key_type = ADS_KEY_TYPE_DISPLAY_TO_VALUE.get(str(val), "hold")
        if hasattr(self, "tracker"):
            self.tracker.trigger_ads_key_type = config.trigger_ads_key_type
        self._log_config(f"Trigger ADS Key Type: {val}")
    
    def _on_tbhold_changed(self, val):
        config.tbhold = val
        self.tracker.tbhold = val
    
    def _on_enableaim_changed(self): 
        config.enableaim = self.var_enableaim.get()

    def _on_ads_fov_enabled_changed(self):
        config.ads_fov_enabled = self.var_ads_fov_enabled.get()
        if hasattr(self, "tracker"):
            self.tracker.ads_fov_enabled = config.ads_fov_enabled
        if str(getattr(self, "_active_tab_name", "")) == "Main Aimbot":
            self._show_aimbot_tab()

    def _on_ads_fovsize_changed(self, val):
        config.ads_fovsize = val
        if hasattr(self, "tracker"):
            self.tracker.ads_fovsize = val
    
    def _on_anti_smoke_changed(self):
        """Main Aimbot Anti-Smoke 闁嬮棞鍥炶"""
        config.anti_smoke_enabled = self.var_anti_smoke.get()
        if hasattr(self.tracker, 'anti_smoke_detector'):
            self.tracker.anti_smoke_detector.set_enabled(config.anti_smoke_enabled)
    
    def _on_enabletb_changed(self): 
        config.enabletb = self.var_enabletb.get()
    
    def _on_enablercs_changed(self):
        """RCS 闁嬮棞鏀硅畩"""
        config.enablercs = self.var_enablercs.get()
    
    def _on_rcs_pull_speed_changed(self, val):
        """RCS Pull Speed 鏀硅畩"""
        config.rcs_pull_speed = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_pull_speed = int(val)
    
    def _on_rcs_activation_delay_changed(self, val):
        """RCS Activation Delay 鏀硅畩"""
        config.rcs_activation_delay = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_activation_delay = int(val)
    
    def _on_rcs_rapid_click_threshold_changed(self, val):
        """RCS Rapid Click Threshold 鏀硅畩"""
        config.rcs_rapid_click_threshold = int(val)
        if hasattr(self, 'tracker'):
            self.tracker.rcs_rapid_click_threshold = int(val)
    
    def _on_rcs_release_y_enabled_changed(self):
        """RCS Release Y-Axis 闁嬮棞鏀硅畩"""
        config.rcs_release_y_enabled = self.var_rcs_release_y_enabled.get()
    
    def _on_rcs_release_y_duration_changed(self, val):
        """RCS Release Y-Axis Duration 鏀硅畩"""
        config.rcs_release_y_duration = float(val)
    
    def _on_color_selected(self, val): 
        config.color = val
        self.tracker.color = val
        # 瀵︽檪閲嶆柊杓夊叆妯″瀷浠ユ噳鐢ㄦ柊鐨勯鑹茶ō瀹?
        from src.utils.detection import reload_model
        self.tracker.model, self.tracker.class_names = reload_model()
        # 鏇存柊 Custom HSV 鍗€濉婄殑鍙鎬?
        self._update_custom_hsv_visibility()
    
    def _update_custom_hsv_visibility(self):
        """Show or hide Custom HSV section based on selected color."""
        current_color = getattr(config, "color", "yellow")
        is_custom = current_color == "custom"

        if hasattr(self, 'custom_hsv_container'):
            if is_custom:
                if not self.custom_hsv_container.winfo_ismapped():
                    self.custom_hsv_container.pack(fill="x", pady=(5, 0))
            else:
                if self.custom_hsv_container.winfo_ismapped():
                    self.custom_hsv_container.pack_forget()

    def _on_custom_hsv_changed(self, key, val):
        """Custom HSV 鍊兼敼璁婃檪鐨勫洖瑾?"""
        setattr(config, key, int(val))
        # 濡傛灉鐣跺墠閬告搰鐨勬槸 custom锛屽鏅傞噸鏂拌級鍏ユā鍨?
        if getattr(config, "color", "yellow") == "custom":
            from src.utils.detection import reload_model
            if hasattr(self, 'tracker'):
                self.tracker.model, self.tracker.class_names = reload_model()
                log_print(f"[UI] Custom HSV updated: {key} = {int(val)}")
    
    def _open_hsv_preview(self):
        """Abre a janela de preview HSV em tempo real."""
        if hasattr(self, '_hsv_preview_window') and self._hsv_preview_window is not None:
            try:
                if self._hsv_preview_window.winfo_exists():
                    self._hsv_preview_window.lift()
                    self._hsv_preview_window.focus_force()
                    return
            except Exception:
                pass

        def _on_apply():
            # Recarrega o modelo de detecao com os novos valores
            if getattr(config, 'color', 'yellow') == 'custom':
                from src.utils.detection import reload_model
                if hasattr(self, 'tracker'):
                    self.tracker.model, self.tracker.class_names = reload_model()
                    log_print('[UI] Custom HSV aplicado via Preview.')
            # Atualiza os sliders da UI principal
            self._sync_hsv_sliders_from_config()

        self._hsv_preview_window = HsvPreviewWindow(
            self, self.capture, on_apply_callback=_on_apply
        )

    def _sync_hsv_sliders_from_config(self):
        """Atualiza os sliders HSV da UI principal a partir do config."""
        keys = [
            ('custom_hsv_min_h', 0), ('custom_hsv_min_s', 0), ('custom_hsv_min_v', 0),
            ('custom_hsv_max_h', 179), ('custom_hsv_max_s', 255), ('custom_hsv_max_v', 255),
        ]
        for key, default in keys:
            val = int(getattr(config, key, default))
            self._set_slider_value(key, val)

    def _on_detection_merge_distance_changed(self, val):
        """Detection Merge Distance 鏀硅畩鏅傜殑鍥炶"""
        config.detection_merge_distance = int(val)
        log_print(f"[UI] Detection merge distance updated: {int(val)}")
    
    def _on_detection_min_contour_points_changed(self, val):
        """Detection Min Contour Points 鏀硅畩鏅傜殑鍥炶"""
        config.detection_min_contour_points = int(val)
        log_print(f"[UI] Detection min contour points updated: {int(val)}")
    
    def _on_mode_selected(self, val): 
        config.mode = val
        self.tracker.mode = val
        # 閲嶆柊娓叉煋 Aimbot tab 浠ラ’绀哄皪鎳夋ā寮忕殑鍙冩暩
        self._show_aimbot_tab()
        # 閲嶆柊楂樹寒姝ｇ⒑鐨勫皫鑸寜閳?
        for name, btn in self.nav_buttons.items():
            if name == "Main Aimbot":
                btn.configure(text_color=COLOR_ACCENT)
            else:
                btn.configure(text_color=COLOR_TEXT_DIM)
    
    def _on_mode_sec_selected(self, val):
        config.mode_sec = val
        self.tracker.mode_sec = val
        # 閲嶆柊娓叉煋 Sec Aimbot tab 浠ラ’绀哄皪鎳夋ā寮忕殑鍙冩暩
        self._show_sec_aimbot_tab()
        # 閲嶆柊楂樹寒姝ｇ⒑鐨勫皫鑸寜閳?
        for name, btn in self.nav_buttons.items():
            if name == "Sec Aimbot":
                btn.configure(text_color=COLOR_ACCENT)
            else:
                btn.configure(text_color=COLOR_TEXT_DIM)
    
    # Sec Aimbot Callbacks
    def _on_normal_x_speed_sec_changed(self, val): 
        config.normal_x_speed_sec = val
        self.tracker.normal_x_speed_sec = val
    
    def _on_normal_y_speed_sec_changed(self, val): 
        config.normal_y_speed_sec = val
        self.tracker.normal_y_speed_sec = val
    
    def _on_config_normal_smooth_sec_changed(self, val): 
        config.normalsmooth_sec = val
        self.tracker.normalsmooth_sec = val
    
    def _on_config_normal_smoothfov_sec_changed(self, val): 
        config.normalsmoothfov_sec = val
        self.tracker.normalsmoothfov_sec = val
    
    def _on_fovsize_sec_changed(self, val): 
        config.fovsize_sec = val
        self.tracker.fovsize_sec = val
    
    def _on_aim_offsetX_sec_changed(self, val):
        config.aim_offsetX_sec = val
    
    def _on_aim_offsetY_sec_changed(self, val):
        config.aim_offsetY_sec = val
    
    def _on_aim_type_sec_selected(self, val):
        config.aim_type_sec = val
    
    def _on_enableaim_sec_changed(self): 
        config.enableaim_sec = self.var_enableaim_sec.get()

    def _on_ads_fov_enabled_sec_changed(self):
        config.ads_fov_enabled_sec = self.var_ads_fov_enabled_sec.get()
        if hasattr(self, "tracker"):
            self.tracker.ads_fov_enabled_sec = config.ads_fov_enabled_sec
        if str(getattr(self, "_active_tab_name", "")) == "Sec Aimbot":
            self._show_sec_aimbot_tab()

    def _on_ads_fovsize_sec_changed(self, val):
        config.ads_fovsize_sec = val
        if hasattr(self, "tracker"):
            self.tracker.ads_fovsize_sec = val
    
    def _on_anti_smoke_sec_changed(self):
        """Secondary Aimbot Anti-Smoke 闁嬮棞鍥炶"""
        config.anti_smoke_enabled_sec = self.var_anti_smoke_sec.get()
        if hasattr(self.tracker, 'anti_smoke_detector_sec'):
            self.tracker.anti_smoke_detector_sec.set_enabled(config.anti_smoke_enabled_sec)
    
    # === NCAF Callbacks (Main) ===
    def _on_ncaf_near_radius_changed(self, val):
        config.ncaf_near_radius = val
        snap = getattr(config, "ncaf_snap_radius", val)
        # Snap 鎳夊ぇ鏂?Near锛涜嫢涓嶇鍓囪嚜鍕曞線涓婅鏁翠甫鍚屾 UI
        if snap <= val:
            snap = min(500, val + 1)
            config.ncaf_snap_radius = snap
            self._set_slider_value("ncaf_snap_radius", snap)
    
    def _on_ncaf_snap_radius_changed(self, val):
        config.ncaf_snap_radius = val
        near = getattr(config, "ncaf_near_radius", val)
        if val <= near:
            near = max(5, val - 1)
            config.ncaf_near_radius = near
            self._set_slider_value("ncaf_near_radius", near)
    
    def _on_ncaf_alpha_changed(self, val):
        config.ncaf_alpha = val
    
    def _on_ncaf_snap_boost_changed(self, val):
        config.ncaf_snap_boost = val
    
    def _on_ncaf_max_step_changed(self, val):
        config.ncaf_max_step = val
    
    def _on_ncaf_min_speed_multiplier_changed(self, val):
        config.ncaf_min_speed_multiplier = val
    
    def _on_ncaf_max_speed_multiplier_changed(self, val):
        config.ncaf_max_speed_multiplier = val
    
    def _on_ncaf_prediction_interval_changed(self, val):
        config.ncaf_prediction_interval = val / 1000.0  # ms 鈫?s
    
    # === NCAF Callbacks (Sec) ===
    def _on_ncaf_near_radius_sec_changed(self, val):
        config.ncaf_near_radius_sec = val
        snap = getattr(config, "ncaf_snap_radius_sec", val)
        if snap <= val:
            snap = min(500, val + 1)
            config.ncaf_snap_radius_sec = snap
            self._set_slider_value("ncaf_snap_radius_sec", snap)
    
    def _on_ncaf_snap_radius_sec_changed(self, val):
        config.ncaf_snap_radius_sec = val
        near = getattr(config, "ncaf_near_radius_sec", val)
        if val <= near:
            near = max(5, val - 1)
            config.ncaf_near_radius_sec = near
            self._set_slider_value("ncaf_near_radius_sec", near)
    
    def _on_ncaf_alpha_sec_changed(self, val):
        config.ncaf_alpha_sec = val
    
    def _on_ncaf_snap_boost_sec_changed(self, val):
        config.ncaf_snap_boost_sec = val
    
    def _on_ncaf_max_step_sec_changed(self, val):
        config.ncaf_max_step_sec = val
    
    def _on_ncaf_min_speed_multiplier_sec_changed(self, val):
        config.ncaf_min_speed_multiplier_sec = val
    
    def _on_ncaf_max_speed_multiplier_sec_changed(self, val):
        config.ncaf_max_speed_multiplier_sec = val
    
    def _on_ncaf_prediction_interval_sec_changed(self, val):
        config.ncaf_prediction_interval_sec = val / 1000.0  # ms 鈫?s
    
    # === WindMouse Callbacks (Main) ===
    def _on_wm_gravity_changed(self, val):
        config.wm_gravity = val
    
    def _on_wm_wind_changed(self, val):
        config.wm_wind = val
    
    def _on_wm_max_step_changed(self, val):
        config.wm_max_step = val
    
    def _on_wm_min_step_changed(self, val):
        config.wm_min_step = val
    
    def _on_wm_min_delay_changed(self, val):
        config.wm_min_delay = val / 1000.0  # ms 鈫?s
    
    def _on_wm_max_delay_changed(self, val):
        config.wm_max_delay = val / 1000.0  # ms 鈫?s
    
    def _on_wm_distance_threshold_changed(self, val):
        config.wm_distance_threshold = val
    
    # === WindMouse Callbacks (Sec) ===
    def _on_wm_gravity_sec_changed(self, val):
        config.wm_gravity_sec = val
    
    def _on_wm_wind_sec_changed(self, val):
        config.wm_wind_sec = val
    
    def _on_wm_max_step_sec_changed(self, val):
        config.wm_max_step_sec = val
    
    def _on_wm_min_step_sec_changed(self, val):
        config.wm_min_step_sec = val
    
    def _on_wm_min_delay_sec_changed(self, val):
        config.wm_min_delay_sec = val / 1000.0  # ms 鈫?s
    
    def _on_wm_max_delay_sec_changed(self, val):
        config.wm_max_delay_sec = val / 1000.0  # ms 鈫?s
    
    def _on_wm_distance_threshold_sec_changed(self, val):
        config.wm_distance_threshold_sec = val
    
    # --- Bezier Callbacks (Main) ---
    def _on_bezier_segments_changed(self, val):
        config.bezier_segments = int(val)
    
    def _on_bezier_ctrl_x_changed(self, val):
        config.bezier_ctrl_x = float(val)
    
    def _on_bezier_ctrl_y_changed(self, val):
        config.bezier_ctrl_y = float(val)
    
    def _on_bezier_speed_changed(self, val):
        config.bezier_speed = float(val)
    
    def _on_bezier_delay_changed(self, val):
        config.bezier_delay = float(val) / 1000.0  # ms 鈫?s
    
    # --- Bezier Callbacks (Sec) ---
    def _on_bezier_segments_sec_changed(self, val):
        config.bezier_segments_sec = int(val)
    
    def _on_bezier_ctrl_x_sec_changed(self, val):
        config.bezier_ctrl_x_sec = float(val)
    
    def _on_bezier_ctrl_y_sec_changed(self, val):
        config.bezier_ctrl_y_sec = float(val)
    
    def _on_bezier_speed_sec_changed(self, val):
        config.bezier_speed_sec = float(val)
    
    def _on_bezier_delay_sec_changed(self, val):
        config.bezier_delay_sec = float(val) / 1000.0  # ms 鈫?s
    
    def _on_aimbot_button_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_mouse_button = k
                if hasattr(self, "tracker"):
                    self.tracker.selected_mouse_button = k
                self._log_config(f"Aim Key: {val}")
                break

    def _on_ads_key_selected(self, val):
        config.ads_key = self._ads_display_to_binding(val)
        if hasattr(self, "tracker"):
            self.tracker.ads_key = config.ads_key
        self._log_config(f"ADS Key: {val}")

    def _on_ads_key_type_selected(self, val):
        config.ads_key_type = ADS_KEY_TYPE_DISPLAY_TO_VALUE.get(str(val), "hold")
        self._log_config(f"ADS Key Type: {val}")
    
    def _on_aimbot_activation_type_selected(self, val):
        activation_type_map = {
            "Hold to Enable": "hold_enable",
            "Hold to Disable": "hold_disable",
            "Toggle": "toggle",
            "Press to Enable": "use_enable"
        }
        config.aimbot_activation_type = activation_type_map.get(val, "hold_enable")
        self._log_config(f"Aim Activation Type: {val}")

    def _on_trigger_type_selected(self, val):
        trigger_type_map = {
            "Classic Trigger": "current",
            "Current": "current",
            "RGB Trigger": "rgb",
        }
        new_trigger_type = trigger_type_map.get(val, "current")
        old_trigger_type = str(getattr(config, "trigger_type", "current")).strip().lower()
        config.trigger_type = new_trigger_type
        self._log_config(f"Trigger Type: {val}")
        # Rebuild tab to show mode-specific controls immediately.
        if new_trigger_type != old_trigger_type:
            self._show_tb_tab()

    def _on_rgb_color_profile_selected(self, val):
        rgb_profile_map = {
            "Red": "red",
            "Yellow": "yellow",
            "Purple": "purple",
            "Custom": "custom",
        }
        config.rgb_color_profile = rgb_profile_map.get(val, "purple")
        # Reuse the same global custom HSV profile used by main color selection.
        if config.rgb_color_profile == "custom":
            config.color = "custom"
            if hasattr(self, "tracker"):
                self.tracker.color = "custom"
        if hasattr(self, "tracker"):
            self.tracker.rgb_color_profile = config.rgb_color_profile
        self._log_config(f"RGB Preset: {val}")

    def _on_tb_button_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_tb_btn = k
                self._log_config(f"Trigger Key: {val}")
                break

    def _on_trigger_activation_type_selected(self, val):
        trigger_activation_map = {
            "Hold to Enable": "hold_enable",
            "Hold to Disable": "hold_disable",
            "Toggle": "toggle",
            # backward compatibility for older saved labels
            "按下啟用": "hold_enable",
            "按下禁用": "hold_disable",
            "切換": "toggle",
        }
        config.trigger_activation_type = trigger_activation_map.get(val, "hold_enable")
        self._log_config(f"Trigger Mode: {val}")

    def _on_trigger_strafe_mode_selected(self, val):
        trigger_strafe_mode_map = {
            "Off": "off",
            "Auto Strafe": "auto",
            "Manual Wait": "manual_wait",
        }
        selected_mode = trigger_strafe_mode_map.get(str(val), "off")
        if selected_mode != "off" and not self._supports_trigger_strafe_ui():
            selected_mode = "off"
        old_mode = str(getattr(config, "trigger_strafe_mode", "off")).strip().lower()
        config.trigger_strafe_mode = selected_mode
        self._log_config(f"Trigger Strafe Mode: {val}")
        if selected_mode != old_mode and str(getattr(self, "_active_tab_name", "")) == "Trigger":
            self._show_tb_tab()

    def _on_trigger_strafe_auto_lead_ms_changed(self, val):
        config.trigger_strafe_auto_lead_ms = int(val)

    def _on_trigger_strafe_manual_neutral_ms_changed(self, val):
        config.trigger_strafe_manual_neutral_ms = int(val)
    
    # Mouse Input Debug Callbacks
    def _on_debug_mouse_input_changed(self):
        """婊戦紶杓稿叆瑾胯│闁嬮棞鏀硅畩"""
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
    
    def _update_mouse_input_debug(self):
        """瀹氭湡鏇存柊婊戦紶杓稿叆瑾胯│椤ず"""
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
        """閲嶇疆鍠€嬫寜閳曠殑瑷堟暩"""
        if hasattr(self.mouse_input_monitor, 'button_counts'):
            self.mouse_input_monitor.button_counts[button_idx] = 0
        if hasattr(self, 'debug_button_widgets') and button_idx in self.debug_button_widgets:
            try:
                self.debug_button_widgets[button_idx]["count_label"].configure(text="Count: 0")
            except Exception:
                pass
    
    def _reset_all_button_counts(self):
        """閲嶇疆鎵€鏈夋寜閳曠殑瑷堟暩"""
        self.mouse_input_monitor.reset_counts()
        if hasattr(self, 'debug_button_widgets'):
            for idx, widgets in self.debug_button_widgets.items():
                try:
                    widgets["count_label"].configure(text="Count: 0")
                except Exception:
                    pass
    
    def _update_debug_log(self):
        """瀹氭湡鏇存柊 Debug 鏃ヨ獙椤ず"""
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
                            message = str(log.get("message", ""))
                            if message:
                                log_text += f"[{timestamp}] {log_type:8s} [{source:15s}] {message}\n"
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
        """娓呯┖ Debug 鏃ヨ獙"""
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
    
    def _on_aimbot_button_sec_selected(self, val):
        for k, name in BUTTONS.items():
            if name == val:
                config.selected_mouse_button_sec = k
                self.tracker.selected_mouse_button_sec = k
                break

    def _on_ads_key_sec_selected(self, val):
        config.ads_key_sec = self._ads_display_to_binding(val)
        if hasattr(self, "tracker"):
            self.tracker.ads_key_sec = config.ads_key_sec
        self._log_config(f"Sec ADS Key: {val}")

    def _on_ads_key_type_sec_selected(self, val):
        config.ads_key_type_sec = ADS_KEY_TYPE_DISPLAY_TO_VALUE.get(str(val), "hold")
        self._log_config(f"Sec ADS Key Type: {val}")
    
    def _on_aimbot_activation_type_sec_selected(self, val):
        activation_type_map = {
            "Hold to Enable": "hold_enable",
            "Hold to Disable": "hold_disable",
            "Toggle": "toggle",
            "Press to Enable": "use_enable"
        }
        config.aimbot_activation_type_sec = activation_type_map.get(val, "hold_enable")
        self._log_config(f"Sec Aim Activation Type: {val}")
    
    def _on_button_mask_enabled_changed(self):
        """Button Mask 绺介枊闂滃洖瑾?"""
        config.button_mask_enabled = self.var_button_mask_enabled.get()
    
    def _on_button_mask_changed(self, key, var):
        """鍠€嬫寜閳?Mask 鐙€鎱嬫敼璁婂洖瑾?"""
        value = var.get()
        setattr(config, key, value)
        button_names = {
            "mask_left_button": "Left (L)",
            "mask_right_button": "Right (R)",
            "mask_middle_button": "Middle (M)",
            "mask_side4_button": "Side 4 (S4)",
            "mask_side5_button": "Side 5 (S5)"
        }
    
    def _on_mouse_lock_main_x_changed(self):
        """Mouse Lock Main Aimbot X-Axis 闁嬮棞鍥炶"""
        try:
            config.mouse_lock_main_x = self.var_mouse_lock_main_x.get()
            # 涓嶅湪姝よ檿瑾跨敤 tick锛岃畵涓诲惊鐠拌檿鐞嗭紝閬垮厤闃诲 UI 绶氱▼
        except Exception as e:
            log_print(f"[Mouse Lock] Error in main_x callback: {e}")
    
    def _on_mouse_lock_main_y_changed(self):
        """Mouse Lock Main Aimbot Y-Axis 闁嬮棞鍥炶"""
        try:
            config.mouse_lock_main_y = self.var_mouse_lock_main_y.get()
            # 涓嶅湪姝よ檿瑾跨敤 tick锛岃畵涓诲惊鐠拌檿鐞嗭紝閬垮厤闃诲 UI 绶氱▼
        except Exception as e:
            log_print(f"[Mouse Lock] Error in main_y callback: {e}")
    
    def _on_mouse_lock_sec_x_changed(self):
        """Mouse Lock Sec Aimbot X-Axis 闁嬮棞鍥炶"""
        try:
            config.mouse_lock_sec_x = self.var_mouse_lock_sec_x.get()
            # 涓嶅湪姝よ檿瑾跨敤 tick锛岃畵涓诲惊鐠拌檿鐞嗭紝閬垮厤闃诲 UI 绶氱▼
        except Exception as e:
            log_print(f"[Mouse Lock] Error in sec_x callback: {e}")
    
    def _on_mouse_lock_sec_y_changed(self):
        """Mouse Lock Sec Aimbot Y-Axis 闁嬮棞鍥炶"""
        try:
            config.mouse_lock_sec_y = self.var_mouse_lock_sec_y.get()
            # 涓嶅湪姝よ檿瑾跨敤 tick锛岃畵涓诲惊鐠拌檿鐞嗭紝閬垮厤闃诲 UI 绶氱▼
        except Exception as e:
            log_print(f"[Mouse Lock] Error in sec_y callback: {e}")
    
    def _check_for_updates(self):
        """Check for updates in background"""
        if self._update_check_in_progress:
            return
        self._update_check_in_progress = True
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _check_for_updates_worker(self):
        try:
            has_update, latest_version, update_info = self.update_checker.check_update()
            if has_update:
                self.after(0, lambda: self._show_update_dialog(latest_version, update_info))
        except Exception as e:
            log_print(f"[Update] Failed to check for updates: {e}")
        finally:
            self._update_check_in_progress = False
    
    def _show_update_dialog(self, latest_version, update_info):
        """Show update dialog with update information"""
        UpdateDialog(self, latest_version, update_info)


class UpdateDialog(ctk.CTkToplevel):
    """Simple update prompt dialog."""

    def __init__(self, parent, latest_version, update_info):
        super().__init__(parent)
        self.parent = parent
        self.latest_version = str(latest_version or "unknown")
        self.update_info = update_info if isinstance(update_info, dict) else {}

        self.title("Update Available")
        self.geometry("520x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_x() + max(0, (parent.winfo_width() - 520) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - 380) // 2)
        self.geometry(f"+{x}+{y}")

        self._build_ui()

    def _pick_text(self):
        for key in ("notes", "changelog", "description", "message"):
            value = self.update_info.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "A new version is available."

    def _pick_url(self):
        for key in ("download_url", "release_url", "url"):
            value = self.update_info.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        return None

    def _build_ui(self):
        frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text=f"New Version: v{self.latest_version}",
            font=("Roboto", 16, "bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=20, pady=(18, 8))

        notes_box = ctk.CTkTextbox(
            frame,
            fg_color=COLOR_SURFACE,
            text_color=COLOR_TEXT,
            border_width=0,
            corner_radius=8,
            height=220,
        )
        notes_box.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        notes_box.insert("1.0", self._pick_text())
        notes_box.configure(state="disabled")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 18))

        ctk.CTkButton(
            btn_row,
            text="Later",
            command=self.destroy,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            width=90,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Skip This",
            command=self._on_skip,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_TEXT_DIM,
            width=100,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            btn_row,
            text="Never Check",
            command=self._on_never,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_SURFACE,
            text_color=COLOR_DANGER,
            width=110,
        ).pack(side="left", padx=(10, 0))

        url = self._pick_url()
        if url:
            ctk.CTkButton(
                btn_row,
                text="Open Release",
                command=lambda: self._open_url(url),
                fg_color=COLOR_TEXT,
                hover_color=COLOR_ACCENT_HOVER,
                text_color=COLOR_BG,
                width=120,
            ).pack(side="right")

    def _on_skip(self):
        try:
            self.parent.update_checker.skip_update()
        except Exception:
            pass
        self.destroy()

    def _on_never(self):
        try:
            self.parent.update_checker.set_never_update(True)
        except Exception:
            pass
        self.destroy()

    def _open_url(self, url: str):
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass


class SettingsWindow(ctk.CTkToplevel):
    """OpenCV 椤ず瑷疆瑕栫獥"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("display settings")
        self.geometry("400x600")
        self.resizable(False, False)
        
        # 缃腑椤ず
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.geometry(f"+{x}+{y}")
        
        # 瑷疆鐐烘ā鎱嬭绐?
        self.transient(parent)
        self.grab_set()
        
        # 闂滈枆瑕栫獥鏅傝嚜鍕曚繚瀛樿ō缃?
        self.protocol("WM_DELETE_WINDOW", self._on_save)
        
        # 鑷ㄦ檪鍎插瓨瑷疆锛堢敤鏂煎彇娑堬級
        self.temp_settings = {
            "show_opencv_windows": getattr(config, "show_opencv_windows", True),
            "show_opencv_mask": getattr(config, "show_opencv_mask", True),
            "show_opencv_detection": getattr(config, "show_opencv_detection", True),
            "show_opencv_roi": getattr(config, "show_opencv_roi", True),
            "show_opencv_triggerbot_mask": getattr(config, "show_opencv_triggerbot_mask", True),
            "show_ndi_raw_stream_window": getattr(config, "show_ndi_raw_stream_window", False),
            "show_udp_raw_stream_window": getattr(config, "show_udp_raw_stream_window", False),
            "show_mode_text": getattr(config, "show_mode_text", True),
            "show_aimbot_status": getattr(config, "show_aimbot_status", True),
            "show_triggerbot_status": getattr(config, "show_triggerbot_status", True),
            "show_target_count": getattr(config, "show_target_count", True),
            "show_crosshair": getattr(config, "show_crosshair", True),
            "show_distance_text": getattr(config, "show_distance_text", True)
        }
        
        self._build_ui()
    
    def _build_ui(self):
        """妲嬪缓 UI"""
        # 涓诲鍣?- 浣跨敤娣辫壊鑳屾櫙锛屽～婊挎暣鍊嬭绐?
        main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 鍏ч儴瀹瑰櫒 (鐢ㄦ柤鍏у閭婅窛)
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 妯欓
        title_label = ctk.CTkLabel(
            content_frame,
            text="DISPLAY SETTINGS",
            font=("Roboto", 16, "bold"),
            text_color=COLOR_TEXT
        )
        title_label.pack(pady=(0, 20), anchor="w")
        
        # 鍒嗙祫1: 鍏ㄥ眬椤ず瑷疆
        self._add_section_title(content_frame, "VISUAL SETTINGS")
        
        # OpenCV 瑕栫獥绺介枊闂?(Switch)
        self.show_opencv_var = tk.BooleanVar(value=self.temp_settings["show_opencv_windows"])
        self._add_switch(content_frame, "Show OpenCV Windows", self.show_opencv_var)

        # 鍒嗛殧
        self._add_spacer(content_frame)
        
        # 鍒嗙祫1.5: OpenCV 瑕栫獥瑭崇窗瑷疆
        self._add_section_title(content_frame, "OPENCV WINDOWS")
        
        # 浣跨敤 Grid 浣堝眬渚嗘帓鍒?OpenCV 瑕栫獥闁嬮棞
        opencv_grid_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        opencv_grid_frame.pack(fill="x", pady=5)
        opencv_grid_frame.grid_columnconfigure(0, weight=1)
        opencv_grid_frame.grid_columnconfigure(1, weight=1)
        
        # 鍚勯爡 OpenCV 瑕栫獥闁嬮棞
        self.show_opencv_mask_var = tk.BooleanVar(value=self.temp_settings["show_opencv_mask"])
        self._add_grid_switch(opencv_grid_frame, "MASK", self.show_opencv_mask_var, 0, 0)
        
        self.show_opencv_detection_var = tk.BooleanVar(value=self.temp_settings["show_opencv_detection"])
        self._add_grid_switch(opencv_grid_frame, "Detection", self.show_opencv_detection_var, 0, 1)
        
        self.show_opencv_roi_var = tk.BooleanVar(value=self.temp_settings["show_opencv_roi"])
        self._add_grid_switch(opencv_grid_frame, "ROI", self.show_opencv_roi_var, 1, 0)
        
        self.show_opencv_triggerbot_mask_var = tk.BooleanVar(value=self.temp_settings["show_opencv_triggerbot_mask"])
        self._add_grid_switch(opencv_grid_frame, "Triggerbot Mask", self.show_opencv_triggerbot_mask_var, 1, 1)

        self.show_ndi_raw_stream_var = tk.BooleanVar(value=self.temp_settings["show_ndi_raw_stream_window"])
        self._add_grid_switch(opencv_grid_frame, "NDI Raw Stream", self.show_ndi_raw_stream_var, 2, 0)

        self.show_udp_raw_stream_var = tk.BooleanVar(value=self.temp_settings["show_udp_raw_stream_window"])
        self._add_grid_switch(opencv_grid_frame, "UDP Raw Stream", self.show_udp_raw_stream_var, 2, 1)

        # 鍒嗛殧
        self._add_spacer(content_frame)
        
        # 鍒嗙祫2: 鏂囧瓧璩囪▕ (Overlay Elements)
        self._add_section_title(content_frame, "OVERLAY ELEMENTS")
        
        # 浣跨敤 Grid 浣堝眬渚嗘帓鍒楅枊闂滐紝浣垮叾鏇存暣榻?
        grid_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        # 鍚勯爡闁嬮棞 (Switch instead of Checkbox for better look)
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
        
        # 搴曢儴鎸夐垥鍗€鍩?
        # 浣跨敤 Spacer 鎺ㄥ埌搴曢儴
        ctk.CTkFrame(content_frame, fg_color="transparent").pack(fill="both", expand=True)
        
        # 鍒嗛殧绶?
        ctk.CTkFrame(content_frame, height=1, fg_color=COLOR_BORDER).pack(fill="x", pady=(0, 15))
        
        # 鎸夐垥瀹瑰櫒
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 5))
        
        # 鍙栨秷鎸夐垥 (Outlined)
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
        
        # 淇濆瓨鎸夐垥 (Filled)
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
        """淇濆瓨瑷疆"""
        # 鏇存柊閰嶇疆
        config.show_opencv_windows = self.show_opencv_var.get()
        config.show_opencv_mask = self.show_opencv_mask_var.get()
        config.show_opencv_detection = self.show_opencv_detection_var.get()
        config.show_opencv_roi = self.show_opencv_roi_var.get()
        config.show_opencv_triggerbot_mask = self.show_opencv_triggerbot_mask_var.get()
        config.show_ndi_raw_stream_window = self.show_ndi_raw_stream_var.get()
        config.show_udp_raw_stream_window = self.show_udp_raw_stream_var.get()
        config.show_mode_text = self.show_mode_var.get()
        config.show_aimbot_status = self.show_aimbot_status_var.get()
        config.show_triggerbot_status = self.show_triggerbot_status_var.get()
        config.show_target_count = self.show_target_count_var.get()
        config.show_crosshair = self.show_crosshair_var.get()
        config.show_distance_text = self.show_distance_var.get()
        
        # 淇濆瓨鍒版枃浠?
        config.save_to_file()
        
        # 闂滈枆瑕栫獥
        self.destroy()
    
    def _on_cancel(self):
        """鍙栨秷涓﹂棞闁?- 涓嶄繚瀛樹换浣曟洿鏀癸紝鎭㈠京鍘熷瑷疆"""
        self.destroy()



