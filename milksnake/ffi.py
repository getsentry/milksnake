import os
import cffi

from ._compat import PY2


def make_ffi(module_path, header):
    """Creates a FFI instance for the given configuration."""
    if not PY2 and isinstance(header, bytes):
        header = header.decode('utf-8')

    ffi = cffi.FFI()
    ffi.cdef(header)
    ffi.set_source(module_path, None)
    return ffi
