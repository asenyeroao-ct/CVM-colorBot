# cython: language_level=3
# distutils: language = c++

from cython cimport view
from libc.stdint cimport *
from libcpp.deque cimport deque as cpp_deque
from libcpp.set cimport set as cpp_set
cimport numpy as cnp

from .wrapper cimport *
from .buffertypes cimport *
from .locks cimport RLock, Condition
from .send_frame_status cimport *
from .audio_reference cimport AudioReference, AudioReferenceConverter
from .framesync_helper cimport FrameSyncAudioInstance_s


cdef class AudioFrame:
    cdef NDIlib_audio_frame_v3_t* ptr
    cdef readonly AudioReferenceConverter reference_converter

    cdef int _get_sample_rate(self) noexcept nogil
    cdef void _set_sample_rate(self, int value) noexcept nogil
    cdef int _get_num_channels(self) noexcept nogil
    cdef int _set_num_channels(self, int value) except -1 nogil
    cdef int _get_num_samples(self) noexcept nogil
    cdef int _set_num_samples(self, int value) except -1 nogil
    cdef AudioReference _get_reference_level(self) noexcept nogil
    cdef int _set_reference_level(self, AudioReference reference) except -1 nogil
    cdef int64_t _get_timecode(self) noexcept nogil
    cdef int64_t _set_timecode(self, int64_t value) noexcept nogil
    cdef int _get_channel_stride(self) noexcept nogil
    cdef int _set_channel_stride(self, int value) except -1 nogil
    cdef uint8_t* _get_data(self) noexcept nogil
    cdef void _set_data(self, uint8_t* data) noexcept nogil
    cdef const char* _get_metadata(self) noexcept nogil
    cdef bytes _get_metadata_bytes(self)
    cdef int64_t _get_timestamp(self) noexcept nogil
    cdef void _set_timestamp(self, int64_t value) noexcept nogil


cdef class AudioRecvFrame(AudioFrame):
    cdef readonly size_t max_buffers
    cdef cpp_deque[size_t] read_indices
    cdef cpp_set[size_t] read_indices_set
    cdef cpp_deque[int64_t] frame_timestamps
    cdef audio_bfr_p audio_bfrs
    cdef audio_bfr_p read_bfr
    cdef audio_bfr_p write_bfr
    cdef readonly RLock read_lock
    cdef readonly RLock write_lock
    cdef readonly Condition read_ready
    cdef readonly Condition write_ready
    cdef cnp.ndarray all_frame_data
    cdef readonly cnp.ndarray current_frame_data
    cdef readonly uint32_t current_timecode
    cdef readonly uint32_t current_timestamp
    cdef size_t[2] bfr_shape
    cdef size_t[2] bfr_strides
    cdef size_t[2] empty_bfr_shape
    cdef readonly size_t view_count

    cpdef size_t get_buffer_depth(self)
    cpdef (size_t, size_t) get_read_shape(self)
    cpdef size_t get_read_length(self)
    cpdef get_all_read_data(self)
    cdef (size_t, size_t) _fill_all_read_data(
        self,
        cnp.float32_t[:,:,:] all_frame_data,
        cnp.float32_t[:,:] result,
        cnp.int64_t[:] timestamps,
        size_t bfr_len,
    ) noexcept nogil

    cpdef get_read_data(self)
    cdef bint _check_read_array_size(self) except -1
    cdef int64_t _fill_read_data(
        self,
        cnp.float32_t[:,:,:] all_frame_data,
        cnp.float32_t[:,:] dest,
        size_t bfr_idx,
        bint advance
    ) except? -1 nogil
    cdef size_t _get_next_write_index(self) except? -1 nogil
    cdef bint can_receive(self) except -1 nogil
    cdef int _check_write_array_size(self) except -1
    cdef int _prepare_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1
    cdef int _process_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1


cdef class AudioFrameSync(AudioFrame):
    cdef FrameSyncAudioInstance_s framesync_instance
    cdef readonly size_t[2] shape
    cdef readonly size_t[2] strides
    cdef size_t view_count

    cdef void _free_framesync_pointers(self) noexcept nogil
    cdef void _free_framesync_data(self) noexcept nogil
    cdef int _process_incoming(self) except -1 nogil


cdef class AudioSendFrame(AudioFrame):
    cdef AudioSendFrame_status_s send_status
    cdef AudioSendFrame_item_s* buffer_write_item
    cdef readonly size_t max_num_samples

    cpdef set_max_num_samples(self, size_t n)
    cdef int _destroy(self) except -1
    cdef bint _write_available(self) noexcept nogil
    cdef void _set_shape_from_memview(
        self,
        AudioSendFrame_item_s* item,
        cnp.float32_t[:,:] data,
    ) noexcept nogil
    cdef AudioSendFrame_item_s* _prepare_buffer_write(self) except NULL nogil
    cdef void _set_buffer_write_complete(self, AudioSendFrame_item_s* item) noexcept nogil
    cdef AudioSendFrame_item_s* _prepare_memview_write(self) except NULL nogil
    cdef void _write_data_to_memview(
        self,
        cnp.float32_t[:,:] data,
        cnp.float32_t[:,:] view,
        AudioSendFrame_item_s* item,
    ) noexcept nogil
    cdef AudioSendFrame_item_s* _get_next_write_frame(self) except NULL nogil
    cdef bint _send_frame_available(self) noexcept nogil
    cdef AudioSendFrame_item_s* _get_send_frame(self) except NULL nogil
    cdef AudioSendFrame_item_s* _get_send_frame_noexcept(self) noexcept nogil
    cdef void _on_sender_write(self, AudioSendFrame_item_s* s_ptr) noexcept nogil
    cdef int _set_sender_status(self, bint attached) except -1 nogil
    cdef int _rebuild_array(self) except -1 nogil
