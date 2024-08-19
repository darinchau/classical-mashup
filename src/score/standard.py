from __future__ import annotations
from .base import ScoreRepresentation
from .simplenote import SimpleNote, StandardNote
from ..util.avl import AVLTree
import enum
from dataclasses import dataclass, astuple
from math import log2, isclose

@dataclass(frozen=True)
class StandardScoreElement:
    onset: float
    "onset: float (in quarter notes from start)"

    def __eq__(self, other: StandardScoreElement):
        if self.__class__ != other.__class__:
            return False
        return isclose(self.onset, other.onset) and self.__key__() == other.__key__()

    def __lt__(self, other: StandardScoreElement):
        if self.onset < other.onset:
            return True

        sort_order = (KeySignature, TimeSignature, Tempo, NoteElement, Expression, Dynamics, TextExpression)
        if self.__class__ != other.__class__:
            return sort_order.index(self.__class__) < sort_order.index(other.__class__)

        return self.__key__() < other.__key__()

    def __key__(self):
        """A custom special method to define the key for sorting."""
        return astuple(self)

    def __post_init__(self):
        assert self.onset >= 0


@dataclass(frozen=True, eq=False)
class NoteElement(StandardScoreElement):
    duration: float
    "duration: float (in quarter notes from start)"

    note_name: StandardNote

    voice: int
    """voice: int - If there are any voices in the score, this is the voice number.

    To reconstruct the M21 Score, we store the nth part in the right hand as n, and -n in the left hand.
    If there are no voice information in the score, this is 0."""

    @classmethod
    def from_note_name(cls, note: str):
        """Purely for testing purposes. Converts a string note to a NoteElement."""
        return cls(0.0, 1.0, StandardNote.from_str(note), 0)

    @property
    def pitch_number(self):
        """The chromatic pitch number of the note. Middle C is 60"""
        return self.note_name.pitch_number

    @property
    def step_number(self):
        """The step number of the note. Middle C is 23 and in/decreases by 1 for each step."""
        return self.note_name.step_number

    @property
    def step_name(self):
        """The step name of the note. Middle C is C4."""
        return self.note_name.step_name

    @property
    def step(self):
        return self.note_name.pitch.step

    @property
    def alter(self):
        return self.note_name.pitch.alter

    @property
    def octave(self):
        return self.note_name.octave

    def __key__(self):
        return (self.onset, self.pitch_number, self.duration)


@dataclass(frozen=True, eq=False)
class KeySignature(StandardScoreElement):
    nsharps: int
    "nsharps: int (flats will be negative number)"

    mode: int
    "mode: int (0 for major, 1 for minor, -1 for unknown)"

    def __post_init__(self):
        assert self.mode in (0, 1, -1)

    @property
    def key(self):
        return SimpleNote.from_index(self.nsharps)


@dataclass(frozen=True, eq=False)
class TimeSignature(StandardScoreElement):
    beats: int
    "beats: int (numerator)"

    beat_type: int
    "beat_type: int (denominator)"

    def __post_init__(self):
        assert self.beats in (2, 3, 4, 5, 6, 7, 8, 9), f"Invalid number of beats {self.beats}"
        assert self.beat_type in (2, 4, 8, 16), f"Invalid beat type {self.beat_type}"


@dataclass(frozen=True, eq=False)
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

@dataclass(frozen=True, eq=False)
class Expression(StandardScoreElement):
    expression: ExpressionType

    @classmethod
    def from_str(cls, onset: float, expression: str):
        expression = expression.lower()
        if expression == "invertedmordent":
            expression = "inverted-mordent"
        return cls(onset, ExpressionType(expression))

    @staticmethod
    def get_allowed_expressions():
        return set(x.value for x in ExpressionType)


@dataclass(frozen=True, eq=False)
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


@dataclass(frozen=True, eq=False)
class Dynamics(StandardScoreElement):
    dynamics: DynamicsType

    @classmethod
    def from_str(cls, onset: float, dynamics: str):
        return cls(onset, DynamicsType(dynamics))

    @staticmethod
    def get_allowed_dynamics():
        return set(x.value for x in DynamicsType)


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

    @classmethod
    def from_standard(cls, score: StandardScore) -> ScoreRepresentation:
        return score

    def to_standard(self) -> StandardScore:
        return self

    def iter(self):
        return self.elements.iter()

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
