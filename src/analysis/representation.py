# Implements various data structure representations for a score
from dataclasses import dataclass

@dataclass(frozen=True)
class NoteRepresentation:
    """Each note is a detailed representation of a note in a score. A list of these uniquely represent a score.

    Implements the partitura representation.

    onset_beat: float: The onset of the note in beats
    duration_beat: float: The duration of the note in beats
    onset_quarter: float: The onset of the note in quarters
    duration_quarter: float: The duration of the note in quarters
    onset_div: int: The onset of the note in divisions
    duration_div: int: The duration of the note in divisions
    pitch: int: The pitch of the note
    voice: int: The voice of the note
    id: str: The id of the note
    step: str: The step of the note
    alter: int: The alteration of the note
    octave: int: The octave of the note
    is_grace: int: Whether the note is a grace note
    grace_type: str: The type of grace note
    ks_fifths: int: Number of sharps or flats in the key signature
    ks_mode: int: The key signature mode
    ts_beats: int: The time signature beats
    ts_beat_type: int: The time signature beat type
    ts_mus_beats: int: The time signature musical beats
    is_downbeat: int: Whether the note is a downbeat
    rel_onset_div: int: The relative onset of the note in divisions
    tot_measure_div: int: The total measure divisions
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
    step: str
    alter: int
    octave: int
    is_grace: int
    grace_type: str
    ks_fifths: int
    ks_mode: int
    ts_beats: int
    ts_beat_type: int
    ts_mus_beats: int
    is_downbeat: int
    rel_onset_div: int
    tot_measure_div: int

    def __repr__(self):
        accidental = "#" if self.alter == 1 else "b" if self.alter == -1 else ""
        return f"NoteRepresentation({self.step}{accidental}{self.octave} at t={self.onset_beat})"

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
            step = array["step"],
            alter = int(array["alter"]),
            octave = int(array["octave"]),
            is_grace = int(array["is_grace"]),
            grace_type = array["grace_type"],
            ks_fifths = int(array["ks_fifths"]),
            ks_mode = int(array["ks_mode"]),
            ts_beats = int(array["ts_beats"]),
            ts_beat_type = int(array["ts_beat_type"]),
            ts_mus_beats = int(array["ts_mus_beats"]),
            is_downbeat = int(array["is_downbeat"]),
            rel_onset_div = int(array["rel_onset_div"]),
            tot_measure_div = int(array["tot_measure_div"])
        )
