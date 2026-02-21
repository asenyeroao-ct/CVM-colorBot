from libc.string cimport strdup
cimport cython
import threading

from .clock cimport time, sleep


__all__ = ('Receiver', 'RecvThreadWorker', 'RecvThread')


cdef NDIlib_frame_type_e recv_frame_type_cast(ReceiveFrameType ft) noexcept nogil:
    if ft == ReceiveFrameType.recv_video:
        return NDIlib_frame_type_video
    elif ft == ReceiveFrameType.recv_audio:
        return NDIlib_frame_type_audio
    elif ft == ReceiveFrameType.recv_metadata:
        return NDIlib_frame_type_metadata
    elif ft == ReceiveFrameType.recv_status_change:
        return NDIlib_frame_type_status_change
    elif ft == ReceiveFrameType.recv_error:
        return NDIlib_frame_type_error
    elif ft == ReceiveFrameType.nothing:
        return NDIlib_frame_type_none
    # return NULL

cdef ReceiveFrameType recv_frame_type_uncast(NDIlib_frame_type_e ft) noexcept nogil:
    if ft == NDIlib_frame_type_video:
        return ReceiveFrameType.recv_video
    elif ft == NDIlib_frame_type_audio:
        return ReceiveFrameType.recv_audio
    elif ft == NDIlib_frame_type_metadata:
        return ReceiveFrameType.recv_metadata
    elif ft == NDIlib_frame_type_status_change:
        return ReceiveFrameType.recv_status_change
    elif ft == NDIlib_frame_type_error:
        return ReceiveFrameType.recv_error
    elif ft == NDIlib_frame_type_none:
        return ReceiveFrameType.nothing
    # return NULL



cdef class RecvCreate:
    # cdef public str source_name
    # cdef public RecvColorFormat color_format
    # cdef public RecvBandwidth bandwidth
    # cdef public bint allow_video_fields
    # cdef public str recv_name

    def __init__(
        self,
        str source_name='',
        color_format=RecvColorFormat.UYVY_BGRA,
        RecvBandwidth bandwidth=RecvBandwidth.highest,
        bint allow_video_fields=True,
        str recv_name=''
    ):
        self.source_name = source_name
        self.color_format = color_format
        self.bandwidth = bandwidth
        self.allow_video_fields = allow_video_fields
        self.recv_name = recv_name

    cdef NDIlib_recv_create_v3_t* build_create_p(self) except *:
        cdef NDIlib_recv_create_v3_t* p = recv_t_create_default()
        # cdef bytes src_name_py = self.source_name.encode()
        # cdef const char* src_name_c = src_name_py

        cdef bytes recv_name_py = self.recv_name.encode()
        cdef const char* recv_name_c = recv_name_py

        # if len(src_name_py):
        #     p.source_to_connect_to.p_ndi_name = src_name_c

        if len(recv_name_py):
            p.p_ndi_recv_name = recv_name_c
        p.color_format = recv_format_cast(self.color_format)
        p.bandwidth = recv_bandwidth_cast(self.bandwidth)
        p.allow_video_fields = self.allow_video_fields

        return p


cdef class Receiver:
    """A receiver for |NDI| streams

    Arguments:
        source_name (str, optional): The |NDI| source name to connect to. An
            empty string (default) indicates no source
        source (Source, optional): A :class:`~.finder.Source` object
            to connect to. ``None`` (default) indices no source.
        color_format: The :class:`~.wrapper.ndi_recv.RecvColorFormat` to accept
        bandwidth: The :class:`~.wrapper.ndi_recv.RecvBandwidth` to use
        allow_video_fields: ``True`` if interlaced video frames can be handled.
            If ``False``, only progressive frames will be delivered.
        recv_name: Name for the receiver


    Attributes:
        source_name (str): The current |NDI| source name
        source (Source): The current :class:`~.finder.Source` object
        video_frame (VideoRecvFrame):
        audio_frame (AudioRecvFrame):
        metadata_frame (MetadataRecvFrame):
        frame_sync (FrameSync):
        ptz (PTZ): Access to the PTZ methods.
    """
    def __cinit__(self, *args, **kwargs):
        self.ptr = NULL
        self.source_ptr = NULL
        self.video_stats.frames_total = 0
        self.video_stats.frames_dropped = 0
        self.video_stats.dropped_percent = 0

        self.audio_stats.frames_total = 0
        self.audio_stats.frames_dropped = 0
        self.audio_stats.dropped_percent = 0

        self.metadata_stats.frames_total = 0
        self.metadata_stats.frames_dropped = 0
        self.metadata_stats.dropped_percent = 0

        self.perf_total_s.video_frames = 0
        self.perf_total_s.audio_frames = 0
        self.perf_total_s.metadata_frames = 0

        self.perf_dropped_s.video_frames = 0
        self.perf_dropped_s.audio_frames = 0
        self.perf_dropped_s.metadata_frames = 0

    def __init__(
        self,
        str source_name='',
        Source source=None,
        color_format=RecvColorFormat.UYVY_BGRA,
        RecvBandwidth bandwidth=RecvBandwidth.lowest,
        bint allow_video_fields=True,
        str recv_name=''
    ):
        self.connection_lock = RLock()
        self.connection_notify = Condition(self.connection_lock)
        self._connected = False
        self._probably_connected = False
        self._num_empty_recv = 0
        self.source = source
        if source is not None:
            source_name = source.name
        self.source_name = source_name
        self.settings = RecvCreate(
            source_name, color_format, bandwidth,
            allow_video_fields, recv_name,
        )
        self.metadata_frame = MetadataRecvFrame()
        self.has_video_frame = False
        self.has_audio_frame = False
        self.has_metadata_frame = True

        cdef NDIlib_recv_create_v3_t* src_p = self.settings.build_create_p()
        try:
            recv_t_copy(src_p, &(self.recv_create))
        except:
            import traceback
            traceback.print_exc()
            raise
        finally:
            recv_t_destroy(src_p)
        self.ptr = NDIlib_recv_create_v3(&(self.recv_create))
        if self.ptr is NULL:
            raise MemoryError()
        self.frame_sync = FrameSync(self)
        self.ptz = PTZ(self)

    def __dealloc__(self):
        self.ptz = None
        self.frame_sync = None
        cdef NDIlib_recv_instance_t p = self.ptr
        if self.ptr is not NULL:
            self.ptr = NULL
            NDIlib_recv_destroy(p)

    cpdef set_video_frame(self, VideoRecvFrame vf):
        """Set the :attr:`video_frame`
        """
        # if self.video_frame is not None:
        #     self.video_ptr = NULL
        self.video_frame = vf
        # if vf is not None:
        #     self.video_ptr = vf.ptr
        self.has_video_frame = vf is not None

    cpdef set_audio_frame(self, AudioRecvFrame af):
        """Set the :attr:`audio_frame`
        """
        # if self.audio_frame is not None:
        #     self.audio_ptr = NULL
        self.audio_frame = af
        # if af is not None:
        #     self.audio_ptr = af.ptr
        self.has_audio_frame = af is not None

    cpdef set_metadata_frame(self, MetadataRecvFrame mf):
        """Set the :attr:`metadata_frame`
        """
        self.metadata_frame = mf
        self.has_metadata_frame = mf is not None

    cpdef set_source(self, Source src):
        """Set the current :attr:`source`

        If the source is None, disconnects if necessary. Otherwise, attempt to
        connect to it.
        """
        if self.source is src:
            return
        if self._is_connected():
            self._disconnect()
        if src is None:
            self.source_name = None
            self.source = src
            self.source_ptr = NULL
        else:
            self.source_name = src.name
            self.source = src
            if not src.valid:
                src.update()
            if src.valid:
                self._connect_to(src.ptr)

    cpdef connect_to(self, Source src):
        """Alias for :meth:`set_source`
        """
        self.set_source(src)

    cdef int _connect_to(self, NDIlib_source_t* src) except -1:
        self.source_name = src.p_ndi_name.decode('UTF-8')
        self.source_ptr = src
        NDIlib_recv_connect(self.ptr, src)
        self._probably_connected = True
        self._set_connected(True)
        return 0

    def disconnect(self):
        """Disconnect from the :attr:`source` (if connected)
        """
        self.set_source(None)

    cdef int _disconnect(self) except -1 nogil:
        # if not self._is_connected():
        #     return
        self.source_ptr = NULL
        NDIlib_recv_connect(self.ptr, NULL)
        self._probably_connected = False
        self._num_empty_recv = 0
        self._set_connected(False)
        return 0

    def reconnect(self):
        self._reconnect()

    cdef int _reconnect(self) except -1 nogil:
        if self._is_connected():
            return 0
        NDIlib_recv_connect(self.ptr, self.source_ptr)
        self._is_connected()
        return 0

    def is_connected(self):
        """Returns `True` if currently connected
        """
        return self._is_connected()

    cdef bint _is_connected(self) except -1 nogil:
        cdef bint r = self._get_num_connections() > 0
        if r is not self._connected:
            self._set_connected(r)
        return r

    cdef int _set_connected(self, bint value) except -1 nogil:
        if value is self._connected:
            return 0
        with gil:
            self.connection_lock._acquire(True, -1)
            try:
                self._connected = value
                self.connection_notify._notify_all()
            finally:
                self.connection_lock._release()
        return 0

    cdef bint _wait_for_connect(self, float timeout) except -1 nogil:
        if self._connected:
            return True
        if self._is_connected():
            return True
        cdef bint r
        with gil:
            self.connection_lock._acquire(True, -1)
            try:
                self.connection_lock.wait(timeout)
            finally:
                self.connection_lock._release()
        return self._connected


    def get_num_connections(self):
        return self._get_num_connections()

    cdef int _get_num_connections(self) except? -1 nogil:
        cdef int r = NDIlib_recv_get_no_connections(self.ptr)
        return r

    def get_performance_data(self):
        self._update_performance()
        cdef dict r = {
            'video':self.video_stats,
            'audio':self.audio_stats,
            'metadata':self.metadata_stats,
        }
        return r

    @cython.cdivision(True)
    cdef int _update_performance(self) except -1 nogil:
        NDIlib_recv_get_performance(self.ptr, &(self.perf_total_s), &(self.perf_dropped_s))

        cdef RecvPerformance_t* vstats = &(self.video_stats)
        cdef RecvPerformance_t* astats = &(self.audio_stats)
        cdef RecvPerformance_t* mstats = &(self.metadata_stats)

        vstats.frames_total = self.perf_total_s.video_frames
        astats.frames_total = self.perf_total_s.audio_frames
        mstats.frames_total = self.perf_total_s.metadata_frames

        vstats.frames_dropped = self.perf_dropped_s.video_frames
        astats.frames_dropped = self.perf_dropped_s.audio_frames
        mstats.frames_dropped = self.perf_dropped_s.metadata_frames

        cdef double pct

        if vstats.frames_total > 0:
            pct = vstats.frames_dropped / <double>vstats.frames_total * 100
            vstats.dropped_percent = pct
        else:
            vstats.dropped_percent = 0
        if astats.frames_total > 0:
            pct = astats.frames_dropped / <double>astats.frames_total * 100
            astats.dropped_percent = pct
        else:
            astats.dropped_percent = 0
        if mstats.frames_total > 0:
            pct = mstats.frames_dropped / <double>mstats.frames_total * 100
            mstats.dropped_percent = pct
        else:
            mstats.dropped_percent = 0
        return 0

    @property
    def program_tally(self):
        """Indicates the program tally state as set by :meth:`set_source_tally_program`
        """
        return self.source_tally.on_program

    @property
    def preview_tally(self):
        """Indicates the preview tally state as set by :meth:`set_source_tally_program`
        """
        return self.source_tally.on_preview

    cpdef set_source_tally_program(self, bint value):
        """Set the program tally state for the currently connected source.

        This method sends a tally command to the source and does not necessarily
        affect the state of the :attr:`source` object's tally. It will be updated
        independently when tally metadata is received.

        This is because other receivers may have also sent tally messages to the
        source. When this occurs, the source's tally remains "on" until **all**
        of its connected receivers have set it to "off" (like a bitwise "OR")
        """
        self._set_source_tally(value, self.source_tally.on_preview)

    cpdef set_source_tally_preview(self, bint value):
        """Set the preview tally state for the currently connected source

        See notes in the :meth:`set_source_tally_program` method
        """
        self._set_source_tally(self.source_tally.on_program, value)

    cdef int _set_source_tally(self, bint program, bint preview) except -1 nogil:
        self.source_tally.on_program = program
        self.source_tally.on_preview = preview
        self._send_source_tally()
        return 0

    cdef int _send_source_tally(self) except -1 nogil:
        NDIlib_recv_set_tally(self.ptr, &(self.source_tally))
        return 0

    cdef int _handle_metadata_frame(self) except -1:
        cdef MetadataRecvFrame mf = self.metadata_frame
        cdef bint pgm, pvw
        if mf.tag == 'ndi_tally_echo':
            pgm = mf.attrs.get('on_program') == 'true'
            pvw = mf.attrs.get('on_preview') == 'true'
            self.source._set_tally(pgm, pvw)
        return 0

    cpdef ReceiveFrameType receive(self, ReceiveFrameType recv_type, uint32_t timeout_ms):
        """Receive frame data of the given type

        If requesting a video or audio frame and the result indicates data was
        received, the incoming frame data will be available in the
        :attr:`video_frame` or :attr:`audio_frame`.

        Arguments:
            recv_type (ReceiveFrameType): The frame type(s) to receive
            timeout_ms (int): Time (in milliseconds) to wait for a frame to be
                available

        Returns a :class:`ReceiveFrameType` indicating what was received.  If
        nothing was available before the timeout, the result will be
        :attr:`ReceiveFrameType.nothing`
        """
        return self._receive(recv_type, timeout_ms)

    cdef ReceiveFrameType _receive(
        self, ReceiveFrameType recv_type, uint32_t timeout_ms
    ) except *:
        cdef VideoRecvFrame video_frame = self.video_frame
        cdef AudioRecvFrame audio_frame = self.audio_frame
        cdef MetadataRecvFrame metadata_frame = self.metadata_frame
        cdef bint has_video_frame = self.has_video_frame
        cdef bint has_audio_frame = self.has_audio_frame
        cdef bint has_metadata_frame = self.has_metadata_frame
        cdef NDIlib_video_frame_v2_t* video_ptr
        cdef NDIlib_audio_frame_v3_t* audio_ptr
        cdef NDIlib_metadata_frame_t* metadata_ptr
        cdef bint buffers_full = False
        cdef int recv_type_flags = <int>recv_type

        if recv_type & ReceiveFrameType.recv_video and has_video_frame:
            if video_frame.can_receive():
                video_ptr = video_frame.ptr
            else:
                recv_type_flags ^= ReceiveFrameType.recv_video
                buffers_full = True
                video_ptr = NULL
        else:
            video_ptr = NULL

        if recv_type & ReceiveFrameType.recv_audio and has_audio_frame:
            if audio_frame.can_receive():
                audio_ptr = audio_frame.ptr
            else:
                recv_type_flags ^= ReceiveFrameType.recv_audio
                buffers_full = True
                audio_ptr = NULL
        else:
            audio_ptr = NULL

        if recv_type & ReceiveFrameType.recv_metadata and has_metadata_frame:
            if metadata_frame.can_receive():
                metadata_ptr = metadata_frame.ptr
            else:
                recv_type_flags ^= ReceiveFrameType.recv_metadata
                buffers_full = True
                metadata_ptr = NULL
        else:
            metadata_ptr = NULL

        if recv_type_flags != <int>recv_type:
            recv_type = ReceiveFrameType(recv_type_flags)

        if not recv_type & ReceiveFrameType.recv_all:
            if buffers_full:
                return ReceiveFrameType.recv_buffers_full
            else:
                return ReceiveFrameType.nothing

        cdef ReceiveFrameType ft = self._do_receive(
            video_ptr, audio_ptr, metadata_ptr, timeout_ms
        )

        if ft == ReceiveFrameType.recv_video and has_video_frame:
            video_frame._prepare_incoming(self.ptr)
        elif ft == ReceiveFrameType.recv_audio and has_audio_frame:
            audio_frame._prepare_incoming(self.ptr)
        elif ft == ReceiveFrameType.recv_metadata and has_metadata_frame:
            metadata_frame._prepare_incoming(self.ptr)

        if ft == ReceiveFrameType.recv_video:
            if has_video_frame:
                video_frame._process_incoming(self.ptr)
            else:
                self.free_video(video_ptr)
        elif ft == ReceiveFrameType.recv_audio:
            if has_audio_frame:
                audio_frame._process_incoming(self.ptr)
            else:
                self.free_audio(audio_ptr)
        elif ft == ReceiveFrameType.recv_metadata:
            if has_metadata_frame:
                metadata_frame._process_incoming(self.ptr)
                self._handle_metadata_frame()
            else:
                self.free_metadata(metadata_ptr)

        return ft

    cdef ReceiveFrameType _do_receive(
        self,
        NDIlib_video_frame_v2_t* video_frame,
        NDIlib_audio_frame_v3_t* audio_frame,
        NDIlib_metadata_frame_t* metadata_frame,
        uint32_t timeout_ms
    ) noexcept nogil:
        cdef NDIlib_frame_type_e r = NDIlib_recv_capture_v3(
            self.ptr, video_frame, audio_frame, metadata_frame, timeout_ms
        )
        cdef ReceiveFrameType ft = recv_frame_type_uncast(r)
        if ft & ReceiveFrameType.recv_all:
            self._num_empty_recv = 0
            self._probably_connected = True
        elif ft & ReceiveFrameType.recv_status_change == 0:
            self._num_empty_recv += 1
        return ft

    cdef void free_video(self, NDIlib_video_frame_v2_t* p) noexcept nogil:
        NDIlib_recv_free_video_v2(self.ptr, p)

    cdef void free_audio(self, NDIlib_audio_frame_v3_t* p) noexcept nogil:
        NDIlib_recv_free_audio_v3(self.ptr, p)

    cdef void free_metadata(self, NDIlib_metadata_frame_t* p) noexcept nogil:
        NDIlib_recv_free_metadata(self.ptr, p)

    def is_ptz_supported(self):
        """Returns `True` if the source accepts PTZ commands

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_is_supported(self.ptr)


cdef class PTZ:
    """PTZ control for a :class:`Receiver`
    """
    def __init__(self, receiver: Receiver):
        self.receiver = receiver

    def __dealloc__(self):
        self.receiver = None

    cdef NDIlib_recv_instance_t _get_ptr(self):
        cdef NDIlib_recv_instance_t ptr = self.receiver.ptr
        if ptr is NULL:
            raise ValueError("Receiver is not connected")
        return ptr

    def set_zoom_level(self, float zoom_level):
        """Set the PTZ zoom level

        Arguments:
            zoom_level (float): `0.0` (max zoomed out) … `1.0` (max zoomed in)

        .. versionadded:: 0.0.7
        """
        if not 0 <= zoom_level <= 1:
            raise ValueError(f"zoom_level must be between 0.0 and 1.0 inclusive, but was {zoom_level}")
        return NDIlib_recv_ptz_zoom(self._get_ptr(), zoom_level)

    def zoom(self, float zoom_speed):
        """Zoom the camera with the given speed.

        The assumption is that this function is called continuously,
        for example while pressing a button in a GUI or HID.

        >>> for _ in range(0, 100):
        ...     time.sleep(0.05)
        ...     receiver.ptz.zoom(.5)

        Arguments:
            zoom_speed (float): `-1.0` (zoom out, max speed) … `0.0` (no zooming) … `1.0` (zoom in, max speed)

        .. versionadded:: 0.0.7
        """
        if not -1 <= zoom_speed <= 1:
            raise ValueError(f"zoom_speed must be between -1.0 and 1.0 inclusive, but was {zoom_speed}")
        return NDIlib_recv_ptz_zoom_speed(self._get_ptr(), zoom_speed)

    def pan_and_tilt(self, float pan_speed, float tilt_speed):
        """Pan and tilt the camera.

        The assumption is that this function is called continuously,
        for example while pressing a button in a GUI or HID.

        >>> for _ in range(0, 100):
        ...     time.sleep(0.05)
        ...     receiver.ptz.pan_and_tilt(.5)

        Arguments:
            pan_speed (float): `1.0` (fastest left) … `0.0` (no movement) … `-1.0` (fastest right)
            tilt_speed (float): `-1.0` (fastest downwards) … `0.0` (no movement) … `1.0` (fastest upwards)

        .. Attention::
            `1` is *to the left*, and `-1` *is to the right*!

        .. versionadded:: 0.0.7
        """
        return self._set_pan_and_tilt_speed(pan_speed, tilt_speed)

    def pan(self, float pan_speed):
        """Pan the camera.

        The assumption is that this function is called continuously,
        for example while pressing a button in a GUI or HID.

        >>> for _ in range(0, 100):
        ...     time.sleep(0.05)
        ...     receiver.ptz.pan(.5)

        Arguments:
            pan_speed (float): `1.0` (fastest left) … `0.0` (no movement) … `-1.0` (fastest right)

        .. Attention:
            `1` is *to the left*, and `-1` *is to the right*!

        This is the same as `pan_and_tilt(pan_speed, 0.0)`, see :meth:`pan_and_tilt`.

        .. versionadded:: 0.0.7
        """
        return self._set_pan_and_tilt_speed(pan_speed, 0.0)

    def tilt(self, float tilt_speed):
        """Pan and tilt the camera.

        The assumption is that this function is called continuously,
        for example while pressing a button in a GUI or HID.

        >>> for _ in range(0, 100):
        ...     time.sleep(0.05)
        ...     receiver.ptz.tilt(.5)

        Arguments:
            tilt_speed (float): `-1.0` (fastest downwards) … `0.0` (no movement) … `1.0` (fastest upwards)

        This is the same as `pan_and_tilt(0.0, tilt_speed)`, see :meth:`pan_and_tilt`.

        .. versionadded:: 0.0.7
        """
        return self._set_pan_and_tilt_speed(0.0, tilt_speed)

    def _set_pan_and_tilt_speed(self, float pan_speed, float tilt_speed):
        if not -1 <= pan_speed <= 1:
            raise ValueError(f"pan_speed must be between -1.0 and 1.0 inclusive, but was {pan_speed}")
        if not -1 <= tilt_speed <= 1:
            raise ValueError(f"tilt_speed must be between -1.0 and 1.0 inclusive, but was {tilt_speed}")
        return NDIlib_recv_ptz_pan_tilt_speed(self._get_ptr(), pan_speed, tilt_speed)

    def set_pan_and_tilt_values(self, float pan_value, float tilt_value):
        """Set pan and tilt angles of the camera.

        Arguments:
            pan_value (float): `-1.0` (leftmost) … `0.0` (center) … `1.0` (right)
            tilt_value (float): `-1.0` (bottom) … `0.0` (middle) … `1.0` (top)

        .. Attention:
            While invoking `pan(-1)` moves the camera to the _right_,
            here a :attr:pan_value of `-1` means _all the way to the left_!

        .. Note::
            Some cameras (e.g. OBSBOT) only support tilt values from `-0.5` to `0.5`.

        .. versionadded:: 0.0.7
        """
        if not -1 <= pan_value <= 1:
            raise ValueError(f"pan_value must be between -1.0 and 1.0 inclusive, but was {pan_value}")
        if not -1 <= tilt_value <= 1:
            raise ValueError(f"tilt_value must be between -1.0 and 1.0 inclusive, but was {tilt_value}")
        return NDIlib_recv_ptz_pan_tilt(self._get_ptr(), pan_value, tilt_value)

    def store_preset(self, int preset_no):
        """Store the current PTZ configuration as preset.

        This includes position, focus, ….

        Arguments:
            preset_no (int): `0` … `99`

        .. versionadded:: 0.0.7
        """
        if not 0 <= preset_no <= 99:
            raise ValueError(f"preset_no must be between 0 and 99 inclusive, but was {preset_no}")
        return NDIlib_recv_ptz_store_preset(self._get_ptr(), preset_no)

    def recall_preset(self, int preset_no, float speed):
        """Recalls a previously stored PTZ preset.

        This includes position, focus, ….
        The speed indicates how fast the camera moves to the position.

        Arguments:
            preset_no (int): `0` … `99`
            speed (float): `0.0` (slowest) … `1.0` (fastest)

        .. versionadded:: 0.0.7
        """
        if not 0 <= preset_no <= 99:
            raise ValueError(f"preset_no must be between 0 and 99 inclusive, but was {preset_no}")
        if not 0 <= speed <= 1:
            raise ValueError(f"speed must be between 0.0 and 1.0 inclusive, but was {speed}")
        return NDIlib_recv_ptz_recall_preset(self._get_ptr(), preset_no, speed)

    def autofocus(self):
        """Re-enables / triggers the autofocus.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_auto_focus(self._get_ptr())

    def set_focus(self, float focus_value):
        """Sets focus to a specific value.

        Arguments:
            focus_value (float): `0.0` (max focus out; infinity) … `1.0` (max focus in)

        .. versionadded:: 0.0.7
        """
        if not 0 <= focus_value <= 1:
            raise ValueError(f"focus_value must be between 0.0 and 1.0 inclusive, but was {focus_value}")
        return NDIlib_recv_ptz_focus(self._get_ptr(), focus_value)

    def focus(self, float focus_speed):
        """Controls the focus of the camera.

        The assumption is that this function is called continuously,
        for example while pressing a button in a GUI or HID.

        >>> for _ in range(0, 100):
        ...     time.sleep(0.05)
        ...     receiver.ptz.focus(.5)

        Arguments:
            focus_speed (float): `-1.0` (focus out) … `0.0` (no change) … `1.0` (focus in)

        .. versionadded:: 0.0.7
        """
        if not -1 <= focus_speed <= 1:
            raise ValueError(f"focus_speed must be between -1 and 1.0 inclusive, but was {focus_speed}")
        return NDIlib_recv_ptz_focus_speed(self._get_ptr(), focus_speed)

    def white_balance_auto(self):
        """Changes the white balance to auto mode.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_white_balance_auto(self._get_ptr())

    def white_balance_indoor(self):
        """Changes the white balance to indoor mode.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_white_balance_indoor(self._get_ptr())

    def white_balance_outdoor(self):
        """Changes the white balance to outdoor mode.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_white_balance_outdoor(self._get_ptr())

    def white_balance_oneshot(self):
        """Determines the white balance automatically from the center of the current frame.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_white_balance_oneshot(self._get_ptr())

    def set_white_balance(self, float red, float blue):
        """Manually set the white balance values.

        Arguments:
            red (float): 0.0 … 1.0
            blue (float): 0.0 … 1.0

        .. versionadded:: 0.0.7
        """
        if not 0 <= red <= 1:
            raise ValueError(f"red must be between 0.0 and 1.0 inclusive, but was {red}")
        if not 0 <= blue <= 1:
            raise ValueError(f"blue must be between 0.0 and 1.0 inclusive, but was {blue}")
        return NDIlib_recv_ptz_white_balance_manual(self._get_ptr(), red, blue)

    def exposure_auto(self):
        """(Re-)enables the auto exposure mode.

        .. versionadded:: 0.0.7
        """
        return NDIlib_recv_ptz_exposure_auto(self._get_ptr())

    def set_exposure_coarse(self, float exposure_level):
        """Manually control the exposure.

        See also :meth:`set_exposure_fine`.

        Arguments:
            exposure_level (float): `0.0` (dark) … `1.0` (bright)

        .. Note::
            Use either this or :meth:`set_exposure_fine`.
            There's no value in using both.
            Prefer :meth:`set_exposure_fine`.

        .. versionadded:: 0.0.7
        """
        if not 0 <= exposure_level <= 1:
            raise ValueError(f"exposure_level must be between 0.0 and 1.0 inclusive, but was {exposure_level}")
        return NDIlib_recv_ptz_exposure_manual(self._get_ptr(), exposure_level)

    def set_exposure_fine(self, float iris, float gain, float shutter_speed):
        """Precisely control the exposure.

        See also :meth:`set_exposure_coarse`.

        Arguments:
            iris (float): `0.0` (closed) … `1.0` (open)
            gain (float): `0.0` (low) … `1.0` (high)
            shutter_speed (float): `0.0` (slow) … `1.0` (fast)

        .. Note::
            Use either this or :meth:`set_exposure_coarse`.
            There's no value in using both.
            Prefer this method.

        .. versionadded:: 0.0.7
        """
        if not 0 <= iris <= 1:
            raise ValueError(f"iris must be between 0.0 and 1.0 inclusive, but was {iris}")
        if not 0 <= gain <= 1:
            raise ValueError(f"gain must be between 0.0 and 1.0 inclusive, but was {gain}")
        if not 0 <= shutter_speed <= 1:
            raise ValueError(f"shutter_speed must be between 0.0 and 1.0 inclusive, but was {shutter_speed}")
        return NDIlib_recv_ptz_exposure_manual_v2(self._get_ptr(), iris, gain, shutter_speed)


cdef class RecvThreadWorker:
    cdef Receiver receiver
    cdef uint32_t timeout_ms
    cdef ReceiveFrameType recv_frame_type
    cdef float wait_time
    cdef Event wait_event
    cdef bint running
    cdef Callback callback

    def __init__(
        self,
        Receiver receiver,
        ReceiveFrameType recv_frame_type,
        uint32_t timeout_ms,
        float wait_time=.1
    ):
        self.receiver = receiver
        assert recv_frame_type & ReceiveFrameType.recv_all
        self.recv_frame_type = recv_frame_type
        self.timeout_ms = timeout_ms
        self.callback = Callback()
        self.wait_event = Event()
        self.wait_time = wait_time

    cdef int run(self) except -1:
        cdef ReceiveFrameType ft
        self.running = True
        while self.running:
            if self.receiver._is_connected():
                ft = self.receiver._receive(self.recv_frame_type, self.timeout_ms)
                if ft & ReceiveFrameType.recv_buffers_full:
                    self.time_sleep(.01)
                    continue
                if ft & self.recv_frame_type:
                    if self.callback.has_callback:
                        self.callback.trigger_callback()
                if self.wait_time >= 0:
                    self.wait_for_evt(self.wait_time)
            else:
                self.wait_for_evt(.1)
        return 0

    cdef void time_sleep(self, double timeout) noexcept nogil:
        sleep(timeout)

    cdef int wait_for_evt(self, double timeout) except -1 nogil:
        with gil:
            self.wait_event._wait(True, timeout)
            self.wait_event._clear()
        return 0


    cdef int stop(self) except -1:
        self.wait_event._set()
        self.running = False
        return 0

class RecvThread(threading.Thread):
    """A thread designed for use with :class:`Receiver`

    Repeatedly calls :meth:`Receiver.receive` using the supplied arguments.
    A callback is then triggered whenever new frames are received.


    This can be used to handle video and audio using two separate threads. One
    thread would be set to use :attr:`~ReceiveFrameType.recv_video` and the
    other to :attr:`~ReceiveFrameType.recv_audio`.

    Arguments:
        receiver (Receiver): The receiver instance
        timeout_ms (int): Timeout (in milliseconds) to use when calling
            :meth:`Receiver.receive`
        recv_frame_type (ReceiveFrameType): The type(s) of frames to receive
        wait_time (float): Amount of time (in seconds) to sleep between calls to
            :meth:`Receiver.receive`

    """
    def __init__(
        self,
        Receiver receiver,
        uint32_t timeout_ms,
        int recv_frame_type = ReceiveFrameType.recv_video | ReceiveFrameType.recv_audio | ReceiveFrameType.recv_metadata,
        float wait_time=.1,
    ):
        super().__init__()
        self.worker = RecvThreadWorker(receiver, recv_frame_type, timeout_ms, wait_time)
        self.stopped = threading.Event()

    def run(self):
        cdef RecvThreadWorker worker = self.worker
        cdef int recv_frame_type = worker.recv_frame_type
        cdef Receiver receiver = worker.receiver

        if recv_frame_type & ReceiveFrameType.recv_video:
            assert receiver.has_video_frame
        if recv_frame_type & ReceiveFrameType.recv_audio:
            assert receiver.has_audio_frame
        if recv_frame_type & ReceiveFrameType.recv_metadata:
            assert receiver.has_metadata_frame
        try:
            worker.run()
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            self.stopped.set()

    def stop(self):
        """Stop the thread
        """
        cdef RecvThreadWorker w = self.worker
        w.stop()
        self.stopped.wait()

    def set_callback(self, cb):
        """Set the callback used to indicate new frames
        """
        cdef RecvThreadWorker w = self.worker
        w.callback.set_callback(cb)

    def set_wait_event(self):
        cdef RecvThreadWorker w = self.worker
        w.wait_event._set()

def test():
    from cyndilib.finder import Finder


    cdef str src_name = "BIRDDOG-1F8A1 (CAM)"
    finder = Finder()
    src = None
    # finder.open()
    i = 0
    while i<10:
        if i == 0:
            finder.update_sources()
        else:
            finder.wait_for_sources(3)
        for _src in finder.iter_sources():
            if 'CAM' in _src.name:
                src = _src
                break
        if src:
            break
        # src = finder.get_source(src_name)
        # if src:
        #     break
        print(i)
        sleep(1)
        i += 1
        # if not src:
        #     finder.wait()
        #     src = finder.get_source(src_name)
    print('src: ', src)
    print('closing finder')
    # finder.close()

    if not src:
        raise Exception('no source')

    print('building receiver')
    cdef ReceiveFrameType recv_type = ReceiveFrameType.recv_all #ReceiveFrameType.recv_video | ReceiveFrameType.recv_audio
    cdef Receiver receiver = Receiver(color_format=RecvColorFormat.RGBX_RGBA)

    cdef VideoRecvFrame vframe = VideoRecvFrame()
    cdef AudioRecvFrame aframe = AudioRecvFrame()
    receiver.set_audio_frame(aframe)
    receiver.set_video_frame(vframe)
    print('connecting src')
    receiver.connect_to(src)
    cdef ReceiveFrameType frame_type
    for i in range(10):
        print('recv.source_name: ', receiver.source_name)
        nc = receiver.get_num_connections()
        connected = receiver.is_connected()
        print(f'connected: {connected}, num_connections: {nc}')
        print('receive…')
        frame_type = receiver._receive(recv_type, 100)
        print('frame_type: ', frame_type)
        # if connected:
        #     break
        sleep(1)
    print('exit')
