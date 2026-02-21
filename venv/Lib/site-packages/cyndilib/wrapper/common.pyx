cdef int raise_withgil(PyObject *error, char *msg) except -1 with gil:
    raise (<object>error)(msg.decode('ascii'))

cdef int raise_exception(char *msg) except -1 nogil:
    raise_withgil(PyExc_Exception, msg)

cdef int raise_mem_err() except -1 nogil:
    raise_withgil(PyExc_MemoryError, b'')


cdef void* mem_alloc(size_t c) noexcept nogil:
    return malloc(c)

cdef void mem_free(void *p) noexcept nogil:
    free(p)
