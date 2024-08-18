from __future__ import annotations
from .base import ScoreRepresentation
from .simplenote import SimpleNote
from ..util.avl import AVLTree
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

    voice: int
    """voice: int - If there are any voices in the score, this is the voice number.

    To reconstruct the M21 Score, we store the nth part in the right hand as n, and -n in the left hand.
    If there are no voice information in the score, this is 0."""

    @classmethod
    def from_note_name(cls, note: str):
        """Purely for testing purposes. Converts a string note to a NoteElement."""
        octave = int(note[-1])
        return cls(0.0, 1.0, SimpleNote(note[:-1]), octave, 0)

    @property
    def pitch_number(self):
        """The chromatic pitch number of the note. Middle C is 60"""
        return self.note_name.pitch_number + 12 * self.octave + 12

    @property
    def step_number(self):
        """The step number of the note. Middle C is 23 and in/decreases by 1 for each step."""
        return 7 * self.octave + self.note_name.step_number - 5

    @property
    def step_name(self):
        """The step name of the note. Middle C is C4."""
        return self.note_name.step

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


class StandardScore(ScoreRepresentation):
    """Defines a standard score representation to which all scores must conform.
    Internally, the standard score is a list of tuples, where each tuple contains
    information about how to reconstruct a score, such as the element type and its
    onset and duration.
    """
    def __init__(self):
        self.elements = AVLTree()

    @classmethod
    def from_array(cls, array: list[StandardScoreElement]):
        """Create a StandardScore from an array."""
        score = cls()
        score.elements = AVLTree.from_array(array)
        return score

    @classmethod
    def from_sorted_array(cls, arr: list[StandardScoreElement], _check: bool = False):
        """Create a StandardScore from a sorted array."""
        score = cls()
        score.elements = AVLTree.from_sorted_array(arr, _check=_check)
        return score

    def insert(self, element: StandardScoreElement):
        self.elements.insert(element)

    def delete(self, element: StandardScoreElement):
        self.elements.delete(element)

    def flatten(self) -> list[StandardScoreElement]:
        return self.elements.flatten()

    def __contains__(self, x: StandardScoreElement):
        return x in self.elements

    def empty(self):
        return self.elements.empty()

    def __len__(self):
        return len(self.elements)

    @classmethod
    def parse(cls, path: str) -> StandardScore:
        # Load as music21 score and convert to standard score
        from .music21 import M21Score
        m21score = M21Score.parse(path)
        return m21score.to_standard()
