from music21.key import KeySignature, Key
from music21.meter.base import TimeSignature
from music21.interval import Interval
from music21.spanner import Slur
from music21.clef import Clef, TrebleClef, BassClef
from music21.common.types import StepName
from music21.dynamics import Dynamic
from typing import Literal
from .base import M21Wrapper, TransposeType
from .note import M21Note
from .util import wrap

class M21TimeSignature(M21Wrapper[TimeSignature]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.numerator in (2, 3, 4, 6, 9, 12)
        assert self._data.denominator in (2, 4, 8)
        assert self.quarter_length == 0.0

    @property
    def numerator(self):
        return self._data.numerator

    @property
    def denominator(self):
        return self._data.denominator

    @property
    def ratio(self):
        return self._data.ratioString

    @staticmethod
    def from_string(s: str):
        """Create a TimeSignature object from a string. Use 'C' or 'common' for common time and 'C/' or 'cut' for cut time."""
        if s in ("C", "common"):
            ts = TimeSignature("4/4")
            ts.symbol = "common"
            return M21TimeSignature(ts)
        elif s in ("C/", "cut"):
            ts = TimeSignature("2/2")
            ts.symbol = "cut"
            return M21TimeSignature(ts)
        else:
            return M21TimeSignature(TimeSignature(s))


class M21KeySignature(M21Wrapper[KeySignature]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.sharps in range(-7, 8)
        assert not self._data.isNonTraditional
        assert self.quarter_length == 0.0

    @property
    def sharps(self):
        return self._data.sharps

    def transpose(self, interval: TransposeType):
        """Transpose the key signature by a certain interval."""
        if isinstance(interval, M21Wrapper):
            it = interval._data
        else:
            it = interval
        key = self._data.transpose(it)
        assert key is not None
        return M21KeySignature(key)

    def accidental_by_step(self, step: StepName) -> int:
        """Returns the accidental of a certain step in the key signature by step name

        ks = KeySignature(3) # 3 sharps
        ks.accidental_by_step('C') == 1
        ks.accidental_by_step('D') == 0
        ks.accidental_by_step('G-') == -2
        """
        accidental = self._data.accidentalByStep(step)
        if accidental is None:
            return 0
        return int(accidental.alter)


class M21Key(M21Wrapper[Key]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.mode in ("major", "minor")
        assert self._data.tonic.isTwelveTone()
        assert self._data.sharps in range(-7, 8)
        assert not self._data.isNonTraditional

    @property
    def tonic(self):
        return self._data.tonic.name

    @property
    def mode(self):
        return self._data.mode

    @property
    def sharps(self) -> int:
        assert self._data.sharps is not None
        return self._data.sharps

    def transpose(self, interval: str | int):
        """Transpose the key signature by a certain interval"""
        if isinstance(interval, M21Wrapper):
            it = interval._data
        else:
            it = interval
        key = self._data.transpose(it)
        assert key is not None
        return M21Key(key)

    def get_key_signature(self):
        """Cast this key object to a key signature object"""
        return M21KeySignature(self._data)

    def relative(self):
        """Return the relative key of the key. G major -> E minor"""
        return M21Key(self._data.relative)

    def parallel(self):
        """Return the parallel key of the key. G major -> G minor"""
        return M21Key(self._data.parallel)


class M21Interval(M21Wrapper[Interval]):
    def sanity_check(self):
        super().sanity_check()
        assert self._data.semitones == int(self._data.semitones)
        specifier = self._data.specifier
        assert specifier is not None and specifier.niceName in ("Perfect", "Major", "Minor", "Augmented", "Diminished")

    @property
    def semitones(self):
        return int(self._data.semitones)

    @property
    def is_consonant(self):
        """Returns True if the interval is consonant, aka one of P5, M3, m3, M6, m6, P1 or its compound derivatives"""
        return self._data.isConsonant()

    @property
    def name(self):
        """Returns the name of the interval. P5, M3, m3, etc."""
        return self._data.name

    @property
    def complement(self):
        """Returns the complement of the interval. P5 becomes P4"""
        return M21Interval(self._data.complement)

    @property
    def reverse(self):
        """Returns the reverse of the interval. P5 becomes P-5"""
        return M21Interval(self._data.reverse())

    @classmethod
    def from_name(cls, name: str):
        """Create an interval object from a name. P5, M3, m3, etc."""
        return cls(Interval(name))

    @classmethod
    def from_notes(cls, note1: M21Note, note2: M21Note):
        """Create an interval object from two notes"""
        return cls(Interval(noteStart=note1._data, noteEnd=note2._data))


class M21Slur(M21Wrapper[Slur]):
    @property
    def spanned_elements(self):
        """Returns a structure which indicates the notes spanned in the slur."""
        stream = self._data.getSpannedElements()
        return [wrap(x) for x in stream]

    def is_first(self, obj: M21Wrapper):
        """Returns True if the object is the first in the spanner"""
        return self._data.isFirst(obj._data)

    def is_last(self, obj: M21Wrapper):
        """Returns True if the object is the last in the wrapper"""
        return self._data.isLast(obj._data)


class M21TrebleClef(M21Wrapper[TrebleClef]):
    def sanity_check(self):
        super().sanity_check()
        assert self.name == "treble"
        assert self.octave_change == 0

    @property
    def name(self):
        """Returns the name """
        n = self._data.name
        if n == "treble":
            return "treble"
        raise ValueError(f"Unknown name for clef: {n}. Did you implicitly modify the clef?")

    @property
    def octave_change(self):
        """Returns the octave change of the clef"""
        return self._data.octaveChange

    @property
    def lowest_line(self):
        """Returns the lowest line of the clef"""
        return self._data.lowestLine

class M21BassClef(M21Wrapper[BassClef]):
    def sanity_check(self):
        super().sanity_check()
        assert self.name == "bass"
        assert self.octave_change == 0

    @property
    def name(self):
        """Returns the name """
        n = self._data.name
        if n == "bass":
            return "bass"
        raise ValueError(f"Unknown name for clef: {n}. Did you implicitly modify the clef?")

    @property
    def octave_change(self):
        """Returns the octave change of the clef"""
        return self._data.octaveChange

    @property
    def lowest_line(self):
        """Returns the lowest line of the clef"""
        return self._data.lowestLine

class M21Dynamics(M21Wrapper[Dynamic]):
    _VALUES = ("ppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "fp")

    def sanity_check(self):
        super().sanity_check()
        assert self._data.value in self._VALUES
        assert self.quarter_length == 0.0

    @property
    def value(self):
        """Returns the dynamic value of the articulation. ppp, pp, p, mp, mf, f, ff, fff, sf, fp"""
        # Use this for comparison instead of the string value to hint the type checker
        for v in self._VALUES:
            if v == self._data.value:
                return v
        raise ValueError(f"Unknown dynamic value: {self._data.value}")

    @property
    def name(self):
        """Returns the length shift of the articulation. 1 means no shift, 1.1 means 10% longer, 0.9 means 10% shorter"""
        return self._data.longName

    @staticmethod
    def from_string(s: str):
        """Create a Dynamics object from a string. Use 'ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff'"""
        if s not in M21Dynamics._VALUES:
            raise ValueError(f"Unknown dynamic value: {s}")
        return M21Dynamics(Dynamic(s))

_ALLOWED = [
    (TimeSignature, M21TimeSignature),
    (KeySignature, M21KeySignature),
    (Key, M21Key),
    (Interval, M21Interval),
    (Slur, M21Slur),
    (TrebleClef, M21TrebleClef),
    (BassClef, M21BassClef),
    (Dynamic, M21Dynamics)
]
