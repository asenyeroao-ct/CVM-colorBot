# cython: language_level=3
# distutils: language = c++


cdef extern from * nogil:
    """
    #include <chrono>
    #include <thread>
    #include <stdint.h>

    void sleep_for_microseconds(double seconds) {
        int64_t i = (int64_t)seconds * 1000000;
        int64_t j = (seconds - (int64_t)seconds) * 1000000;
        i += j;
        auto microseconds = std::chrono::microseconds(i);
        std::this_thread::sleep_for(microseconds);
    }

    double get_cpp_time() {
        using namespace std::chrono;
        auto tsNow = high_resolution_clock::now();
        auto msD = duration_cast<microseconds>(tsNow.time_since_epoch());
        double result = msD.count();
        result *= 0.000001;
        return result;
    }
    """
    cdef double get_cpp_time() noexcept nogil
    cdef void sleep_for_microseconds(double seconds) noexcept nogil


cdef inline double time() noexcept nogil:
    return get_cpp_time()

cdef inline void sleep(double seconds) noexcept nogil:
    with nogil:
        sleep_for_microseconds(seconds)
