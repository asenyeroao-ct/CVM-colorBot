# cython: language_level=3
# distutils: language = c++

# from .ndi_dynload cimport *
# cdef extern from "Processing.NDI.DynamicLoad.h" nogil:
cdef extern from * nogil:

    cdef struct NDIlib_v5:
        pass

# cdef extern from * nogil:
#     """
#     #ifndef NDILIB_CPP_DEFAULT_VALUE
#     #    ifdef __cplusplus
#     #        define NDILIB_CPP_DEFAULT_VALUE(a) =(a)
#     #    else // __cplusplus
#     #        define NDILIB_CPP_DEFAULT_VALUE(a)
#     #    endif // __cplusplus
#     #endif // NDILIB_CPP_DEFAULT_VALUE
#
#     """

cdef extern from 'Processing.NDI.Lib.h' nogil:
    void NDILIB_CPP_DEFAULT_VALUE(long a)
    const char* NDIlib_version()

    # cdef struct NDIlib_v5

    const NDIlib_v5* NDIlib_v5_load()

# cdef inline const NDIlib_v5* lib_v5_load():
#     return NDIlib_v5_load()
