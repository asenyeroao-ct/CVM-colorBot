# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .wrapper cimport *

from .locks cimport RLock, Condition, Event
from .finder cimport Source
from .video_frame cimport VideoRecvFrame
from .audio_frame cimport AudioRecvFrame
from .metadata_frame cimport MetadataRecvFrame
from .framesync cimport FrameSync
from .callback cimport Callback


cpdef enum ReceiveFrameType:
    nothing = 0
    recv_video = 1
    recv_audio = 2
    recv_metadata = 4
    recv_status_change = 8
    recv_error = 16
    recv_buffers_full = 32
    recv_all = recv_video | recv_audio | recv_metadata

cdef struct RecvPerformance_t:
    int64_t frames_total
    int64_t frames_dropped
    double dropped_percent

cdef NDIlib_frame_type_e recv_frame_type_cast(ReceiveFrameType ft) noexcept nogil
cdef ReceiveFrameType recv_frame_type_uncast(NDIlib_frame_type_e ft) noexcept nogil

cdef class RecvCreate:
    cdef public str source_name
    cdef public RecvColorFormat color_format
    cdef public RecvBandwidth bandwidth
    cdef public bint allow_video_fields
    cdef public str recv_name

    cdef NDIlib_recv_create_v3_t* build_create_p(self) except *


cdef class Receiver:
    cdef RecvCreate settings
    cdef readonly FrameSync frame_sync
    cdef readonly VideoRecvFrame video_frame
    cdef readonly AudioRecvFrame audio_frame
    cdef readonly MetadataRecvFrame metadata_frame
    cdef readonly str source_name
    cdef readonly bint has_video_frame, has_audio_frame, has_metadata_frame
    cdef readonly RLock connection_lock
    cdef readonly Condition connection_notify
    cdef readonly Source source
    cdef readonly NDIlib_tally_t source_tally
    cdef NDIlib_source_t* source_ptr
    cdef NDIlib_recv_performance_t perf_total_s
    cdef NDIlib_recv_performance_t perf_dropped_s
    cdef readonly RecvPerformance_t video_stats
    cdef readonly RecvPerformance_t audio_stats
    cdef readonly RecvPerformance_t metadata_stats
    cdef bint _connected, _probably_connected
    cdef size_t _num_empty_recv
    cdef NDIlib_recv_instance_t ptr
    cdef NDIlib_recv_create_v3_t recv_create
    cdef readonly PTZ ptz

    cpdef set_video_frame(self, VideoRecvFrame vf)
    cpdef set_audio_frame(self, AudioRecvFrame af)
    cpdef set_metadata_frame(self, MetadataRecvFrame mf)
    cpdef set_source(self, Source src)
    cpdef connect_to(self, Source src)
    cdef int _connect_to(self, NDIlib_source_t* src) except -1
    cdef int _disconnect(self) except -1 nogil
    cdef int _reconnect(self) except -1 nogil
    cdef bint _is_connected(self) except -1 nogil
    cdef int _set_connected(self, bint value) except -1 nogil
    cdef int _get_num_connections(self) except? -1 nogil
    cdef bint _wait_for_connect(self, float timeout) except -1 nogil
    cdef int _update_performance(self) except -1 nogil
    cpdef set_source_tally_program(self, bint value)
    cpdef set_source_tally_preview(self, bint value)
    cdef int _set_source_tally(self, bint program, bint preview) except -1 nogil
    cdef int _send_source_tally(self) except -1 nogil
    cdef int _handle_metadata_frame(self) except -1
    cpdef ReceiveFrameType receive(
        self, ReceiveFrameType recv_type, uint32_t timeout_ms
    )
    cdef ReceiveFrameType _receive(
        self, ReceiveFrameType recv_type, uint32_t timeout_ms
    ) except *

    cdef ReceiveFrameType _do_receive(
        self,
        NDIlib_video_frame_v2_t* video_frame,
        NDIlib_audio_frame_v3_t* audio_frame,
        NDIlib_metadata_frame_t* metadata_frame,
        uint32_t timeout_ms
    ) noexcept nogil

    cdef void free_video(self, NDIlib_video_frame_v2_t* p) noexcept nogil
    cdef void free_audio(self, NDIlib_audio_frame_v3_t* p) noexcept nogil
    cdef void free_metadata(self, NDIlib_metadata_frame_t* p) noexcept nogil

cdef class PTZ:
    cdef Receiver receiver

    cdef NDIlib_recv_instance_t _get_ptr(self)
