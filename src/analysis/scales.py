# A static module that provides functions to work with scales.
from __future__ import annotations
from typing import Literal
from functools import lru_cache
import re
import music21 as m21

class ChordLabel(m21.note.Lyric):
    pass

class SimpleNote(tuple[
        Literal["C", "D", "E", "F", "G", "A", "B"], Literal[-2, -1, 0, 1, 2]
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

    _INTERVAL_LOOKUP: dict[tuple[int, int], str] = {
        (2, 0): "d2",
        (2, 1): "m2",
        (2, 2): "M2",
        (2, 3): "A2",
        (3, 2): "d3",
        (3, 3): "m3",
        (3, 4): "M3",
        (3, 5): "A3",
        (4, 4): "d4",
        (4, 5): "P4",
        (4, 6): "A4",
        (5, 6): "d5",
        (5, 7): "P5",
        (5, 8): "A5",
        (6, 7): "d6",
        (6, 8): "m6",
        (6, 9): "M6",
        (6, 10): "A6",
        (7, 9): "d7",
        (7, 10): "m7",
        (7, 11): "M7",
        (7, 0): "A7",
        (1, 11): "d8",
        (1, 0): "P8",
        (1, 1): "A8",
    }
    def __new__(cls, note: str,):
        # Just use a lookup table
        if note not in cls._NOTE_LOOKUP:
            raise ValueError(f"Invalid note {note}")
        note, sharps = cls._NOTE_LOOKUP[note]
        return super().__new__(cls, (note, sharps))

    @property
    def step(self):
        """Returns the diatonic step of the note"""
        return self[0]

    @property
    def alter(self):
        """Returns the accidental of the note"""
        return self[1]

    @property
    def note_name(self):
        """Returns the note name of the note"""
        accidental = {
            -2: "bb",
            -1: "b",
            0: "",
            1: "#",
            2: "x"
        }[self[1]]
        return f"{self.step}{accidental}"

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
    def pitch_number(self):
        """Let SimpleNote(C) = 0, returns the pitch number of the note."""
        return ({
            "C": 0,
            "D": 2,
            "E": 4,
            "F": 5,
            "G": 7,
            "A": 9,
            "B": 11
        }[self.step] + self[1]) % 12

    def get_pitch_dist(self, other: SimpleNote) -> int:
        """Returns the pitch distance between two notes, where we assume that the other note is higher than the current note."""
        nsteps = other.step_number - self.step_number + 1
        if nsteps < 1:
            nsteps += 7
        assert 1 <= nsteps <= 7
        return nsteps

    def get_semitone_dist(self, other: SimpleNote) -> int:
        """Returns the semitone distance between two notes, mod 12, where we assume that the other note is higher than the current note."""
        nsemitones = other.pitch_number - self.pitch_number
        if nsemitones < 0:
            nsemitones += 12
        assert 0 <= nsemitones <= 11
        return nsemitones

    def get_interval(self, other: SimpleNote) -> str:
        """Returns the interval between two notes, where we assume that the other note is higher than the current note.
        If the interval is weird enough like a double augmented second, we return "Unknown"."""
        nsteps = self.get_pitch_dist(other)
        nsemitones = self.get_semitone_dist(other)
        lookup = (nsteps, nsemitones)
        if lookup not in self._INTERVAL_LOOKUP:
            return "Unknown"
        return self._INTERVAL_LOOKUP[lookup]

    @classmethod
    def from_pitch(cls, pitch: m21.pitch.Pitch) -> SimpleNote:
        """Creates a SimpleNote from a music21 pitch."""
        return cls(pitch.name.replace("-", "b").replace("##", "x"))

    @classmethod
    def from_note(cls, note: m21.note.Note) -> SimpleNote:
        """Creates a SimpleNote from a music21 note."""
        return cls.from_pitch(note.pitch)

@lru_cache(maxsize=1)
def get_supported_scale_names():
    """Returns a list of supported scales."""
    return [
        "C Major",
        "G Major",
        "D Major",
        "A Major",
        "E Major",
        "B Major",
        "F# Major",
        "C# Major",
        "F Major",
        "Bb Major",
        "Eb Major",
        "Ab Major",
        "Db Major",
        "Gb Major",
        "Cb Major",
        "A Minor",
        "E Minor",
        "B Minor",
        "F# Minor",
        "C# Minor",
        "G# Minor",
        "D# Minor",
        "A# Minor",
        "D Minor",
        "G Minor",
        "C Minor",
        "F Minor",
        "Bb Minor",
        "Eb Minor",
        "Ab Minor",
    ]

@lru_cache(maxsize=1)
def get_scales():
    """Returns a mapping of scale names to the notes in the scale. Majors are majors and minors are harmonic minors."""
    mapping = {
        "C Major": [SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B")],
        "G Major": [SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#")],
        "D Major": [SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#")],
        "A Major": [SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#")],
        "E Major": [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#")],
        "B Major": [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#")],
        "F# Major": [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#")],
        "C# Major": [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B#")],
        "F Major": [SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E")],
        "Bb Major": [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A")],
        "Eb Major": [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D")],
        "Ab Major": [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G")],
        "Db Major": [SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C")],
        "Gb Major": [SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F")],
        "Cb Major": [SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("Fb"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb")],
        "A Minor": [SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G#")],
        "E Minor": [SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C"), SimpleNote("D#")],
        "B Minor": [SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G"), SimpleNote("A#")],
        "F# Minor": [SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D"), SimpleNote("E#")],
        "C# Minor": [SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A"), SimpleNote("B#")],
        "G# Minor": [SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E"), SimpleNote("Fx")],
        "D# Minor": [SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("G#"), SimpleNote("A#"), SimpleNote("B"), SimpleNote("Cx")],
        "A# Minor": [SimpleNote("A#"), SimpleNote("B#"), SimpleNote("C#"), SimpleNote("D#"), SimpleNote("E#"), SimpleNote("F#"), SimpleNote("Gx")],
        "D Minor": [SimpleNote("D"), SimpleNote("E"), SimpleNote("F"), SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C#")],
        "G Minor": [SimpleNote("G"), SimpleNote("A"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F#")],
        "C Minor": [SimpleNote("C"), SimpleNote("D"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("B")],
        "F Minor": [SimpleNote("F"), SimpleNote("G"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("E")],
        "Bb Minor": [SimpleNote("Bb"), SimpleNote("C"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("A")],
        "Eb Minor": [SimpleNote("Eb"), SimpleNote("F"), SimpleNote("Gb"), SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("D")],
        "Ab Minor": [SimpleNote("Ab"), SimpleNote("Bb"), SimpleNote("Cb"), SimpleNote("Db"), SimpleNote("Eb"), SimpleNote("Fb"), SimpleNote("G")],
    }

    # Perform some sanity checks
    for scale, notes in mapping.items():
        if len(notes) != 7:
            raise ValueError(f"Invalid scale {scale}")

        difference = [notes[i].get_interval(notes[i+1]) for i in range(6)] + [notes[6].get_interval(notes[0])]
        if "Major" in scale:
            assert difference == ["M2", "M2", "m2", "M2", "M2", "M2", "m2"]

        elif "Minor" in scale:
            assert difference == ["M2", "m2", "M2", "M2", "m2", "A2", "m2"]

        else:
            raise ValueError(f"Invalid scale {scale}")

    assert set(mapping.keys()) == set(get_supported_scale_names())
    return mapping
