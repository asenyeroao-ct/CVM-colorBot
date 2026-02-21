# cython: language_level=3
# distutils: language = c++

from libc.stdint cimport int64_t
from libcpp.list cimport list as cpp_list
from cpython.ref cimport PyObject

cdef extern from *:
    ctypedef Py_ssize_t Py_intptr_t

cdef extern from "Python.h":
    ctypedef int64_t _PyTime_t

    _PyTime_t _PyTime_GetMonotonicClock()
    double _PyTime_AsSecondsDouble(_PyTime_t t)

cdef extern from "pythread.h":
    ctypedef void *PyThread_type_lock

    cdef enum PyLockStatus:
        PY_LOCK_FAILURE = 0
        PY_LOCK_ACQUIRED = 1
        PY_LOCK_INTR
    enum:
        NOWAIT_LOCK = 0
        WAIT_LOCK = 1

    long PyThread_get_thread_ident()
    PyThread_type_lock PyThread_allocate_lock()
    void PyThread_free_lock(PyThread_type_lock)
    int PyThread_acquire_lock(PyThread_type_lock, int mode) nogil
    void PyThread_release_lock(PyThread_type_lock) nogil
    ctypedef long long PY_TIMEOUT_T

    # /* If microseconds == 0, the call is non-blocking: it returns immediately
    #     even when the lock can't be acquired.
    #     If microseconds > 0, the call waits up to the specified duration.
    #     If microseconds < 0, the call waits until success (or abnormal failure)
    #
    #     microseconds must be less than PY_TIMEOUT_MAX. Behaviour otherwise is
    #     undefined.
    #
    #     If intr_flag is true and the acquire is interrupted by a signal, then the
    #     call will return PY_LOCK_INTR.  The caller may reattempt to acquire the
    #     lock.
    # */
    PyLockStatus PyThread_acquire_lock_timed(PyThread_type_lock,
                                             PY_TIMEOUT_T microseconds,
                                             int intr_flag) nogil


ctypedef cpp_list[Py_intptr_t] obj_ptr_list_t

cdef struct LockStatus_s:
    PyThread_type_lock lock
    bint is_locked
    long owner
    int acquire_count
    int pending_requests

cdef class Lock:
    cdef LockStatus_s* _lock
    cdef public str name

    cdef bint _is_locked(self)
    cdef bint _do_acquire(self, long owner) except -1
    cdef bint _do_acquire_timed(self, long owner, PY_TIMEOUT_T microseconds) except -1
    cdef int _do_release(self) except -1
    cdef int _check_acquire(self) except -1
    cdef int _check_release(self) except -1
    cdef bint _acquire(self, bint block, double timeout) except -1
    cdef bint _release(self) except -1
    cpdef bint acquire(self, bint block=*, double timeout=*) except -1
    cpdef bint release(self) except -1

cdef class RLock(Lock):

    cdef bint _is_owned_c(self, long owner) except -1
    cpdef bint _is_owned(self) except -1
    cdef int _acquire_restore_c(self, long current_owner, int count, long owner) except -1
    cdef int _acquire_restore(self, (int, long) state) except -1
    cdef (int, long) _release_save_c(self) except *
    cdef (int, long) _release_save(self) except *

cdef class Condition:
    cdef readonly RLock rlock
    # cdef readonly object _waiters
    cdef obj_ptr_list_t _waiters

    cpdef bint acquire(self, bint block=*, double timeout=*) except -1
    cdef bint _acquire(self, bint block, double timeout) except -1
    cpdef bint release(self) except -1
    cdef bint _release(self) except -1
    # cpdef _acquire_restore(self, state)
    cdef int _acquire_restore(self, (int, long) state) except -1
    cdef (int, long) _release_save(self) except *
    cpdef bint _is_owned(self) except -1
    cdef int _ensure_owned(self) except -1
    cpdef bint wait(self, object timeout=*)
    cdef bint _wait(self, bint block, double timeout=*) except -1
    cpdef bint wait_for(self, object predicate, object timeout=*) except -1
    cdef int _notify(self, Py_ssize_t n=*) except -1
    cdef int _notify_all(self) except -1


cdef class Event:
    cdef readonly Condition _cond
    cdef readonly bint _flag

    cdef bint _is_set(self) noexcept nogil
    cdef int _set(self) except -1
    cdef int _clear(self) except -1
    cdef bint _wait(self, bint block, double timeout) except -1
