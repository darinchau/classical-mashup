# Provides a wrapper for music21's classes with some convenience functions
# This is because music21's classes are very general. By imposing certain restrictions
# from the scope of our project, we can make the code easier (for me) to reason about.

from __future__ import annotations
from dataclasses import dataclass
import music21 as m21
import copy
from music21.midi.translate import streamToMidiFile
from src.util import is_ipython
from music21.base import Music21Object as M21Object
from music21.duration import Duration
from music21.common.types import OffsetQL, StepName
from music21.interval import Interval
from music21.stream.base import Part, Score
from typing import Generic, TypeVar
from .util import wrap

T = TypeVar("T", bound=M21Object, covariant=True)
T2 = TypeVar("T2", bound=M21Object)
class M21Wrapper(Generic[T]):
    """The base wrapper class for music21 objects. All subclasses should inherit from this class."""
    def __init__(self, obj: T, *, skip_check: bool = False):
        self._data = obj
        self._checked = skip_check
        if not self._checked:
            self.sanity_check()
        assert self._checked, f"The object {self._data} has not been sanity checked. Have you called sanity_check() on the parent class?"

    def sanity_check(self):
        """A method to check certain properties on M21Objects. This poses certain guarantees on objects."""
        # Checks the base type
        try:
            base_ty = self.__orig_bases__[0].__args__[0] # type: ignore
            assert isinstance(self._data, base_ty)
        except (AttributeError, IndexError, TypeError):
            pass
        self._checked = True

    @property
    def duration(self) -> Duration:
        """Return a copy of the duration object of the underlying m21 object."""
        duration = self._data.duration
        return copy.deepcopy(duration)

    @property
    def quarter_length(self) -> OffsetQL:
        """Return the duration of the object in quarter length."""
        return self.duration.quarterLength

    def get_context_by_class(self, cls: type[T2]) -> M21Wrapper[T2] | None:
        """Return the parent object of the object that is an instance of cls."""
        ctx = self._data.getContextByClass(cls)
        return wrap(ctx) if ctx is not None else None

    @property
    def part(self):
        """Returns a Part object that the object belongs to, if it exists."""
        from .stream import M21Part
        ctx = self._data.getContextByClass(Part)
        return M21Part(ctx) if ctx is not None else None

    @property
    def score(self):
        """Returns a Score object that the object belongs to, if it exists."""
        from .stream import M21Score
        ctx = self._data.getContextByClass(Score)
        return M21Score(ctx) if ctx is not None else None

    def copy(self):
        """Return a deep copy of the object."""
        return copy.deepcopy(self)

    def show(self, fmt = None):
        """Calls the show method of the music21 Stream object. Refer to the music21 documentation for more information."""
        return self._data.show(fmt)

    def __repr__(self):
        return f"<|{self._data.__repr__()}|>"

    @property
    def id(self):
        """Returns a unique integer representing this object"""
        return self._data.id

    def set_duration(self, quarter_length: float):
        new_obj = self.copy()
        new_obj._data.duration.quarterLength = quarter_length
        return new_obj

TransposeType = str | int | M21Wrapper[Interval]
