# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .ndi_structs cimport *
from .ndi_recv cimport *

cdef extern from "Processing.NDI.FrameSync.h" nogil:

    # // The type instance for a frame-synchronizer.
    cdef struct NDIlib_framesync_instance_type
    ctypedef NDIlib_framesync_instance_type* NDIlib_framesync_instance_t

    # // Create a frame synchronizer instance that can be used to get frames from a receiver. Once this receiver
    # // has been bound to a frame-sync then you should use it in order to receive video frames. You can continue
    # // to use the underlying receiver for other operations (tally, PTZ, etc...). Note that it remains your
    # // responsibility to destroy the receiver even when a frame-sync is using it. You should always destroy the
    # // receiver after the frame-sync has been destroyed.
    # //
    # PROCESSINGNDILIB_API
    NDIlib_framesync_instance_t NDIlib_framesync_create(NDIlib_recv_instance_t p_receiver)

    # // Destroy a frame-sync implementation.
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_destroy(NDIlib_framesync_instance_t p_instance)

    # // This function will pull audio samples from the frame-sync queue. This function will always return data
    # // immediately, inserting silence if no current audio data is present. You should call this at the rate that
    # // you want audio and it will automatically adapt the incoming audio signal to match the rate at which you
    # // are calling by using dynamic audio sampling. Note that you have no obligation that your requested sample
    # // rate, no channels and no samples match the incoming signal and all combinations of conversions
    # // are supported.
    # //
    # // If you wish to know what the current incoming audio format is, then you can make a call with the
    # // parameters set to zero and it will then return the associated settings. For instance a call as follows:
    # //
    # //     NDIlib_framesync_capture_audio(p_instance, p_audio_data, 0, 0, 0);
    # //
    # // will return in p_audio_data the current received audio format if there is one or sample_rate and
    # // no_channels equal to zero if there is not one. At any time you can specify sample_rate and no_channels as
    # // zero and it will return the current received audio format.
    # //
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_capture_audio(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_audio_frame_v2_t* p_audio_data,
        int sample_rate, int no_channels, int no_samples
    )
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_capture_audio_v2(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_audio_frame_v3_t* p_audio_data,
        int sample_rate, int no_channels, int no_samples
    )

    # // Free audio returned by NDIlib_framesync_capture_audio.
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_free_audio(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_audio_frame_v2_t* p_audio_data
    )
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_free_audio_v2(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_audio_frame_v3_t* p_audio_data
    )

    # // This function will tell you the approximate current depth of the audio queue to give you an indication
    # // of the number of audio samples you can request. Note that if you should treat the results of this function
    # // with some care because in reality the frame-sync API is meant to dynamically resample audio to match the
    # // rate that you are calling it. If you have an inaccurate clock then this function can be useful.
    # // for instance :
    # //
    # //  while(true)
    # //  {   int no_samples = NDIlib_framesync_audio_queue_depth(p_instance);
    # //      NDIlib_framesync_capture_audio( ... );
    # //      play_audio( ... )
    # //      NDIlib_framesync_free_audio( ... )
    # //      inaccurate_sleep( 33ms );
    # //  }
    # //
    # // Obviously because audio is being received in real-time there is no guarantee after the call that the
    # // number is correct since new samples might have been captured in that time. On synchronous use of this
    # // function however this will be the minimum number of samples in the queue at any later time until
    # // NDIlib_framesync_capture_audio is called.
    # //
    # PROCESSINGNDILIB_API
    int NDIlib_framesync_audio_queue_depth(NDIlib_framesync_instance_t p_instance)

    # // This function will pull video samples from the frame-sync queue. This function will always immediately
    # // return a video sample by using time-base correction. You can specify the desired field type which is then
    # // used to return the best possible frame. Note that field based frame-synchronization means that the
    # // frame-synchronizer attempts to match the fielded input phase with the frame requests so that you have the
    # // most correct possible field ordering on output. Note that the same frame can be returned multiple times.
    # //
    # // If no video frame has ever been received, this will return NDIlib_video_frame_v2_t as an empty (all zero)
    # // structure. The reason for this is that it allows you to determine that there has not yet been any video
    # // and act accordingly. For instance you might want to display a constant frame output at a particular video
    # // format, or black.
    # //
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_capture_video(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_video_frame_v2_t* p_video_data,
        NDIlib_frame_format_type_e field_type
    )

    # // Free audio returned by NDIlib_framesync_capture_video.
    # //
    # PROCESSINGNDILIB_API
    void NDIlib_framesync_free_video(
        NDIlib_framesync_instance_t p_instance,
        NDIlib_video_frame_v2_t* p_video_data
    )
