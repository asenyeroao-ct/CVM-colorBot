import tkinter as tk

import customtkinter as ctk

from src.utils.config import config


def _set_float(app, key, value):
    setattr(config, key, float(value))


def _set_int(app, key, value):
    setattr(config, key, int(float(value)))


def _rgb_profile_display(value):
    mapping = {
        "red": "Red",
        "yellow": "Yellow",
        "purple": "Purple",
        "custom": "Custom",
    }
    return mapping.get(str(value).strip().lower(), "Purple")


def _build_normal_params(app, parent):
    app._add_slider_in_frame(parent, "X-Speed", "magnet_normal_x_speed", 0.1, 2000,
                             float(getattr(config, "magnet_normal_x_speed", 3.0)),
                             lambda v: _set_float(app, "magnet_normal_x_speed", v), is_float=True)
    app._add_slider_in_frame(parent, "Y-Speed", "magnet_normal_y_speed", 0.1, 2000,
                             float(getattr(config, "magnet_normal_y_speed", 3.0)),
                             lambda v: _set_float(app, "magnet_normal_y_speed", v), is_float=True)
    app._add_slider_in_frame(parent, "Smooth", "magnet_normalsmooth", 0.1, 1000,
                             float(getattr(config, "magnet_normalsmooth", 30.0)),
                             lambda v: _set_float(app, "magnet_normalsmooth", v), is_float=True)
    app._add_slider_in_frame(parent, "Smooth FOV", "magnet_normalsmoothfov", 1, 1000,
                             float(getattr(config, "magnet_normalsmoothfov", 30.0)),
                             lambda v: _set_float(app, "magnet_normalsmoothfov", v), is_float=True)


def _build_flick_params(app, parent):
    app._add_slider_in_frame(parent, "Strength X", "magnet_flick_strength_x", 0.01, 5.0,
                             float(getattr(config, "magnet_flick_strength_x", 5.0)),
                             lambda v: _set_float(app, "magnet_flick_strength_x", v), is_float=True)
    app._add_slider_in_frame(parent, "Strength Y", "magnet_flick_strength_y", 0.01, 5.0,
                             float(getattr(config, "magnet_flick_strength_y", 5.0)),
                             lambda v: _set_float(app, "magnet_flick_strength_y", v), is_float=True)


def _build_silent_params(app, parent):
    app._add_slider_in_frame(parent, "Distance", "magnet_silent_distance", 0.1, 10.0,
                             float(getattr(config, "magnet_silent_distance", 1.0)),
                             lambda v: _set_float(app, "magnet_silent_distance", v), is_float=True)
    app._add_slider_in_frame(parent, "Silent Delay (ms)", "magnet_silent_delay", 0, 2000,
                             float(getattr(config, "magnet_silent_delay", 100.0)),
                             lambda v: _set_float(app, "magnet_silent_delay", v), is_float=True)
    app._add_slider_in_frame(parent, "Move Delay (ms)", "magnet_silent_move_delay", 0, 2000,
                             float(getattr(config, "magnet_silent_move_delay", 500.0)),
                             lambda v: _set_float(app, "magnet_silent_move_delay", v), is_float=True)
    app._add_slider_in_frame(parent, "Return Delay (ms)", "magnet_silent_return_delay", 0, 2000,
                             float(getattr(config, "magnet_silent_return_delay", 500.0)),
                             lambda v: _set_float(app, "magnet_silent_return_delay", v), is_float=True)


def _build_ncaf_params(app, parent):
    app._add_slider_in_frame(parent, "Snap Radius", "magnet_ncaf_snap_radius", 1, 500,
                             float(getattr(config, "magnet_ncaf_snap_radius", 150.0)),
                             lambda v: _set_float(app, "magnet_ncaf_snap_radius", v), is_float=True)
    app._add_slider_in_frame(parent, "Near Radius", "magnet_ncaf_near_radius", 1, 500,
                             float(getattr(config, "magnet_ncaf_near_radius", 50.0)),
                             lambda v: _set_float(app, "magnet_ncaf_near_radius", v), is_float=True)
    app._add_slider_in_frame(parent, "Alpha", "magnet_ncaf_alpha", 0.01, 10.0,
                             float(getattr(config, "magnet_ncaf_alpha", 1.5)),
                             lambda v: _set_float(app, "magnet_ncaf_alpha", v), is_float=True)
    app._add_slider_in_frame(parent, "Snap Boost", "magnet_ncaf_snap_boost", 0.01, 10.0,
                             float(getattr(config, "magnet_ncaf_snap_boost", 0.3)),
                             lambda v: _set_float(app, "magnet_ncaf_snap_boost", v), is_float=True)
    app._add_slider_in_frame(parent, "Max Step", "magnet_ncaf_max_step", 0.1, 500,
                             float(getattr(config, "magnet_ncaf_max_step", 50.0)),
                             lambda v: _set_float(app, "magnet_ncaf_max_step", v), is_float=True)
    app._add_slider_in_frame(parent, "Min Speed Mult", "magnet_ncaf_min_speed_multiplier", 0.001, 10.0,
                             float(getattr(config, "magnet_ncaf_min_speed_multiplier", 0.01)),
                             lambda v: _set_float(app, "magnet_ncaf_min_speed_multiplier", v), is_float=True)
    app._add_slider_in_frame(parent, "Max Speed Mult", "magnet_ncaf_max_speed_multiplier", 0.01, 50.0,
                             float(getattr(config, "magnet_ncaf_max_speed_multiplier", 10.0)),
                             lambda v: _set_float(app, "magnet_ncaf_max_speed_multiplier", v), is_float=True)
    app._add_slider_in_frame(parent, "Prediction Interval", "magnet_ncaf_prediction_interval", 0.0, 1.0,
                             float(getattr(config, "magnet_ncaf_prediction_interval", 0.016)),
                             lambda v: _set_float(app, "magnet_ncaf_prediction_interval", v), is_float=True)


def _build_windmouse_params(app, parent):
    app._add_slider_in_frame(parent, "Gravity", "magnet_wm_gravity", 0.1, 30.0,
                             float(getattr(config, "magnet_wm_gravity", 9.0)),
                             lambda v: _set_float(app, "magnet_wm_gravity", v), is_float=True)
    app._add_slider_in_frame(parent, "Wind", "magnet_wm_wind", 0.1, 30.0,
                             float(getattr(config, "magnet_wm_wind", 3.0)),
                             lambda v: _set_float(app, "magnet_wm_wind", v), is_float=True)
    app._add_slider_in_frame(parent, "Max Step", "magnet_wm_max_step", 0.1, 100.0,
                             float(getattr(config, "magnet_wm_max_step", 15.0)),
                             lambda v: _set_float(app, "magnet_wm_max_step", v), is_float=True)
    app._add_slider_in_frame(parent, "Min Step", "magnet_wm_min_step", 0.1, 50.0,
                             float(getattr(config, "magnet_wm_min_step", 2.0)),
                             lambda v: _set_float(app, "magnet_wm_min_step", v), is_float=True)
    app._add_slider_in_frame(parent, "Min Delay", "magnet_wm_min_delay", 0.0, 0.1,
                             float(getattr(config, "magnet_wm_min_delay", 0.001)),
                             lambda v: _set_float(app, "magnet_wm_min_delay", v), is_float=True)
    app._add_slider_in_frame(parent, "Max Delay", "magnet_wm_max_delay", 0.0, 0.1,
                             float(getattr(config, "magnet_wm_max_delay", 0.003)),
                             lambda v: _set_float(app, "magnet_wm_max_delay", v), is_float=True)
    app._add_slider_in_frame(parent, "Distance Threshold", "magnet_wm_distance_threshold", 1, 1000,
                             float(getattr(config, "magnet_wm_distance_threshold", 50.0)),
                             lambda v: _set_float(app, "magnet_wm_distance_threshold", v), is_float=True)


def _build_bezier_params(app, parent):
    app._add_slider_in_frame(parent, "Segments", "magnet_bezier_segments", 1, 30,
                             float(getattr(config, "magnet_bezier_segments", 8)),
                             lambda v: _set_int(app, "magnet_bezier_segments", v))
    app._add_slider_in_frame(parent, "Control X", "magnet_bezier_ctrl_x", 0.0, 100.0,
                             float(getattr(config, "magnet_bezier_ctrl_x", 16.0)),
                             lambda v: _set_float(app, "magnet_bezier_ctrl_x", v), is_float=True)
    app._add_slider_in_frame(parent, "Control Y", "magnet_bezier_ctrl_y", 0.0, 100.0,
                             float(getattr(config, "magnet_bezier_ctrl_y", 16.0)),
                             lambda v: _set_float(app, "magnet_bezier_ctrl_y", v), is_float=True)
    app._add_slider_in_frame(parent, "Speed", "magnet_bezier_speed", 0.01, 10.0,
                             float(getattr(config, "magnet_bezier_speed", 1.0)),
                             lambda v: _set_float(app, "magnet_bezier_speed", v), is_float=True)
    app._add_slider_in_frame(parent, "Delay", "magnet_bezier_delay", 0.0, 0.1,
                             float(getattr(config, "magnet_bezier_delay", 0.002)),
                             lambda v: _set_float(app, "magnet_bezier_delay", v), is_float=True)


def _build_pid_params(app, parent):
    app._add_slider_in_frame(parent, "Kp Min", "magnet_pid_kp_min", 0.0, 20.0,
                             float(getattr(config, "magnet_pid_kp_min", 3.7)),
                             lambda v: _set_float(app, "magnet_pid_kp_min", v), is_float=True)
    app._add_slider_in_frame(parent, "Kp Max", "magnet_pid_kp_max", 0.0, 20.0,
                             float(getattr(config, "magnet_pid_kp_max", 3.7)),
                             lambda v: _set_float(app, "magnet_pid_kp_max", v), is_float=True)
    app._add_slider_in_frame(parent, "Ki", "magnet_pid_ki", 0.0, 100.0,
                             float(getattr(config, "magnet_pid_ki", 24.0)),
                             lambda v: _set_float(app, "magnet_pid_ki", v), is_float=True)
    app._add_slider_in_frame(parent, "Kd", "magnet_pid_kd", 0.0, 10.0,
                             float(getattr(config, "magnet_pid_kd", 0.11)),
                             lambda v: _set_float(app, "magnet_pid_kd", v), is_float=True)
    app._add_slider_in_frame(parent, "Max Output", "magnet_pid_max_output", 0.1, 500.0,
                             float(getattr(config, "magnet_pid_max_output", 50.0)),
                             lambda v: _set_float(app, "magnet_pid_max_output", v), is_float=True)
    app._add_slider_in_frame(parent, "X-Speed", "magnet_pid_x_speed", 0.01, 10.0,
                             float(getattr(config, "magnet_pid_x_speed", 1.0)),
                             lambda v: _set_float(app, "magnet_pid_x_speed", v), is_float=True)
    app._add_slider_in_frame(parent, "Y-Speed", "magnet_pid_y_speed", 0.01, 10.0,
                             float(getattr(config, "magnet_pid_y_speed", 1.0)),
                             lambda v: _set_float(app, "magnet_pid_y_speed", v), is_float=True)


def _build_mode_params(app, parent, mode_value):
    builders = {
        "Normal": _build_normal_params,
        "Flick": _build_flick_params,
        "Silent": _build_silent_params,
        "NCAF": _build_ncaf_params,
        "WindMouse": _build_windmouse_params,
        "Bezier": _build_bezier_params,
        "PID": _build_pid_params,
    }
    builders.get(mode_value, _build_normal_params)(app, parent)


def build_magnet_trigger_tab(app):
    """Build Magnet Trigger tab UI in isolated module.

    Magnet Trigger UI 鎷嗗埌鐙珛 folder/module锛岄伩鍏?ui.py 榪囧ぇ.
    """
    app._active_tab_name = "Magnet Trigger"
    app._clear_content()
    app._add_title("Magnet Trigger")

    sec_core = app._create_collapsible_section(app.content_frame, "Core", initially_open=True)

    app.var_enable_magnet_trigger = tk.BooleanVar(value=getattr(config, "enable_magnet_trigger", False))
    app._add_switch_in_frame(
        sec_core,
        "Enable Magnet Trigger",
        app.var_enable_magnet_trigger,
        app._on_enable_magnet_trigger_changed,
    )
    app._checkbox_vars["enable_magnet_trigger"] = app.var_enable_magnet_trigger

    current_key = app._ads_binding_to_display(getattr(config, "magnet_keybind", 0))
    app.magnet_key_bind_button = app._add_bind_capture_row_in_frame(
        sec_core,
        "Keybind",
        current_key,
        app._start_magnet_key_capture,
    )

    activation_types = ["Hold to Enable", "Hold to Disable", "Toggle"]
    app.magnet_activation_type_option = app._add_option_row_in_frame(
        sec_core,
        "Activation",
        activation_types,
        app._on_magnet_activation_type_selected,
    )
    app._option_widgets["magnet_activation_type"] = app.magnet_activation_type_option
    app.magnet_activation_type_option.set({
        "hold_enable": "Hold to Enable",
        "hold_disable": "Hold to Disable",
        "toggle": "Toggle",
    }.get(str(getattr(config, "magnet_activation_type", "hold_enable")).strip().lower(), "Hold to Enable"))

    aim_modes = ["Normal", "Flick", "Silent", "NCAF", "WindMouse", "Bezier", "PID Controller (Risk)"]
    app.magnet_mode_option = app._add_option_row_in_frame(
        sec_core,
        "Aim Mode",
        aim_modes,
        app._on_magnet_mode_selected,
    )
    app._option_widgets["magnet_mode"] = app.magnet_mode_option
    current_mode = app._aim_mode_value_to_display(getattr(config, "magnet_mode", "Normal"))
    app.magnet_mode_option.set(current_mode)

    trigger_modes = ["Classic Trigger", "RGB Trigger"]
    app.magnet_trigger_type_option = app._add_option_row_in_frame(
        sec_core,
        "Trigger Mode",
        trigger_modes,
        app._on_magnet_trigger_type_selected,
    )
    app._option_widgets["magnet_trigger_type"] = app.magnet_trigger_type_option
    current_trigger_type = str(getattr(config, "magnet_trigger_type", "current")).strip().lower()
    app.magnet_trigger_type_option.set("RGB Trigger" if current_trigger_type == "rgb" else "Classic Trigger")

    sec_target = app._create_collapsible_section(app.content_frame, "Targeting", initially_open=True)
    app._add_slider_in_frame(sec_target, "Magnet FOV", "magnet_fov", 1, 500,
                             float(getattr(config, "magnet_fov", 45.0)),
                             app._on_magnet_fov_changed, is_float=True)
    app._add_slider_in_frame(sec_target, "Fire Radius", "magnet_fire_radius", 1, 50,
                             float(getattr(config, "magnet_fire_radius", 6.0)),
                             app._on_magnet_fire_radius_changed, is_float=True)
    app._add_slider_in_frame(sec_target, "Confirm Frames", "magnet_trigger_confirm_frames", 1, 10,
                             float(getattr(config, "magnet_trigger_confirm_frames", 1)),
                             lambda v: _set_int(app, "magnet_trigger_confirm_frames", v))

    sec_mode = app._create_collapsible_section(app.content_frame, "Aim Parameters", initially_open=True)
    current_mode_value = app._aim_mode_display_to_value(getattr(config, "magnet_mode", "Normal"))
    _build_mode_params(app, sec_mode, current_mode_value)

    sec_trigger = app._create_collapsible_section(app.content_frame, "Trigger Parameters", initially_open=True)
    current_trigger_type = str(getattr(config, "magnet_trigger_type", "current")).strip().lower()
    if current_trigger_type == "rgb":
        app._add_slider_in_frame(sec_trigger, "ROI Size", "magnet_trigger_roi_size", 1, 200,
                                 float(getattr(config, "magnet_trigger_roi_size", 8)),
                                 lambda v: _set_int(app, "magnet_trigger_roi_size", v))
        app.magnet_rgb_color_profile_option = app._add_option_row_in_frame(
            sec_trigger,
            "RGB Profile",
            ["Red", "Yellow", "Purple", "Custom"],
            app._on_magnet_rgb_color_profile_selected,
        )
        app._option_widgets["magnet_rgb_color_profile"] = app.magnet_rgb_color_profile_option
        app.magnet_rgb_color_profile_option.set(
            _rgb_profile_display(getattr(config, "magnet_rgb_color_profile", "purple"))
        )
        app._add_slider_in_frame(sec_trigger, "Tolerance", "magnet_rgb_tolerance", 0, 255,
                                 float(getattr(config, "magnet_rgb_tolerance", 30)),
                                 lambda v: _set_int(app, "magnet_rgb_tolerance", v))
        if str(getattr(config, "magnet_rgb_color_profile", "purple")).strip().lower() == "custom":
            custom_rgb = app._create_collapsible_section(sec_trigger, "Custom RGB", initially_open=True)
            app._add_slider_in_frame(custom_rgb, "R", "magnet_rgb_custom_r", 0, 255,
                                     float(getattr(config, "magnet_rgb_custom_r", 161)),
                                     lambda v: _set_int(app, "magnet_rgb_custom_r", v))
            app._add_slider_in_frame(custom_rgb, "G", "magnet_rgb_custom_g", 0, 255,
                                     float(getattr(config, "magnet_rgb_custom_g", 69)),
                                     lambda v: _set_int(app, "magnet_rgb_custom_g", v))
            app._add_slider_in_frame(custom_rgb, "B", "magnet_rgb_custom_b", 0, 255,
                                     float(getattr(config, "magnet_rgb_custom_b", 163)),
                                     lambda v: _set_int(app, "magnet_rgb_custom_b", v))
        app._add_slider_in_frame(sec_trigger, "Delay Min (s)", "magnet_rgb_trigger_delay_min", 0.0, 5.0,
                                 float(getattr(config, "magnet_rgb_trigger_delay_min", 0.08)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_delay_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Delay Max (s)", "magnet_rgb_trigger_delay_max", 0.0, 5.0,
                                 float(getattr(config, "magnet_rgb_trigger_delay_max", 0.15)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_delay_max", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Hold Min (ms)", "magnet_rgb_trigger_hold_min", 0, 1000,
                                 float(getattr(config, "magnet_rgb_trigger_hold_min", 40.0)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_hold_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Hold Max (ms)", "magnet_rgb_trigger_hold_max", 0, 1000,
                                 float(getattr(config, "magnet_rgb_trigger_hold_max", 60.0)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_hold_max", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Cooldown Min (s)", "magnet_rgb_trigger_cooldown_min", 0.0, 5.0,
                                 float(getattr(config, "magnet_rgb_trigger_cooldown_min", 0.0)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_cooldown_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Cooldown Max (s)", "magnet_rgb_trigger_cooldown_max", 0.0, 5.0,
                                 float(getattr(config, "magnet_rgb_trigger_cooldown_max", 0.0)),
                                 lambda v: _set_float(app, "magnet_rgb_trigger_cooldown_max", v), is_float=True)
    else:
        app._add_slider_in_frame(sec_trigger, "Delay Min (s)", "magnet_trigger_delay_min", 0.0, 5.0,
                                 float(getattr(config, "magnet_trigger_delay_min", 0.08)),
                                 lambda v: _set_float(app, "magnet_trigger_delay_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Delay Max (s)", "magnet_trigger_delay_max", 0.0, 5.0,
                                 float(getattr(config, "magnet_trigger_delay_max", 0.15)),
                                 lambda v: _set_float(app, "magnet_trigger_delay_max", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Hold Min (ms)", "magnet_trigger_hold_min", 0, 1000,
                                 float(getattr(config, "magnet_trigger_hold_min", 40.0)),
                                 lambda v: _set_float(app, "magnet_trigger_hold_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Hold Max (ms)", "magnet_trigger_hold_max", 0, 1000,
                                 float(getattr(config, "magnet_trigger_hold_max", 60.0)),
                                 lambda v: _set_float(app, "magnet_trigger_hold_max", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Cooldown Min (s)", "magnet_trigger_cooldown_min", 0.0, 5.0,
                                 float(getattr(config, "magnet_trigger_cooldown_min", 0.0)),
                                 lambda v: _set_float(app, "magnet_trigger_cooldown_min", v), is_float=True)
        app._add_slider_in_frame(sec_trigger, "Cooldown Max (s)", "magnet_trigger_cooldown_max", 0.0, 5.0,
                                 float(getattr(config, "magnet_trigger_cooldown_max", 0.0)),
                                 lambda v: _set_float(app, "magnet_trigger_cooldown_max", v), is_float=True)

    sec_notes = app._create_collapsible_section(app.content_frame, "Notes", initially_open=False)
    ctk.CTkLabel(
        sec_notes,
        text=(
            "Magnet Trigger uses its own aim mode, trigger mode, and timing values. "
            "Clicking runs in a dedicated worker thread with a lock, so only one press-delay-release sequence can run at a time."
        ),
        font=("Roboto", 10),
        text_color=getattr(app, "COLOR_TEXT_DIM", None) or "#7A7A7A",
        justify="left",
        wraplength=720,
        anchor="w",
    ).pack(fill="x", pady=(4, 2))
