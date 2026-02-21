
from cpython cimport PyObject
from cpython.method cimport PyMethod_Check
from cpython.weakref cimport PyWeakref_NewRef, PyWeakref_GetObject


__all__ = ('Callback', 'WeakMethod')


cdef class Callback:
    def __init__(self):
        self.has_callback = False
        self.is_weakref = False
        self.cb = None
        self.weak_cb = None

    cdef int set_callback(self, object cb) except -1:
        assert not self.has_callback
        cdef bint is_weakref = False
        if PyMethod_Check(cb):
            self.weak_cb = WeakMethod(cb)
            self.cb = None
            is_weakref = True
        else:
            self.weak_cb = None
            self.cb = cb
        self.is_weakref = is_weakref
        self.has_callback = True
        return 0

    cdef int remove_callback(self) except -1:
        self.has_callback = False
        self.cb = None
        self.weak_cb = None
        return 0

    cdef int trigger_callback(self) except -1:
        if not self.has_callback:
            return 0

        cdef object cb
        cdef bint is_alive
        cdef WeakMethod weak_cb = self.weak_cb
        if self.is_weakref:
            is_alive = weak_cb.trigger_callback()
            if not is_alive:
                self.weak_cb = None
                self.has_callback = False
        else:
            cb = self.cb
            cb()
        return 0


cdef class WeakMethod:
    def __init__(self, object meth):
        cdef object obj = meth.__self__
        cdef object func = meth.__func__
        def _ref_cb(arg):
            self.alive = False

        self.obj_ref = PyWeakref_NewRef(obj, _ref_cb)
        self.func_ref = PyWeakref_NewRef(func, _ref_cb)
        self.meth_type = type(meth)
        self.alive = True

    cdef bint trigger_callback(self) except -1:
        if not self.alive:
            return False
        cdef PyObject* obj_ptr = PyWeakref_GetObject(self.obj_ref)
        if not obj_ptr:
            self.alive = False
            return False
        cdef PyObject* func_ptr = PyWeakref_GetObject(self.func_ref)
        if not func_ptr:
            self.alive = False
            return False
        cdef object func = <object>func_ptr
        cdef object obj = <object>obj_ptr
        cdef object meth = self.meth_type(func, obj)
        meth()
        return True
