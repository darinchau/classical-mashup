# A music score class provides useful data classes for representing our piano music.
from dataclasses import dataclass
from .time_series import TimeSeries
from functools import lru_cache
from abc import ABC, abstractmethod

@lru_cache(maxsize=128)
def midi_to_freq(midi: int) -> float:
    """Convert a midi note to a frequency"""
    assert 0 <= midi <= 127
    return 2 ** ((midi - 69) / 12) * 440

def midi_to_note_name(midi: int) -> str:
    """Convert a midi note to a note name"""
    assert 0 <= midi <= 127
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note = notes[midi % 12]
    octave = midi // 12 - 1
    return f"{note}{octave}"

class Notation:
    def __new__(cls, *args, **kwargs):
        if cls is Notation:
            raise TypeError("MusicMarking class may not be instantiated")

@dataclass(frozen=True)
class Note(Notation):
    note_number: int
    duration: float

    def __post_init__(self):
        assert 0 <= self.note_number <= 127
        assert self.duration > 0

    @property
    def note_name(self) -> str:
        return midi_to_note_name(self.note_number)

    @property
    def frequency(self) -> float:
        return midi_to_freq(self.note_number)

    def __repr__(self):
        return f"Note({self.note_name})"

@dataclass(frozen=True)
class Pedal(Notation):
    duration: float

    def __post_init__(self):
        assert self.duration > 0

    def __repr__(self):
        return f"Pedal"

@dataclass(frozen=True)
class Rest(Notation):
    duration: float

    def __post_init__(self):
        assert self.duration > 0

    def __repr__(self):
        return f"Rest"

@dataclass(frozen=True)
class DynamicMarking(Notation):
    marking: str
    _ignore_check: bool = False

    def __post_init__(self):
        if not self._ignore_check:
            assert self.marking in ["ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "fp", "cresc.", "dim."]

    def __repr__(self):
        return f"DynamicMarking({self.marking})"

class MusicScore:
    @dataclass(frozen=True)
    class MusicMarking:
        """A class to specify the duration of each marking. The markings are stored in a list.
        For example, a Note(69) on starting_measure = 1, starting_subdivision = 0, ending_subdivision = 2, total_subdivisions = 4
        indicates that the note is played on the first measure, and has two beats in duration.
        Measure 0 is the pickup measure, and the first measure starts at 1.
        """
        marking: Notation
        starting_measure: int
        starting_subdivision: int
        ending_subdivision: int
        total_subdivisions: int
        voice: int

        def __post_init__(self):
            assert self.starting_measure >= 0
            assert 0 <= self.starting_subdivision < self.total_subdivisions
            if self.marking.__class__ in [Note, Rest]:
                assert 1 <= self.voice <= 4, "Voice must be between 1 and 4"
                assert self.starting_subdivision < self.ending_subdivision, "Ending subdivision must be greater than starting subdivision"

            if self.marking.__class__ in [Pedal, DynamicMarking]:
                assert self.voice == -1, "Voice must be -1 for Pedal and DynamicMarking"

    def __init__(self, tempo: int, time_signature: tuple[int, int]):
        self.markings: list[MusicScore.MusicMarking] = []
        self.tempo = tempo
        self.time_signature = time_signature
        assert time_signature[0] in (2, 3, 4, 5, 6, 9, 12), f"Time signature not supported: {time_signature}"
        assert time_signature[1] in (2, 4, 8), f"Time signature not supported: {time_signature}"

    def add_marking(self, marking: Notation, starting_measure: int, starting_subdivision: int, ending_subdivision: int, total_subdivisions: int, voice: int = -1):
        if voice == -1:
            if marking.__class__ in [Note, Rest]:
                voice = 1
            else:
                voice = -1
        markings = MusicScore.MusicMarking(
            marking=marking,
            starting_measure=starting_measure,
            starting_subdivision=starting_subdivision,
            ending_subdivision=ending_subdivision,
            total_subdivisions=total_subdivisions,
            voice=voice
        )

        #TODO perform validation checks, e.g. overlap checks
        self.markings.append(markings)
