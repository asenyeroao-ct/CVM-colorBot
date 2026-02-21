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
from .framesync_helper cimport FrameSyncVideoInstance_s


cdef class VideoFrame:
    cdef readonly bytes _metadata_bytes
    cdef NDIlib_video_frame_v2_t* ptr
    cdef FourCCPackInfo pack_info
    cdef frame_rate_t frame_rate

    cpdef str get_format_string(self)
    cdef (int, int) _get_resolution(self) noexcept nogil
    cdef int _set_resolution(self, int xres, int yres) except -1 nogil
    cdef int _get_xres(self) noexcept nogil
    cdef int _set_xres(self, int value) except -1 nogil
    cdef int _get_yres(self) noexcept nogil
    cdef int _set_yres(self, int value) except -1 nogil
    cdef FourCC _get_fourcc(self) noexcept nogil
    cdef int _set_fourcc(self, FourCC value) except -1 nogil
    cdef uint8_t _get_bits_per_pixel(self) noexcept nogil
    cdef uint8_t _get_padded_bits_per_pixel(self) noexcept nogil
    cdef frame_rate_t* _get_frame_rate(self) noexcept nogil
    cdef int _set_frame_rate(self, frame_rate_ft fr) noexcept nogil
    cdef float _get_aspect(self) noexcept nogil
    cdef void _set_aspect(self, float value) noexcept nogil
    cdef FrameFormat _get_frame_format(self) noexcept nogil
    cdef void _set_frame_format(self, FrameFormat fmt) noexcept nogil
    cdef int64_t _get_timecode(self) noexcept nogil
    cdef int64_t _set_timecode(self, int64_t value) noexcept nogil
    cdef int _get_line_stride(self) noexcept nogil
    cdef void _set_line_stride(self, int value) noexcept nogil
    cdef size_t _get_buffer_size(self) noexcept nogil
    cdef uint8_t* _get_data(self) noexcept nogil
    cdef void _set_data(self, uint8_t* data) noexcept nogil
    cdef const char* _get_metadata(self) noexcept nogil
    cdef bytes _get_metadata_bytes(self)
    cdef int _set_metadata(self, bytes metadata) except -1
    cdef int64_t _get_timestamp(self) noexcept nogil
    cdef void _set_timestamp(self, int64_t value) noexcept nogil
    cdef size_t _get_data_size(self) noexcept nogil
    cpdef size_t get_data_size(self)
    cdef int _recalc_pack_info(self, bint use_ptr_stride=*) except -1 nogil

cdef class VideoRecvFrame(VideoFrame):
    cdef readonly size_t max_buffers
    cdef cpp_deque[size_t] read_indices
    cdef cpp_set[size_t] read_indices_set
    cdef video_bfr_p video_bfrs
    cdef video_bfr_p read_bfr
    cdef video_bfr_p write_bfr
    cdef readonly RLock read_lock
    cdef readonly RLock write_lock
    cdef readonly Condition read_ready
    cdef readonly Condition write_ready
    cdef cnp.ndarray all_frame_data
    cdef readonly cnp.ndarray current_frame_data
    cdef size_t[1] bfr_shape
    cdef size_t[1] bfr_strides
    cdef size_t view_count

    cdef int _check_read_array_size(self) except -1
    cdef int _fill_read_data(self, bint advance) except -1 nogil
    cdef size_t _get_next_write_index(self) except? -1 nogil
    cdef bint can_receive(self) except -1 nogil
    cdef int _check_write_array_size(self) except -1
    cdef int _prepare_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1
    cdef int _process_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1


cdef class VideoFrameSync(VideoFrame):
    cdef FrameSyncVideoInstance_s framesync_instance
    cdef readonly size_t[1] shape
    cdef readonly size_t[1] strides
    cdef size_t view_count

    cdef void _free_framesync_pointers(self) noexcept nogil
    cdef void _free_framesync_data(self) noexcept nogil
    cdef int _process_incoming(self) except -1 nogil


cdef class VideoSendFrame(VideoFrame):
    cdef VideoSendFrame_status_s send_status
    cdef VideoSendFrame_item_s* buffer_write_item

    cdef int _destroy(self) except -1
    cdef bint _write_available(self) noexcept nogil
    cdef VideoSendFrame_item_s* _prepare_buffer_write(self) except NULL nogil
    cdef void _set_buffer_write_complete(self, VideoSendFrame_item_s* item) noexcept nogil
    cdef VideoSendFrame_item_s* _prepare_memview_write(self) except NULL nogil
    cdef void _write_data_to_memview(
        self,
        cnp.uint8_t[:] data,
        cnp.uint8_t[:] view,
        VideoSendFrame_item_s* item,
    ) noexcept nogil
    cdef VideoSendFrame_item_s* _get_next_write_frame(self) except NULL nogil
    cdef bint _send_frame_available(self) noexcept nogil
    cdef VideoSendFrame_item_s* _get_send_frame(self) except NULL nogil
    cdef VideoSendFrame_item_s* _get_send_frame_noexcept(self) noexcept nogil
    cdef void _on_sender_write(self, VideoSendFrame_item_s* s_ptr) noexcept nogil
    cdef int _set_sender_status(self, bint attached) except -1 nogil
    cdef int _rebuild_array(self) except -1 nogil
