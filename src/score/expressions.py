# An Expression is something that modifies the note in a way that is not pitch or timbre related. This includes trills, fermatas, appregios, etc..
from __future__ import annotations
import music21 as m21
from music21.expressions import (
    Expression, Trill, Turn, Mordent, InvertedMordent, Fermata, TextExpression, Ornament, GeneralMordent
)
from typing import TypeVar
from .base import M21Object, M21Wrapper
from .note import M21Note
from .symbol import M21Interval
from abc import ABC, abstractmethod

T = TypeVar("T", bound=Expression, covariant=True)
class M21Expression(M21Wrapper[T]):
    """Represents an articulation object in music21. This class should be inherited by all articulation classes."""
    @property
    def name(self):
        """Returns the name of the expression"""
        return self._data.name

    def realize(self, note: M21Note) -> tuple[list[M21Note], list[M21Note], list[M21Note]]:
        """Realizes the expression on the note. What we return is a tuple of three things:
        - prepend: The notes that would eat up the previous note. Something like a grace note
        - main_note: The note that modifies and replaces the expression. Something like a trill, turn, etc.
        - append: The notes that would eat up the following note. Currently unused.
        """
        # Default like a normal note. This is the case for stuff like a fermata, or a text expression
        return [], [note], []


class M21Trill(M21Expression[Trill]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.accidental is None or self._data.accidental.alter in (-1, 0, 1), f"Only trills with accidentals of -1, 0, 1 are supported, found: {self._data.accidental}"
        assert self._data.direction in ("up", "down"), f"Only up and down trills are supported, found: {self._data.direction}"

    @property
    def accidental(self):
        """Returns the accidental of the trill. Should be -1, 0, 1"""
        a = self._data.accidental
        if a is None:
            return 0.
        return a.alter

    @property
    def direction(self):
        """Returns the direction of the trill. Should be 'up' or 'down'"""
        if self._data.direction == "up":
            return "up"
        elif self._data.direction == "down":
            return "down"
        else:
            raise ValueError(f"Unknown trill direction: {self._data.direction}")

    @property
    def is_inverted(self):
        """Returns True if the trill is inverted, False otherwise."""
        return self.direction == "down"

    def get_interval(self, note: M21Note) -> M21Interval:
        """Returns the interval of the trill relative to the note"""
        interval = self._data.getSize(note._data)
        assert isinstance(interval, m21.interval.Interval)
        return M21Interval(interval)


class M21Turn(M21Expression[Turn]):
    """Represents a turn expression."""
    def sanity_check(self):
        assert self.upper_accidental in (-1, 0, 1), f"Only turns with accidentals of -1, 0, 1 are supported, found: {self.upper_accidental}"
        assert self.lower_accidental in (-1, 0, 1), f"Only turns with accidentals of -1, 0, 1 are supported, found: {self.lower_accidental}"

    @property
    def is_inverted(self):
        """Returns True if the turn is inverted, False otherwise. Notice a normal turn is the one without the |"""
        return self._data._isInverted

    @property
    def upper_accidental(self):
        """Returns the upper accidental of the turn. Should be -1, 0, 1"""
        a = self._data.upperAccidental
        if a is None:
            return 0.
        return a.alter

    @property
    def lower_accidental(self):
        """Returns the lower accidental of the turn. Should be -1, 0, 1"""
        a = self._data.lowerAccidental
        if a is None:
            return 0.
        return a.alter

    def get_upper_interval(self, note: M21Note) -> M21Interval:
        """Returns the interval of the turn relative to the note"""
        interval = self._data.getSize(note._data, "upper")
        assert isinstance(interval, m21.interval.Interval)
        return M21Interval(interval)

    def get_lower_interval(self, note: M21Note) -> M21Interval:
        """Returns the interval of the turn relative to the note"""
        interval = self._data.getSize(note._data, "lower")
        assert isinstance(interval, m21.interval.Interval)
        return M21Interval(interval)


class M21Mordent(M21Expression[GeneralMordent]):
    """Represents a mordent expression."""
    def sanity_check(self):
        super().sanity_check()
        assert self._data.direction in ("up", "down"), f"Only upper and lower mordents are supported, found: {self._data.direction}"
        assert self._data.accidental is None or self._data.accidental.alter in (-1, 0, 1), f"Only mordents with accidentals of -1, 0, 1 are supported, found: {self._data.accidental}"

    @property
    def direction(self):
        """Returns the direction of the mordent. Should be 'up' or 'down'"""
        if self._data.direction == "up":
            return "up"
        elif self._data.direction == "down":
            return "down"
        else:
            raise ValueError(f"Unknown mordent direction: {self._data.direction}")

    @property
    def is_inverted(self):
        """Returns True if the mordent is inverted, False otherwise. Notice a normal modernt is the one without the |"""
        return self.direction == "up"

    @property
    def accidental(self):
        """Returns the accidental of the mordent. Should be -1, 0, 1"""
        if self._data.accidental is None:
            return 0
        return self._data.accidental.alter

    def get_interval(self, note: M21Note) -> M21Interval:
        """Returns the interval of the mordent relative to the note"""
        interval = self._data.getSize(note._data)
        assert isinstance(interval, m21.interval.Interval) # This should always be true - I checked the source code
        # and it appears that the return type is always Interval
        return M21Interval(interval)


class M21Fermata(M21Expression[Fermata]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.shape == "normal", "Only normal fermatas are supported"

    @property
    def expression_type(self):
        """Returns the type of the fermata. Should be 'upright' or 'inverted'"""
        if self._data.shape == "upright":
            return "upright"
        elif self._data.shape == "inverted":
            return "inverted"
        else:
            raise ValueError(f"Unknown fermata shape: {self._data.shape}")


class M21TextExpression(M21Expression[TextExpression]):
    @classmethod
    def from_text(cls, text: str) -> M21TextExpression:
        return cls(TextExpression(text))

_ALLOWED = (
    (Trill, M21Trill),
    (Turn, M21Turn),
    (Mordent, M21Mordent),
    (InvertedMordent, M21Mordent),
    (Fermata, M21Fermata),
    (TextExpression, M21TextExpression)
)
