from collections import namedtuple

PackagePath = namedtuple("PackagePath", "project, package")

def split_package(arg, brg=None):
    if isinstance(arg, PackagePath):
        return arg
    if hasattr(arg, '__iter__'):
        # list, tuple, generator
        return PackagePath(*arg)
    if brg is not None:
        return PackagePath(arg, brg)

    components = arg.split('/')
    if not len(components) == 2:
        raise ValueError("'{}' is not a package string".format(arg))
    return PackagePath(*components)
