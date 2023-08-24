from abc import ABCMeta

from ...creator import Creator
from ...describe import Describe


class VirtualenvBuiltin(Creator, Describe, metaclass=ABCMeta):
    """A creator that does operations itself without delegation, if we can create it we can also describe it"""

    def __init__(self, options, interpreter):
        Creator.__init__(self, options, interpreter)
        Describe.__init__(self, self.dest, interpreter)


__all__ = [
    "VirtualenvBuiltin",
]
