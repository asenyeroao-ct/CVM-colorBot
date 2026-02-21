cimport cython

cdef int frame_status_init(SendFrame_status_s_ft* ptr) except -1 nogil:
    ptr.data.num_buffers = MAX_FRAME_BUFFERS
    ptr.data.write_index = 0
    ptr.data.read_index = NULL_INDEX
    ptr.data.ndim = 0
    ptr.data.attached_to_sender = False
    cdef size_t i
    for i in range(3):
        ptr.data.shape[i] = 0
        ptr.data.strides[i] = 0
    for i in range(MAX_FRAME_BUFFERS):
        ptr.items[i].data.idx = i
        frame_status_item_init(&(ptr.items[i]))
    return 0

cdef int frame_status_item_init(SendFrame_item_s_ft* ptr) except -1 nogil:
    ptr.data.view_count = 0
    ptr.data.alloc_size = 0
    ptr.data.write_available = True
    ptr.data.read_available = False
    cdef size_t i
    for i in range(3):
        ptr.data.shape[i] = 0
        ptr.data.strides[i] = 0
    if ptr.frame_ptr is not NULL:
        return 0
    if SendFrame_item_s_ft is VideoSendFrame_item_s:
        ptr.frame_ptr = video_frame_create_default()
    elif SendFrame_item_s_ft is AudioSendFrame_item_s:
        ptr.frame_ptr = audio_frame_create_default()
    else:
        raise_exception('fused type is borked')
    if ptr.frame_ptr is NULL:
        raise_mem_err()
    return 0


cdef void frame_status_free(SendFrame_status_s_ft* ptr) noexcept nogil:
    cdef size_t i
    for i in range(MAX_FRAME_BUFFERS):
        frame_status_item_free(&(ptr.items[i]))
    ptr.data.write_index = 0
    ptr.data.read_index = NULL_INDEX


cdef void frame_status_item_free(SendFrame_item_s_ft* ptr) noexcept nogil:
    if ptr.frame_ptr is NULL:
        return
    frame_status_item_free_p_data(ptr)
    NDIlib_frame_type_ft_free(ptr.frame_ptr)
    # mem_free(ptr.frame_ptr)
    ptr.frame_ptr = NULL


cdef void NDIlib_frame_type_ft_free(NDIlib_frame_type_ft* frame_ptr) noexcept nogil:
    if NDIlib_frame_type_ft is NDIlib_video_frame_v2_t:
        video_frame_destroy(frame_ptr)
    elif NDIlib_frame_type_ft is NDIlib_audio_frame_v3_t:
        audio_frame_destroy(frame_ptr)
    else:
        pass


cdef int frame_status_copy_frame_ptr(
    SendFrame_status_s_ft* ptr,
    NDIlib_frame_type_ft* frame_ptr,
) except -1 nogil:

    cdef size_t i
    for i in range(MAX_FRAME_BUFFERS):
        frame_status_item_copy_frame_ptr(&(ptr.items[i]), frame_ptr)
    return 0


cdef int frame_status_item_copy_frame_ptr(
    SendFrame_item_s_ft* ptr,
    NDIlib_frame_type_ft* frame_ptr,
) except -1 nogil:
    if SendFrame_item_s_ft is VideoSendFrame_item_s and NDIlib_frame_type_ft is NDIlib_video_frame_v2_t:
        if ptr.frame_ptr is NULL:
            ptr.frame_ptr = video_frame_create_default()
        video_frame_copy(frame_ptr, ptr.frame_ptr)
    elif SendFrame_item_s_ft is AudioSendFrame_item_s and NDIlib_frame_type_ft is NDIlib_audio_frame_v3_t:
        if ptr.frame_ptr is NULL:
            ptr.frame_ptr = audio_frame_create_default()
        audio_frame_copy(frame_ptr, ptr.frame_ptr)
    else:
        raise_exception('fused type is borked')
    return 0


cdef int frame_status_alloc_p_data(SendFrame_status_s_ft* ptr) except -1 nogil:
    if ptr.data.ndim < 1 or ptr.data.ndim > 3:
        raise_withgil(PyExc_ValueError, 'ndim must be between 1 and 3')

    cdef size_t total_size = ptr.data.strides[ptr.data.ndim-1]
    cdef size_t i

    for i in range(ptr.data.ndim):
        total_size *= ptr.data.shape[i]

    if total_size == 0:
        raise_withgil(PyExc_ValueError, 'cannot create with size of zero')

    for i in range(MAX_FRAME_BUFFERS):
        frame_status_item_alloc_p_data(&(ptr.items[i]), total_size, ptr.data.shape, ptr.data.strides)
    return 0

cdef int frame_status_item_alloc_p_data(
    SendFrame_item_s_ft* ptr,
    size_t total_size,
    size_t[3] shape,
    size_t[3] strides,
) except -1 nogil:

    cdef size_t i
    for i in range(3):
        ptr.data.shape[i] = shape[i]
        ptr.data.strides[i] = strides[i]
    frame_status_item_free_p_data(ptr)
    ptr.frame_ptr.p_data = <uint8_t*>mem_alloc(sizeof(uint8_t) * total_size)
    if ptr.frame_ptr.p_data is NULL:
        raise_mem_err()
    ptr.data.alloc_size = total_size
    return 0

cdef void frame_status_item_free_p_data(SendFrame_item_s_ft* ptr) noexcept nogil:
    if ptr.frame_ptr.p_data is NULL:
        return
    if ptr.data.read_available:
        ptr.frame_ptr == NULL
    else:
        mem_free(ptr.frame_ptr.p_data)
        ptr.frame_ptr.p_data = NULL
    ptr.data.alloc_size = 0

cdef void frame_status_set_send_ready(SendFrame_status_s_ft* ptr) noexcept nogil:
    cdef size_t idx = ptr.data.write_index
    ptr.items[idx].data.write_available = False
    ptr.items[idx].data.read_available = True
    ptr.data.read_index = idx
    ptr.data.write_index = frame_status_get_next_write_index(ptr)

cdef size_t frame_status_get_next_write_index(
    SendFrame_status_s_ft* ptr,
) noexcept nogil:
    cdef size_t next_idx = ptr.data.write_index, i = 0
    while True:
        if ptr.items[next_idx].data.write_available:
            return next_idx
        with cython.cdivision(True):
            next_idx = (next_idx + 1) % MAX_FRAME_BUFFERS
        i += 1
        if i > MAX_FRAME_BUFFERS * 2:
            break
    return NULL_INDEX

cdef void frame_status_set_send_complete(
    SendFrame_status_s_ft* ptr,
    size_t idx,
) noexcept nogil:

    ptr.items[idx].data.write_available = True
    ptr.items[idx].data.read_available = False
    if ptr.data.read_index == idx:
        ptr.data.read_index = frame_status_get_next_read_index(ptr)


cdef size_t frame_status_get_next_read_index(
    SendFrame_status_s_ft* ptr,
) noexcept nogil:

    cdef size_t idx = ptr.data.read_index, i = 0
    if idx == NULL_INDEX:
        with cython.cdivision(True):
            idx = (ptr.data.write_index - 1) % MAX_FRAME_BUFFERS
    while True:
        if ptr.items[idx].data.read_available:
            return idx
        with cython.cdivision(True):
            idx = (idx + 1) % MAX_FRAME_BUFFERS
        i += 1
        if i > MAX_FRAME_BUFFERS * 2:
            break
    return NULL_INDEX
