# cython: language_level=3
# distutils: language = c++

cdef struct rational_t:
    int numerator
    int denominator

ctypedef rational_t frame_rate_t

ctypedef fused frame_rate_ft:
    frame_rate_t
    int[2]


ctypedef float float32_t
ctypedef double float64_t
ctypedef long double float128_t
ctypedef Py_ssize_t Py_intptr_t
