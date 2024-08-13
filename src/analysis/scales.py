# A static module that provides functions to work with scales.
from __future__ import annotations
from typing import Literal
from functools import lru_cache
import re
import music21 as m21
import numpy as np
import typing

class ChordLabel(m21.note.Lyric):
    """A class that represents a chord label. Subclasses music21.note.Lyric so it can be added onto a note."""
    pass

_IS_SCALE_NAME = re.compile(r"^[CDEFGAB](#|x|b{1,2})? M(ajor|inor|inorN)$")

LINE_OF_FIFTH = np.array([
    ("Fbb", "", -2, 3, -14),
    ("Cbb", "", -2, 10, -14),
    ("Gbb", "", -2, 5, -13),
    ("Dbb", "d2", -2, 0, -12),
    ("Abb", "d6", -2, 7, -11),
    ("Ebb", "d3", -2, 2, -10),
    ("Bbb", "d7", -2, 9, -9),
    ("Fb", "d4", -1, 4, -8),
    ("Cb", "d8", -1, 11, -7),
    ("Gb", "d5", -1, 6, -6),
    ("Db", "m2", -1, 1, -5),
    ("Ab", "m6", -1, 8, -4),
    ("Eb", "m3", -1, 3, -3),
    ("Bb", "m7", -1, 10,- 2),
    ("F", "P4", 0, 5, -1),
    ("C", "P8", 0, 0, 0),
    ("G", "P5", 0, 7, 1),
    ("D", "M2", 0, 2, 2),
    ("A", "M6", 0, 9, 3),
    ("E", "M3", 0, 4, 4),
    ("B", "M7", 0, 11, 5),
    ("F#", "A4", 1, 6, 6),
    ("C#", "A8", 1, 1, 7),
    ("G#", "A5", 1, 8, 8),
    ("D#", "A2", 1, 3, 9),
    ("A#", "A6", 1, 10, 10),
    ("E#", "A3", 1, 5, 11),
    ("B#", "A7", 1, 0, 12),
    ("Fx", "", 2, 7, 13),
    ("Cx", "", 2, 2, 14),
    ("Gx", "", 2, 9, 15),
    ("Dx", "", 2, 4, 16),
    ("Ax", "", 2, 11, 17),
    ("Ex", "", 2, 6, 18),
    ("Bx", "", 2, 1, 19),
], dtype=[
    ("note_name", np.str_, 3), # note name
    ("transposition", np.str_, 2), # transposition wrt C
    ("alter", np.int8), # number of sharps added to the note
    ("semitones", np.int8), # number of semitones from C
    ("index", np.int8), # number of notes from C on the circle of fifths
])

class SimpleNote:
    """A simplified representation of a note without any timing or absolute octave information."""
    __slots__ = ("_entry",)
    def __init__(self, entry: str | int | np.ndarray):
        if isinstance(entry, np.ndarray) and entry.dtype == LINE_OF_FIFTH.dtype and entry.size == 1:
            self._entry = entry[0]

        elif isinstance(entry, np.void) and entry.dtype == LINE_OF_FIFTH.dtype:
            self._entry = typing.cast(np.ndarray, entry) # Just to make type checker happy

        elif isinstance(entry, int):
            self._entry = LINE_OF_FIFTH[entry]

        elif isinstance(entry, str):
            entry_ = LINE_OF_FIFTH[LINE_OF_FIFTH["note_name"] == entry]
            if entry_.size == 0:
                raise ValueError(f"Invalid note name {entry}")
            self._entry = entry_[0]
        else:
            raise ValueError(f"Invalid entry {entry}")

        # TODO perform validation if necessary
        ...

    @property
    def step(self) -> str:
        """Returns the diatonic step of the note"""
        return self._entry["note_name"].item()[0]

    @property
    def alter(self) -> int:
        """Returns the accidental of the note"""
        return self._entry["alter"].item()

    @property
    def note_name(self) -> str:
        """Returns the note name of the note"""
        return self._entry["note_name"].item()

    def __repr__(self):
        return f"SimpleNote({self.note_name})"

    @property
    def step_number(self):
        """Returns the diatonic step number of the note. C is 0, D is 1, etc."""
        return {
            "C": 0,
            "D": 1,
            "E": 2,
            "F": 3,
            "G": 4,
            "A": 5,
            "B": 6
        }[self.step]

    @property
    def pitch_number(self) -> int:
        """Let SimpleNote(C) = 0, returns the pitch number of the note."""
        return self._entry["semitones"].item()

    def get_interval(self, other: SimpleNote) -> str:
        """Returns the interval between two notes, where we assume that the other note is higher than the current note.
        If the interval is weird enough like a double augmented second, we return "Unknown"."""
        diff = other._entry["index"] - self._entry["index"]
        if diff < -14 or diff > 19:
            return "Unknown"
        interval = LINE_OF_FIFTH[LINE_OF_FIFTH["index"] == diff][0]["transposition"]
        return interval

    def transpose(self, interval: str) -> SimpleNote:
        """Transposes the note by a given interval."""
        transpotition_entry = LINE_OF_FIFTH["transposition"] == interval
        if transpotition_entry.size == 0:
            raise ValueError(f"Invalid interval {interval}")
        interval_entry = LINE_OF_FIFTH[transpotition_entry][0]
        return SimpleNote(LINE_OF_FIFTH[LINE_OF_FIFTH["index"] == interval_entry["index"] + self._entry["index"]][0])

    @classmethod
    def from_pitch(cls, pitch: m21.pitch.Pitch) -> SimpleNote:
        """Creates a SimpleNote from a music21 pitch."""
        return cls(pitch.name.replace("-", "b").replace("##", "x"))

    @classmethod
    def from_note(cls, note: m21.note.Note) -> SimpleNote:
        """Creates a SimpleNote from a music21 note."""
        return cls.from_pitch(note.pitch)

    def __eq__(self, other: SimpleNote):
        return self._entry["index"] == other._entry["index"]

def is_scale_supported(scale: str):
    """Returns a list of supported scales."""
    return _IS_SCALE_NAME.match(scale) is not None

_C_index = np.where(LINE_OF_FIFTH["note_name"] == "C")[0][0]
@lru_cache(maxsize=24)
def get_scales(scale: str):
    """Returns a mapping of scale names to the notes in the scale. Majors are majors and minors are harmonic minors.

    If you want natural minors, use MinorN"""
    note_name, major_minor = scale.split(" ")
    self_abs_idx = SimpleNote(note_name)._entry["index"] + _C_index
    if  major_minor == "Major":
        arr = np.array([0, 2, 4, -1, 1, 3, 5])
    elif major_minor == "Minor":
        arr = np.array([0, 2, -3, -1, 1, -4, 5])
    elif major_minor == "MinorN":
        arr = np.array([0, 2, -3, -1, 1, -4, -2])
    else:
        raise ValueError(f"Invalid scale {scale}")
    return [SimpleNote(entry) for entry in LINE_OF_FIFTH[self_abs_idx + arr]]
