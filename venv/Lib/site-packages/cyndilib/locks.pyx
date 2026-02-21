
"""Thread synchronization primitives implemented at the C level

This module is **heavily** inspired by the `FastRLock`_ library with a few
adjustments and additions.

.. _FastRLock: https://github.com/scoder/fastrlock
"""

import threading
from itertools import islice
from collections import deque

from cpython.ref cimport Py_INCREF, Py_DECREF
from cpython.mem cimport PyMem_Malloc, PyMem_Free

from .clock cimport time


__all__ = ('Lock', 'RLock', 'Condition', 'Event')


cdef inline bint _lock_lock(LockStatus_s *lock, long current_thread,
                            bint blocking, PY_TIMEOUT_T microseconds) except -1 nogil:

    return _acquire_lock(lock, current_thread, blocking, microseconds, False)


cdef inline bint _lock_rlock(LockStatus_s *lock, long current_thread,
                             bint blocking, PY_TIMEOUT_T microseconds) except -1 nogil:
    # Note that this function *must* hold the GIL when being called.
    # We just use 'nogil' in the signature to make sure that no Python
    # code execution slips in that might free the GIL

    if lock.acquire_count:
        # locked! - by myself?
        if lock.owner == current_thread:
            lock.acquire_count += 1
            return True
    elif not lock.pending_requests:
        # not locked, not requested - go!
        lock.owner = current_thread
        lock.acquire_count = 1
        return True
    # need to get the real lock
    return _acquire_lock(lock, current_thread, blocking, microseconds, True)

cdef inline int _unlock_lock(LockStatus_s *lock) except -1 nogil:
    # Note that this function *must* hold the GIL when being called.
    # We just use 'nogil' in the signature to make sure that no Python
    # code execution slips in that might free the GIL

    #assert lock.acquire_count > 0
    lock.acquire_count -= 1
    if lock.acquire_count == 0:
        lock.owner = -1
        if lock.is_locked:
            PyThread_release_lock(lock.lock)
        lock.is_locked = False
    return 0

cdef bint _acquire_lock(LockStatus_s *lock, long current_thread, bint blocking,
                        PY_TIMEOUT_T microseconds, bint reentrant) except -1 nogil:
    cdef int locked
    cdef PyLockStatus result

    wait = WAIT_LOCK if blocking else NOWAIT_LOCK
    if reentrant and not lock.is_locked and not lock.pending_requests:
        # someone owns it but didn't acquire the real lock - do that
        # now and tell the owner to release it when done
        if PyThread_acquire_lock(lock.lock, NOWAIT_LOCK):
            lock.is_locked = True
    #assert lock._is_locked

    lock.pending_requests += 1

    # wait for the lock owning thread to release it
    with nogil:
        if blocking and microseconds > 0:
            while True:
                result = PyThread_acquire_lock_timed(lock.lock, microseconds, 1)
                if result == PyLockStatus.PY_LOCK_ACQUIRED:
                    break
                elif result == PyLockStatus.PY_LOCK_FAILURE:
                    return False
        else:
            while True:
                locked = PyThread_acquire_lock(lock.lock, wait)
                if locked:
                    break
                if wait == NOWAIT_LOCK:
                    return False
    lock.pending_requests -= 1
    #assert not lock.is_locked
    #assert lock.reentry_count == 0
    #assert locked
    lock.is_locked = True
    lock.owner = current_thread
    lock.acquire_count = 1
    return True

cdef LockStatus_s* LockStatus_create() except *:
    cdef LockStatus_s* lock = <LockStatus_s*>PyMem_Malloc(sizeof(LockStatus_s))
    if lock is NULL:
        raise MemoryError()

    lock.is_locked = False
    lock.owner = -1
    lock.acquire_count = 0
    lock.pending_requests = 0
    lock.lock = PyThread_allocate_lock()
    if lock.lock is NULL:
        PyMem_Free(lock)
        raise MemoryError()
    return lock

cdef int LockStatus_destroy(LockStatus_s* lock) except -1:
    if lock.lock != NULL:
        PyThread_free_lock(lock.lock)
        lock.lock = NULL
    PyMem_Free(lock)
    return 0

cdef class Lock:
    """Implementation of :class:`threading.Lock`. A Primitive non-reentrant
    lock (or mutex)

    This class supports use as a :term:`context manager` and can be acquired
    and released using the :keyword:`with` statement.
    """
    def __cinit__(self):
        self._lock = LockStatus_create()
        self.name = ''

    def __dealloc__(self):
        cdef LockStatus_s* lock
        if self._lock != NULL:
            lock = self._lock
            LockStatus_destroy(lock)
            self._lock = NULL

    @property
    def locked(self):
        """True if the lock is acquired
        """
        return self._is_locked()

    cdef bint _is_locked(self):
        if self._lock.acquire_count > 0 or self._lock.owner >= 0 or self._lock.is_locked:
            return True
        return False

    cdef bint _do_acquire(self, long owner) except -1:
        return _lock_lock(self._lock, owner, True, -1)

    cdef bint _do_acquire_timed(self, long owner, PY_TIMEOUT_T microseconds) except -1:
        return _lock_lock(self._lock, owner, True, microseconds)

    cdef int _do_release(self) except -1:
        _unlock_lock(self._lock)
        return 0

    cdef int _check_acquire(self) except -1:
        # cdef long tid = PyThread_get_thread_ident()
        #
        # if self._lock.owner == tid:
        #     raise RuntimeError('lock already acquired')
        return 0

    cdef int _check_release(self) except -1:
        # cdef long tid = PyThread_get_thread_ident()
        #
        # if self._lock.owner != tid:
        #     raise RuntimeError('cannot release un-acquired lock')
        return 0

    cdef bint _acquire(self, bint block, double timeout) except -1:
        cdef double microseconds
        cdef double multiplier = 1000000
        cdef long tid = PyThread_get_thread_ident()

        self._check_acquire()
        if timeout == 0:
            block = False
        elif timeout < 0:
            block = True
        if block:
            if timeout < 0:
                microseconds = -1
            else:
                microseconds = timeout * multiplier
            return self._do_acquire_timed(tid, <PY_TIMEOUT_T> microseconds)
        else:
            microseconds = 0
            return self._do_acquire_timed(tid, <PY_TIMEOUT_T> microseconds)

    cdef bint _release(self) except -1:
        self._check_release()
        self._do_release()
        return self._lock.is_locked

    cpdef bint acquire(self, bint block=True, double timeout=-1) except -1:
        """Acquire the lock, blocking or non-blocking

        Arguments:
            block (bool, optional): If ``True`` (the default), block until the
                lock is unlocked. If ``False``, acquire the lock if it it isn't
                already locked and return immediately.
            timeout (float, optional): Maximum time (in seconds) to block
                waiting to acquire the lock. A value of ``-1`` specifies an
                unbounded wait.


        .. note::

            The arguments in this method vary slightly from that of
            :meth:`threading.Lock.acquire` where it is considered an error to
            specify a *timeout* with *blocking* set to ``False``.

            In this implementation, the *block* argument is ignored if *timeout*
            is given.

        Returns:
            bool: ``True`` if the lock was acquired, otherwise ``False``.

        """
        return self._acquire(block, timeout)

    cpdef bint release(self) except -1:
        """Release the lock

        Raises:
            RuntimeError: If the lock is not :attr:`locked`
        """
        return self._release()

    def __enter__(self):
        self._acquire(True, -1)
        return self

    def __exit__(self, *args):
        self._release()

    def __repr__(self):
        return '<{self.__class__} {self.name} (locked={self.locked}) at {id}>'.format(self=self, id=id(self))

cdef class RLock(Lock):
    """Implementation of :class:`threading.RLock`. A reentrant lock that can be
    acquired multiple times by the same thread

    Each call to :meth:`~Lock.acquire` must be followed by corresponding a call
    to :meth:`~Lock.release` before the lock is unlocked.

    This class supports use as a :term:`context manager` and can be acquired
    and released using the :keyword:`with` statement.
    """
    cdef bint _do_acquire(self, long owner) except -1:
        return _lock_rlock(self._lock, owner, True, -1)

    cdef bint _do_acquire_timed(self, long owner, PY_TIMEOUT_T microseconds) except -1:
        return _lock_rlock(self._lock, owner, True, microseconds)

    cdef int _check_acquire(self) except -1:
        return 0

    cdef int _check_release(self) except -1:
        cdef long tid = PyThread_get_thread_ident()

        if self._lock.owner != tid:
            raise RuntimeError('cannot release un-owned lock')
        return 0

    cdef bint _is_owned_c(self, long owner) except -1:
        return owner == self._lock.owner

    cpdef bint _is_owned(self) except -1:
        cdef long tid = PyThread_get_thread_ident()
        return self._is_owned_c(tid)

    cdef int _acquire_restore_c(self, long current_owner, int count, long owner) except -1:
        self._do_acquire(current_owner)
        self._lock.acquire_count = count
        self._lock.owner = owner

    cdef int _acquire_restore(self, (int, long) state) except -1:
        cdef int count
        cdef long current_owner, owner
        current_owner = PyThread_get_thread_ident()
        count, owner = state
        self._acquire_restore_c(current_owner, count, owner)

    cdef (int, long) _release_save_c(self) except *:
        cdef int count = self._lock.acquire_count
        cdef long owner = self._lock.owner

        self._do_release()
        return count, owner

    cdef (int, long) _release_save(self) except *:
        if not self._lock.acquire_count:
            raise RuntimeError("cannot release un-acquired lock")
        return self._release_save_c()

cdef class Condition:
    """Implementation of :class:`threading.Condition`. Allows one or more thread
    to wait until they are notified by another thread.

    Arguments:
        init_lock (RLock, optional): If provided, a :class:`RLock` instance to be
            used as the underlying lock. If not provided or ``None`` a new
            :class:`RLock` will be created.

    This class supports use as a :term:`context manager` and can be acquired
    and released using the :keyword:`with` statement.
    """
    def __cinit__(self, init_lock=None, *args, **kwargs):
        cdef RLock lock
        if init_lock is not None:
            assert isinstance(init_lock, RLock)
            lock = init_lock
        else:
            lock = RLock()
        self.rlock = lock
        # self._waiters = deque()

    def __enter__(self):
        self.rlock._acquire(True, -1)
        return self

    def __exit__(self, *args):
        # return self.rlock.__exit__(*args)
        self.rlock._release()

    cpdef bint acquire(self, bint block=True, double timeout=-1) except -1:
        """Acquire the underlying lock

        Arguments and return values match those of :meth:`Lock.acquire`
        """
        return self.rlock._acquire(block, timeout)

    cdef bint _acquire(self, bint block, double timeout) except -1:
        return self.rlock._acquire(block, timeout)

    cpdef bint release(self) except -1:
        """Release the underlying lock

        Arguments and return values match those of :meth:`Lock.release`
        """
        return self.rlock._release()

    cdef bint _release(self) except -1:
        return self.rlock._release()

    cdef int _acquire_restore(self, (int, long) state) except -1:
        self.rlock._acquire_restore(state)
        return 0

    cdef (int, long) _release_save(self) except *:
        return self.rlock._release_save()

    cpdef bint _is_owned(self) except -1:
        cdef long tid = PyThread_get_thread_ident()
        return self.rlock._is_owned_c(tid)

    cdef int _ensure_owned(self) except -1:
        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        return 0

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self._lock, self._waiters.size())

    cpdef bint wait(self, object timeout=None):
        """Wait until notified or until a timeout occurs

        The underlying lock must be held before a call to this method.
        Once called, releases lock then blocks until awakened by a call to
        :meth:`notify` or :meth:`notify_all` by another thread, or until the
        timeout (if given) has been reached.

        Arguments:
            timeout (float, optional): If provided, the maximum amount of time
                (in seconds) to block. If ``-1`` is given (or ``None``), the
                blocking duration is unbounded.

        Returns:
            bool: ``True`` if notified before the timeout (if any), ``False``
                if a timeout was given and was reached.

        Raises:
            RuntimeError: If the lock was not acquired before this
                method was called
        """
        cdef bint block
        cdef double _timeout

        if timeout is None:
            _timeout = -1
            block = True
        else:
            block = False
            _timeout = <double> timeout
        return self._wait(block, _timeout)

    cdef bint _wait(self, bint block, double timeout=-1) except -1:
        cdef Lock waiter
        cdef bint gotit = False

        self._ensure_owned()
        waiter = Lock()
        waiter._acquire(True, -1)
        # self._waiters.append(waiter)
        cdef PyObject* obj_ptr = <PyObject*>waiter
        cdef Py_intptr_t w_id = <Py_intptr_t>obj_ptr
        self._waiters.push_back(w_id)
        Py_INCREF(waiter)
        cdef (int, long) saved_state = self._release_save()

        try:    # restore state no matter what (e.g., KeyboardInterrupt)
            if block:
                waiter._acquire(True, -1)
                gotit = True
            else:
                if timeout > 0:
                    gotit = waiter._acquire(True, timeout)
                else:
                    gotit = waiter._acquire(False, -1)
            return gotit
        finally:
            self._acquire_restore(saved_state)
            if not gotit:
                # if waiter in self._waiters:
                #     self._waiters.remove(waiter)
                self._waiters.remove(w_id)
                Py_DECREF(waiter)
                # try:
                #     self._waiters.remove(waiter)
                # except ValueError:
                #     pass

    cpdef bint wait_for(self, object predicate, object timeout=None) except -1:
        """Wait until a condition evaluates to ``True``

        Repeatedly calls :meth:`wait` until the given predicate is satisfied or
        the timeout has been reached.

        Arguments:
            predicate (typing.Callable): A callable whose return value will be
                evaluated as a boolean value. Any returned value that can be
                evaluated as ``True`` (``bool(predicate())``) will satisfy the
                condition.
            timeout (float, optional): If provided, the maximum amount of time
                (in seconds) to wait for the condition to be satisfied.
                If ``-1`` is given (or ``None``), waits indefinitely.

        Returns:
            bool: ``True`` if the condition was satisfied before the timeout
            (if given), ``False`` otherwise.

        Raises:
            RuntimeError: If the lock was not acquired before this
                method was called
        """
        cdef double _timeout, endtime, waittime
        cdef bint has_timeout, result

        if timeout is not None:
            has_timeout = True
            _timeout = <double> timeout
            waittime = _timeout
            endtime = -1
        else:
            has_timeout = False

        result = predicate()
        while not result:
            if has_timeout:
                if endtime == -1:
                    endtime = time() + waittime
                else:
                    waittime = endtime - time()
                    if waittime <= 0:
                        break
            self._wait(True, waittime)
            result = predicate()
        return result

    def notify(self, Py_ssize_t n=1):
        """Wake up at least *n* threads waiting for this condition variable

        The lock must be acquired before this method is called. Since waiting
        threads must reacquire the lock before returning from the
        :meth:`wait` method, the caller must release it.

        Arguments:
            n (int): Maximum number of threads to notify. Defaults to ``1``

        Raises:
            RuntimeError: If the lock was not acquired before this
                method was called
        """
        self._notify(n)

    cdef int _notify(self, Py_ssize_t n=1) except -1:
        cdef Lock waiter

        self._ensure_owned()
        # all_waiters = self._waiters
        # waiters_to_notify = deque(islice(all_waiters, n))
        # cdef obj_ptr_list_t waiters_to_notify = [v for v in enumerate(self._waiters) if i >= n]
        # if not waiters_to_notify:
        #     return
        cdef PyObject* obj_ptr# = <PyObject*>waiter
        cdef Py_intptr_t w_id# = <Py_intptr_t>obj_ptr
        # cdef Lock waiter
        cdef size_t i = 0
        while n > 0 and self._waiters.size():
            # i += 1
            # if i < n:
            #     continue
            w_id = self._waiters.front()
            self._waiters.pop_front()
            obj_ptr = <PyObject*>w_id
            waiter = <object>obj_ptr
            waiter._release()
            Py_DECREF(waiter)
            n -= 1
            # waiter = waiters_to_notify.popleft()
            # waiter._release()
        # for waiter in waiters_to_notify:
        #     waiter._release()
        #     try:
        #         all_waiters.remove(waiter)
        #     except ValueError:
        #         pass
        return 0

    def notify_all(self):
        """Like :meth:`notify`, but wakes all waiting threads

        Raises:
            RuntimeError: If the lock was not acquired before this
                method was called
        """
        self._notify(self._waiters.size())

    cdef int _notify_all(self) except -1:
        self._notify(self._waiters.size())
        return 0

cdef class Event:
    """Implementation of :class:`threading.Event`. A simple flag-based thread
    communication primitive where one thread signals an event and other
    threads wait for it.
    """
    def __init__(self):
        self._cond = Condition()
        self._flag = False

    def is_set(self) -> bool:
        """Returns ``True`` if the event has been set
        """
        return self._flag

    cdef bint _is_set(self) noexcept nogil:
        return self._flag

    def set(self):
        """Set the internal flag to ``True``, awakening any threads waiting for it
        """
        self._set()

    cdef int _set(self) except -1:
        self._cond._acquire(True, -1)
        try:
            self._flag = True
            self._cond.notify_all()
        finally:
            self._cond._release()
        return 0

    def clear(self):
        """Reset the internal flag to ``False``.  After this, any threads making
        a call to :meth:`wait` will block until the event is :meth:`set` again
        """
        self._clear()

    cdef int _clear(self) except -1:
        self._cond._acquire(True, -1)
        self._flag = False
        self._cond._release()
        return 0

    def wait(self, object timeout=None) -> bool:
        """Block until the internal flag is ``True`` by a call to :meth:`set`
        by another thread. If the flag is already ``True``, return immediately.

        Arguments:
            timeout (float, optional): If given, the maximum time in seconds to
                block waiting for the flag. If ``-1`` (or ``None``), blocks
                indefinitely.

        Returns:
            bool: ``True`` if the flag was set before a timeout, ``False`` otherwise
        """
        cdef bint block
        cdef double _timeout

        if timeout is None:
            _timeout = -1
            block = True
        else:
            block = False
            _timeout = <double> timeout

        return self._wait(block, timeout)

    cdef bint _wait(self, bint block, double timeout) except -1:
        cdef bint signaled
        self._cond._acquire(True, -1)
        try:
            signaled = self._flag
            if not signaled:
                signaled = self._cond._wait(block, timeout)
            return signaled
        finally:
            self._cond._release()
