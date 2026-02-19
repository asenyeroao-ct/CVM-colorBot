"""
RGB Trigger module.
"""
import random
import threading
import time

try:
    import cv2
except Exception:
    cv2 = None

import numpy as np

from src.utils.config import config
from src.utils.debug_logger import log_print
from src.utils.mouse import is_button_pressed
from .trigger_strafe_helper import apply_manual_wait_gate, reset_strafe_runtime_state, run_with_auto_strafe


RGB_PRESETS = {
    "red": {"rgb": (180, 40, 40), "tol_min": 30, "tol_max": 30},
    "yellow": {"rgb": (230, 230, 80), "tol_min": 35, "tol_max": 35},
    "purple": {"rgb": (161, 69, 163), "tol_min": 25, "tol_max": 30},
}


def _is_valid_button_index(value):
    try:
        button_index = int(value)
    except (TypeError, ValueError):
        return False
    return 0 <= button_index <= 4


def _safe_button_pressed(value):
    if not _is_valid_button_index(value):
        return False
    try:
        return bool(is_button_pressed(int(value)))
    except Exception:
        return False


def _resolve_activation_mode(state_dict, selected_tb_btn, selected_2_tb):
    mode = str(getattr(config, "trigger_activation_type", "hold_enable")).strip().lower()
    if mode not in {"hold_enable", "hold_disable", "toggle"}:
        mode = "hold_enable"

    primary_valid = _is_valid_button_index(selected_tb_btn)
    secondary_valid = _is_valid_button_index(selected_2_tb)
    if not primary_valid and not secondary_valid:
        return False, False, "BUTTON_NOT_CONFIGURED"

    pressed_primary = _safe_button_pressed(selected_tb_btn) if primary_valid else False
    pressed_secondary = _safe_button_pressed(selected_2_tb) if secondary_valid else False
    is_pressed = bool(pressed_primary or pressed_secondary)

    if mode == "hold_enable":
        active = is_pressed
    elif mode == "hold_disable":
        active = not is_pressed
    else:
        last_pressed = bool(state_dict.get("activation_last_pressed", False))
        toggle_state = bool(state_dict.get("activation_toggle_state", False))
        if (not last_pressed) and is_pressed:
            toggle_state = not toggle_state
        state_dict["activation_toggle_state"] = toggle_state
        active = toggle_state

    state_dict["activation_last_pressed"] = is_pressed
    return active, is_pressed, None


def _reset_wait_state(state_dict):
    with state_dict["burst_lock"]:
        if state_dict.get("burst_state") != "bursting":
            state_dict["enter_range_time"] = None
            state_dict["random_delay"] = None
            state_dict["burst_state"] = None
        state_dict["confirm_count"] = 0


def _resolve_rgb_profile():
    profile_key = str(getattr(config, "rgb_color_profile", "purple")).strip().lower()
    if profile_key not in RGB_PRESETS:
        profile_key = "purple"
    preset = RGB_PRESETS[profile_key]
    tolerance = int(preset["tol_max"])
    return profile_key, tuple(preset["rgb"]), tolerance


def _create_rgb_mask(roi_bgr, target_rgb, tolerance):
    if roi_bgr is None or roi_bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    if len(roi_bgr.shape) == 2:
        roi_bgr = cv2.cvtColor(roi_bgr, cv2.COLOR_GRAY2BGR)
    elif roi_bgr.shape[2] == 4:
        roi_bgr = cv2.cvtColor(roi_bgr, cv2.COLOR_BGRA2BGR)
    elif roi_bgr.shape[2] > 3:
        roi_bgr = roi_bgr[:, :, :3]
    roi_rgb = roi_bgr[:, :, ::-1].astype(np.int16)
    target = np.array(target_rgb, dtype=np.int16)
    diff = np.abs(roi_rgb - target)
    return (np.all(diff <= int(tolerance), axis=2).astype(np.uint8) * 255)


def _execute_single_click(controller, hold_min, hold_max, state_dict):
    with state_dict["burst_lock"]:
        state_dict["burst_state"] = "bursting"

    button_pressed = False
    try:
        hold_ms = random.uniform(float(hold_min), float(hold_max))
        def _fire_single_click():
            nonlocal button_pressed
            try:
                controller.press()
                button_pressed = True
                time.sleep(max(0.0, hold_ms) / 1000.0)
            except Exception as exc:
                log_print(f"[RGB Trigger press error] {exc}")
            finally:
                if button_pressed:
                    try:
                        controller.release()
                        button_pressed = False
                    except Exception as exc:
                        log_print(f"[RGB Trigger release error] {exc}")

        run_with_auto_strafe(_fire_single_click)
    except Exception as exc:
        log_print(f"[RGB Trigger click sequence error] {exc}")
    finally:
        try:
            if button_pressed:
                controller.release()
        except Exception:
            pass
        with state_dict["burst_lock"]:
            state_dict["burst_state"] = None
            state_dict["burst_thread"] = None


def process_rgb_triggerbot(frame, img, controller, state_dict, close_debug_windows):
    if not getattr(config, "enabletb", False):
        with state_dict["burst_lock"]:
            state_dict["burst_state"] = None
            state_dict["activation_toggle_state"] = False
            state_dict["activation_last_pressed"] = False
            state_dict["enter_range_time"] = None
            state_dict["random_delay"] = None
            state_dict["confirm_count"] = 0
            state_dict["deactivation_release_sent"] = False
            reset_strafe_runtime_state(state_dict)
        close_debug_windows()
        return "DISABLED"

    selected_tb_btn = getattr(config, "selected_tb_btn", None)
    selected_2_tb = getattr(config, "selected_2_tb", None)
    activation_active, _, activation_error = _resolve_activation_mode(
        state_dict, selected_tb_btn, selected_2_tb
    )
    if activation_error is not None:
        with state_dict["burst_lock"]:
            state_dict["burst_state"] = None
            state_dict["activation_toggle_state"] = False
            state_dict["activation_last_pressed"] = False
            state_dict["enter_range_time"] = None
            state_dict["random_delay"] = None
            state_dict["confirm_count"] = 0
            state_dict["deactivation_release_sent"] = False
            reset_strafe_runtime_state(state_dict)
        close_debug_windows()
        return activation_error

    if not activation_active:
        reset_strafe_runtime_state(state_dict)
        should_release = False
        with state_dict["burst_lock"]:
            if state_dict.get("burst_state") != "bursting":
                state_dict["enter_range_time"] = None
                state_dict["random_delay"] = None
                state_dict["burst_state"] = None
                state_dict["deactivation_release_sent"] = False
            else:
                if not bool(state_dict.get("deactivation_release_sent", False)):
                    state_dict["deactivation_release_sent"] = True
                    should_release = True
            state_dict["confirm_count"] = 0
        if should_release:
            try:
                controller.release()
            except Exception:
                pass
        mode = str(getattr(config, "trigger_activation_type", "hold_enable")).strip().lower()
        close_debug_windows()
        if mode == "toggle":
            return "TOGGLE_OFF"
        if mode == "hold_disable":
            return "BUTTON_HELD_DISABLED"
        return "BUTTON_NOT_PRESSED"
    with state_dict["burst_lock"]:
        state_dict["deactivation_release_sent"] = False
        if state_dict.get("burst_state") == "bursting":
            return "RGB_FIRING"

    manual_wait_allowed, manual_wait_status = apply_manual_wait_gate(state_dict)
    if not manual_wait_allowed:
        _reset_wait_state(state_dict)
        close_debug_windows()
        return manual_wait_status or "STRAFE_WAIT"

    if cv2 is None:
        return "ERROR: OpenCV unavailable"

    try:
        cx0, cy0 = int(frame.xres // 2), int(frame.yres // 2)
        tb_fov = float(getattr(config, "tbfovsize", 0))
        roi_size = max(1, int(tb_fov)) if tb_fov > 0 else 8
        x1, y1 = max(cx0 - roi_size, 0), max(cy0 - roi_size, 0)
        x2, y2 = min(cx0 + roi_size, img.shape[1]), min(cy0 + roi_size, img.shape[0])
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            close_debug_windows()
            return "INVALID_ROI"

        profile_key, target_rgb, tolerance = _resolve_rgb_profile()
        mask = _create_rgb_mask(roi, target_rgb, tolerance)
        pixel_count = int(cv2.countNonZero(mask))
        detected = pixel_count > 0

        show_windows = bool(getattr(config, "show_opencv_windows", True))
        show_roi = bool(getattr(config, "show_opencv_roi", True))
        show_mask = bool(getattr(config, "show_opencv_triggerbot_mask", True))
        shown_any = False
        if show_windows and show_roi:
            cv2.imshow("ROI", roi)
            shown_any = True
        else:
            try:
                cv2.destroyWindow("ROI")
            except Exception:
                pass
        if show_windows and show_mask:
            cv2.imshow("Mask", mask)
            shown_any = True
        else:
            try:
                cv2.destroyWindow("Mask")
            except Exception:
                pass
        if shown_any:
            cv2.waitKey(1)

        now = time.time()
        if not detected:
            _reset_wait_state(state_dict)
            return "NO_TARGET"

        with state_dict["burst_lock"]:
            current_state = state_dict.get("burst_state")
            enter_time = state_dict.get("enter_range_time")
            last_trigger = state_dict.get("last_trigger_time", 0.0)
            random_delay = state_dict.get("random_delay")
            current_cooldown = float(state_dict.get("current_cooldown", 0.0))

        cooldown_min = float(getattr(config, "rgb_tbcooldown_min", 0.0))
        cooldown_max = float(getattr(config, "rgb_tbcooldown_max", 0.0))
        if cooldown_max > 0 and current_cooldown > 0:
            if (now - float(last_trigger)) < current_cooldown:
                remaining = current_cooldown - (now - float(last_trigger))
                return f"COOLDOWN ({remaining:.2f}s)"

        if current_state == "bursting":
            return "RGB_FIRING"

        delay_min = float(getattr(config, "rgb_tbdelay_min", 0.08))
        delay_max = float(getattr(config, "rgb_tbdelay_max", 0.15))
        if enter_time is None:
            random_delay = random.uniform(delay_min, delay_max)
            with state_dict["burst_lock"]:
                state_dict["enter_range_time"] = now
                state_dict["random_delay"] = random_delay
                state_dict["burst_state"] = "waiting"
            enter_time = now
        elif random_delay is None:
            random_delay = random.uniform(delay_min, delay_max)
            with state_dict["burst_lock"]:
                state_dict["random_delay"] = random_delay

        elapsed = now - enter_time
        if random_delay > 0 and elapsed < random_delay:
            return f"WAITING ({elapsed:.3f}s/{random_delay:.3f}s)"

        hold_min = float(getattr(config, "rgb_tbhold_min", 40))
        hold_max = float(getattr(config, "rgb_tbhold_max", 60))
        with state_dict["burst_lock"]:
            if state_dict.get("burst_thread") is not None and state_dict["burst_thread"].is_alive():
                return "RGB_IN_PROGRESS"

            click_thread = threading.Thread(
                target=_execute_single_click,
                args=(controller, hold_min, hold_max, state_dict),
                daemon=True,
            )
            state_dict["burst_thread"] = click_thread
            state_dict["burst_state"] = "bursting"
            state_dict["last_trigger_time"] = now
            state_dict["enter_range_time"] = None
            state_dict["random_delay"] = None
            state_dict["confirm_count"] = 0
            if cooldown_max > 0:
                state_dict["current_cooldown"] = random.uniform(cooldown_min, cooldown_max)
            else:
                state_dict["current_cooldown"] = 0.0

        click_thread.start()
        return f"RGB_TRIGGERED ({profile_key}, tol={tolerance})"
    except Exception as exc:
        log_print("[RGB Trigger error]", exc)
        return f"ERROR: {str(exc)}"
