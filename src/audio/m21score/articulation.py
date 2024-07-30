# An articulation is something that changes the length, dynamic, pitch (N/A), or timbre (N/A) of a note.

import music21 as m21
from music21.articulations import (
    # Base classes
    Articulation, PitchArticulation, TimbreArticulation,

    # Supported ones
    Accent, Staccato, Tenuto
)
from typing import TypeVar
from .base import M21Object, M21Wrapper

T = TypeVar("T", bound=Articulation, covariant=True)

class M21Articulation(M21Wrapper[T]):
    """Represents an articulation object in music21. This class should be inherited by all articulation classes."""
    def sanity_check(self):
        assert not isinstance(self._data, PitchArticulation), "Articulations that alter the pitch are not supported"
        assert not isinstance(self._data, TimbreArticulation), "Articulations that alter the timbre are not supported"

    @property
    def volume_shift(self):
        """Returns the volume shift of the articulation. 1 means no shift, 1.1 means 10% louder, 0.9 means 10% quieter"""
        return self._data.volumeShift + 1

    @property
    def length_shift(self):
        """Returns the length shift of the articulation. 1 means no shift, 1.1 means 10% longer, 0.9 means 10% shorter"""
        return self._data.lengthShift

class M21Accent(M21Articulation[Accent]):
    """Represents an accent articulation"""
    pass

class M21Staccato(M21Articulation[Staccato]):
    """Represents a staccato articulation"""
    pass

class M21Tenuto(M21Articulation[Tenuto]):
    """Represents a tenuto articulation"""
    pass
