from __future__ import annotations
from .base import ScoreRepresentation
from .simplenote import SimpleNote
import enum
from dataclasses import dataclass, astuple
from math import log2, isclose

@dataclass(frozen=True)
class StandardScoreElement:
    onset: float
    "onset: float (in quarter notes from start)"

    def __lt__(self, other: StandardScoreElement):
        if self.onset < other.onset:
            return True

        if self.__class__.__name__ != other.__class__.__name__:
            return self.__class__.__name__ < other.__class__.__name__

        return self.__key__() < other.__key__()

    def __key__(self):
        """A custom special method to define the key for sorting."""
        return astuple(self)

    def __post_init__(self):
        assert self.onset >= 0


@dataclass(frozen=True)
class NoteElement(StandardScoreElement):
    duration: float
    "duration: float (in quarter notes from start)"

    note_name: SimpleNote
    "note_name: SimpleNote"

    octave: int
    "octave: int. Middle C is octave 4. Bottom note is A0. Top note is C8."

    @classmethod
    def from_str(cls, onset: float, duration: float, note: str):
        octave = int(note[-1])
        return cls(onset, duration, SimpleNote(note[:-1]), octave)

    @property
    def pitch_number(self):
        """The chromatic pitch number of the note. Middle C is 60"""
        return self.note_name.pitch_number + 12 * self.octave + 12

    @property
    def step_number(self):
        """The step number of the note. Middle C is 23 and in/decreases by 1 for each step."""
        return 7 * self.octave + self.note_name.step_number - 5

    def __key__(self):
        return (self.onset, self.pitch_number)


@dataclass(frozen=True)
class KeySignature(StandardScoreElement):
    nsharps: int
    "nsharps: int (flats will be negative number)"

    mode: int
    "mode: int (0 for major, 1 for minor)"

    def __post_init__(self):
        assert self.mode in (0, 1)

    @property
    def key(self):
        return SimpleNote.from_index(self.nsharps)


@dataclass(frozen=True)
class TimeSignature(StandardScoreElement):
    beats: int
    "beats: int (numerator)"

    beat_type: int
    "beat_type: int (denominator)"

    def __post_init__(self):
        assert self.beats in (2, 3, 4, 5, 6, 7, 8, 9), f"Invalid number of beats {self.beats}"
        assert self.beat_type in (2, 4, 8, 16), f"Invalid beat type {self.beat_type}"


@dataclass(frozen=True)
class Tempo(StandardScoreElement):
    note_value: int
    "note_value: int (1 for quarter note, 2 for half note, etc.)"

    tempo: float
    "tempo: note per minute"

    def __post_init__(self):
        assert isclose(log2(self.note_value), int(log2(self.note_value))), f"Invalid note value {self.note_value}"
        assert self.tempo > 0


class ExpressionType(enum.StrEnum):
    TRILL = "trill"
    TURN = "turn"
    MORDENT = "mordent"
    INVERTED_MORDENT = "inverted-mordent"
    FERMATA = "fermata"

@dataclass(frozen=True)
class Expression(StandardScoreElement):
    expression: ExpressionType

    @classmethod
    def from_str(cls, onset: float, expression: str):
        return cls(onset, ExpressionType(expression))


@dataclass(frozen=True)
class TextExpression(StandardScoreElement):
    text: str


class DynamicsType(enum.StrEnum):
    PPP = "ppp"
    PP = "pp"
    P = "p"
    MP = "mp"
    MF = "mf"
    F = "f"
    FF = "ff"
    FFF = "fff"
    SF = "sf"
    FP = "fp"


@dataclass(frozen=True)
class Dynamics(StandardScoreElement):
    dynamics: DynamicsType

    @classmethod
    def from_str(cls, onset: float, dynamics: str):
        return cls(onset, DynamicsType(dynamics))

class ArticulationType(enum.StrEnum):
    ACCENT = "accent"
    STACCATO = "staccato"
    TENUTO = "tenuto"


@dataclass(frozen=True)
class Articulation(StandardScoreElement):
    articulation: ArticulationType

    @classmethod
    def from_str(cls, onset: float, articulation: str):
        return cls(onset, ArticulationType(articulation))

### AVL Tree implementation ###


class StandardScore(ScoreRepresentation):
    """Defines a standard score representation to which all scores must conform.
    Internally, the standard score is a list of tuples, where each tuple contains
    information about how to reconstruct a score, such as the element type and its
    onset and duration.
    """
