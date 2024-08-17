# Implements various data structure representations for a score
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from ..score import M21Score

@dataclass(frozen=True)
class NoteRepresentation:
    """Each note is a detailed representation of a note in a score. A list of these uniquely represent a score.

    Implements the partitura representation.

    # Note time information
    onset_beat: float: The onset of the note in beats
    duration_beat: float: The duration of the note in beats
    onset_quarter: float: The onset of the note in quarter notes
    duration_quarter: float: The duration of the note in quarter notes
    onset_div: int: The onset of the note in divisions
    duration_div: int: The duration of the note in divisions

    # Note information
    pitch: int: The pitch of the note (C4 = 60)
    voice: int: The voice of the note
    id: str: The id of the note

    step: str: The step of the note
    alter: int: The alteration of the note
    octave: int: The octave of the note

    # Grace Notes
    is_grace: int: Whether the note is a grace note
    grace_type: str: The type of grace note

    # Key Signature
    ks_fifths: int: Number of sharps or flats in the key signature
    ks_mode: int: The key signature mode

    # Time Signature
    ts_beats: int: The numerator of the time signature
    ts_beat_type: int: The denominator of the time signature

    # Metrical information
    is_downbeat: int: Whether the note is a downbeat
    rel_onset_div: int: The relative onset of the note in divisions wrt the first beat of the current measure it is in
    tot_measure_div: int: The total number of divisions in the current measure
    """
    onset_beat: float
    duration_beat: float
    onset_quarter: float
    duration_quarter: float
    onset_div: int
    duration_div: int
    pitch: int
    voice: int
    id: str
    step_: str
    alter: int
    octave: int
    is_grace: int
    grace_type: str
    ks_fifths: int
    ks_mode: int
    ts_beats: int
    ts_beat_type: int
    is_downbeat: bool
    rel_onset_div: int
    tot_measure_div: int

    def __post_init__(self):
        assert self.step_ in ("C", "D", "E", "F", "G", "A", "B")

    def __repr__(self):
        accidental = "#" if self.alter == 1 else "b" if self.alter == -1 else ""
        return f"NoteRepresentation({self.step}{accidental}{self.octave} at t={self.onset_beat})"

    @property
    def step(self):
        """The step of the note"""
        assert self.step_ in ("C", "D", "E", "F", "G", "A", "B")
        return self.step_

    @classmethod
    def from_array(cls, array):
        return cls(
            onset_beat = float(array["onset_beat"]),
            duration_beat = float(array["duration_beat"]),
            onset_quarter = float(array["onset_quarter"]),
            duration_quarter = float(array["duration_quarter"]),
            onset_div = int(array["onset_div"]),
            duration_div = int(array["duration_div"]),
            pitch = int(array["pitch"]),
            voice = int(array["voice"]),
            id = array["id"],
            step_ = array["step"],
            alter = int(array["alter"]),
            octave = int(array["octave"]),
            is_grace = int(array["is_grace"]),
            grace_type = array["grace_type"],
            ks_fifths = int(array["ks_fifths"]),
            ks_mode = int(array["ks_mode"]),
            ts_beats = int(array["ts_beats"]),
            ts_beat_type = int(array["ts_beat_type"]),
            is_downbeat = bool(array["is_downbeat"]),
            rel_onset_div = int(array["rel_onset_div"]),
            tot_measure_div = int(array["tot_measure_div"])
        )

    @property
    def offset_beat(self):
        """The offset of the note in beats"""
        return self.onset_beat + self.duration_beat

    @property
    def offset_quarter(self):
        """The offset of the note in quarters"""
        return self.onset_quarter + self.duration_quarter

    def to_simple_note(self):
        from .scales import SimpleNote
        return SimpleNote.from_step_alter(self.step, self.alter)
