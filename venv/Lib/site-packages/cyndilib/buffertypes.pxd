# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .wrapper cimport *


cdef struct audio_bfr_t:
    int64_t timecode
    int64_t timestamp
    size_t sample_rate
    size_t num_channels
    size_t num_samples
    size_t total_size
    bint valid
    audio_bfr_t* prev
    audio_bfr_t* next
    const float* p_data # unpacked float32 samples with shape [num_channels, num_samples]

cdef struct video_bfr_t:
    int64_t timecode
    int64_t timestamp
    float aspect
    FourCC fourcc
    FrameFormat format
    size_t line_stride
    size_t xres
    size_t yres
    size_t total_size
    bint valid
    video_bfr_t* prev
    video_bfr_t* next
    uint8_t* p_data

cdef struct metadata_bfr_t:
    int64_t timecode
    size_t length
    bint valid
    metadata_bfr_t* prev
    metadata_bfr_t* next
    char* p_data

ctypedef audio_bfr_t* audio_bfr_p
ctypedef video_bfr_t* video_bfr_p
ctypedef metadata_bfr_t* metadata_bfr_p

ctypedef fused av_frame_bfr_ft:
    audio_bfr_p
    video_bfr_p
    metadata_bfr_p

cdef audio_bfr_p audio_frame_bfr_create(audio_bfr_p parent) except NULL nogil
cdef video_bfr_p video_frame_bfr_create(video_bfr_p parent) except NULL nogil
cdef int av_frame_bfr_init(av_frame_bfr_ft bfr) except -1 nogil
cdef int av_frame_bfr_copy(av_frame_bfr_ft src, av_frame_bfr_ft dst) except -1 nogil
cdef size_t av_frame_bfr_count(av_frame_bfr_ft bfr) except -1 nogil
cdef av_frame_bfr_ft av_frame_bfr_get_head(av_frame_bfr_ft bfr) noexcept nogil
cdef av_frame_bfr_ft av_frame_bfr_get_tail(av_frame_bfr_ft bfr) noexcept nogil
cdef int av_frame_bfr_destroy(av_frame_bfr_ft bfr) except -1 nogil
cdef av_frame_bfr_ft av_frame_bfr_remove(av_frame_bfr_ft bfr) noexcept nogil
cdef int av_frame_bfr_free_parent(av_frame_bfr_ft bfr, bint single_step=*) except -1 nogil
cdef int av_frame_bfr_free_child(av_frame_bfr_ft bfr, bint single_step=*) except -1 nogil
