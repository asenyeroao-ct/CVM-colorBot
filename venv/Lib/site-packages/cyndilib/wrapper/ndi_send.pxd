# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .ndi_structs cimport *

cdef extern from "Processing.NDI.Send.h" nogil:

    # // Structures and type definitions required by NDI sending.
    # // The reference to an instance of the sender.
    cdef struct NDIlib_send_instance_type
    ctypedef NDIlib_send_instance_type* NDIlib_send_instance_t

    # // The creation structure that is used when you are creating a sender.
    cdef struct NDIlib_send_create_t:
        # // The name of the NDI source to create. This is a NULL terminated UTF8 string.
        const char* p_ndi_name

        # // What groups should this source be part of. NULL means default.
        const char* p_groups

        # // Do you want audio and video to "clock" themselves. When they are clocked then by adding video frames,
        # // they will be rate limited to match the current frame rate that you are submitting at. The same is true
        # // for audio. In general if you are submitting video and audio off a single thread then you should only
        # // clock one of them (video is probably the better of the two to clock off). If you are submitting audio
        # // and video of separate threads then having both clocked can be useful.
        bint clock_video
        bint clock_audio

    # // Create a new sender instance. This will return NULL if it fails. If you specify leave p_create_settings
    # // null then the sender will be created with default settings.
    # PROCESSINGNDILIB_API
    NDIlib_send_instance_t NDIlib_send_create(const NDIlib_send_create_t* p_create_settings)

    # // This will destroy an existing finder instance.
    # PROCESSINGNDILIB_API
    void NDIlib_send_destroy(NDIlib_send_instance_t p_instance)

    # // This will add a video frame.
    # PROCESSINGNDILIB_API
    void NDIlib_send_send_video_v2(NDIlib_send_instance_t p_instance, const NDIlib_video_frame_v2_t* p_video_data)

    # // This will add a video frame and will return immediately, having scheduled the frame to be displayed. All
    # // processing and sending of the video will occur asynchronously. The memory accessed by NDIlib_video_frame_t
    # // cannot be freed or re-used by the caller until a synchronizing event has occurred. In general the API is
    # // better able to take advantage of asynchronous processing than you might be able to by simple having a
    # // separate thread to submit frames.
    # //
    # // This call is particularly beneficial when processing BGRA video since it allows any color conversion,
    # // compression and network sending to all be done on separate threads from your main rendering thread.
    # //
    # // Synchronizing events are :
    # // - a call to NDIlib_send_send_video
    # // - a call to NDIlib_send_send_video_async with another frame to be sent
    # // - a call to NDIlib_send_send_video with p_video_data=NULL
    # // - a call to NDIlib_send_destroy
    # PROCESSINGNDILIB_API
    void NDIlib_send_send_video_async_v2(NDIlib_send_instance_t p_instance, const NDIlib_video_frame_v2_t* p_video_data)

    # // This will add an audio frame.
    # PROCESSINGNDILIB_API
    void NDIlib_send_send_audio_v2(NDIlib_send_instance_t p_instance, const NDIlib_audio_frame_v2_t* p_audio_data)

    # // This will add an audio frame.
    # PROCESSINGNDILIB_API
    void NDIlib_send_send_audio_v3(NDIlib_send_instance_t p_instance, const NDIlib_audio_frame_v3_t* p_audio_data)

    # // This will add a metadata frame.
    # PROCESSINGNDILIB_API
    void NDIlib_send_send_metadata(NDIlib_send_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // This allows you to receive metadata from the other end of the connection.
    # PROCESSINGNDILIB_API
    NDIlib_frame_type_e NDIlib_send_capture(
        NDIlib_send_instance_t p_instance,
        NDIlib_metadata_frame_t* p_metadata,
        uint32_t timeout_in_ms
    )

    # // Free the buffers returned by capture for metadata.
    # PROCESSINGNDILIB_API
    void NDIlib_send_free_metadata(NDIlib_send_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // Determine the current tally sate. If you specify a timeout then it will wait until it has changed,
    # // otherwise it will simply poll it and return the current tally immediately. The return value is whether
    # // anything has actually change (true) or whether it timed out (false)
    # PROCESSINGNDILIB_API
    bint NDIlib_send_get_tally(NDIlib_send_instance_t p_instance, NDIlib_tally_t* p_tally, uint32_t timeout_in_ms)

    # // Get the current number of receivers connected to this source. This can be used to avoid even rendering
    # // when nothing is connected to the video source. which can significantly improve the efficiency if you want
    # // to make a lot of sources available on the network. If you specify a timeout that is not 0 then it will
    # // wait until there are connections for this amount of time.
    # PROCESSINGNDILIB_API
    int NDIlib_send_get_no_connections(NDIlib_send_instance_t p_instance, uint32_t timeout_in_ms)

    # // Connection based metadata is data that is sent automatically each time a new connection is received. You
    # // queue all of these up and they are sent on each connection. To reset them you need to clear them all and
    # // set them up again.
    # PROCESSINGNDILIB_API
    void NDIlib_send_clear_connection_metadata(NDIlib_send_instance_t p_instance)

    # // Add a connection metadata string to the list of what is sent on each new connection. If someone is already
    # // connected then this string will be sent to them immediately.
    # PROCESSINGNDILIB_API
    void NDIlib_send_add_connection_metadata(NDIlib_send_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // This will assign a new fail-over source for this video source. What this means is that if this video
    # // source was to fail any receivers would automatically switch over to use this source, unless this source
    # // then came back online. You can specify NULL to clear the source.
    # PROCESSINGNDILIB_API
    void NDIlib_send_set_failover(NDIlib_send_instance_t p_instance, const NDIlib_source_t* p_failover_source)

    # // Retrieve the source information for the given sender instance.  This pointer is valid until NDIlib_send_destroy is called.
    # PROCESSINGNDILIB_API
    const NDIlib_source_t* NDIlib_send_get_source_name(NDIlib_send_instance_t p_instance)


cdef NDIlib_send_create_t* send_t_create(
    const char* ndi_name,
    const char* groups
) except NULL nogil

cdef void send_t_initialize(
    NDIlib_send_create_t* p,
    const char* ndi_name,
    const char* groups,
) noexcept nogil

cdef void send_t_destroy(NDIlib_send_create_t* p) noexcept nogil
