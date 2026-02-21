cimport cython
from cpython.ref cimport PyObject
from libc.string cimport memcpy

from fractions import Fraction
import numpy as np

from .wrapper.ndi_structs cimport fourcc_pack_info_init


__all__ = ('VideoFrame', 'VideoRecvFrame', 'VideoFrameSync', 'VideoSendFrame')


cdef class VideoFrame:
    """Base class for video frames
    """
    def __cinit__(self, *args, **kwargs):
        self.ptr = video_frame_create_default()
        if self.ptr is NULL:
            raise MemoryError()
        fourcc_pack_info_init(&(self.pack_info))

    def __init__(self, *args, **kwargs):
        self.frame_rate.numerator = self.ptr.frame_rate_N
        self.frame_rate.denominator = self.ptr.frame_rate_D

    def __dealloc__(self):
        cdef NDIlib_video_frame_v2_t* p = self.ptr
        self.ptr = NULL
        if p is not NULL:
            video_frame_destroy(p)

    cpdef str get_format_string(self):
        """Get the video format as a string based off of resolution, frame rate
        and field format ("1080i59.94", etc)
        """
        cdef int yres = self._get_yres()
        if yres <= 0:
            return 'unknown'
        cdef FrameFormat fmt = self._get_frame_format()
        cdef str fieldStr = 'p' if fmt == FrameFormat.progressive else 'i'
        cdef frame_rate_t* fr = self._get_frame_rate()
        cdef double fr_dbl = fr.numerator / <double>fr.denominator
        cdef str fr_str
        if fr_dbl % 1 == 0:
            fr_str = f'{fr_dbl:.2f}'
        else:
            fr_str = f'{fr_dbl:.0f}'
        return f'{yres}{fieldStr}{fr_str}'

    def get_resolution(self):
        """Get the video resolution as a tuple of ``(width, height)``
        """
        return self._get_resolution()
    def set_resolution(self, int xres, int yres):
        """Set the video resolution
        """
        self._set_resolution(xres, yres)
    cdef (int, int) _get_resolution(self) noexcept nogil:
        return (self.ptr.xres, self.ptr.yres)
    cdef int _set_resolution(self, int xres, int yres) except -1 nogil:
        self.ptr.xres = xres
        self.ptr.yres = yres
        self._recalc_pack_info()
        if self.ptr.yres > 0:
            with cython.cdivision(True):
                self._set_aspect(self.ptr.xres / <double>(self.ptr.yres))
        return 0

    @property
    def xres(self):
        """X resolution (width)
        """
        return self._get_xres()

    @property
    def yres(self):
        """Y resolution (height)
        """
        return self._get_yres()

    cdef int _get_xres(self) noexcept nogil:
        return self.ptr.xres
    cdef int _set_xres(self, int value) except -1 nogil:
        self.ptr.xres = value
        self._recalc_pack_info()
        if self.ptr.yres > 0:
            with cython.cdivision(True):
                self._set_aspect(self.ptr.xres / <double>(self.ptr.yres))
        return 0

    cdef int _get_yres(self) noexcept nogil:
        return self.ptr.yres
    cdef int _set_yres(self, int value) except -1 nogil:
        self.ptr.yres = value
        self._recalc_pack_info()
        if self.ptr.yres > 0:
            with cython.cdivision(True):
                self._set_aspect(self.ptr.xres / <double>(self.ptr.yres))
        return 0

    @property
    def fourcc(self):
        """The current :class:`~.wrapper.ndi_structs.FourCC` format type
        """
        return self._get_fourcc()

    def get_fourcc(self):
        """Get the :class:`~.wrapper.ndi_structs.FourCC` format type
        """
        return self._get_fourcc()
    def set_fourcc(self, FourCC value):
        """Set the :class:`~.wrapper.ndi_structs.FourCC` format type
        """
        self._set_fourcc(value)
    cdef FourCC _get_fourcc(self) noexcept nogil:
        return fourcc_type_uncast(self.ptr.FourCC)
    cdef int _set_fourcc(self, FourCC value) except -1 nogil:
        self.ptr.FourCC = fourcc_type_cast(value)
        self._recalc_pack_info()
        return 0

    @property
    def bits_per_pixel(self):
        """Bits per pixel for the current :attr:`fourcc`

        .. versionadded:: 0.0.5

        """
        return self._get_bits_per_pixel()

    @property
    def padded_bits_per_pixel(self):
        """Padded bits per pixel for the current :attr:`fourcc`

        .. versionadded:: 0.0.5

        """
        return self._get_padded_bits_per_pixel()

    @property
    def padded_bytes_per_line(self):
        """Padded bytes per line for the current :attr:`fourcc`

        .. versionadded:: 0.0.6

        """
        return self.pack_info.padded_bytes_per_line

    cdef uint8_t _get_bits_per_pixel(self) noexcept nogil:
        return self.pack_info.bits_per_pixel

    cdef uint8_t _get_padded_bits_per_pixel(self) noexcept nogil:
        return self.pack_info.padded_bits_per_pixel

    def get_frame_rate(self) -> Fraction:
        """Get the video frame rate
        """
        return Fraction(self.ptr.frame_rate_N, self.ptr.frame_rate_D)
    def set_frame_rate(self, value: Fraction):
        """Set the video frame rate
        """
        cdef int[2] fr = [value.numerator, value.denominator]
        self._set_frame_rate(fr)

    cdef frame_rate_t* _get_frame_rate(self) noexcept nogil:
        self.frame_rate.numerator = self.ptr.frame_rate_N
        self.frame_rate.denominator = self.ptr.frame_rate_D
        return &self.frame_rate

    cdef int _set_frame_rate(self, frame_rate_ft fr) noexcept nogil:
        if frame_rate_ft is frame_rate_t:
            self.ptr.frame_rate_N = fr.numerator
            self.ptr.frame_rate_D = fr.denominator
        else:
            self.ptr.frame_rate_N = fr[0]
            self.ptr.frame_rate_D = fr[1]
        self.frame_rate.numerator = self.ptr.frame_rate_N
        self.frame_rate.denominator = self.ptr.frame_rate_D
        return 0

    cdef float _get_aspect(self) noexcept nogil:
        return self.ptr.picture_aspect_ratio
    cdef void _set_aspect(self, float value) noexcept nogil:
        self.ptr.picture_aspect_ratio = value

    cdef FrameFormat _get_frame_format(self) noexcept nogil:
        return frame_format_uncast(self.ptr.frame_format_type)
    cdef void _set_frame_format(self, FrameFormat fmt) noexcept nogil:
        self.ptr.frame_format_type = frame_format_cast(fmt)

    cdef int64_t _get_timecode(self) noexcept nogil:
        return self.ptr.timecode
    cdef int64_t _set_timecode(self, int64_t value) noexcept nogil:
        self.ptr.timecode = value

    def get_line_stride(self):
        return self._get_line_stride()

    cdef int _get_line_stride(self) noexcept nogil:
        return self.ptr.line_stride_in_bytes
    cdef void _set_line_stride(self, int value) noexcept nogil:
        self.ptr.line_stride_in_bytes = value

    def get_buffer_size(self):
        return self._get_buffer_size()

    cdef size_t _get_buffer_size(self) noexcept nogil:
        return self.pack_info.total_size

    cdef uint8_t* _get_data(self) noexcept nogil:
        return self.ptr.p_data
    cdef void _set_data(self, uint8_t* data) noexcept nogil:
        self.ptr.p_data = data

    cdef const char* _get_metadata(self) noexcept nogil:
        return self.ptr.p_metadata

    cdef bytes _get_metadata_bytes(self):
        cdef bytes result = self.ptr.p_metadata
        return result

    def set_metadata(self, bytes metadata):
        """Set the metadata for the video frame

        .. versionadded:: 0.0.6

        """
        self._set_metadata(metadata)
    cdef int _set_metadata(self, bytes metadata) except -1:
        self._metadata_bytes = metadata
        self.ptr.p_metadata = self._metadata_bytes
        return 0

    cdef int64_t _get_timestamp(self) noexcept nogil:
        return self.ptr.timestamp
    cdef void _set_timestamp(self, int64_t value) noexcept nogil:
        self.ptr.timestamp = value

    def get_timestamp_posix(self):
        """Get the current :term:`timestamp <ndi-timestamp>` converted to float
        seconds (posix)
        """
        cdef double r = ndi_time_to_posix(self.ptr.timestamp)
        return r

    def get_timecode_posix(self):
        """Get the current :term:`timecode <ndi-timecode>` converted to float
        seconds (posix)
        """
        cdef double r = ndi_time_to_posix(self.ptr.timecode)
        return r

    # cdef double _get_timestamp_posix(self) nogil:
    #     return ndi_time_to_posix(self.ptr.timestamp)

    cdef size_t _get_data_size(self) noexcept nogil:
        return self._get_buffer_size()
    cpdef size_t get_data_size(self):
        return self._get_data_size()

    cdef int _recalc_pack_info(self, bint use_ptr_stride=True) except -1 nogil:
        cdef FourCC fcc = self._get_fourcc()
        cdef bint changed = False
        cdef size_t line_stride = 0
        if use_ptr_stride:
            line_stride = self.ptr.line_stride_in_bytes
        if self.pack_info.fourcc != fcc:
            self.pack_info.fourcc = fcc
            changed = True
        if self.ptr.xres != self.pack_info.xres or self.ptr.yres != self.pack_info.yres:
            self.pack_info.xres = self.ptr.xres
            self.pack_info.yres = self.ptr.yres
            changed = True
        if self.pack_info.xres == 0 or self.pack_info.yres == 0:
            return 0
        if changed:
            calc_fourcc_pack_info(&(self.pack_info), line_stride)
            # only overwrite our line_stride_in_bytes if it was left unspecified in the NDI video frame.
            if not use_ptr_stride:
                self.ptr.line_stride_in_bytes = self.pack_info.line_strides[0]
        return 0


cdef class VideoRecvFrame(VideoFrame):
    """Video frame to be used with a :class:`.receiver.Receiver`

    Arguments:
        max_buffers (int, optional): The maximum number of items to store
            in the buffer. Defaults to ``4``

    Incoming data from the receiver is placed into temporary buffers so it can
    be read without possibly losing frames.

    The buffer items retain both the frame data and corresponding timestamps.
    They can be read using the :meth:`fill_p_data` method or using the
    :ref:`buffer protocol <frame-buffer-protocol>`.

    """
    def __cinit__(self, *args, **kwargs):
        self.video_bfrs = video_frame_bfr_create(self.video_bfrs)
        self.read_bfr = video_frame_bfr_create(self.video_bfrs)
        self.write_bfr = video_frame_bfr_create(self.read_bfr)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_buffers = kwargs.get('max_buffers', 4)
        self.read_lock = RLock()
        self.write_lock = RLock()
        self.read_ready = Condition(self.read_lock)
        self.write_ready = Condition(self.write_lock)
        self.all_frame_data = np.zeros((self.max_buffers, 0), dtype=np.uint8)
        self.current_frame_data = np.zeros(0, dtype=np.uint8)
        self.view_count = 0

    def __dealloc__(self):
        cdef video_bfr_p bfr = self.video_bfrs
        if self.video_bfrs is not NULL:
            self.video_bfrs = NULL
            self.write_bfr = NULL
            av_frame_bfr_destroy(bfr)

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        # buffer view is flattened on first axis
        cdef size_t bfr_len, size_in_bytes
        cdef bint is_empty
        cdef cnp.ndarray[cnp.uint8_t, ndim=1] frame_data
        self.read_lock._acquire(True, -1)
        try:
            bfr_len = self.read_indices.size()
            is_empty = bfr_len == 0
            if not is_empty:
                if self.view_count == 0:
                    self._check_read_array_size()
                    frame_data = self.current_frame_data
                    if frame_data.shape[0] == 0:
                        is_empty = True
                    else:
                        self._fill_read_data(advance=True)
            if is_empty:
                raise ValueError('Buffer empty')
            self.view_count += 1
        finally:
            self.read_lock._release()

        frame_data = self.current_frame_data
        self.bfr_shape[0] = frame_data.shape[0]
        self.bfr_strides[0] = frame_data.strides[0]
        size_in_bytes = frame_data.strides[0] * frame_data.shape[0]

        buffer.buf = <uint8_t *>frame_data.data
        buffer.format = 'B'
        buffer.internal = NULL
        buffer.itemsize = frame_data.strides[0]
        buffer.len = size_in_bytes
        buffer.ndim = frame_data.ndim
        buffer.obj = self
        buffer.readonly = 1
        buffer.shape = <Py_ssize_t*>self.bfr_shape
        buffer.strides = <Py_ssize_t*>self.bfr_strides
        buffer.suboffsets = NULL

    def __releasebuffer__(self, Py_buffer *buffer):
        self.read_lock._acquire(True, -1)
        self.view_count -= 1
        self.read_lock._release()

    def get_view_count(self):
        return self.view_count

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef int _check_read_array_size(self) except -1:
        cdef cnp.uint8_t[:,:] all_frame_data = self.all_frame_data
        cdef cnp.uint8_t[:] read_data = self.current_frame_data
        cdef size_t ncols = all_frame_data.shape[1]
        if read_data.shape[0] != ncols:
            self.read_lock._acquire(True, -1)
            try:
                self.current_frame_data = np.zeros(ncols, dtype=np.uint8)
            finally:
                self.read_lock._release()
        return 0

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef int _fill_read_data(self, bint advance) except -1 nogil:
        cdef cnp.uint8_t[:,:] all_frame_data = self.all_frame_data
        cdef cnp.uint8_t[:] arr = self.current_frame_data
        cdef size_t bfr_idx = self.read_indices.front()
        with nogil:
            if advance:
                self.read_indices.pop_front()
                self.read_indices_set.erase(bfr_idx)

            arr[...] = all_frame_data[bfr_idx,...]
        return 0

    def get_buffer_depth(self) -> int:
        """Get the number of buffered frames
        """
        return self.read_indices.size()

    def buffer_full(self) -> bool:
        """Returns True if the buffers are all in use
        """
        return self.read_indices.size() >= self.max_buffers

    def skip_frames(self, bint eager):
        """Discard buffered frame(s)

        If the buffers remain full and the application can't keep up,
        this can be used as a last resort.

        Arguments:
            eager (bool): If True, discard all buffered frames except one
                (the most recently received). If False, only discard one frame

        Returns the number of frames skipped
        """
        cdef size_t idx, max_remain, cur_size, num_skipped = 0
        self.read_lock._acquire(True, -1)
        try:
            cur_size = self.read_indices.size()
            if not cur_size:
                return
            if eager:
                max_remain = 1
            else:
                max_remain = cur_size - 1
            while True:
                idx = self.read_indices.front()
                self.read_indices.pop_front()
                self.read_indices_set.erase(idx)
                num_skipped += 1
                if not eager:
                    break
                if self.read_indices.size() <= max_remain:
                    break
        finally:
            self.read_lock._release()
        return num_skipped

    @cython.boundscheck(False)
    @cython.wraparound(False)
    def fill_p_data(self, cnp.uint8_t[:] dest):
        """Copy the first buffered frame data into the given
        destination array (or memoryview).

        The array should be typed as unsigned 8-bit integers sized to match
        that of :meth:`~VideoFrame.get_buffer_size`
        """
        cdef size_t bfr_len, vc, bfr_idx
        cdef cnp.uint8_t[:,:] all_frame_data = self.all_frame_data
        cdef cnp.uint8_t[:] read_view = self.current_frame_data
        cdef bint valid = False
        self.read_lock._acquire(True, -1)
        try:
            vc = self.view_count
            self.view_count += 1
            try:
                with nogil:
                    bfr_len = self.read_indices.size()
                    if vc == 0:
                        if bfr_len > 0:
                            bfr_idx = self.read_indices.front()
                            self.read_indices.pop_front()
                            self.read_indices_set.erase(bfr_idx)
                            dest[:] = all_frame_data[bfr_idx,:]
                            valid = True
                    else:
                        dest[:] = read_view
                        valid = True
            finally:
                self.view_count -= 1
            return valid
        finally:
            self.read_lock._release()

    cdef size_t _get_next_write_index(self) except? -1 nogil:
        cdef size_t idx, niter, result, bfr_len = self.read_indices.size()

        if bfr_len > 0:
            result = self.read_indices.back() + 1
            if result >= self.max_buffers:
                result = 0
        else:
            result = 0
        niter = 0
        while self.read_indices_set.count(result) != 0:
            result += 1
            if result >= self.max_buffers:
                result = 0
            niter += 1
            if niter > self.max_buffers * 2:
                raise_withgil(PyExc_ValueError, 'could not get write index')
        return result

    cdef bint can_receive(self) except -1 nogil:
        return self.read_indices.size() < self.max_buffers

    cdef int _check_write_array_size(self) except -1:
        cdef cnp.uint8_t[:,:] arr = self.all_frame_data
        cdef size_t ncols = self._get_buffer_size()

        if arr.shape[1] == ncols:
            return 0
        self.read_lock._acquire(True, -1)
        try:
            self.all_frame_data = np.zeros((self.max_buffers, ncols), dtype=np.uint8)
            self.read_indices.clear()
            self.read_indices_set.clear()
            if self.view_count == 0:
                self.current_frame_data = np.zeros(ncols, dtype=np.uint8)
        finally:
            self.read_lock._release()
        return 0

    cdef int _prepare_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1:
        cdef size_t bfr_idx
        self._recalc_pack_info(use_ptr_stride=True)
        self._check_write_array_size()
        if self.read_indices.size() == self.max_buffers:
            self.read_lock._acquire(True, -1)
            try:
                if self.read_indices.size() == self.max_buffers:
                    bfr_idx = self.read_indices.front()
                    self.read_indices.pop_front()
                    self.read_indices_set.erase(bfr_idx)
            finally:
                self.read_lock._release()
        return 0

    cdef int _process_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1:
        cdef video_bfr_p write_bfr = self.write_bfr
        cdef video_bfr_p read_bfr = self.read_bfr
        cdef NDIlib_video_frame_v2_t* p = self.ptr
        cdef frame_rate_t fr = self.frame_rate
        cdef size_t size_in_bytes = self._get_buffer_size()
        cdef size_t buffer_index = self._get_next_write_index()
        cdef cnp.uint8_t[:,:] all_frame_data = self.all_frame_data
        cdef cnp.uint8_t[:] write_view = all_frame_data[buffer_index]

        with nogil:
            fr.numerator = p.frame_rate_N
            fr.denominator = p.frame_rate_D

            write_bfr.timecode = p.timecode
            write_bfr.timestamp = p.timestamp
            write_bfr.line_stride = p.line_stride_in_bytes
            write_bfr.format = frame_format_uncast(p.frame_format_type)
            write_bfr.fourcc = fourcc_type_uncast(p.FourCC)
            write_bfr.xres = p.xres
            write_bfr.yres = p.yres
            write_bfr.aspect = p.picture_aspect_ratio
            write_bfr.total_size = size_in_bytes
            uint8_ptr_to_memview_1d(p.p_data, write_view)
            self.read_bfr.total_size = self.write_bfr.total_size
            self.read_indices.push_back(buffer_index)
            self.read_indices_set.insert(buffer_index)

            write_bfr.valid = True

            if recv_ptr is not NULL:
                NDIlib_recv_free_video_v2(recv_ptr, self.ptr)
        return 0

cdef class VideoFrameSync(VideoFrame):
    """Video frame for use with :class:`.framesync.FrameSync`

    Unlike :class:`VideoRecvFrame`, this object does not store or buffer any
    data. It will always contain the most recent video frame data after a call to
    :meth:`.framesync.FrameSync.capture_video`.

    This is by design since the FrameSync methods utilize buffering from within
    the |NDI| library.

    Data can be read using the :meth:`get_array` method or by using the
    :ref:`buffer protocol <frame-buffer-protocol>`.
    """
    def __cinit__(self, *args, **kwargs):
        self.shape[0] = 0
        self.strides[0] = 0
        self.view_count = 0
        self.framesync_instance.fs_ptr = NULL
        self.framesync_instance.free_data = NULL

    def __dealloc__(self):
        self.framesync_instance.fs_ptr = NULL
        self.framesync_instance.free_data = NULL

    cdef void _free_framesync_pointers(self) noexcept nogil:
        self.framesync_instance.free_data = NULL
        self.framesync_instance.fs_ptr = NULL

    cdef void _free_framesync_data(self) noexcept nogil:
        cdef FrameSyncVideoInstance_s* ptr = &self.framesync_instance
        if ptr.free_data is NULL:
            return
        ptr.free_data(ptr, self.ptr)


    def get_array(self):
        """Get the video frame data as an :class:`numpy.ndarray` of unsigned
        8-bit integers
        """
        cdef cnp.ndarray[cnp.uint8_t, ndim=1] arr = np.empty(self.shape, dtype=np.uint8)
        cdef cnp.uint8_t[:] arr_view = arr
        cdef cnp.uint8_t[:] self_view = self
        arr_view[...] = self_view
        return arr

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        cdef NDIlib_video_frame_v2_t* p = self.ptr

        buffer.buf = <char *>p.p_data
        buffer.format = 'B'
        buffer.internal = NULL
        buffer.itemsize = sizeof(uint8_t)
        buffer.len = self.shape[0]
        buffer.ndim = 1
        buffer.obj = self
        buffer.readonly = 1
        buffer.shape = <Py_ssize_t*>self.shape
        buffer.strides = <Py_ssize_t*>self.strides
        buffer.suboffsets = NULL

        self.view_count += 1

    def __releasebuffer__(self, Py_buffer *buffer):
        self.view_count -= 1
        if self.view_count == 0:
            self._free_framesync_data()
            self.shape[0] = 0

    cdef int _process_incoming(self) except -1 nogil:
        if self.view_count > 0:
            raise_withgil(PyExc_ValueError, 'cannot write with view active')

        self._recalc_pack_info(use_ptr_stride=True)
        cdef NDIlib_video_frame_v2_t* p = self.ptr
        cdef size_t size_in_bytes = self._get_buffer_size()
        self.shape[0] = size_in_bytes
        self.strides[0] = sizeof(uint8_t)
        return 0


cdef class VideoSendFrame(VideoFrame):
    """Video frame for use with :class:`.sender.Sender`

    .. note::

        Instances of this class are not intended to be created directly nor are
        its methods. They are instead called from the :class:`sender.Sender`
        write methods.

    """
    def __cinit__(self, *args, **kwargs):
        frame_status_init(&(self.send_status))
        self.send_status.data.ndim = 1
        self.buffer_write_item = NULL

    def __dealloc__(self):
        self.buffer_write_item = NULL
        frame_status_free(&(self.send_status))

    @property
    def attached_to_sender(self):
        return self.send_status.data.attached_to_sender

    @property
    def write_index(self):
        return self.send_status.data.write_index

    @property
    def read_index(self):
        return self.send_status.data.read_index

    @property
    def shape(self):
        cdef VideoSendFrame_status_s* ptr = &(self.send_status)
        cdef list l = ptr.data.shape
        return tuple(l[:ptr.data.ndim])

    @property
    def strides(self):
        cdef VideoSendFrame_status_s* ptr = &(self.send_status)
        cdef list l = ptr.data.strides
        return tuple(l[:ptr.data.ndim])

    @property
    def ndim(self):
        return self.send_status.data.ndim

    def destroy(self):
        self._destroy()

    cdef int _destroy(self) except -1:
        self.buffer_write_item = NULL
        frame_status_free(&(self.send_status))
        return 0

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        cdef VideoSendFrame_item_s* item = self.buffer_write_item
        if item is NULL:
            item = self._prepare_buffer_write()
        item.data.view_count += 1
        buffer.buf = <uint8_t*>item.frame_ptr.p_data
        buffer.format = 'B'
        buffer.internal = <void*>item
        buffer.itemsize = sizeof(uint8_t)
        buffer.len = item.data.alloc_size
        buffer.ndim = self.send_status.data.ndim
        buffer.obj = self
        buffer.readonly = 0
        buffer.shape = <Py_ssize_t*>item.data.shape
        buffer.strides = <Py_ssize_t*>item.data.strides
        buffer.suboffsets = NULL

    def __releasebuffer__(self, Py_buffer *buffer):
        cdef VideoSendFrame_item_s* item
        if buffer.internal is not NULL:
            item = <VideoSendFrame_item_s*>buffer.internal
            if item.data.view_count > 0:
                item.data.view_count -= 1

    def get_write_available(self):
        return self._write_available()

    cdef bint _write_available(self) noexcept nogil:
        cdef size_t idx = frame_status_get_next_write_index(&(self.send_status))
        return idx != NULL_INDEX

    cdef VideoSendFrame_item_s* _prepare_buffer_write(self) except NULL nogil:
        if self.buffer_write_item is not NULL:
            raise_withgil(PyExc_RuntimeError, 'buffer_write_item is not null')
        cdef VideoSendFrame_item_s* item = self._get_next_write_frame()
        if item.data.view_count != 0:
            raise_withgil(PyExc_RuntimeError, 'buffer item view count nonzero')
        self.buffer_write_item = item
        return item

    cdef void _set_buffer_write_complete(self, VideoSendFrame_item_s* item) noexcept nogil:
        cdef VideoSendFrame_item_s* cur_item = self.buffer_write_item
        if cur_item is not NULL and cur_item.data.idx == item.data.idx:
            self.buffer_write_item = NULL
        self.send_status.data.read_index = item.data.idx
        frame_status_set_send_ready(&(self.send_status))

    def write_data(self, cnp.uint8_t[:] data):
        """Write a frame of video data to the internal buffer

        The buffered data will then be sent on the next call to
        :meth:`.sender.Sender.send_video` or :meth:`.sender.Sender.send_video_async`

        Arguments:
            data: A 1-d array or memoryview of unsigned 8-bit integers
                formatted as described in :class:`.wrapper.ndi_structs.FourCC`

        .. note::

            This method is available for flexibility, but using
            :meth:`.sender.Sender.write_video` or :meth:`.sender.Sender.write_video_async`
            may be more desirable as the video data will be buffered and
            sent immediately

        """
        cdef VideoSendFrame_item_s* item = self._prepare_memview_write()
        cdef cnp.uint8_t[:] view = self

        assert data.shape[0] == view.shape[0]
        self._write_data_to_memview(data, view, item)

    cdef VideoSendFrame_item_s* _prepare_memview_write(self) except NULL nogil:
        return self._prepare_buffer_write()

    cdef void _write_data_to_memview(
        self,
        cnp.uint8_t[:] data,
        cnp.uint8_t[:] view,
        VideoSendFrame_item_s* item,
    ) noexcept nogil:
        view[:] = data
        self._set_buffer_write_complete(item)

    cdef VideoSendFrame_item_s* _get_next_write_frame(self) except NULL nogil:
        cdef size_t idx = frame_status_get_next_write_index(&(self.send_status))
        if idx == NULL_INDEX:
            raise_withgil(PyExc_RuntimeError, 'no write frame available')
        self.send_status.data.write_index = idx
        return &(self.send_status.items[idx])

    cdef int _recalc_pack_info(self, bint use_ptr_stride=False) except -1 nogil:
        return VideoFrame._recalc_pack_info(self, use_ptr_stride)

    cdef bint _send_frame_available(self) noexcept nogil:
        cdef size_t idx = frame_status_get_next_read_index(&(self.send_status))
        return idx != NULL_INDEX

    cdef VideoSendFrame_item_s* _get_send_frame(self) except NULL nogil:
        cdef size_t idx = frame_status_get_next_read_index(&(self.send_status))
        if idx == NULL_INDEX:
            raise_withgil(PyExc_IndexError, 'no read index available')
        return &(self.send_status.items[idx])

    cdef VideoSendFrame_item_s* _get_send_frame_noexcept(self) noexcept nogil:
        """Version of :meth:`_get_send_frame` that does NOT check if an
        index is available

        :meth:`_send_frame_available` must be checked before calling this
        or bad things could happen
        """
        cdef size_t idx = frame_status_get_next_read_index(&(self.send_status))
        return &(self.send_status.items[idx])

    cdef void _on_sender_write(self, VideoSendFrame_item_s* s_ptr) noexcept nogil:
        frame_status_set_send_complete(&(self.send_status), s_ptr.data.idx)

    cdef int _set_sender_status(self, bint attached) except -1 nogil:
        if attached:
            self._recalc_pack_info()
            self._rebuild_array()
        self.send_status.data.attached_to_sender = attached
        return 0

    cdef int _set_xres(self, int value) except -1 nogil:
        if self.send_status.data.attached_to_sender:
            raise_exception('Cannot alter frame')
        return VideoFrame._set_xres(self, value)

    cdef int _set_yres(self, int value) except -1 nogil:
        if self.send_status.data.attached_to_sender:
            raise_exception('Cannot alter frame')
        return VideoFrame._set_yres(self, value)

    cdef int _set_resolution(self, int xres, int yres) except -1 nogil:
        if self.send_status.data.attached_to_sender:
            raise_exception('Cannot alter frame')
        return VideoFrame._set_resolution(self, xres, yres)

    cdef int _set_fourcc(self, FourCC value) except -1 nogil:
        if self.send_status.data.attached_to_sender:
            raise_exception('Cannot alter frame')
        return VideoFrame._set_fourcc(self, value)

    cdef int _rebuild_array(self) except -1 nogil:
        cdef VideoSendFrame_status_s* s_ptr = &(self.send_status)
        frame_status_copy_frame_ptr(s_ptr, self.ptr)
        s_ptr.data.shape[0] = self._get_buffer_size()
        s_ptr.data.strides[0] = sizeof(uint8_t)
        frame_status_alloc_p_data(s_ptr)
        return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cdef int uint8_ptr_to_memview_1d(uint8_t* p, cnp.uint8_t[:] dest) except -1 nogil:
    cdef size_t ncols = dest.shape[0]
    cdef size_t i

    for i in range(ncols):
        dest[i] = p[i]
    return 0






# def uint32_2d_to_uint8_3d(cnp.ndarray[cnp.uint32_t, ndim=2] in_arr):
#     cdef cnp.ndarray[uint8_t, ndim=3] out_arr = np.empty((in_arr.shape[0], in_arr.shape[1], 4), dtype=np.uint8)
#     _uint32_2d_to_uint8_3d(in_arr, out_arr)
#     return out_arr
#
# @cython.boundscheck(False)
# @cython.wraparound(False)
# cdef _uint32_2d_to_uint8_3d(cnp.uint32_t[:,:] src, cnp.uint8_t[:,:,:] dest):
#     cdef size_t nrows = src.shape[0], ncols = src.shape[1]
#     cdef size_t i, j, k
#     cdef uint32_t v
#
#     for i in range(nrows):
#         for j in range(ncols):
#             v = src[i,j]
#             dest[i,j,0] = (v >> 24) & 0xff
#             dest[i,j,1] = (v >> 16) & 0xff
#             dest[i,j,2] = (v >>  8) & 0xff
#             dest[i,j,3] = (v >>  0) & 0xff
