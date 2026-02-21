# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
"""
Utilities for handling |NDI| audio reference levels.

.. versionadded:: 0.0.8

"""

cimport cython
from libc.math cimport log10

from cyndilib.wrapper.common cimport raise_withgil, PyExc_ValueError

__all__ = ('AudioReference', 'AudioReferenceConverter')



cdef AudioReference_s AUDIO_REFERENCES[4]
AUDIO_REFERENCES[0].reference = AudioReference.dBu
AUDIO_REFERENCES[1].reference = AudioReference.dBVU
AUDIO_REFERENCES[2].reference = AudioReference.dBFS_smpte
AUDIO_REFERENCES[3].reference = AudioReference.dBFS_ebu


cdef double AudioReference_s_calc_amplitude(AudioReference_s* ptr, double value_dB) noexcept nogil:
    return 10 ** ((value_dB - ptr.value) / 20.0)


cdef double AudioReference_s_calc_dB(AudioReference_s* ptr, double value_amplitude) except? 100 nogil:
    return 20 * log10(value_amplitude) + ptr.value


cdef int AudioReference_s_init(AudioReference_s* ptr, AudioReference reference) except -1 nogil:
    ptr.reference = reference
    ptr.value = <double>reference
    ptr.multiplier = AudioReference_s_calc_amplitude(ptr, 0.0)
    ptr.divisor = 1.0 / ptr.multiplier
    return 0


cdef AudioReference_s* AudioReference_s_get(AudioReference reference) except NULL nogil:
    cdef AudioReference_s* ptr
    cdef size_t i
    for i in range(4):
        ptr = &AUDIO_REFERENCES[i]
        if ptr.reference == reference:
            return ptr
    raise_withgil(PyExc_ValueError, "Invalid AudioReference")


cdef int _init_all_references() except -1:
    cdef AudioReference_s* ptr
    cdef AudioReference reference
    cdef size_t i
    for i in range(4):
        ptr = &AUDIO_REFERENCES[i]
        AudioReference_s_init(ptr, ptr.reference)
    return 0


_init_all_references()




cdef class AudioReferenceConverter:
    """Convert between different |NDI| :class:`AudioReference` levels.


    .. versionadded:: 0.0.8

    """
    def __cinit__(self, *args, **kwargs):
        self.ptr = NULL

    def __init__(self, AudioReference reference = AudioReference.dBVU):
        cdef AudioReference_s* ptr = AudioReference_s_get(reference)
        self.ptr = ptr

    def __dealloc__(self):
        self.ptr = NULL

    @property
    def reference(self):
        """The :class:`AudioReference` for this converter."""
        return self.ptr.reference
    @reference.setter
    def reference(self, AudioReference reference):
        self._set_reference(reference)

    @property
    def is_ndi_native(self):
        """Check if the current :attr:`reference` level is the native |NDI| level.
        """
        return self._is_ndi_native()

    cdef bint _is_ndi_native(self) noexcept nogil:
        return self.ptr.reference == AudioReference.dBVU

    cdef int _set_reference(self, AudioReference reference) except -1 nogil:
        cdef AudioReference_s* ptr = AudioReference_s_get(reference)
        self.ptr = ptr
        return 0

    @property
    def value(self):
        """The dB value of the :attr:`reference` level.
        """
        return self.ptr.value

    @property
    def multiplier(self):
        """The value to convert from |NDI| levels to the current :attr:`reference` level.

        This is calculated as:

        >>> multiplier = self.calc_amplitude(0.0)

        """
        return self.ptr.multiplier

    @property
    def divisor(self):
        """The value to convert from the current :attr:`reference` level to |NDI| levels.

        This is calculated as:

        >>> divisor = 1 / self.multiplier

        """
        return self.ptr.divisor

    def calc_amplitude(self, double value_dB):
        r"""Calculate the amplitude from a dB value, taking into account the
        :attr:`reference` level.

        This is calculated as:

        .. math::

            A = 10 ^ {\frac{dB - V_{ref}}{20}}

        where :math:`V_{ref}` is the dB value of the current :attr:`reference` level
        and :math:`dB` is the input `value_dB`.
        """
        return self._calc_amplitude(value_dB)

    cdef double _calc_amplitude(self, double value_dB) noexcept nogil:
        return AudioReference_s_calc_amplitude(self.ptr, value_dB)

    def calc_dB(self, double value_amplitude):
        r"""Calculate the dB value from an amplitude, taking into account the
        :attr:`reference` level.

        This is calculated as:

        .. math::

            dB = 20 * log_{10}(A) + V_{ref}

        where :math:`V_{ref}` is the dB value of the current :attr:`reference` level
        and :math:`A` is the input `value_amplitude`.
        """
        return self._calc_dB(value_amplitude)

    cdef double _calc_dB(self, double value_amplitude) except? 100 nogil:
        return AudioReference_s_calc_dB(self.ptr, value_amplitude)

    def to_other(self, AudioReference other, double value, bint force = False):
        r"""Convert an amplitude value from the current :attr:`reference` level to
        another reference level.

        This is calculated as:

        .. math::

            V_{o} = V \cdot \frac{M_{o}}{D_{s}}


        where :math:`M_{o}` is the :attr:`multiplier` of this instance,
        :math:`D_{s}` is the :attr:`divisor` of *other*, :math:`V` is the input value,
        and :math:`V_{o}` is the output value.
        """
        return self._to_other(other, value, force)

    cdef double _get_scale(self, AudioReference other) noexcept nogil:
        cdef AudioReference_s* other_ptr = AudioReference_s_get(other)
        return other_ptr.multiplier * self.ptr.divisor

    cdef double _to_other(self, AudioReference other, double value, bint force = False) noexcept nogil:
        if self.ptr.reference == other and not force:
            return value
        cdef double scale = self._get_scale(other)
        return value * scale

    def to_other_array(
        self,
        AudioReference other,
        float[:,:] src,
        float[:,:] dst
    ):
        """Convert a 2D array of values from the current :attr:`reference` level to another.

        Arguments:
            other: The target :class:`AudioReference` level.
            src: The 2D source array of values.
            dst: The 2D destination array for the converted values.
        """
        self._to_other_array(other, src, dst)

    cdef int _to_other_array(
        self,
        AudioReference other,
        float[:,:] src,
        float[:,:] dst
    ) except -1 nogil:
        cdef double scale = self._get_scale(other)
        copy_scale_array(src, dst, scale)
        return 0

    def to_other_array_in_place(self, AudioReference other, float[:,:] value, bint force = False):
        """Convert a 2D array of values from the current :attr:`reference` level to another.

        This is an in-place conversion.

        Arguments:
            other: The target :class:`AudioReference` level.
            value: The 2D array of values to convert.
            force (bool, optional): Whether to force the conversion even if the levels are the same.
                Default is False.  (This is mainly used for testing)
        """
        self._to_other_array_in_place(other, value, force)

    cdef int _to_other_array_in_place(self, AudioReference other, float[:,:] value, bint force = False) except -1 nogil:
        cdef double scale = self._get_scale(other)
        copy_scale_array(value, value, scale)
        return 0

    def to_ndi_array(self, float[:,:] src, float[:,:] dest):
        """Convert a 2D array of values to |NDI| levels.

        Arguments:
            src: The 2D source array of values.
            dest: The 2D destination array for the converted values.
        """
        self._to_ndi_array(src, dest)

    cdef int _to_ndi_array(self, float[:,:] src, float[:,:] dest) except -1 nogil:
        if self._is_ndi_native():
            dest[...] = src
            return 0
        cdef double scale = self.ptr.multiplier
        copy_scale_array(src, dest, scale)
        return 0

    cdef int _to_ndi_float_ptr(self, float[:,:] src, float *dest) except -1 nogil:
        cdef double scale = self.ptr.multiplier
        cdef size_t nrows = src.shape[0], ncols = src.shape[1], i, j, k = 0
        for i in range(nrows):
            for j in range(ncols):
                dest[k] = src[i,j] * scale
                k += 1
        return 0

    cdef int _to_ndi_frame_in_place(self, NDIlib_audio_frame_v3_t* frame) except -1 nogil:
        if self._is_ndi_native():
            return 0
        cdef double scale = self.ptr.multiplier
        cdef size_t nrows = frame.no_channels, ncols = frame.no_samples, i, j
        cdef float* data = <float*>frame.p_data
        for i in range(nrows):
            for j in range(ncols):
                data[i * ncols + j] *= scale
        return 0

    def from_ndi_array(self, float[:,:] src, float[:,:] dest):
        """Convert a 2D array of values from |NDI| levels.

        Arguments:
            src: The 2D source array of values.
            dest: The 2D destination array for the converted values.
        """
        self._from_ndi_array(src, dest)

    cdef int _from_ndi_array(self, float[:,:] src, float[:,:] dest) except -1 nogil:
        if self._is_ndi_native():
            dest[...] = src
            return 0
        cdef double scale = self.ptr.divisor
        copy_scale_array(src, dest, scale)
        return 0

    cdef int _from_ndi_float_ptr(self, float *src, float[:,:] dest) except -1 nogil:
        cdef double scale = self.ptr.divisor
        cdef size_t nrows = dest.shape[0], ncols = dest.shape[1], i, j, k = 0
        for i in range(nrows):
            for j in range(ncols):
                dest[i,j] = src[k] * scale
                k += 1
        return 0

    cdef int _from_ndi_frame_in_place(self, NDIlib_audio_frame_v3_t* frame) except -1 nogil:
        if self._is_ndi_native():
            return 0
        cdef double scale = self.ptr.divisor
        cdef size_t nrows = frame.no_channels, ncols = frame.no_samples, i, j
        cdef float* data = <float*>frame.p_data
        for i in range(nrows):
            for j in range(ncols):
                data[i * ncols + j] *= scale
        return 0

    def __repr__(self):
        return f"<AudioReferenceConverter reference={self.reference} value={self.value}>"

    def __str__(self):
        return str(self.reference)



cdef int copy_scale_array(
    float[:,:] src,
    float[:,:] dest,
    double scale
) except -1 nogil:
    cdef size_t nrows = src.shape[0], ncols = src.shape[1], i, j
    for i in range(nrows):
        for j in range(ncols):
            dest[i,j] = src[i,j] * scale
    return 0
