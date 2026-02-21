
__all__ = ('RecvBandwidth', 'RecvColorFormat')

cdef NDIlib_recv_create_v3_t* recv_t_create() except NULL nogil:
    cdef NDIlib_recv_create_v3_t* p = <NDIlib_recv_create_v3_t*>mem_alloc(sizeof(NDIlib_recv_create_v3_t))
    if p is NULL:
        raise_mem_err()
    return p

cdef NDIlib_recv_create_v3_t* recv_t_create_default() except NULL nogil:
    cdef NDIlib_recv_create_v3_t* p = recv_t_create()
    p.source_to_connect_to.p_ndi_name = NULL
    p.source_to_connect_to.p_url_address = NULL
    p.color_format = recv_format_cast(RecvColorFormat.UYVY_BGRA)
    p.bandwidth = recv_bandwidth_cast(RecvBandwidth.highest)
    p.allow_video_fields = True
    p.p_ndi_recv_name = NULL
    return p

cdef int recv_t_copy(NDIlib_recv_create_v3_t* src, NDIlib_recv_create_v3_t* dest) except -1 nogil:
    dest.source_to_connect_to = src.source_to_connect_to
    dest.color_format = src.color_format
    dest.bandwidth = src.bandwidth
    dest.allow_video_fields = src.allow_video_fields
    dest.p_ndi_recv_name = src.p_ndi_recv_name
    return 0


cdef void recv_t_destroy(NDIlib_recv_create_v3_t* p) noexcept nogil:
    if p is not NULL:
        mem_free(p)
