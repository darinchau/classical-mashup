# Provides a wrapper for music21's classes with some convenience functions
# This is because music21's classes are very general. By imposing certain restrictions
# from the scope of our project, we can make the code easier (for me) to reason about.

from .base import M21Wrapper
from .note import M21Note, M21Chord, M21Rest
from .stream import M21Part, M21Score, M21Measure, M21StreamWrapper
from .symbol import M21TimeSignature, M21KeySignature, M21Key, M21Interval, M21Slur, M21BassClef, M21Dynamics, M21TrebleClef
from .articulation import M21Accent, M21Articulation, M21Staccato, M21Tenuto
from .expressions import M21Expression, M21Fermata, M21Mordent, M21Trill, M21Turn, M21TextExpression
from .util import load_score_from_corpus, load_part_from_corpus

from music21.base import Music21Object as M21Object
