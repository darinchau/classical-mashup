# Implements the partitura representation of a score
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from ..score import M21Score
from .standard import StandardScore, NoteElement
from .base import ScoreRepresentation
from typing import Iterable

@dataclass(frozen=True)
class PartituraNote:
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
        from .simplenote import SimpleNote
        return SimpleNote.from_step_alter(self.step, self.alter)

    def __lt__(self, other: PartituraNote):
        return (self.onset_beat, self.pitch) < (other.onset_beat, other.pitch)

class PartituraScore(ScoreRepresentation):
    """The partitura score is not really the partitura score - rather it is a list of notes that resembles the structured arrays of partitura scores.
    This way it is easy to convert to and from the standard score representation, but also easy to use in partitura-specific methods."""
    def __init__(self, notes: list[PartituraNote] | np.ndarray):
        if isinstance(notes, np.ndarray):
            notes = [PartituraNote.from_array(note) for note in notes]
        self.notes = notes

    def __eq__(self, other: PartituraScore):
        return sorted(self.notes) == sorted(other.notes)

    @classmethod
    def from_standard(cls, score: StandardScore) -> PartituraScore:
        return M21Score.from_standard(score).to_partitura()

    def to_standard(self) -> StandardScore:
        return StandardScore.from_array([
            NoteElement(
                onset = note.onset_quarter,
                duration = note.duration_quarter,
                note_name=note.to_simple_note(),
                octave=note.octave,
                voice=note.voice
            ) for note in self.notes
        ])

    def to_note_array(self):
        return np.array([
            (
                note.onset_beat,
                note.duration_beat,
                note.onset_quarter,
                note.duration_quarter,
                note.onset_div,
                note.duration_div,
                note.pitch,
                note.voice,
                note.id,
                note.step,
                note.alter,
                note.octave,
                note.is_grace,
                note.grace_type,
                note.ks_fifths,
                note.ks_mode,
                note.ts_beats,
                note.ts_beat_type,
                note.is_downbeat,
                note.rel_onset_div,
                note.tot_measure_div
            ) for note in self.notes
        ], dtype = [
            ('onset_beat', '<f4'),
            ('duration_beat', '<f4'),
            ('onset_quarter', '<f4'),
            ('duration_quarter', '<f4'),
            ('onset_div', '<i4'),
            ('duration_div', '<i4'),
            ('pitch', '<i4'),
            ('voice', '<i4'),
            ('id', '<U256'),
            ('step', '<U256'),
            ('alter', '<i4'),
            ('octave', '<i4'),
            ('is_grace', 'i1'),
            ('grace_type', '<U256'),
            ('ks_fifths', '<i4'),
            ('ks_mode', '<i4'),
            ('ts_beats', '<i4'),
            ('ts_beat_type', '<i4'),
            ('is_downbeat', '<i4'),
            ('rel_onset_div', '<i4'),
            ('tot_measure_div', '<i4')
        ])

    ### Helper conversion methods ###
    @classmethod
    def from_score(cls, score: ScoreRepresentation):
        if isinstance(score, M21Score):
            return score.to_partitura()
        return super().from_score(score)

    def note_elements(self) -> Iterable[NoteElement]:
        for x in sorted(self.notes, key=lambda x: (x.onset_quarter, x.pitch, x.duration_quarter)):
            yield NoteElement(
                onset = x.onset_quarter,
                duration = x.duration_quarter,
                note_name = x.to_simple_note(),
                octave = x.octave,
                voice = x.voice
            )
