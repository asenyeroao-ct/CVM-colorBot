"""
HSV Filter Preview Window - real-time preview for HSV filter tuning.
"""
import threading
import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from src.utils.config import config
from src.utils.debug_logger import log_print

COLOR_BG = "#121212"
COLOR_SURFACE = "#1E1E1E"
COLOR_ACCENT = "#FFFFFF"
COLOR_TEXT = "#E0E0E0"
COLOR_TEXT_DIM = "#757575"
COLOR_BORDER = "#2C2C2C"
COLOR_SUCCESS = "#4CAF50"
COLOR_DANGER = "#CF6679"

FONT_MAIN = ("Roboto", 11)
FONT_BOLD = ("Roboto", 11, "bold")
FONT_TITLE = ("Roboto", 13, "bold")
FONT_SMALL = ("Roboto", 10)

PREVIEW_W = 320
PREVIEW_H = 240

EYEDROPPER_H_TOL = 8
EYEDROPPER_S_TOL = 45
EYEDROPPER_V_TOL = 45


def _grab_frame_bgr(capture_service) -> np.ndarray | None:
    """Capture a BGR frame using the same path as the main loop."""
    try:
        frame = capture_service.read_frame(apply_fov=False)
        if frame is not None and frame.size > 0:
            if len(frame.shape) == 2:
                return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            if frame.shape[2] == 4:
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return frame.copy()
    except Exception as exc:
        log_print(f"[HsvPreview] grab frame error: {exc}")
    return None


def _apply_hsv_mask(bgr: np.ndarray, h_lo, h_hi, s_lo, s_hi, v_lo, v_hi):
    """Apply HSV mask and return (filtered image, binary mask)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lo = np.array([h_lo, s_lo, v_lo], dtype=np.uint8)
    hi = np.array([h_hi, s_hi, v_hi], dtype=np.uint8)
    mask = cv2.inRange(hsv, lo, hi)

    result = bgr.copy()
    result[mask == 0] = (result[mask == 0] * 0.2).astype(np.uint8)
    result[mask > 0] = np.clip(
        result[mask > 0].astype(np.int16) + [0, 60, 0], 0, 255
    ).astype(np.uint8)
    return result, mask


def _bgr_to_pil(bgr: np.ndarray, w: int, h: int) -> ImageTk.PhotoImage:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb).resize((w, h), Image.NEAREST)
    return ImageTk.PhotoImage(pil)


def _gray_to_pil(gray: np.ndarray, w: int, h: int) -> ImageTk.PhotoImage:
    pil = Image.fromarray(gray).resize((w, h), Image.NEAREST)
    return ImageTk.PhotoImage(pil)


class HsvPreviewWindow(ctk.CTkToplevel):
    """
    Real-time HSV filter preview window.
    Shows live capture with HSV mask applied alongside the binary mask.
    Each channel (H, S, V) has Low and High sliders in the same row.
    """

    def __init__(self, parent, capture_service, on_apply_callback=None):
        super().__init__(parent)

        self.capture_service = capture_service
        self.on_apply_callback = on_apply_callback

        self._h_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_h", 0)))
        self._h_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_h", 179)))
        self._s_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_s", 0)))
        self._s_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_s", 255)))
        self._v_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_v", 0)))
        self._v_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_v", 255)))

        self._running = True
        self._last_bgr = None
        self._preview_hsv = None
        self._lock = threading.Lock()

        self._photo_orig = None
        self._photo_mask = None
        self._photo_result = None

        self._eyedropper_active = False
        self._eyedropper_icon = None
        self._preview_canvases = []

        self._build_ui()
        self._start_capture_thread()
        self._schedule_update()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.title("HSV Filter Preview")
        self.configure(fg_color=COLOR_BG)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        title_bar = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=0)
        title_bar.pack(fill="x")
        ctk.CTkLabel(
            title_bar,
            text="HSV FILTER PREVIEW",
            font=FONT_TITLE,
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(
            title_bar,
            text="Adjust sliders and see the result in real time",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        ).pack(side="left", padx=4)

        main = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLOR_BORDER,
            scrollbar_button_hover_color=COLOR_SURFACE,
        )
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        prev_row = ctk.CTkFrame(main, fg_color="transparent")
        prev_row.pack(fill="x")

        orig_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        orig_col.pack(side="left", expand=True, fill="both", padx=(0, 6))
        ctk.CTkLabel(
            orig_col,
            text="ORIGINAL",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        ).pack(pady=(6, 2))
        self._canvas_orig = tk.Canvas(
            orig_col,
            width=PREVIEW_W,
            height=PREVIEW_H,
            bg="#000000",
            highlightthickness=0,
        )
        self._canvas_orig.pack(padx=6, pady=(0, 6))

        res_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        res_col.pack(side="left", expand=True, fill="both", padx=(6, 6))
        ctk.CTkLabel(
            res_col,
            text="WITH FILTER",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        ).pack(pady=(6, 2))
        self._canvas_result = tk.Canvas(
            res_col,
            width=PREVIEW_W,
            height=PREVIEW_H,
            bg="#000000",
            highlightthickness=0,
        )
        self._canvas_result.pack(padx=6, pady=(0, 6))

        mask_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        mask_col.pack(side="left", expand=True, fill="both", padx=(6, 0))
        ctk.CTkLabel(
            mask_col,
            text="MASK",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        ).pack(pady=(6, 2))
        self._canvas_mask = tk.Canvas(
            mask_col,
            width=PREVIEW_W,
            height=PREVIEW_H,
            bg="#000000",
            highlightthickness=0,
        )
        self._canvas_mask.pack(padx=6, pady=(0, 6))

        self._preview_canvases = [self._canvas_orig, self._canvas_result, self._canvas_mask]
        for canvas in self._preview_canvases:
            canvas.bind("<Button-1>", self._on_preview_click)

        sliders_frame = ctk.CTkFrame(main, fg_color=COLOR_SURFACE, corner_radius=6)
        sliders_frame.pack(fill="x", pady=(10, 4))

        ctk.CTkLabel(
            sliders_frame,
            text="HSV RANGE",
            font=FONT_BOLD,
            text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self._build_channel_row(sliders_frame, "H  Hue", self._h_lo, self._h_hi, 0, 179, "#E05050")
        self._build_channel_row(sliders_frame, "S  Sat", self._s_lo, self._s_hi, 0, 255, "#50B0E0")
        self._build_channel_row(sliders_frame, "V  Val", self._v_lo, self._v_hi, 0, 255, "#80E080")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))

        self._eyedropper_icon = self._load_eyedropper_icon()
        self._btn_eyedropper = ctk.CTkButton(
            btn_row,
            text="" if self._eyedropper_icon else "Pick",
            image=self._eyedropper_icon,
            width=40,
            height=32,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            corner_radius=4,
            command=self._toggle_eyedropper,
        )
        self._btn_eyedropper.pack(side="left", padx=(0, 6))

        self._lbl_pixels = ctk.CTkLabel(
            btn_row,
            text="Detected pixels: 0",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        )
        self._lbl_pixels.pack(side="left", padx=8)

        self._lbl_pick = ctk.CTkLabel(
            btn_row,
            text="Pick mode: Off",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        )
        self._lbl_pick.pack(side="left", padx=(4, 8))

        ctk.CTkButton(
            btn_row,
            text="Close",
            width=100,
            height=32,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            corner_radius=4,
            command=self._on_close,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_row,
            text="Apply to Config",
            width=160,
            height=32,
            fg_color=COLOR_SUCCESS,
            hover_color="#388E3C",
            text_color="#000000",
            font=FONT_BOLD,
            corner_radius=4,
            command=self._on_apply,
        ).pack(side="right", padx=6)

        ctk.CTkButton(
            btn_row,
            text="Reset",
            width=80,
            height=32,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_DANGER,
            font=FONT_MAIN,
            corner_radius=4,
            command=self._on_reset,
        ).pack(side="right", padx=6)

        self._set_eyedropper_active(False)

    def _build_channel_row(
        self,
        parent,
        label: str,
        var_lo: tk.IntVar,
        var_hi: tk.IntVar,
        min_v: int,
        max_v: int,
        accent: str,
    ):
        """Create a row with Low and High sliders for one HSV channel."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(
            row,
            text=label,
            font=FONT_BOLD,
            text_color=COLOR_TEXT,
            width=60,
            anchor="w",
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        ctk.CTkLabel(
            row,
            text="Low",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            width=30,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        lbl_lo = ctk.CTkLabel(
            row,
            text=str(var_lo.get()),
            font=FONT_BOLD,
            text_color=COLOR_TEXT,
            width=36,
            anchor="e",
        )
        lbl_lo.grid(row=0, column=3, sticky="e", padx=(4, 0))
        slider_lo = ctk.CTkSlider(
            row,
            from_=min_v,
            to=max_v,
            number_of_steps=max_v,
            fg_color=COLOR_BORDER,
            progress_color=accent,
            button_color=accent,
            button_hover_color=COLOR_ACCENT,
            height=10,
            variable=var_lo,
            command=lambda v, lbl=lbl_lo, var=var_lo: self._on_slider(v, lbl, var, True, var_hi),
        )
        slider_lo.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        ctk.CTkLabel(
            row,
            text="High",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            width=30,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")
        lbl_hi = ctk.CTkLabel(
            row,
            text=str(var_hi.get()),
            font=FONT_BOLD,
            text_color=COLOR_TEXT,
            width=36,
            anchor="e",
        )
        lbl_hi.grid(row=1, column=3, sticky="e", padx=(4, 0))
        slider_hi = ctk.CTkSlider(
            row,
            from_=min_v,
            to=max_v,
            number_of_steps=max_v,
            fg_color=COLOR_BORDER,
            progress_color=accent,
            button_color=accent,
            button_hover_color=COLOR_ACCENT,
            height=10,
            variable=var_hi,
            command=lambda v, lbl=lbl_hi, var=var_hi: self._on_slider(v, lbl, var, False, var_lo),
        )
        slider_hi.grid(row=1, column=2, sticky="ew", padx=(4, 0))

        var_lo.trace_add("write", lambda *_args, lbl=lbl_lo, var=var_lo: lbl.configure(text=str(var.get())))
        var_hi.trace_add("write", lambda *_args, lbl=lbl_hi, var=var_hi: lbl.configure(text=str(var.get())))

        row.columnconfigure(2, weight=1)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_slider(self, val, label_widget, var: tk.IntVar, is_low: bool, partner: tk.IntVar):
        """Update label and enforce low <= high constraint."""
        ival = int(round(float(val)))
        var.set(ival)
        label_widget.configure(text=str(ival))
        if is_low and ival > partner.get():
            partner.set(ival)
        elif not is_low and ival < partner.get():
            partner.set(ival)

    def _on_apply(self):
        """Save current slider values to config."""
        config.custom_hsv_min_h = self._h_lo.get()
        config.custom_hsv_max_h = self._h_hi.get()
        config.custom_hsv_min_s = self._s_lo.get()
        config.custom_hsv_max_s = self._s_hi.get()
        config.custom_hsv_min_v = self._v_lo.get()
        config.custom_hsv_max_v = self._v_hi.get()
        config.save_to_file()
        log_print(
            f"[HsvPreview] Applied: H[{self._h_lo.get()}-{self._h_hi.get()}] "
            f"S[{self._s_lo.get()}-{self._s_hi.get()}] "
            f"V[{self._v_lo.get()}-{self._v_hi.get()}]"
        )
        if self.on_apply_callback:
            self.on_apply_callback()

    def _on_reset(self):
        """Restore values from saved config."""
        self._set_eyedropper_active(False)
        self._h_lo.set(int(getattr(config, "custom_hsv_min_h", 0)))
        self._h_hi.set(int(getattr(config, "custom_hsv_max_h", 179)))
        self._s_lo.set(int(getattr(config, "custom_hsv_min_s", 0)))
        self._s_hi.set(int(getattr(config, "custom_hsv_max_s", 255)))
        self._v_lo.set(int(getattr(config, "custom_hsv_min_v", 0)))
        self._v_hi.set(int(getattr(config, "custom_hsv_max_v", 255)))
        self._lbl_pick.configure(text="Pick mode: Off")

    def _toggle_eyedropper(self):
        self._set_eyedropper_active(not self._eyedropper_active)

    def _set_eyedropper_active(self, is_active: bool):
        self._eyedropper_active = bool(is_active)

        cursor = "crosshair" if self._eyedropper_active else ""
        for canvas in self._preview_canvases:
            canvas.configure(cursor=cursor)

        if self._eyedropper_active:
            self._btn_eyedropper.configure(
                fg_color=COLOR_SUCCESS,
                hover_color="#388E3C",
                text_color="#000000",
            )
            self._lbl_pick.configure(text="Pick mode: ON (click preview)")
        else:
            self._btn_eyedropper.configure(
                fg_color=COLOR_SURFACE,
                hover_color=COLOR_BORDER,
                text_color=COLOR_TEXT,
            )

    def _on_preview_click(self, event):
        if not self._eyedropper_active or self._preview_hsv is None:
            return

        x = max(0, min(int(event.x), PREVIEW_W - 1))
        y = max(0, min(int(event.y), PREVIEW_H - 1))

        src_h, src_w = self._preview_hsv.shape[:2]
        src_x = min(src_w - 1, int(x * src_w / PREVIEW_W))
        src_y = min(src_h - 1, int(y * src_h / PREVIEW_H))

        h, s, v = [int(vv) for vv in self._preview_hsv[src_y, src_x]]
        self._set_hsv_range_from_pick(h, s, v)
        self._set_eyedropper_active(False)

        self._lbl_pick.configure(text=f"Picked HSV: {h}, {s}, {v}")
        log_print(f"[HsvPreview] Eyedropper picked HSV ({h}, {s}, {v}) at ({src_x}, {src_y})")

    def _set_hsv_range_from_pick(self, h: int, s: int, v: int):
        self._h_lo.set(max(0, h - EYEDROPPER_H_TOL))
        self._h_hi.set(min(179, h + EYEDROPPER_H_TOL))
        self._s_lo.set(max(0, s - EYEDROPPER_S_TOL))
        self._s_hi.set(min(255, s + EYEDROPPER_S_TOL))
        self._v_lo.set(max(0, v - EYEDROPPER_V_TOL))
        self._v_hi.set(min(255, v + EYEDROPPER_V_TOL))

    @staticmethod
    def _load_eyedropper_icon():
        root_dir = Path(__file__).resolve().parent.parent
        icon_path = root_dir / "themes" / "icon" / "EyedropperTool.png"
        if not icon_path.exists():
            log_print(f"[HsvPreview] Eyedropper icon not found: {icon_path}")
            return None

        try:
            icon_img = Image.open(icon_path).convert("RGBA")
            return ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(18, 18))
        except Exception as exc:
            log_print(f"[HsvPreview] Failed to load eyedropper icon: {exc}")
            return None

    def _on_close(self):
        self._running = False
        try:
            self.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Capture thread
    # ------------------------------------------------------------------

    def _start_capture_thread(self):
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()

    def _capture_loop(self):
        while self._running:
            bgr = _grab_frame_bgr(self.capture_service)
            if bgr is not None:
                with self._lock:
                    self._last_bgr = bgr
            time.sleep(0.05)  # ~20 fps

    # ------------------------------------------------------------------
    # Preview update loop (main thread via after)
    # ------------------------------------------------------------------

    def _schedule_update(self):
        if not self._running:
            return
        try:
            self._update_preview()
        except Exception as exc:
            log_print(f"[HsvPreview] update error: {exc}")
        self.after(50, self._schedule_update)  # ~20 fps

    def _update_preview(self):
        with self._lock:
            bgr = self._last_bgr.copy() if self._last_bgr is not None else None

        if bgr is None:
            bgr = self._make_placeholder()

        h_lo, h_hi = self._h_lo.get(), self._h_hi.get()
        s_lo, s_hi = self._s_lo.get(), self._s_hi.get()
        v_lo, v_hi = self._v_lo.get(), self._v_hi.get()

        self._preview_hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        result, mask = _apply_hsv_mask(bgr, h_lo, h_hi, s_lo, s_hi, v_lo, v_hi)
        pixel_count = int(cv2.countNonZero(mask))

        self._photo_orig = _bgr_to_pil(bgr, PREVIEW_W, PREVIEW_H)
        self._photo_result = _bgr_to_pil(result, PREVIEW_W, PREVIEW_H)
        self._photo_mask = _gray_to_pil(mask, PREVIEW_W, PREVIEW_H)

        self._canvas_orig.delete("all")
        self._canvas_result.delete("all")
        self._canvas_mask.delete("all")

        self._canvas_orig.create_image(0, 0, anchor="nw", image=self._photo_orig)
        self._canvas_result.create_image(0, 0, anchor="nw", image=self._photo_result)
        self._canvas_mask.create_image(0, 0, anchor="nw", image=self._photo_mask)

        self._lbl_pixels.configure(text=f"Detected pixels: {pixel_count}")

    @staticmethod
    def _make_placeholder() -> np.ndarray:
        """Generate a hue-gradient placeholder when there is no capture signal."""
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        for x in range(320):
            h = int(x / 320 * 179)
            col = cv2.cvtColor(
                np.array([[[h, 200, 200]]], dtype=np.uint8),
                cv2.COLOR_HSV2BGR,
            )[0][0]
            img[:, x] = col

        cv2.putText(
            img,
            "No capture signal",
            (60, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        return img

    def destroy(self):
        self._running = False
        if hasattr(self, "_preview_canvases") and hasattr(self, "_btn_eyedropper"):
            self._set_eyedropper_active(False)
        super().destroy()
