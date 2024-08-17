# A static module that provides functions to work with scales.
from __future__ import annotations
from typing import Literal
from functools import lru_cache
import re
import music21 as m21
import numpy as np
import typing
from dataclasses import dataclass

class ChordLabel(m21.note.Lyric):
    """A class that represents a chord label. Subclasses music21.note.Lyric so it can be added onto a note."""
    pass

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
LINE_OF_FIFTH.flags.writeable = False

@dataclass(frozen=True)
class SimpleNote:
    """A simplified representation of a note without any timing or absolute octave information."""
    note_name: str
    """note_name: The name of the note, like 'C' or 'D#'."""

    alter: int
    """alter: The accidental of the note. 0 for natural, -1 for flat, 1 for sharp, etc."""

    index: int
    """index: The number of sharps or flats in the note if it were in a Major key signature."""

    pitch_number: int
    """pitch_number: The pitch number of the note. Let SimpleNote(C) = 0."""

    def __init__(self, entry: str | int | np.ndarray):
        if isinstance(entry, np.ndarray) and entry.dtype == LINE_OF_FIFTH.dtype and entry.size == 1:
            _entry = entry[0]

        elif isinstance(entry, np.void) and entry.dtype == LINE_OF_FIFTH.dtype:
            _entry = typing.cast(np.ndarray, entry) # Just to make type checker happy

        elif isinstance(entry, int):
            _entry = LINE_OF_FIFTH[entry]

        elif isinstance(entry, str):
            _entry = LINE_OF_FIFTH[LINE_OF_FIFTH["note_name"] == entry]
            if _entry.size == 0:
                raise ValueError(f"Invalid note name {entry}")
            _entry = _entry[0]
        else:
            raise ValueError(f"Invalid entry {entry}")

        super().__setattr__("note_name", _entry["note_name"].item())
        super().__setattr__("alter", _entry["alter"].item())
        super().__setattr__("pitch_number", _entry["semitones"].item())
        super().__setattr__("index", _entry["index"].item())

    @property
    def step(self) -> Literal["C", "D", "E", "F", "G", "A", "B"]:
        """Returns the diatonic step of the note"""
        assert self.note_name[0] in ("C", "D", "E", "F", "G", "A", "B")
        return self.note_name[0]

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

    def get_interval(self, other: SimpleNote) -> str:
        """Returns the interval between two notes, where we assume that the other note is higher than the current note.
        If the interval is weird enough like a double augmented second, we return "Unknown"."""
        diff = other.index - self.index
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
        transposed_index = interval_entry["index"] + self.index
        if not transposed_index in range(-14, 20):
            raise ValueError(f"Invalid interval {interval}")
        return SimpleNote(LINE_OF_FIFTH[LINE_OF_FIFTH["index"] == transposed_index][0])

    @classmethod
    def from_pitch(cls, pitch: m21.pitch.Pitch) -> SimpleNote:
        """Creates a SimpleNote from a music21 pitch."""
        return cls(pitch.name.replace("-", "b").replace("##", "x"))

    @classmethod
    def from_note(cls, note: m21.note.Note) -> SimpleNote:
        """Creates a SimpleNote from a music21 note."""
        return cls.from_pitch(note.pitch)

    @classmethod
    def from_step_alter(cls, step: str, alter: int) -> SimpleNote:
        """Creates a SimpleNote from a step and an alter."""
        return cls(f"{step}{['bb', 'b', '', '#', 'x'][alter + 2]}")

    @classmethod
    def from_index(cls, index: int) -> SimpleNote:
        """Creates a SimpleNote from an index."""
        return cls(LINE_OF_FIFTH[LINE_OF_FIFTH["index"] == index][0])

    def __eq__(self, other: SimpleNote):
        return self.index == other.index
