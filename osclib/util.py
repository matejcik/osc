from collections import namedtuple

from . import package

class PackagePath (namedtuple("PackagePath", "project, name")):
    """
    This is horrible.

    It must be changed.

    We can't have inconsistency between things that return PackagePath
    and Package. That's pure bullshit.
    Why am I even doing this.
    """
    __slots__ = ()

    def package(self, api):
        return package.Package(api, self.project, self.name)


# TODO look for usages of split_package, make sure we don't *need* them
# or convert them all to take an api argument and make them a full Package
# Or change Package to not need API?
def split_package(arg, brg=None):
    if isinstance(arg, package.Package) or isinstance(arg, PackagePath):
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
