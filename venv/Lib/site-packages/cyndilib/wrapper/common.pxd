# cython: language_level=3
# distutils: language = c++

from libc.stdlib cimport malloc, free

cdef extern from 'Python.h':
    ctypedef struct PyObject
    PyObject *PyExc_Exception
    PyObject *PyExc_RuntimeError
    PyObject *PyExc_KeyError
    PyObject *PyExc_IndexError
    PyObject *PyExc_ValueError
    PyObject *PyExc_TypeError
    PyObject *PyExc_MemoryError
    PyObject *PyExc_ZeroDivisionError


cdef int raise_withgil(PyObject *error, char *msg) except -1 with gil
cdef int raise_exception(char *msg) except -1 nogil
cdef int raise_mem_err() except -1 nogil
cdef void* mem_alloc(size_t c) noexcept nogil
cdef void mem_free(void *p) noexcept nogil
