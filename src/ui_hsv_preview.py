"""
HSV Filter Preview Window
Janela de preview em tempo real para ajuste dos valores HSV.
"""
import threading
import time
import tkinter as tk

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from src.utils.config import config
from src.utils.debug_logger import log_print

# --- Cores (herda o tema da UI principal) ---
COLOR_BG      = "#121212"
COLOR_SURFACE = "#1E1E1E"
COLOR_ACCENT  = "#FFFFFF"
COLOR_TEXT    = "#E0E0E0"
COLOR_TEXT_DIM = "#757575"
COLOR_BORDER  = "#2C2C2C"
COLOR_SUCCESS = "#4CAF50"
COLOR_DANGER  = "#CF6679"

FONT_MAIN  = ("Roboto", 11)
FONT_BOLD  = ("Roboto", 11, "bold")
FONT_TITLE = ("Roboto", 13, "bold")
FONT_SMALL = ("Roboto", 10)

PREVIEW_W = 320
PREVIEW_H = 240


def _grab_frame_bgr(capture_service) -> np.ndarray | None:
    """Tenta capturar um frame BGR da fonte ativa. Retorna None se falhar."""
    try:
        mode = getattr(capture_service, "mode", "NDI")

        if mode == "NDI":
            ndi = getattr(capture_service, "ndi", None)
            if ndi and ndi.is_connected():
                frame = ndi.capture_frame()
                if frame is not None:
                    raw = np.frombuffer(frame.data, dtype=np.uint8).reshape(
                        frame.yres, frame.xres, 4
                    )
                    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

        elif mode == "UDP":
            udp = getattr(capture_service, "udp_manager", None)
            if udp:
                receiver = udp.get_receiver() if hasattr(udp, "get_receiver") else None
                if receiver:
                    frame = receiver.get_current_frame()
                    if frame is not None and frame.size > 0:
                        if len(frame.shape) == 2:
                            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        if frame.shape[2] == 4:
                            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        return frame.copy()

        elif mode == "MSS":
            mss = getattr(capture_service, "mss_capture", None)
            if mss and mss.is_connected():
                frame = mss.capture_frame()
                if frame is not None and frame.size > 0:
                    if len(frame.shape) == 2:
                        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    if frame.shape[2] == 4:
                        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    return frame.copy()

        elif mode == "CaptureCard":
            cam = getattr(capture_service, "capture_card_camera", None)
            if cam:
                ret, frame = cam.read()
                if ret and frame is not None:
                    return frame.copy()

    except Exception as exc:
        log_print(f"[HsvPreview] grab frame error: {exc}")

    return None


def _apply_hsv_mask(bgr: np.ndarray, h_lo, h_hi, s_lo, s_hi, v_lo, v_hi) -> np.ndarray:
    """Aplica a máscara HSV e retorna a imagem com a máscara visível em verde sobre escuro."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lo = np.array([h_lo, s_lo, v_lo], dtype=np.uint8)
    hi = np.array([h_hi, s_hi, v_hi], dtype=np.uint8)
    mask = cv2.inRange(hsv, lo, hi)
    # Aplica a máscara colorida (verde) sobre fundo escuro
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
    Janela de ajuste HSV com preview em tempo real.
    Exibe o frame original e o frame com máscara HSV lado a lado.
    Cada canal (H, S, V) tem dois sliders: Low e High.
    """

    def __init__(self, parent, capture_service, on_apply_callback=None):
        super().__init__(parent)

        self.capture_service = capture_service
        self.on_apply_callback = on_apply_callback

        # Lê valores atuais do config
        self._h_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_h", 0)))
        self._h_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_h", 179)))
        self._s_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_s", 0)))
        self._s_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_s", 255)))
        self._v_lo = tk.IntVar(value=int(getattr(config, "custom_hsv_min_v", 0)))
        self._v_hi = tk.IntVar(value=int(getattr(config, "custom_hsv_max_v", 255)))

        self._running = True
        self._last_bgr = None
        self._lock = threading.Lock()
        self._photo_orig = None
        self._photo_mask = None
        self._photo_result = None

        self._build_ui()
        self._start_capture_thread()
        self._schedule_update()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.title("HSV Filter Preview")
        self.configure(fg_color=COLOR_BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # ── Título ──────────────────────────────────────────────────────
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
            text="Ajuste os sliders e veja o resultado em tempo real",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        ).pack(side="left", padx=4)

        # ── Área principal ───────────────────────────────────────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # ── Previews ─────────────────────────────────────────────────────
        prev_row = ctk.CTkFrame(main, fg_color="transparent")
        prev_row.pack(fill="x")

        # Original
        orig_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        orig_col.pack(side="left", expand=True, fill="both", padx=(0, 6))
        ctk.CTkLabel(orig_col, text="ORIGINAL", font=FONT_SMALL, text_color=COLOR_TEXT_DIM).pack(pady=(6, 2))
        self._canvas_orig = tk.Canvas(
            orig_col, width=PREVIEW_W, height=PREVIEW_H,
            bg="#000000", highlightthickness=0
        )
        self._canvas_orig.pack(padx=6, pady=(0, 6))

        # Resultado (masked)
        res_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        res_col.pack(side="left", expand=True, fill="both", padx=(6, 6))
        ctk.CTkLabel(res_col, text="COM FILTRO HSV", font=FONT_SMALL, text_color=COLOR_TEXT_DIM).pack(pady=(6, 2))
        self._canvas_result = tk.Canvas(
            res_col, width=PREVIEW_W, height=PREVIEW_H,
            bg="#000000", highlightthickness=0
        )
        self._canvas_result.pack(padx=6, pady=(0, 6))

        # Máscara binária
        mask_col = ctk.CTkFrame(prev_row, fg_color=COLOR_SURFACE, corner_radius=6)
        mask_col.pack(side="left", expand=True, fill="both", padx=(6, 0))
        ctk.CTkLabel(mask_col, text="MÁSCARA", font=FONT_SMALL, text_color=COLOR_TEXT_DIM).pack(pady=(6, 2))
        self._canvas_mask = tk.Canvas(
            mask_col, width=PREVIEW_W, height=PREVIEW_H,
            bg="#000000", highlightthickness=0
        )
        self._canvas_mask.pack(padx=6, pady=(0, 6))

        # ── Sliders HSV ───────────────────────────────────────────────────
        sliders_frame = ctk.CTkFrame(main, fg_color=COLOR_SURFACE, corner_radius=6)
        sliders_frame.pack(fill="x", pady=(10, 4))

        ctk.CTkLabel(
            sliders_frame, text="AJUSTE HSV",
            font=FONT_BOLD, text_color=COLOR_TEXT_DIM
        ).pack(anchor="w", padx=14, pady=(10, 4))

        # H
        self._build_channel_row(sliders_frame, "H  Hue", self._h_lo, self._h_hi, 0, 179, "#E05050")
        # S
        self._build_channel_row(sliders_frame, "S  Sat", self._s_lo, self._s_hi, 0, 255, "#50B0E0")
        # V
        self._build_channel_row(sliders_frame, "V  Val", self._v_lo, self._v_hi, 0, 255, "#80E080")

        # ── Botões ────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))

        # Info pixel count
        self._lbl_pixels = ctk.CTkLabel(
            btn_row, text="Pixels detectados: —",
            font=FONT_SMALL, text_color=COLOR_TEXT_DIM
        )
        self._lbl_pixels.pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row,
            text="Fechar",
            width=100, height=32,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=FONT_MAIN,
            corner_radius=4,
            command=self._on_close,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_row,
            text="Aplicar ao Config",
            width=160, height=32,
            fg_color=COLOR_SUCCESS,
            hover_color="#388E3C",
            text_color="#000000",
            font=FONT_BOLD,
            corner_radius=4,
            command=self._on_apply,
        ).pack(side="right", padx=6)

        # Botão Reset
        ctk.CTkButton(
            btn_row,
            text="Reset",
            width=80, height=32,
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_BORDER,
            text_color=COLOR_DANGER,
            font=FONT_MAIN,
            corner_radius=4,
            command=self._on_reset,
        ).pack(side="right", padx=6)

    def _build_channel_row(self, parent, label: str, var_lo: tk.IntVar, var_hi: tk.IntVar,
                           min_v: int, max_v: int, accent: str):
        """Cria uma linha com dois sliders (Low / High) para um canal HSV."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(2, 8))

        # Label canal
        ctk.CTkLabel(row, text=label, font=FONT_BOLD, text_color=COLOR_TEXT, width=60, anchor="w").grid(
            row=0, column=0, rowspan=2, sticky="w", padx=(0, 12)
        )

        # ─ Low ─
        ctk.CTkLabel(row, text="Low", font=FONT_SMALL, text_color=COLOR_TEXT_DIM, width=30, anchor="w").grid(
            row=0, column=1, sticky="w"
        )
        lbl_lo = ctk.CTkLabel(row, text=str(var_lo.get()), font=FONT_BOLD, text_color=COLOR_TEXT, width=36, anchor="e")
        lbl_lo.grid(row=0, column=3, sticky="e", padx=(4, 0))

        slider_lo = ctk.CTkSlider(
            row,
            from_=min_v, to=max_v,
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

        # ─ High ─
        ctk.CTkLabel(row, text="High", font=FONT_SMALL, text_color=COLOR_TEXT_DIM, width=30, anchor="w").grid(
            row=1, column=1, sticky="w"
        )
        lbl_hi = ctk.CTkLabel(row, text=str(var_hi.get()), font=FONT_BOLD, text_color=COLOR_TEXT, width=36, anchor="e")
        lbl_hi.grid(row=1, column=3, sticky="e", padx=(4, 0))

        slider_hi = ctk.CTkSlider(
            row,
            from_=min_v, to=max_v,
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

        row.columnconfigure(2, weight=1)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_slider(self, val, label_widget, var: tk.IntVar, is_low: bool, partner: tk.IntVar):
        """Atualiza label e garante low <= high."""
        ival = int(round(float(val)))
        var.set(ival)
        label_widget.configure(text=str(ival))

        # Garante low <= high
        if is_low and ival > partner.get():
            partner.set(ival)
        elif not is_low and ival < partner.get():
            partner.set(ival)

    def _on_apply(self):
        """Salva os valores atuais no config."""
        config.custom_hsv_min_h = self._h_lo.get()
        config.custom_hsv_max_h = self._h_hi.get()
        config.custom_hsv_min_s = self._s_lo.get()
        config.custom_hsv_max_s = self._s_hi.get()
        config.custom_hsv_min_v = self._v_lo.get()
        config.custom_hsv_max_v = self._v_hi.get()
        config.save_to_file()
        log_print(
            f"[HsvPreview] Aplicado: H[{self._h_lo.get()}-{self._h_hi.get()}] "
            f"S[{self._s_lo.get()}-{self._s_hi.get()}] "
            f"V[{self._v_lo.get()}-{self._v_hi.get()}]"
        )
        if self.on_apply_callback:
            self.on_apply_callback()

    def _on_reset(self):
        """Reseta para os valores do config atual."""
        self._h_lo.set(int(getattr(config, "custom_hsv_min_h", 0)))
        self._h_hi.set(int(getattr(config, "custom_hsv_max_h", 179)))
        self._s_lo.set(int(getattr(config, "custom_hsv_min_s", 0)))
        self._s_hi.set(int(getattr(config, "custom_hsv_max_s", 255)))
        self._v_lo.set(int(getattr(config, "custom_hsv_min_v", 0)))
        self._v_hi.set(int(getattr(config, "custom_hsv_max_v", 255)))

    def _on_close(self):
        self._running = False
        try:
            self.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Captura em thread separada
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
            time.sleep(0.05)  # ~20 fps de captura

    # ------------------------------------------------------------------
    # Loop de atualização do preview (main thread via after)
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

        # Parâmetros atuais dos sliders
        h_lo = self._h_lo.get()
        h_hi = self._h_hi.get()
        s_lo = self._s_lo.get()
        s_hi = self._s_hi.get()
        v_lo = self._v_lo.get()
        v_hi = self._v_hi.get()

        result, mask = _apply_hsv_mask(bgr, h_lo, h_hi, s_lo, s_hi, v_lo, v_hi)
        pixel_count = int(cv2.countNonZero(mask))

        # Converte para PhotoImage (mantém referência para evitar GC)
        self._photo_orig   = _bgr_to_pil(bgr,    PREVIEW_W, PREVIEW_H)
        self._photo_result = _bgr_to_pil(result,  PREVIEW_W, PREVIEW_H)
        self._photo_mask   = _gray_to_pil(mask,   PREVIEW_W, PREVIEW_H)

        self._canvas_orig.create_image(0, 0, anchor="nw", image=self._photo_orig)
        self._canvas_result.create_image(0, 0, anchor="nw", image=self._photo_result)
        self._canvas_mask.create_image(0, 0, anchor="nw", image=self._photo_mask)

        self._lbl_pixels.configure(text=f"Pixels detectados: {pixel_count}")

    @staticmethod
    def _make_placeholder() -> np.ndarray:
        """Gera uma imagem gradiente de placeholder quando não há frame."""
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        for x in range(320):
            h = int(x / 320 * 179)
            col = cv2.cvtColor(np.array([[[h, 200, 200]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)[0][0]
            img[:, x] = col
        cv2.putText(
            img, "Sem sinal de captura", (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA
        )
        return img

    def destroy(self):
        self._running = False
        super().destroy()
