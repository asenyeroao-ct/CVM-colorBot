# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *
from libcpp.string cimport string as cpp_string

from .wrapper cimport *

cdef class MetadataFrame:
    cdef NDIlib_metadata_frame_t* ptr
    cdef cpp_string xml_bytes
    cdef readonly str tag
    cdef readonly dict attrs
    cdef char* _get_data(self) nogil
    cdef void _set_data(self, char* data) nogil
    cdef int64_t _get_timecode(self) nogil
    cdef void _set_timecode(self, int64_t value) nogil

cdef class MetadataRecvFrame(MetadataFrame):
    cdef bint can_receive(self) except -1 nogil
    cdef int _prepare_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1
    cdef int _process_incoming(self, NDIlib_recv_instance_t recv_ptr) except -1

cdef class MetadataSendFrame(MetadataFrame):
    cdef bint _serialize(self) except -1
    cdef int _update(self, dict other) except -1
    cdef int _clear(self) except -1
