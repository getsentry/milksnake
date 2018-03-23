from . import _native


def test():
    point = _native.lib.example_get_origin()
    return (point.x, point.y)
