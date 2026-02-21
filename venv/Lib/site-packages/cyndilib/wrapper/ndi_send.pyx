
cdef NDIlib_send_create_t* send_t_create(
    const char* ndi_name,
    const char* groups
) except NULL nogil:
    cdef NDIlib_send_create_t* p = <NDIlib_send_create_t*>mem_alloc(sizeof(NDIlib_send_create_t))
    if p is NULL:
        raise_mem_err()
    send_t_initialize(p, ndi_name, groups)
    return p

cdef void send_t_initialize(
    NDIlib_send_create_t* p,
    const char* ndi_name,
    const char* groups,
) noexcept nogil:
    p.p_ndi_name = ndi_name
    p.p_groups = groups
    p.clock_video = True
    p.clock_audio = True


cdef void send_t_destroy(NDIlib_send_create_t* p) noexcept nogil:
    if p is not NULL:
        mem_free(p)
