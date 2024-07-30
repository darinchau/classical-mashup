import copy
from .base import M21Wrapper, TransposeType
import music21 as m21
from music21.note import NotRest, Note, Rest
from music21.chord import Chord
from music21.common.types import StepName, OffsetQL
from typing import Literal, Generic, TypeVar
from music21.duration import Duration, GraceDuration, AppoggiaturaDuration

def _wrap_upcast(obj):
    if isinstance(obj, Note):
        return M21Note(obj)
    elif isinstance(obj, Chord):
        return M21Chord(obj)
    else:
        raise ValueError(f"Cannot wrap object of type {type(obj)}")

T = TypeVar("T", bound=Note | Chord, covariant=True)
class M21NoteWrapper(M21Wrapper[T]):
    """Represents a music21 Note object with some convenience functions and properties. A note must be a 12-tone pitched note with a certain duration and within the midi range."""
    def sanity_check(self):
        super().sanity_check()
        assert isinstance(self._data, (Note, Chord))

    @property
    def pitches(self):
        """Return the pitches of the note"""
        return tuple(copy.deepcopy(x) for x in self._data.pitches)

    @property
    def name(self):
        """Returns a common name of the note"""
        return self._data.fullName

    def get_grace(self, appoggiatura: bool = False):
        """Returns a copy of the grace notes of the note"""
        return self._data.getGrace(appoggiatura=appoggiatura)

    @property
    def is_grace(self):
        """Returns True if the note or chord is a grace note"""
        return isinstance(self.duration, GraceDuration)

    @property
    def is_appoggiatura(self):
        """Returns True if the note or chord is an appoggiatura"""
        return isinstance(self.duration, AppoggiaturaDuration)

    def transpose(self, interval: TransposeType):
        if isinstance(interval, M21Wrapper):
            it = interval._data
        else:
            it = interval
        note = self._data.transpose(it, inPlace=False)
        assert note is not None
        return _wrap_upcast(note)

    def get_next_note(self):
        """Returns the next note or chord in the active stream"""
        next_note = self._data.next(NotRest)
        if next_note is None:
            return None
        return _wrap_upcast(next_note)

    def _get_associated_grace_note_ctx(self, as_parent: bool = False):
        """Used internally to get the grace note context associated with this note"""
        from .stream import GraceNoteContext
        if not as_parent and not self.is_grace:
            return

        active_site = self._data.activeSite
        if active_site is None:
            return
        ctxs = active_site.getElementsByClass(GraceNoteContext)
        if not ctxs:
            return
        ctx: GraceNoteContext | None = None
        for c in ctxs:
            if as_parent:
                if c.parent == self._data:
                    ctx = c
                    break
            else:
                if self._data in c:
                    ctx = c
                    break
        if ctx is None:
            return
        return ctx

    def get_grace_notes(self):
        """Returns a list of grace notes associated with the note"""
        ctx = self._get_associated_grace_note_ctx(as_parent=True)
        if ctx is None:
            return []

        return [_wrap_upcast(x) for x in ctx.notes]

    @property
    def is_grace_note(self):
        """Returns True the note is a grace note somewhere in a stream, associated with a note"""
        ctx = self._get_associated_grace_note_ctx(as_parent=False)
        return ctx is not None and ctx.note_type == "grace"

    @property
    def is_nachschlagen(self):
        """Returns True the note is a nachschlagen note somewhere in a stream, associated with a note"""
        ctx = self._get_associated_grace_note_ctx(as_parent=False)
        return ctx is not None and ctx.note_type == "nachschlagen"

    @property
    def has_grace_note_parent(self):
        """Returns True if the note is a grace note with a parent"""
        return self._get_associated_grace_note_ctx(as_parent=False) is not None

    @property
    def has_grace_note_child(self):
        """Returns True if the note has a grace note child"""
        return self._get_associated_grace_note_ctx(as_parent=True) is not None


class M21Note(M21NoteWrapper[Note]):
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
        note = Note(name, **kwargs)
        return cls(note)

    @property
    def step(self) -> StepName:
        """Returns the step name of the note. Must be one of 'C', 'D', 'E', 'F', 'G', 'A', 'B'."""
        return self._data.pitch.step


class M21Chord(M21Wrapper[Chord]):
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

    @classmethod
    def from_notes(cls, notes: list[M21Note]):
        """Create a chord object from a list of notes"""
        return cls(Chord([n._data for n in notes]))

    def transpose(self, interval: TransposeType):
        """Transpose the chord by a certain interval"""
        if isinstance(interval, M21Wrapper):
            it = interval._data
        else:
            it = interval
        chord = self._data.transpose(it, inPlace=False)
        assert chord is not None
        return M21Chord(chord)


class M21Rest(M21Wrapper[Rest]):
    """Wrapper for music21 Rest object"""
    @property
    def name(self):
        """Returns the full name of the Rest object"""
        return self._data.fullName
