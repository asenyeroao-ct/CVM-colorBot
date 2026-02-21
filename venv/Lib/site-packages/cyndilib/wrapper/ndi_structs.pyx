from libc.math cimport llround

__all__ = ('FrameType', 'FourCC', 'FrameFormat', 'get_ndi_version')


def get_ndi_version():
    return NDIlib_version().decode('UTF-8')


cdef double ndi_time_to_posix(int64_t ndi_ts) noexcept nogil:
    cdef float128_t result = <float128_t>ndi_ts * 1e-7
    return <double>result

cdef int64_t posix_time_to_ndi(double ts) noexcept nogil:
    cdef long long result = llround(ts * 1e7)
    return result

cdef NDIlib_source_t* source_create() except NULL nogil:
    cdef NDIlib_source_t* p = <NDIlib_source_t*>mem_alloc(sizeof(NDIlib_source_t))
    if p is NULL:
        raise_mem_err()
    p.p_ndi_name = NULL
    p.p_url_address = NULL
    return p

cdef void source_destroy(NDIlib_source_t* p) noexcept nogil:
    if p is not NULL:
        mem_free(p)

cdef NDIlib_video_frame_v2_t* video_frame_create() except NULL nogil:
    cdef NDIlib_video_frame_v2_t* p = <NDIlib_video_frame_v2_t*>mem_alloc(sizeof(NDIlib_video_frame_v2_t))
    if p is NULL:
        raise_mem_err()
    return p

cdef NDIlib_video_frame_v2_t* video_frame_create_default() except NULL nogil:
    cdef NDIlib_video_frame_v2_t* p = video_frame_create()
    p.xres = 0
    p.yres = 0
    p.FourCC = fourcc_type_cast(FourCC.UYVY)
    p.frame_rate_N = 30000
    p.frame_rate_D = 1001
    p.picture_aspect_ratio = 0
    p.frame_format_type = frame_format_cast(FrameFormat.progressive)
    p.timecode = NDIlib_send_timecode_synthesize
    p.p_data = NULL
    p.line_stride_in_bytes = 0
    p.p_metadata = NULL
    p.timestamp = 0
    return p

cdef int video_frame_copy(
    NDIlib_video_frame_v2_t* src,
    NDIlib_video_frame_v2_t* dest
) except -1 nogil:
    dest.xres = src.xres
    dest.yres = src.yres
    dest.FourCC = src.FourCC
    dest.line_stride_in_bytes = src.line_stride_in_bytes
    dest.frame_rate_N = src.frame_rate_N
    dest.frame_rate_D = src.frame_rate_D
    dest.picture_aspect_ratio = src.picture_aspect_ratio
    dest.frame_format_type = src.frame_format_type
    dest.timecode = src.timecode
    dest.timestamp = src.timestamp
    return 0


cdef void video_frame_destroy(NDIlib_video_frame_v2_t* p) noexcept nogil:
    pass
    # if p is not NULL:
    #     if p.p_data is not NULL:
    #         mem_free(p.p_data)
    #         p.p_data = NULL
    #     # if p.p_metadata is not NULL:
    #     #     mem_free(p.p_metadata)
    #     #     # p.p_metadata = NULL
    #     mem_free(p)


cdef NDIlib_audio_frame_v3_t* audio_frame_create() except NULL nogil:
    cdef NDIlib_audio_frame_v3_t* p = <NDIlib_audio_frame_v3_t*>mem_alloc(sizeof(NDIlib_audio_frame_v3_t))
    if p is NULL:
        raise_mem_err()
    return p

cdef NDIlib_audio_frame_v3_t* audio_frame_create_default() except NULL nogil:
    cdef NDIlib_audio_frame_v3_t* p = audio_frame_create()
    p.sample_rate = 48000
    p.no_channels = 2
    p.no_samples = 0
    p.timecode = NDIlib_send_timecode_synthesize
    p.FourCC = NDIlib_FourCC_audio_type_FLTP
    p.channel_stride_in_bytes = 0
    p.timestamp = 0
    p.p_data = NULL
    return p

cdef int audio_frame_copy(
    NDIlib_audio_frame_v3_t* src,
    NDIlib_audio_frame_v3_t* dest
) except -1 nogil:
    dest.sample_rate = src.sample_rate
    dest.no_channels = src.no_channels
    dest.no_samples = src.no_samples
    dest.timecode = src.timecode
    dest.FourCC = src.FourCC
    dest.channel_stride_in_bytes = src.channel_stride_in_bytes
    dest.timestamp = src.timestamp
    return 0


cdef void audio_frame_destroy(NDIlib_audio_frame_v3_t* p) noexcept nogil:
    pass
    # if p is not NULL:
    #     if p.p_data is not NULL:
    #         mem_free(p.p_data)
    #         p.p_data = NULL
    #     # if p.p_metadata is not NULL:
    #     #     mem_free(p.p_metadata)
    #     #     # p.p_metadata = NULL
    #     mem_free(p)

cdef NDIlib_metadata_frame_t* metadata_frame_create() except NULL nogil:
    cdef NDIlib_metadata_frame_t* p = <NDIlib_metadata_frame_t*>mem_alloc(sizeof(NDIlib_metadata_frame_t))
    if p is NULL:
        raise_mem_err()
    p.length = 0
    p.timecode = NDIlib_send_timecode_synthesize
    p.p_data = NULL
    return p

cdef void metadata_frame_destroy(NDIlib_metadata_frame_t* p) noexcept nogil:
    pass
    # if p is not NULL:
    #     if p.p_data is not NULL:
    #         mem_free(p.p_data)
    #         p.p_data = NULL
    #     mem_free(p)

cdef FourCCPackInfo* fourcc_pack_info_create() except NULL nogil:
    cdef FourCCPackInfo* p = <FourCCPackInfo*>mem_alloc(sizeof(FourCCPackInfo))
    if p is NULL:
        raise_mem_err()
    fourcc_pack_info_init(p)
    return p

cdef void fourcc_pack_info_init(FourCCPackInfo* p) noexcept nogil:
    cdef size_t i
    p.fourcc = FourCC.UYVY
    p.xres = 0
    p.yres = 0
    p.bits_per_pixel = 16
    p.padded_bits_per_pixel = 16
    p.padded_bytes_per_line = 0
    p.total_bits = 0
    p.num_planes = 0
    p.total_size = 0
    for i in range(4):
        p.line_strides[i] = 0
        p.stride_offsets[i] = 0

cdef int fourcc_pack_info_destroy(FourCCPackInfo* p) except -1 nogil:
    if p is not NULL:
        mem_free(p)
    return 0


cdef FourCCPackInfo* get_fourcc_pack_info(FourCC fourcc, size_t xres, size_t yres) except NULL nogil:
    cdef FourCCPackInfo* p = fourcc_pack_info_create()
    p.fourcc = fourcc
    p.xres = xres
    p.yres = yres
    calc_fourcc_pack_info(p)
    return p


cdef int calc_fourcc_pack_info(FourCCPackInfo* p, size_t frame_line_stride=0) except -1 nogil:
    cdef size_t xres = p.xres, yres = p.yres
    cdef uint32_t chroma_width, chroma_height
    cdef uint8_t padded_bits_per_pixel = 0
    cdef int16_t padded_bytes_per_line = 0
    cdef size_t expected_line_stride = 0
    cdef size_t total_size = 0, i

    for i in range(4):
        p.line_strides[i] = 0
        p.stride_offsets[i] = 0

    # 4:2:2 YUVY
    if p.fourcc == FourCC.UYVY:
        p.num_planes = 1
        p.bits_per_pixel = 16
        chroma_width = xres >> 1
        chroma_height = yres
        expected_line_stride = sizeof(uint8_t) * xres + (sizeof(uint8_t) * chroma_width) * 2
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.total_size = p.line_strides[0] * yres

    # 4:2:2:4 YUVA + alpha plane
    elif p.fourcc == FourCC.UYVA:
        p.num_planes = 2
        p.bits_per_pixel = 24
        chroma_width = xres >> 1
        chroma_height = yres
        expected_line_stride = sizeof(uint8_t) * (xres + chroma_width * 2)
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.line_strides[1] = sizeof(uint8_t) * xres + padded_bytes_per_line
        p.stride_offsets[1] = p.line_strides[0] * yres
        p.total_size = p.stride_offsets[1] + p.line_strides[1] * yres

    # 4:2:2 <uint16_t>Y + <uint16_t>UV
    elif p.fourcc == FourCC.P216:
        p.num_planes = 2
        p.bits_per_pixel = 24
        chroma_width = xres >> 1
        chroma_height = yres
        expected_line_stride = sizeof(uint16_t) * xres
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.line_strides[1] = sizeof(uint16_t) * chroma_width * 2 + padded_bytes_per_line
        p.stride_offsets[1] = p.line_strides[0] * yres
        p.total_size = p.stride_offsets[1] + p.line_strides[1] * chroma_height

    # 4:2:2:4 <uint16_t>Y + <uint16_t>UV + <uint16_t>A
    elif p.fourcc == FourCC.PA16:
        p.num_planes = 3
        p.bits_per_pixel = 48
        chroma_width = xres >> 1
        chroma_height = yres
        expected_line_stride = sizeof(uint16_t) * xres
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.line_strides[1] = sizeof(uint16_t) * chroma_width * 2 + padded_bytes_per_line
        p.line_strides[2] = sizeof(uint16_t) * xres + padded_bytes_per_line
        p.stride_offsets[1] = p.line_strides[0] * yres
        p.stride_offsets[2] = p.stride_offsets[1] + p.line_strides[1] * chroma_height
        p.total_size = p.stride_offsets[2] + p.line_strides[2] * yres

    # 4:2:0 <uint8_t>Y + <uint8_t>V + <uint8_t>U
    # * in I420 the V and U planes are swapped
    elif p.fourcc == FourCC.YV12 or p.fourcc == FourCC.I420:
        p.num_planes = 3
        p.bits_per_pixel = 12
        chroma_width = xres >> 1
        chroma_height = yres >> 1
        expected_line_stride = sizeof(uint8_t) * xres
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.line_strides[1] = sizeof(uint8_t) * chroma_width + padded_bytes_per_line
        p.line_strides[2] = sizeof(uint8_t) * chroma_width + padded_bytes_per_line
        p.stride_offsets[1] = p.line_strides[0] * yres
        p.stride_offsets[2] = p.stride_offsets[1] + p.line_strides[1] * chroma_height
        p.total_size = p.stride_offsets[2] + p.line_strides[2] * chroma_height

    # 4:2:0 <uint8_t>Y + <uint8_t>UV
    elif p.fourcc == FourCC.NV12:
        p.num_planes = 2
        p.bits_per_pixel = 12
        chroma_width = xres >> 1
        chroma_height = yres >> 1
        expected_line_stride = sizeof(uint8_t) * xres
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.line_strides[1] = sizeof(uint8_t) * chroma_width * 2 + padded_bytes_per_line
        p.stride_offsets[1] = p.line_strides[0] * yres
        p.total_size = p.stride_offsets[1] + p.line_strides[1] * chroma_height

    # 4:4:4:4 RGB0/RGBA
    elif p.fourcc == FourCC.BGRA or p.fourcc == FourCC.BGRX or p.fourcc == FourCC.RGBA or p.fourcc == FourCC.RGBX:
        p.num_planes = 1
        if p.fourcc == FourCC.BGRA or p.fourcc == RGBA:
            p.bits_per_pixel = 32
        else:
            p.bits_per_pixel = 24
            padded_bits_per_pixel = 32
        expected_line_stride = sizeof(uint8_t) * xres * 4
        if frame_line_stride:
            padded_bytes_per_line = frame_line_stride - expected_line_stride
            p.line_strides[0] = frame_line_stride
        else:
            p.line_strides[0] = expected_line_stride
        p.total_size = p.line_strides[0] * yres
    else:
        raise_withgil(PyExc_ValueError, 'Unknown FourCC type')

    if padded_bits_per_pixel == 0:
        padded_bits_per_pixel = p.bits_per_pixel
    p.padded_bits_per_pixel = padded_bits_per_pixel
    p.padded_bytes_per_line = padded_bytes_per_line
    p.total_bits = p.padded_bits_per_pixel * xres * yres
    return 0
