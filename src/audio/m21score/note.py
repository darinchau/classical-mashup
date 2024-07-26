from .base import M21Wrapper, TransposeType
import music21 as m21
from music21.common.types import StepName

class M21Note(M21Wrapper[m21.note.Note]):
    """Represents a music21 Note object with some convenience functions and properties. A note must be a 12-tone pitched note with a certain duration and within the midi range."""
    def sanity_check(self):
        super().sanity_check()
        assert self._data.pitch.isTwelveTone()
        assert 0 <= self.midi_index < 128

    @property
    def name(self) -> str:
        """Return the name of the note in octave notation"""
        return self._data.pitch.nameWithOctave

    @property
    def frequency(self) -> float:
        """Returns the note frequency of the note"""
        return self._data.pitch.frequency

    @property
    def midi_index(self):
        """Returns the MIDI index of the note, where A=440 is index 69. Nice"""
        return int(self._data.pitch.ps)

    def transpose(self, interval: TransposeType):
        if isinstance(interval, M21Wrapper):
            it = interval._data
        else:
            it = interval
        note = self._data.transpose(interval, inPlace=False)
        assert note is not None
        return M21Note(note)

    @classmethod
    def from_name(cls, name: str, **kwargs):
        """Create a note object from a name. C4, D#5, etc.

        If quarter_length > 0, then this would override any kwargs that modify the duration of the created note"""
        # I just hope m21 would support 8th, 4th, 2nd
        if "type" in kwargs and kwargs["type"] in ("8th", "4th", "2nd"):
            kwargs["type"] = {
                "8th": "eighth",
                "4th": "quarter",
                "2nd": "half"
            }[kwargs["type"]]
        note = m21.note.Note(name, **kwargs)
        return cls(note)

    @property
    def step(self) -> StepName:
        """Returns the step name of the note. Must be one of 'C', 'D', 'E', 'F', 'G', 'A', 'B'."""
        return self._data.pitch.step

class M21Chord(M21Wrapper[m21.chord.Chord]):
    def sanity_check(self):
        super().sanity_check()
        _ = self.notes # This constructs the notes which will check if every note is a valid note

    @property
    def notes(self):
        """Return the notes that makes up the chord"""
        return tuple(M21Note(x) for x in self._data.notes)

    @property
    def name(self):
        """Returns the name of the chord"""
        return self._data.commonName

    @property
    def inversion(self):
        return self._data.inversion()

    def to_roman_numeral(self, key: str):
        """Convert the chord to a roman numeral in a certain key"""
        return m21.roman.romanNumeralFromChord(self._data, key)

    def to_closed_position(self):
        """Return a new chord object that is in closed position"""
        return M21Chord(self._data.closedPosition())

    @classmethod
    def from_roman_numeral(cls, rn: str, key: str):
        """Create a chord object from a roman numeral in a certain key"""
        return cls(m21.roman.RomanNumeral(rn, key))


class M21Rest(M21Wrapper[m21.note.Rest]):
    """Wrapper for music21 Rest object"""
    @property
    def name(self):
        """Returns the full name of the Rest object"""
        return self._data.fullName
