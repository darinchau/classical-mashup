# Provides a wrapper for music21's classes with some convenience functions
# This is because music21's classes are very general. By imposing certain restrictions
# from the scope of our project, we can make the code easier (for me) to reason about.

from .base import M21Wrapper
from .note import M21Note, M21Chord, M21Rest
from .stream import M21Part, M21Score, M21Measure, M21StreamWrapper
from .symbol import M21TimeSignature, M21KeySignature, M21Key, M21Interval, M21Slur, M21Clef
from .articulation import M21Accent, M21Articulation, M21Staccato, M21Tenuto

from music21.base import Music21Object as M21Object
from music21.duration import Duration
from music21.stream.base import Stream, Score, Part, Measure
from music21.note import Note, Rest
from music21.chord import Chord
from music21.key import KeySignature, Key
from music21.meter.base import TimeSignature
from music21.interval import Interval
from music21.clef import Clef
from music21.spanner import Slur
