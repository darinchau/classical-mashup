from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Self, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .standard import StandardScore

class ScoreRepresentation(ABC):
    """Defines an abstract class for score representation. All score representations must conform to this class and convert to and from standard representation."""
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
T = TypeVar('T', bound=ScoreRepresentation)
