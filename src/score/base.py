from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Self, TypeVar
import enum

T = TypeVar('T', bound=ScoreRepresentation)
class ScoreRepresentation(ABC):
    """Defines an abstract class for score representation."""
    @abstractmethod
    def to_standard(self) -> StandardScore:
        """Converts the score to a standard score representation."""
        pass

    @classmethod
    @abstractmethod
    def from_standard(cls, score: StandardScore) -> ScoreRepresentation:
        """Converts a standard score representation to the current representation."""
        pass

    def conform(self: T) -> T:
        """Conforms the score to the current representation."""
        return self.from_standard(self.to_standard())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScoreRepresentation):
            return NotImplemented
        return self.to_standard() == other.to_standard()


class StandardScore(ScoreRepresentation):
    """Defines a standard score representation to which all scores must conform.
    Internally, the standard score is a list of tuples, where each tuple contains
    information about how to reconstruct a score
    """
