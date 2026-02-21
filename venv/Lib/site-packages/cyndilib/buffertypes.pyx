

cdef audio_bfr_p audio_frame_bfr_create(audio_bfr_p parent) except NULL nogil:
    if parent is not NULL and parent.next is not NULL:
        raise_withgil(PyExc_ValueError, 'next pointer already exists')

    cdef audio_bfr_p bfr = <audio_bfr_p>mem_alloc(sizeof(audio_bfr_t))
    if bfr is NULL:
        raise_mem_err()
    av_frame_bfr_init(bfr)
    if parent is not NULL:
        bfr.prev = parent
        parent.next = bfr
    return bfr


cdef video_bfr_p video_frame_bfr_create(video_bfr_p parent) except NULL nogil:
    if parent is not NULL and parent.next is not NULL:
        raise_withgil(PyExc_ValueError, 'next pointer already exists')

    cdef video_bfr_p bfr = <video_bfr_p>mem_alloc(sizeof(video_bfr_t))
    if bfr is NULL:
        raise_mem_err()

    av_frame_bfr_init(bfr)

    if parent is not NULL:
        bfr.prev = parent
        parent.next = bfr

    return bfr


cdef int av_frame_bfr_init(av_frame_bfr_ft bfr) except -1 nogil:
    bfr.next = NULL
    bfr.prev = NULL
    bfr.timecode = 0
    bfr.valid = False
    bfr.p_data = NULL
    if av_frame_bfr_ft is audio_bfr_p:
        bfr.timestamp = 0
        bfr.sample_rate = 0
        bfr.num_channels = 0
        bfr.num_samples = 0
        bfr.total_size = 0
    elif av_frame_bfr_ft is video_bfr_p:
        bfr.timestamp = 0
        bfr.aspect = 0
        bfr.xres = 0
        bfr.yres = 0
        bfr.line_stride = 0
        bfr.total_size = 0
        bfr.fourcc = FourCC.UYVA
        bfr.format = FrameFormat.progressive
    elif av_frame_bfr_ft is metadata_bfr_p:
        bfr.length = 0
    return 0

cdef int av_frame_bfr_copy(av_frame_bfr_ft src, av_frame_bfr_ft dst) except -1 nogil:
    dst.timecode = src.timecode
    if av_frame_bfr_ft is audio_bfr_p:
        dst.timestamp = src.timestamp
        dst.sample_rate = src.sample_rate
        dst.num_channels = src.num_channels
        dst.num_samples = src.num_channels
        dst.total_size = src.total_size
    elif av_frame_bfr_ft is video_bfr_p:
        dst.timestamp = src.timestamp
        dst.aspect = src.aspect
        dst.xres = src.xres
        dst.yres = src.yres
        dst.line_stride = src.line_stride
        dst.total_size = src.total_size
        dst.fourcc = src.fourcc
        dst.format = src.format
    elif av_frame_bfr_ft is metadata_bfr_p:
        dst.length = src.length
    return 0

cdef size_t av_frame_bfr_count(av_frame_bfr_ft bfr) except -1 nogil:
    cdef size_t r = 1
    if bfr is NULL:
        return r
    bfr = av_frame_bfr_get_head(bfr)
    while bfr.next is not NULL:
        bfr = bfr.next
        r += 1
    return r
    # cdef av_frame_bfr_ft tmp = bfr
    # while tmp.next is not NULL:
    #     tmp = tmp.next
    #     r += 1
    # tmp = bfr
    # while tmp.prev is


cdef av_frame_bfr_ft av_frame_bfr_get_head(av_frame_bfr_ft bfr) noexcept nogil:
    cdef av_frame_bfr_ft result = bfr
    while result.prev is not NULL:
        result = result.prev
    return result

cdef av_frame_bfr_ft av_frame_bfr_get_tail(av_frame_bfr_ft bfr) noexcept nogil:
    cdef av_frame_bfr_ft result = bfr
    while result.next is not NULL:
        result = result.next
    return result

cdef int av_frame_bfr_destroy(av_frame_bfr_ft bfr) except -1 nogil:
    if bfr.prev is not NULL:
        av_frame_bfr_free_parent(bfr, False)
    if bfr.next is not NULL:
        av_frame_bfr_free_child(bfr, False)
    av_frame_bfr_free_single(bfr)
    return 0

cdef av_frame_bfr_ft av_frame_bfr_remove(av_frame_bfr_ft bfr) noexcept nogil:
    cdef av_frame_bfr_ft parent = bfr.prev
    cdef av_frame_bfr_ft child = bfr.next
    bfr.prev = NULL
    bfr.next = NULL
    av_frame_bfr_free_single(bfr)
    if parent is not NULL and child is not NULL:
        parent.next = child
        child.prev = parent
    elif parent is not NULL:
        return parent
    elif child is not NULL:
        return child
    return NULL

cdef void av_frame_bfr_free_single(av_frame_bfr_ft bfr) noexcept nogil:
    cdef size_t data_size
    if bfr.p_data is not NULL:
        # if av_frame_bfr_ft is audio_bfr_p:
        #     data_size = sizeof(float) * bfr.num_channels * bfr.num_samples
        if av_frame_bfr_ft is video_bfr_p:
            # data_size = bfr.total_size
            mem_free(bfr.p_data)
            bfr.p_data = NULL

        # elif av_frame_bfr_ft is metadata_bfr_p:
        #     data_size = sizeof(char) * bfr.length
    mem_free(bfr)

cdef int av_frame_bfr_free_parent(av_frame_bfr_ft bfr, bint single_step=True) except -1 nogil:
    if bfr.prev is NULL:
        raise_withgil(PyExc_ValueError, 'no parent bfr')
    cdef av_frame_bfr_ft parent = bfr.prev
    bfr.prev = NULL
    if parent.prev is not NULL:
        if single_step:
            raise_withgil(PyExc_ValueError, 'parent has more reverse links')
        else:
            if parent.prev.prev is NULL:
                av_frame_bfr_remove(parent.prev)
            else:
                av_frame_bfr_free_parent(parent, single_step)
            parent.next = NULL
    bfr.prev = NULL
    av_frame_bfr_free_single(parent)
    return 0

cdef int av_frame_bfr_free_child(av_frame_bfr_ft bfr, bint single_step=True) except -1 nogil:
    if bfr.next is NULL:
        raise_withgil(PyExc_ValueError, 'no child bfr')
    cdef av_frame_bfr_ft child = bfr.next
    bfr.next = NULL
    if child.next is not NULL:
        if single_step:
            raise_withgil(PyExc_ValueError, 'child has more forward links')
        else:
            if child.next.next is NULL:
                av_frame_bfr_remove(child.next)
            else:
                av_frame_bfr_free_child(child, single_step)
            child.prev = NULL
    bfr.next = NULL
    av_frame_bfr_free_single(child)
    return 0
