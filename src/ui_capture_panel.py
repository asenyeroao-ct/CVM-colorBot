"""Independent capture settings panel opened from the General tab card."""
import tkinter as tk
import customtkinter as ctk

from src.utils.config import config

COLOR_BG = "#040B16"
COLOR_SURFACE = "#061325"
COLOR_ACCENT = "#00FF41"
COLOR_TEXT = "#B9D8FF"
COLOR_TEXT_DIM = "#5F7FA8"
COLOR_BORDER = "#0B7A2B"
COLOR_SUCCESS = "#00FF7F"
COLOR_DANGER = "#FF4D6D"


class CapturePanelWindow(ctk.CTkToplevel):
    """Standalone capture settings window."""

    def __init__(self, parent, on_close=None):
        super().__init__(parent)
        self.app = parent
        self._on_close = on_close

        self.title("Capture Settings")
        self.configure(fg_color=COLOR_BG)
        self.geometry("760x720")
        self.minsize(640, 520)
        self.attributes("-topmost", True)

        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.bind("<Escape>", lambda _event: self._handle_close())

        header = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="CAPTURE SETTINGS",
            font=("Consolas", 16, "bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=16, pady=12)
        self.status_label = ctk.CTkLabel(
            header,
            text=self._status_text(),
            font=("Consolas", 11),
            text_color=COLOR_TEXT_DIM,
        )
        self.status_label.pack(side="right", padx=16)

        body = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLOR_BORDER,
            scrollbar_button_hover_color=COLOR_SURFACE,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 16))
        self.body = body

        try:
            self.update_idletasks()
            x = parent.winfo_x() + parent.winfo_width() + 12
            y = parent.winfo_y()
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.after(50, self.lift)
        self.after(80, self.focus_force)

    def _status_text(self):
        mode = str(getattr(self.app.capture, "mode", getattr(config, "capture_mode", "NDI")))
        connected = False
        try:
            connected = bool(self.app.capture.is_connected())
        except Exception:
            connected = False
        state = "Connected" if connected else "Disconnected"
        return f"{self._display_mode(mode)}  ·  {state}"

    @staticmethod
    def _display_mode(mode):
        mapping = {
            "CaptureCard": "Capture Card (OpenCV)",
            "CaptureCardGStreamer": "Capture Card (GStreamer)",
        }
        return mapping.get(str(mode), str(mode))

    def refresh_status(self):
        if self.winfo_exists():
            self.status_label.configure(text=self._status_text())
            color = COLOR_SUCCESS if "Connected" in self._status_text() else COLOR_TEXT_DIM
            try:
                connected = bool(self.app.capture.is_connected())
                self.status_label.configure(text_color=COLOR_SUCCESS if connected else COLOR_TEXT_DIM)
            except Exception:
                self.status_label.configure(text_color=color)

    def _handle_close(self):
        callback = self._on_close
        try:
            self.destroy()
        except Exception:
            pass
        if callable(callback):
            callback()
