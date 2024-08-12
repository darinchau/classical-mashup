# A static module that provides functions to work with scales.
from __future__ import annotations
from typing import Literal
from functools import lru_cache
import re

class SimpleNote(tuple[
        Literal["C", "D", "E", "F", "G", "A", "B"], int, Literal[-2, -1, 0, 1, 2]
    ]):
    """A simplified representation of a note without any timing or absolute octave information."""
    _NOTE_LOOKUP: dict[str, tuple[Literal["C", "D", "E", "F", "G", "A", "B"], Literal[-2, -1, 0, 1, 2]]] = {
        "Cbb": ("C", -2),
        "Cb": ("C", -1),
        "C": ("C", 0),
        "C#": ("C", 1),
        "Cx": ("C", 2),
        "Dbb": ("D", -2),
        "Db": ("D", -1),
        "D": ("D", 0),
        "D#": ("D", 1),
        "Dx": ("D", 2),
        "Ebb": ("E", -2),
        "Eb": ("E", -1),
        "E": ("E", 0),
        "E#": ("E", 1),
        "Ex": ("E", 2),
        "Fbb": ("F", -2),
        "Fb": ("F", -1),
        "F": ("F", 0),
        "F#": ("F", 1),
        "Fx": ("F", 2),
        "Gbb": ("G", -2),
        "Gb": ("G", -1),
        "G": ("G", 0),
        "G#": ("G", 1),
        "Gx": ("G", 2),
        "Abb": ("A", -2),
        "Ab": ("A", -1),
        "A": ("A", 0),
        "A#": ("A", 1),
        "Ax": ("A", 2),
        "Bbb": ("B", -2),
        "Bb": ("B", -1),
        "B": ("B", 0),
        "B#": ("B", 1),
        "Bx": ("B", 2),
    }
    def __new__(cls,
                note: str,
                relative_octave: int = 0,
            ):
        # Just use a lookup table
        if note not in cls._NOTE_LOOKUP:
            raise ValueError(f"Invalid note {note}")
        note, sharps = cls._NOTE_LOOKUP[note]
        return super().__new__(cls, (note, relative_octave, sharps))

    @property
    def step(self):
        """Returns the diatonic step of the note"""
        return self[0]

    @property
    def note_name(self):
        """Returns the note name of the note"""
        if self[1] < 0:
            name = self.step + "_" * abs(self[1])
        elif self[1] > 0:
            name = self.step + "'" * self[1]
        else:
            name = self.step

        accidental = {
            -2: "bb",
            -1: "b",
            0: "",
            1: "#",
            2: "x"
        }[self[2]]
        return f"{name}{accidental}"

    def __repr__(self):
        return f"SimpleNote({self.note_name})"

    @property
    def pitch_number(self):
        """Let SimpleNote(C) = 0, returns the pitch number of the note"""
        return {
            "C": 0,
            "D": 2,
            "E": 4,
            "F": 5,
            "G": 7,
            "A": 9,
            "B": 11
        }[self.step] + self[1] * 12 + self[2]

    def __lt__(self, value: SimpleNote) -> bool:
        return self.pitch_number < value.pitch_number

MAJOR_SCALE = {
    SimpleNote("C"): [SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B")],
    SimpleNote("G"): [SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#")],
    SimpleNote("D"): [SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#")],
    SimpleNote("A"): [SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#")],
    SimpleNote("E"): [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#")],
    SimpleNote("B"): [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#")],
    SimpleNote("F#"): [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#")],
    SimpleNote("C#"): [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B#")],
    SimpleNote("F"): [SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E")],
    SimpleNote("Bb"): [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A")],
    SimpleNote("Eb"): [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D")],
    SimpleNote("Ab"): [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G")],
    SimpleNote("Db"): [SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C")],
    SimpleNote("Gb"): [SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F")],
    SimpleNote("Cb"): [SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("Fb"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb")],
}

HARMONIC_MINOR_SCALE = {
    SimpleNote("A"): [SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G#")],
    SimpleNote("E"): [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D#")],
    SimpleNote("B"): [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A#")],
    SimpleNote("F#"): [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E#")],
    SimpleNote("C#"): [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B#")],
    SimpleNote("G#"): [SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("Fx")],
    SimpleNote("D#"): [SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("Cx")],
    SimpleNote("A#"): [SimpleNote("A#"), SimpleNote("B#"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("Gx")],
    SimpleNote("D"): [SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C#")],
    SimpleNote("G"): [SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F#")],
    SimpleNote("C"): [SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("B")],
    SimpleNote("F"): [SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("E")],
    SimpleNote("Bb"): [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("A")],
    SimpleNote("Eb"): [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("D")],
    SimpleNote("Ab"): [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("Fb"), SimpleNote("G")],
}

MELODIC_MINOR_UP = {
    SimpleNote("A"): [SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#")],
    SimpleNote("E"): [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#")],
    SimpleNote("B"): [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#")],
    SimpleNote("F#"): [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#")],
    SimpleNote("C#"): [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B#")],
    SimpleNote("G#"): [SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("Fx")],
    SimpleNote("D#"): [SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B#"), SimpleNote("Cx")],
    SimpleNote("A#"): [SimpleNote("A#"), SimpleNote("B#"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("Gx")],
    SimpleNote("D"): [SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#")],
    SimpleNote("G"): [SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#")],
    SimpleNote("C"): [SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B")],
    SimpleNote("F"): [SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E")],
    SimpleNote("Bb"): [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A")],
    SimpleNote("Eb"): [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D")],
    SimpleNote("Ab"): [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G")],
}

MELODIC_MINOR_DOWN = {
    SimpleNote("A"): [SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G")],
    SimpleNote("E"): [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D")],
    SimpleNote("B"): [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A")],
    SimpleNote("F#"): [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E")],
    SimpleNote("C#"): [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B")],
    SimpleNote("G#"): [SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F")],
    SimpleNote("D#"): [SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C")],
    SimpleNote("A#"): [SimpleNote("A#"), SimpleNote("B#"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G")],
    SimpleNote("D"): [SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C")],
    SimpleNote("G"): [SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F")],
    SimpleNote("C"): [SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb")],
    SimpleNote("F"): [SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb")],
    SimpleNote("Bb"): [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab")],
    SimpleNote("Eb"): [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db")],
    SimpleNote("Ab"): [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("Fb"), SimpleNote("Gb")],
}
