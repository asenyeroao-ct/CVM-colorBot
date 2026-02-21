# cython: language_level=3
# distutils: language = c++

cdef class Callback:
    cdef bint has_callback
    cdef bint is_weakref
    cdef object cb, weak_cb

    cdef int set_callback(self, object cb) except -1
    cdef int remove_callback(self) except -1
    cdef int trigger_callback(self) except -1

cdef class WeakMethod:
    cdef object obj_ref, func_ref, meth_type
    cdef bint alive

    cdef bint trigger_callback(self) except -1
