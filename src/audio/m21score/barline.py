from music21.bar import Barline, Repeat
from typing import Literal
from .base import M21Wrapper

class M21Barline(M21Wrapper[Barline]):
    _ALLOWED_TYPES = ("regular", "double", "final", "repeat", "heavy-light")

    def sanity_check(self):
        super().sanity_check()
        assert self.quarter_length == 0.0
        if isinstance(self._data, Repeat):
            assert self._data.direction in ("start", "end")

    def _sanitize_in_place(self):
        if self._data.type not in self._ALLOWED_TYPES:
            self._data = Barline('regular')
        if isinstance(self._data, Repeat):
            self._data.times = 2
        return self

    @property
    def type(self):
        s = self._data.type
        for t in self._ALLOWED_TYPES:
            if s == t:
                return t
        raise ValueError(f"Unknown barline type: {s}")

    @property
    def direction(self):
        if isinstance(self._data, Repeat):
            if self._data.direction == "start":
                return "start"
            if self._data.direction == "end":
                return "end"
            raise ValueError(f"Unknown repeat direction: {self._data.direction}")
        return None

_ALLOWED = (
    (Barline, M21Barline),
)
