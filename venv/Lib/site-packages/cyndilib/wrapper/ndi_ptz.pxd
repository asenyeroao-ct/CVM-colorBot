# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .ndi_structs cimport *
from .ndi_send cimport *
from .ndi_recv cimport *

cdef extern from "Processing.NDI.Recv.ex.h" nogil:
    # // Has this receiver got PTZ control. Note that it might take a second or two after the connection for this
    # // value to be set. To avoid the need to poll this function, you can know when the value of this function
    # // might have changed when the NDILib_recv_capture* call would return NDIlib_frame_type_status_change.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_is_supported(NDIlib_recv_instance_t p_instance);

    # // PTZ Controls.
    # // Zoom to an absolute value.
    # // zoom_value = 0.0 (zoomed in) ... 1.0 (zoomed out)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_zoom(NDIlib_recv_instance_t p_instance, const float zoom_value);

    # // Zoom at a particular speed.
    # // zoom_speed = -1.0 (zoom outwards) ... +1.0 (zoom inwards)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_zoom_speed(NDIlib_recv_instance_t p_instance, const float zoom_speed);

    # // Set the pan and tilt to an absolute value.
    # // pan_value  = -1.0 (left) ... 0.0 (centered) ... +1.0 (right)
    # // tilt_value = -1.0 (bottom) ... 0.0 (centered) ... +1.0 (top)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_pan_tilt(NDIlib_recv_instance_t p_instance, const float pan_value, const float tilt_value);

    # // Set the pan and tilt direction and speed.
    # // pan_speed = -1.0 (moving right) ... 0.0 (stopped) ... +1.0 (moving left)
    # // tilt_speed = -1.0 (down) ... 0.0 (stopped) ... +1.0 (moving up)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_pan_tilt_speed(NDIlib_recv_instance_t p_instance, const float pan_speed, const float tilt_speed);

    # // Store the current position, focus, etc... as a preset.
    # // preset_no = 0 ... 99
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_store_preset(NDIlib_recv_instance_t p_instance, const int preset_no);

    # // Recall a preset, including position, focus, etc...
    # // preset_no = 0 ... 99
    # // speed = 0.0(as slow as possible) ... 1.0(as fast as possible) The speed at which to move to the new preset.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_recall_preset(NDIlib_recv_instance_t p_instance, const int preset_no, const float speed);

    # // Put the camera in auto-focus.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_auto_focus(NDIlib_recv_instance_t p_instance);

    # // Focus to an absolute value.
    # // focus_value = 0.0 (focused to infinity) ... 1.0 (focused as close as possible)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_focus(NDIlib_recv_instance_t p_instance, const float focus_value);

    # // Focus at a particular speed.
    # // focus_speed = -1.0 (focus outwards) ... +1.0 (focus inwards)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_focus_speed(NDIlib_recv_instance_t p_instance, const float focus_speed);

    # // Put the camera in auto white balance mode.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_white_balance_auto(NDIlib_recv_instance_t p_instance);

    # // Put the camera in indoor white balance.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_white_balance_indoor(NDIlib_recv_instance_t p_instance);

    # // Put the camera in indoor white balance.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_white_balance_outdoor(NDIlib_recv_instance_t p_instance);

    # // Use the current brightness to automatically set the current white balance.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_white_balance_oneshot(NDIlib_recv_instance_t p_instance);

    # // Set the manual camera white balance using the R, B values.
    # // red = 0.0(not red) ... 1.0(very red)
    # // blue = 0.0(not blue) ... 1.0(very blue)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_white_balance_manual(NDIlib_recv_instance_t p_instance, const float red, const float blue);

    # // Put the camera in auto-exposure mode.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_exposure_auto(NDIlib_recv_instance_t p_instance);

    # // Manually set the camera exposure iris.
    # // exposure_level = 0.0(dark) ... 1.0(light)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_exposure_manual(NDIlib_recv_instance_t p_instance, const float exposure_level);

    # // Manually set the camera exposure parameters.
    # // iris = 0.0(dark) ... 1.0(light)
    # // gain = 0.0(dark) ... 1.0(light)
    # // shutter_speed = 0.0(slow) ... 1.0(fast)
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_ptz_exposure_manual_v2(
        NDIlib_recv_instance_t p_instance,
    const float iris, const float gain, const float shutter_speed
    );
