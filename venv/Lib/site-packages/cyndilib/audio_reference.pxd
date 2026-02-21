# cython: language_level=3
# distutils: language = c++

from .wrapper.ndi_structs cimport NDIlib_audio_frame_v3_t



cpdef enum AudioReference:
    """An enum for |NDI| Audio Reference Levels

    The member values correspond to the :term:`normalized <normalized audio>`
    (+/- 1.0) values described in the :ref:`guide_audio_dynamic_range` section of the
    documentation.

    Attributes:
        dBu (int): Reference for :term:`dBu` (+4 dB)
        dBVU (int): Reference for :term:`dBVU` (0 dB)
        dBFS_smpte (int): Reference for :term:`dBFS` (SMPTE) (-20 dB)
        dBFS_ebu (int): Reference for :term:`dBFS` (EBU) (-14 dB)


    .. versionadded:: 0.0.8

    """
    dBu = 4
    dBVU = 0
    dBFS_smpte = -20
    dBFS_ebu = -14


cdef struct AudioReference_s:
    AudioReference reference
    double value
    double multiplier
    double divisor




cdef class AudioReferenceConverter:
    cdef AudioReference_s* ptr

    cdef int _set_reference(self, AudioReference reference) except -1 nogil
    cdef bint _is_ndi_native(self) noexcept nogil
    cdef double _calc_amplitude(self, double value_dB) noexcept nogil
    cdef double _calc_dB(self, double value_amplitude) except? 100 nogil
    cdef double _get_scale(self, AudioReference other) noexcept nogil
    cdef double _to_other(self, AudioReference other, double value, bint force=*) noexcept nogil
    cdef int _to_other_array_in_place(self, AudioReference other, float[:,:] value, bint force=*) except -1 nogil
    cdef int _to_other_array(
        self,
        AudioReference other,
        float[:,:] src,
        float[:,:] dst
    ) except -1 nogil
    cdef int _to_ndi_array(self, float[:,:] src, float[:,:] dest) except -1 nogil
    cdef int _from_ndi_array(self, float[:,:] src, float[:,:] dest) except -1 nogil
    cdef int _to_ndi_float_ptr(self, float[:,:] src, float *dest) except -1 nogil
    cdef int _to_ndi_frame_in_place(self, NDIlib_audio_frame_v3_t* frame) except -1 nogil
    cdef int _from_ndi_float_ptr(self, float *src, float[:,:] dest) except -1 nogil
    cdef int _from_ndi_frame_in_place(self, NDIlib_audio_frame_v3_t* frame) except -1 nogil
