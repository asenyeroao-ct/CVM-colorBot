# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .types cimport *
from .common cimport *
from .ndi_structs cimport *

cdef extern from "Processing.NDI.Recv.h" nogil:

    # // Structures and type definitions required by NDI finding.
    # // The reference to an instance of the receiver.
    cdef struct NDIlib_recv_instance_type
    ctypedef NDIlib_recv_instance_type* NDIlib_recv_instance_t

    enum NDIlib_recv_bandwidth_e:
        NDIlib_recv_bandwidth_metadata_only
        NDIlib_recv_bandwidth_audio_only
        NDIlib_recv_bandwidth_lowest
        NDIlib_recv_bandwidth_highest

        # // Make sure this is a 32-bit enumeration.
        # NDIlib_recv_bandwidth_max = 0x7fffffff

    enum NDIlib_recv_color_format_e:
        # // When there is no alpha channel, this mode delivers BGRX.
        # // When there is an alpha channel, this mode delivers BGRA.
        NDIlib_recv_color_format_BGRX_BGRA

        # // When there is no alpha channel, this mode delivers UYVY.
        # // When there is an alpha channel, this mode delivers BGRA.
        NDIlib_recv_color_format_UYVY_BGRA

        # // When there is no alpha channel, this mode delivers BGRX.
        # // When there is an alpha channel, this mode delivers RGBA.
        NDIlib_recv_color_format_RGBX_RGBA

        # // When there is no alpha channel, this mode delivers UYVY.
        # // When there is an alpha channel, this mode delivers RGBA.
        NDIlib_recv_color_format_UYVY_RGBA

        # // This format will try to decode the video using the fastest available color format for the incoming
        # // video signal. This format follows the following guidelines, although different platforms might
        # // vary slightly based on their capabilities and specific performance profiles. In general if you want
        # // the best performance this mode should be used.
        # //
        # // When using this format, you should consider than allow_video_fields is true, and individual fields
        # // will always be delivered.
        # //
        # // For most video sources on most platforms, this will follow the following conventions.
        # //      No alpha channel : UYVY
        # //      Alpha channel    : UYVA
        NDIlib_recv_color_format_fastest

        # // This format will try to provide the video in the format that is the closest to native for the incoming
        # // codec yielding the highest quality. Specifically, this allows for receiving on 16bpp color from many
        # // sources.
        # //
        # // When using this format, you should consider than allow_video_fields is true, and individual fields
        # // will always be delivered.
        # //
        # // For most video sources on most platforms, this will follow the following conventions
        # //      No alpha channel : P216, or UYVY
        # //      Alpha channel    : PA16 or UYVA
        NDIlib_recv_color_format_best

        # // Legacy definitions for backwards compatibility.
        NDIlib_recv_color_format_e_BGRX_BGRA
        NDIlib_recv_color_format_e_UYVY_BGRA
        NDIlib_recv_color_format_e_RGBX_RGBA
        NDIlib_recv_color_format_e_UYVY_RGBA

    # // The creation structure that is used when you are creating a receiver.
    cdef struct NDIlib_recv_create_v3_t:
        # // The source that you wish to connect to.
        NDIlib_source_t source_to_connect_to

        # // Your preference of color space. See above.
        NDIlib_recv_color_format_e color_format

        # // The bandwidth setting that you wish to use for this video source. Bandwidth controlled by changing
        # // both the compression level and the resolution of the source. A good use for low bandwidth is working
        # // on WIFI connections.
        NDIlib_recv_bandwidth_e bandwidth

        # // When this flag is FALSE, all video that you receive will be progressive. For sources that provide
        # // fields, this is de-interlaced on the receiving side (because we cannot change what the up-stream
        # //  source was actually rendering. This is provided as a convenience to down-stream sources that do not
        # // wish to understand fielded video. There is almost no  performance impact of using this function.
        bint allow_video_fields

        # // The name of the NDI receiver to create. This is a NULL terminated UTF8 string and should be the name
        # // of receive channel that you have. This is in many ways symmetric with the name of senders, so this
        # // might be "Channel 1" on your system. If this is NULL then it will use the filename of your application
        # // indexed with the number of the instance number of this receiver.
        const char* p_ndi_recv_name

        # NDIlib_recv_create_v3_t()

    # // This allows you determine the current performance levels of the receiving to be able to detect whether
    # // frames have been dropped.
    cdef struct NDIlib_recv_performance_t:
        # // The number of video frames.
        int64_t video_frames

        # // The number of audio frames.
        int64_t audio_frames

        # // The number of metadata frames.
        int64_t metadata_frames

    # // Get the current queue depths.
    cdef struct NDIlib_recv_queue_t:
        # // The number of video frames.
        int video_frames

        # // The number of audio frames.
        int audio_frames

        # // The number of metadata frames.
        int metadata_frames

    # // Create a new receiver instance. This will return NULL if it fails. If you create this with the default
    # // settings (NULL) then it will automatically determine a receiver name.
    # PROCESSINGNDILIB_API
    NDIlib_recv_instance_t NDIlib_recv_create_v3(const NDIlib_recv_create_v3_t* p_create_settings)

    # // This will destroy an existing receiver instance.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_destroy(NDIlib_recv_instance_t p_instance)

    # // This function allows you to change the connection to another video source, you can also disconnect it by
    # // specifying a NULL here. This allows you to preserve a receiver without needing to.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_connect(NDIlib_recv_instance_t p_instance, const NDIlib_source_t* p_src)

    # // This will allow you to receive video, audio and metadata frames. Any of the buffers can be NULL, in which
    # // case data of that type will not be captured in this call. This call can be called simultaneously on
    # // separate threads, so it is entirely possible to receive audio, video, metadata all on separate threads.
    # // This function will return NDIlib_frame_type_none if no data is received within the specified timeout and
    # // NDIlib_frame_type_error if the connection is lost. Buffers captured with this must be freed with the
    # // appropriate free function below.
    # PROCESSINGNDILIB_API
    NDIlib_frame_type_e NDIlib_recv_capture_v2(
        NDIlib_recv_instance_t p_instance,
        NDIlib_video_frame_v2_t* p_video_data,
        NDIlib_audio_frame_v2_t* p_audio_data,
        NDIlib_metadata_frame_t* p_metadata,
        uint32_t timeout_in_ms
    )

    # // This will allow you to receive video, audio and metadata frames. Any of the buffers can be NULL, in which
    # // case data of that type will not be captured in this call. This call can be called simultaneously on
    # // separate threads, so it is entirely possible to receive audio, video, metadata all on separate threads.
    # // This function will return NDIlib_frame_type_none if no data is received within the specified timeout and
    # // NDIlib_frame_type_error if the connection is lost. Buffers captured with this must be freed with the
    # // appropriate free function below.
    # PROCESSINGNDILIB_API
    NDIlib_frame_type_e NDIlib_recv_capture_v3(
        NDIlib_recv_instance_t p_instance,
        NDIlib_video_frame_v2_t* p_video_data,
        NDIlib_audio_frame_v3_t* p_audio_data,
        NDIlib_metadata_frame_t* p_metadata,
        uint32_t timeout_in_ms
    )

    # // Free the buffers returned by capture for video.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_free_video_v2(NDIlib_recv_instance_t p_instance, const NDIlib_video_frame_v2_t* p_video_data)

    # // Free the buffers returned by capture for audio.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_free_audio_v2(NDIlib_recv_instance_t p_instance, const NDIlib_audio_frame_v2_t* p_audio_data)

    # // Free the buffers returned by capture for audio.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_free_audio_v3(NDIlib_recv_instance_t p_instance, const NDIlib_audio_frame_v3_t* p_audio_data)

    # // Free the buffers returned by capture for metadata.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_free_metadata(NDIlib_recv_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // This will free a string that was allocated and returned by NDIlib_recv (for instance the
    # // NDIlib_recv_get_web_control) function.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_free_string(NDIlib_recv_instance_t p_instance, const char* p_string)

    # // This function will send a meta message to the source that we are connected too. This returns FALSE if we
    # // are not currently connected to anything.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_send_metadata(NDIlib_recv_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // Set the up-stream tally notifications. This returns FALSE if we are not currently connected to anything.
    # // That said, the moment that we do connect to something it will automatically be sent the tally state.
    # PROCESSINGNDILIB_API
    bint NDIlib_recv_set_tally(NDIlib_recv_instance_t p_instance, const NDIlib_tally_t* p_tally)

    # // Get the current performance structures. This can be used to determine if you have been calling
    # // NDIlib_recv_capture fast enough, or if your processing of data is not keeping up with real-time. The total
    # // structure will give you the total frame counts received, the dropped structure will tell you how many
    # // frames have been dropped. Either of these could be NULL.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_get_performance(NDIlib_recv_instance_t p_instance, NDIlib_recv_performance_t* p_total, NDIlib_recv_performance_t* p_dropped)

    # // This will allow you to determine the current queue depth for all of the frame sources at any time.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_get_queue(NDIlib_recv_instance_t p_instance, NDIlib_recv_queue_t* p_total)

    # // Connection based metadata is data that is sent automatically each time a new connection is received. You
    # // queue all of these up and they are sent on each connection. To reset them you need to clear them all and
    # // set them up again.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_clear_connection_metadata(NDIlib_recv_instance_t p_instance)

    # // Add a connection metadata string to the list of what is sent on each new connection. If someone is already
    # // connected then this string will be sent to them immediately.
    # PROCESSINGNDILIB_API
    void NDIlib_recv_add_connection_metadata(NDIlib_recv_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata)

    # // Is this receiver currently connected to a source on the other end, or has the source not yet been found or
    # // is no longer online. This will normally return 0 or 1.
    # PROCESSINGNDILIB_API
    int NDIlib_recv_get_no_connections(NDIlib_recv_instance_t p_instance)

    # // Get the URL that might be used for configuration of this input. Note that it might take a second or two
    # // after the connection for this value to be set. This function will return NULL if there is no web control
    # // user interface. You should call NDIlib_recv_free_string to free the string that is returned by this
    # // function. The returned value will be a fully formed URL, for instance "http://10.28.1.192/configuration/".
    # // To avoid the need to poll this function, you can know when the value of this function might have changed
    # // when the NDILib_recv_capture* call would return NDIlib_frame_type_status_change.
    # PROCESSINGNDILIB_API
    const char* NDIlib_recv_get_web_control(NDIlib_recv_instance_t p_instance)


cpdef enum RecvBandwidth:
    metadata_only = NDIlib_recv_bandwidth_metadata_only
    audio_only = NDIlib_recv_bandwidth_audio_only
    lowest = NDIlib_recv_bandwidth_lowest
    highest = NDIlib_recv_bandwidth_highest

cdef inline NDIlib_recv_bandwidth_e recv_bandwidth_cast(RecvBandwidth value) noexcept nogil:
    return <NDIlib_recv_bandwidth_e>value
cdef inline RecvBandwidth recv_bandwidth_uncast(NDIlib_recv_bandwidth_e value) noexcept nogil:
    return <RecvBandwidth>value


cpdef enum RecvColorFormat:
    BGRX_BGRA = NDIlib_recv_color_format_BGRX_BGRA
    UYVY_BGRA = NDIlib_recv_color_format_UYVY_BGRA
    RGBX_RGBA = NDIlib_recv_color_format_RGBX_RGBA
    UYVY_RGBA = NDIlib_recv_color_format_UYVY_RGBA
    fastest = NDIlib_recv_color_format_fastest
    best = NDIlib_recv_color_format_best

cdef inline NDIlib_recv_color_format_e recv_format_cast(RecvColorFormat value) noexcept nogil:
    return <NDIlib_recv_color_format_e>value
cdef inline RecvColorFormat recv_format_uncast(NDIlib_recv_color_format_e value) noexcept nogil:
    return <RecvColorFormat>value

cdef NDIlib_recv_create_v3_t* recv_t_create() except NULL nogil
cdef NDIlib_recv_create_v3_t* recv_t_create_default() except NULL nogil
cdef int recv_t_copy(NDIlib_recv_create_v3_t* src, NDIlib_recv_create_v3_t* dest) except -1 nogil
cdef void recv_t_destroy(NDIlib_recv_create_v3_t* p) noexcept nogil
