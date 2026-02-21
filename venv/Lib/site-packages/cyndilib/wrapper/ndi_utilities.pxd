# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport *

from .ndi_lib cimport *
from .ndi_structs cimport *
from .ndi_send cimport *

cdef extern from "Processing.NDI.utilities.h" nogil:

    # // This describes an audio frame.
    cdef struct NDIlib_audio_frame_interleaved_16s_t:
        # // The sample-rate of this buffer.
        int sample_rate

        # // The number of audio channels.
        int no_channels

        # // The number of audio samples per channel.
        int no_samples

        # // The timecode of this frame in 100-nanosecond intervals.
        int64_t timecode

        # // The audio reference level in dB. This specifies how many dB above the reference level (+4 dBU) is the
        # // full range of 16-bit audio. If you do not understand this and want to just use numbers:
        # // - If you are sending audio, specify +0 dB. Most common applications produce audio at reference level.
        # // - If receiving audio, specify +20 dB. This means that the full 16-bit range corresponds to
        # //   professional level audio with 20 dB of headroom. Note that if you are writing it into a file it
        # //   might sound soft because you have 20 dB of headroom before clipping.
        int reference_level

        # // The audio data, interleaved 16-bit samples.
        int16_t* p_data

    # // This describes an audio frame.
    cdef struct NDIlib_audio_frame_interleaved_32s_t:
        # // The sample-rate of this buffer.
        int sample_rate

        # // The number of audio channels.
        int no_channels

        # // The number of audio samples per channel.
        int no_samples

        # // The timecode of this frame in 100-nanosecond intervals.
        int64_t timecode

        # // The audio reference level in dB. This specifies how many dB above the reference level (+4 dBU) is the
        # // full range of 32-bit audio. If you do not understand this and want to just use numbers:
        # // - If you are sending audio, specify +0 dB. Most common applications produce audio at reference level.
        # // - If receiving audio, specify +20 dB. This means that the full 32-bit range corresponds to
        # //   professional level audio with 20 dB of headroom. Note that if you are writing it into a file it
        # //   might sound soft because you have 20 dB of headroom before clipping.
        int reference_level

        # // The audio data, interleaved 32-bit samples.
        int32_t* p_data

    # // This describes an audio frame.
    cdef struct NDIlib_audio_frame_interleaved_32f_t:
        # // The sample-rate of this buffer.
        int sample_rate

        # // The number of audio channels.
        int no_channels

        # // The number of audio samples per channel.
        int no_samples

        # // The timecode of this frame in 100-nanosecond intervals.
        int64_t timecode

        # // The audio data, interleaved 32-bit floating-point samples.
        float* p_data

    # // This will add an audio frame in interleaved 16-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_send_send_audio_interleaved_16s(NDIlib_send_instance_t p_instance, const NDIlib_audio_frame_interleaved_16s_t* p_audio_data)

    # // This will add an audio frame in interleaved 32-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_send_send_audio_interleaved_32s(NDIlib_send_instance_t p_instance, const NDIlib_audio_frame_interleaved_32s_t* p_audio_data)

    # // This will add an audio frame in interleaved floating point.
    # PROCESSINGNDILIB_API
    void NDIlib_util_send_send_audio_interleaved_32f(NDIlib_send_instance_t p_instance, const NDIlib_audio_frame_interleaved_32f_t* p_audio_data)

    # // Convert to interleaved 16-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_to_interleaved_16s_v2(const NDIlib_audio_frame_v2_t* p_src, NDIlib_audio_frame_interleaved_16s_t* p_dst)

    # // Convert from interleaved 16-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_from_interleaved_16s_v2(const NDIlib_audio_frame_interleaved_16s_t* p_src, NDIlib_audio_frame_v2_t* p_dst)

    # // Convert to interleaved 32-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_to_interleaved_32s_v2(const NDIlib_audio_frame_v2_t* p_src, NDIlib_audio_frame_interleaved_32s_t* p_dst)

    # // Convert from interleaved 32-bit.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_from_interleaved_32s_v2(const NDIlib_audio_frame_interleaved_32s_t* p_src, NDIlib_audio_frame_v2_t* p_dst)

    # // Convert to interleaved floating point.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_to_interleaved_32f_v2(const NDIlib_audio_frame_v2_t* p_src, NDIlib_audio_frame_interleaved_32f_t* p_dst)

    # // Convert from interleaved floating point.
    # PROCESSINGNDILIB_API
    void NDIlib_util_audio_from_interleaved_32f_v2(const NDIlib_audio_frame_interleaved_32f_t* p_src, NDIlib_audio_frame_v2_t* p_dst)

    # // This is a helper function that you may use to convert from 10-bit packed UYVY into 16-bit semi-planar. The
    # // FourCC on the source is ignored in this function since we do not define a V210 format in NDI. You must
    # // make sure that there is memory and a stride allocated in p_dst.
    # PROCESSINGNDILIB_API
    void NDIlib_util_V210_to_P216(const NDIlib_video_frame_v2_t* p_src_v210, NDIlib_video_frame_v2_t* p_dst_p216)

    # // This converts from 16-bit semi-planar to 10-bit. You must make sure that there is memory and a stride
    # // allocated in p_dst.
    # PROCESSINGNDILIB_API
    void NDIlib_util_P216_to_V210(const NDIlib_video_frame_v2_t* p_src_p216, NDIlib_video_frame_v2_t* p_dst_v210)
