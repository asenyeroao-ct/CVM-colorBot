# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .ndi_structs cimport *


cdef extern from "Processing.NDI.Find.h" nogil:

    cdef struct NDIlib_find_instance_type
    ctypedef NDIlib_find_instance_type* NDIlib_find_instance_t

    #// The creation structure that is used when you are creating a finder.
    cdef struct NDIlib_find_create_t:
        # // Do we want to include the list of NDI sources that are running on the local machine? If TRUE then
        # // local sources will be visible, if FALSE then they will not.
        bint show_local_sources

        # // Which groups do you want to search in for sources.
        const char* p_groups

        # // The list of additional IP addresses that exist that we should query for sources on. For instance, if
        # // you want to find the sources on a remote machine that is not on your local sub-net then you can put a
        # // comma separated list of those IP addresses here and those sources will be available locally even
        # // though they are not mDNS discoverable. An example might be "12.0.0.8,13.0.12.8". When none is
        # // specified the registry is used.
        # // Default = NULL;
        const char* p_extra_ips

    # // Create a new finder instance. This will return NULL if it fails.
    NDIlib_find_instance_t NDIlib_find_create_v2(const NDIlib_find_create_t* p_create_settings)

    # // This will destroy an existing finder instance.
    # PROCESSINGNDILIB_API
    void NDIlib_find_destroy(NDIlib_find_instance_t p_instance)

    # // This function will recover the current set of sources (i.e. the ones that exist right this second). The
    # // char* memory buffers returned in NDIlib_source_t are valid until the next call to
    # // NDIlib_find_get_current_sources or a call to NDIlib_find_destroy. For a given NDIlib_find_instance_t, do
    # // not call NDIlib_find_get_current_sources asynchronously.
    # PROCESSINGNDILIB_API
    const NDIlib_source_t* NDIlib_find_get_current_sources(NDIlib_find_instance_t p_instance, uint32_t* p_no_sources)

    # // This will allow you to wait until the number of online sources have changed.
    # PROCESSINGNDILIB_API
    bint NDIlib_find_wait_for_sources(NDIlib_find_instance_t p_instance, uint32_t timeout_in_ms)
