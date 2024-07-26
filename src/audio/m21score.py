# Provides a wrapper for music21's classes with some convenience functions
# This is because music21's classes are very general. By imposing certain restrictions
# from the scope of our project, we can make the code easier (for me) to reason about.

from __future__ import annotations
from fractions import Fraction
from dataclasses import dataclass
import music21 as m21
import copy
from music21.midi.translate import streamToMidiFile
import tempfile
from src.util import is_ipython
import base64
from music21 import common
from music21.base import Music21Object as M21Object
from music21.duration import Duration
from music21.common.types import OffsetQL, StepName
from music21.stream.base import Stream, Score, Part, Opus, Measure
from music21.note import Note, Rest
from music21.chord import Chord
from music21.key import KeySignature, Key
from music21.meter.base import TimeSignature
from music21.interval import Interval
from music21.clef import Clef
from music21.spanner import Slur
import subprocess
from .audio import Audio
import warnings
from typing import Generic, TypeVar, Iterable

T = TypeVar("T", bound=M21Object, covariant=True)
T2 = TypeVar("T2", bound=M21Object)
class M21Wrapper(Generic[T]):
    """The base wrapper class for music21 objects. All subclasses should inherit from this class."""
    def __init__(self, obj: T, *, skip_check: bool = False):
        self._data = obj
        self._checked = skip_check
        if not self._checked:
            self.sanity_check()
        assert self._checked, f"The object {self._data} has not been sanity checked. Have you called sanity_check() on the parent class?"

    def sanity_check(self):
        """A method to check certain properties on M21Objects. This poses certain guarantees on objects."""
        # Checks the base type
        try:
            base_ty = self.__orig_bases__[0].__args__[0]
            assert isinstance(self._data, base_ty)
        except (AttributeError, IndexError, TypeError):
            pass
        self._checked = True

    @property
    def duration(self) -> Duration:
        """Return a copy of the duration object of the underlying m21 object."""
        duration = self._data.duration
        return copy.deepcopy(duration)

    @property
    def quarter_length(self) -> OffsetQL:
        """Return the duration of the object in quarter length."""
        return self.duration.quarterLength

    def get_context_by_class(self, cls: type[T2]) -> M21Wrapper[T2] | None:
        """Return the parent object of the object that is an instance of cls."""
        ctx = self._data.getContextByClass(cls)
        return wrap(ctx) if ctx is not None else None

    @property
    def part(self):
        """Returns a Part object that the object belongs to, if it exists."""
        ctx = self._data.getContextByClass(Part)
        return M21Part(ctx) if ctx is not None else None

    @property
    def score(self):
        """Returns a Score object that the object belongs to, if it exists."""
        ctx = self._data.getContextByClass(Score)
        return M21Score(ctx) if ctx is not None else None

    def copy(self):
        """Return a deep copy of the object."""
        return copy.deepcopy(self)

    def show(self, fmt = None):
        """Calls the show method of the music21 Stream object. Refer to the music21 documentation for more information."""
        return self._data.show(fmt)

    def __repr__(self):
        return f"<|{self._data.__repr__()}|>"

    @property
    def id(self):
        """Returns a unique integer representing this object"""
        return self._data.id

    def set_duration(self, quarter_length: float):
        new_obj = self.copy()
        new_obj._data.duration.quarterLength = quarter_length
        return new_obj


TransposeType = str | int | M21Wrapper[Interval]

class M21Note(M21Wrapper[Note]):
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


class M21Rest(M21Wrapper[Rest]):
    """Wrapper for music21 Rest object"""
    @property
    def name(self):
        """Returns the full name of the Rest object"""
        return self._data.fullName


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


Q = TypeVar("Q", bound=Stream)
class M21StreamWrapper(M21Wrapper[Q]):
    """Wrapper for music21 Stream object. Provides methods to iterate over the stream."""
    def sanity_check(self):
        super().sanity_check()
        for children in self:
            pass

    def __iter__(self):
        for children in self._data:
            yield wrap(children)

    @property
    def notes(self):
        """Returns an iterator of notes in the stream"""
        return [M21Note(n) for n in self._data.recurse().notes if isinstance(n, Note)]

    @property
    def rests(self):
        """Returns an iterator of rests in the stream"""
        return [M21Rest(n) for n in self._data.recurse().notes if isinstance(n, Rest)]

    def show(self, fmt = None):
        """Calls the show method of the music21 Stream object. Refer to the music21 documentation for more information."""
        return self._data.show(fmt)

    def add_grace_note(self, note: M21Note | M21Chord, grace_notes: Iterable[M21Note | M21Chord], *,
                       slur: bool = True,
                       appoggiatura: bool = False,
                       override_priority: bool = False):
        """Add grace notes to the note. The grace note will be inserted before the note and after any other grace notes. Returns the new stream.
        The function will also implicitly modify all the notes in the grace_notes list to become the added grace_notes

        Extra parameters:
        slur (bool): Whether to add a slur to the whole thing or no
        appogiatura (bool): Whether to add an appoggiatura or a slashed grace note (acciaccatura)
        override_priority (bool): Whether to automatically change the priority of grace notes. Set to True if the order of grace notes are not expected"""
        def wrap(x: Note | Chord):
            if isinstance(x, Note):
                return M21Note(x)
            elif isinstance(x, Chord):
                return M21Chord(x)
            else:
                raise ValueError(f"Unknown type found for note: {x.__class__}")

        new_stream = self.copy()

        # Find the corresponding note in the copied stream
        copied_note = [n for n in new_stream._data.recurse().notes if n.derivation.origin is not None and n.derivation.origin.id == note.id]
        if not copied_note:
            raise ValueError(f"Note {note.id} not found in {self}")
        copied_note = copied_note[0]

        # Perform some checks on copied_note. We perform type checks on the ._data to account for subclasses
        assert len(copied_note.pitches) > 0
        assert all(p.isTwelveTone() for p in copied_note.pitches)
        copied_note = wrap(copied_note)

        _ = [x._data.getGrace(appoggiatura=appoggiatura, inPlace=True) for x in grace_notes]
        grace_notes = [x for x in grace_notes if x is not None]

        active_site = copied_note._data.activeSite
        if active_site is None:
            raise ValueError(f"Note {note.id} is currently not active")

        offset = copied_note._data.getOffsetBySite(active_site)
        for i, gn in enumerate(reversed(grace_notes)):
            active_site.insert(offset, gn._data)
            if override_priority:
                gn._data.priority = copied_note._data.priority - i - 1

        if slur:
            sl = m21.spanner.Slur([gn._data for gn in grace_notes] + [copied_note._data])
            active_site.insert(0.0, sl)
        return new_stream

    def add_nachschlagen(self, note: M21Note | M21Chord, grace_notes: Iterable[M21Note | M21Chord], *, override_priority: bool = False):
        """Adds a nachschlagen to a note. A nachschlagen is the little flourish notes after a trill that indicates the resolve of a trill."""
        stream = self.add_grace_note(note=note, grace_notes=grace_notes, slur=False, appoggiatura=True, override_priority=override_priority)
        copied_note = [n for n in stream._data.recurse().notes if n.derivation.origin is not None and n.derivation.origin.id == note.id][0]
        for i, gn in enumerate(grace_notes):
            gn._data.priority = copied_note.priority + 1 + i
        return stream


class M21Measure(M21StreamWrapper[Measure]):
    """Wrapper for a music21 Measure object"""
    pass


class M21Part(M21StreamWrapper[Part]):
    """Wrapper for music21 Part object"""
    def measure(self, measure_number: int):
        """Grabs a single measure specified by measure number"""
        measure = self._data.measure(measure_number)
        if measure is None:
            raise ValueError(f"Measure {measure_number} does not exist in the part.")
        return M21Measure(measure)


class M21Score(M21StreamWrapper[Score]):
    @classmethod
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        # Purely for convenience
        test_cases = {
            "-test.prelude": "resources/scores/Prelude in C Major.mid",
            "-test.1079": "resources/scores/Musical Offering BWV 1079.mxl"
        }
        if path in test_cases:
            path = test_cases[path]
        score = m21.converter.parse(path)
        if not isinstance(score, Score):
            raise ValueError(f"The file {path} is parsed as a {score.__class__.__name__} which is not supported yet.")
        return cls(score)

    def write_to_midi(self, path: str):
        """Write a music21 Stream object to a MIDI file."""
        file = streamToMidiFile(self._data, addStartDelay=True)
        file.open(path, "wb")
        try:
            file.write()
        finally:
            file.close()

    def to_binary_midi(self):
        """Convert a music21 Stream object to a binary MIDI file."""
        with tempfile.NamedTemporaryFile(suffix='.mid') as f:
            self.write_to_midi(f.name)
            with open(f.name, 'rb') as fp:
                binary_midi_data = fp.read()

        return binary_midi_data

    def play(self):
        """Play the score inside Jupyter."""
        assert is_ipython(), "This function can only be called inside Jupyter."
        play_binary_midi_m21(self.to_binary_midi())

    def to_audio(self,
                 sample_rate: int = 44100,
                 soundfont_path: str = "~/.fluidsynth/default_sound_font.sf2",
                 verbose: bool = False):
        """Convert a music21 Stream object to our Audio object."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mid") as f1,
            tempfile.NamedTemporaryFile(suffix=".wav") as f2
        ):
            self.write_to_midi(f1.name)
            convert_midi_to_wav(f1.name, f2.name, soundfont_path, sample_rate, verbose)
            return Audio.load(f2.name)

    @property
    def parts(self):
        """Returns the parts of the score as a list of Parts wrapper."""
        return [M21Part(x) for x in self._data.parts]

    def measure(self, measure_number: int):
        """Grabs a single measure specified by measure number"""
        return M21Score(self._data.measure(measure_number))

    def measures(self, start: int, end: int):
        """Grabs a range of measure specified by measure number"""
        return M21Score(self._data.measures(start, end))


def wrap(obj: T2) -> M21Wrapper[T2]:
    """Attempts to wrap a music21 object into a wrapper class in the best possible way.
    Not advisable to use this function directly. Use the wrapper classes directly instead."""
    class_lookup = [
        (Note, M21Note),
        (Rest, M21Rest),
        (Chord, M21Chord),
        (Part, M21Part),
        (Score, M21Score),
        (Measure, M21Measure),
        (Interval, M21Interval),
        (Key, M21Key),
        (KeySignature, M21KeySignature),
        (TimeSignature, M21TimeSignature),
        (Stream, M21StreamWrapper)
    ]
    for cls, wrapper in class_lookup:
        if obj.isClassOrSubclass((cls,)):
            return wrapper(obj)
    return M21Wrapper(obj)


def play_binary_midi_m21(b: bytes):
    """Play a midi file in bytes inside Jupyter"""
    # Code referenced from music21/music21/ipython21/converters
    assert is_ipython()
    from IPython.display import display, HTML
    b64 = base64.b64encode(b)
    s = common.SingletonCounter()
    output_id = 'midiPlayerDiv' + str(s())

    load_require_script = '''
        <script
        src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js"
        ></script>
    '''

    utf_binary = b64.decode('utf-8')
    display(HTML('''
        <div id="''' + output_id + '''"></div>
        <link rel="stylesheet" href="https://cuthbertLab.github.io/music21j/css/m21.css">
        ''' + load_require_script + '''
        <script>
        function ''' + output_id + '''_play() {
            const rq = require.config({
                paths: {
                    'music21': 'https://cuthbertLab.github.io/music21j/releases/music21.debug',
                }
            });
            rq(['music21'], function(music21) {
                mp = new music21.miditools.MidiPlayer();
                mp.addPlayer("#''' + output_id + '''");
                mp.base64Load("data:audio/midi;base64,''' + utf_binary + '''");
            });
        }
        if (typeof require === 'undefined') {
            setTimeout(''' + output_id + '''_play, 2000);
        } else {
            ''' + output_id + '''_play();
        }
        </script>'''))

def convert_midi_to_wav(input_path: str, output_path: str, soundfont_path="~/.fluidsynth/default_sound_font.sf2", sample_rate=44100, verbose=False):
    subprocess.call(['fluidsynth', '-ni', soundfont_path, input_path, '-F', output_path, '-r', str(sample_rate)],
        stdout=subprocess.DEVNULL if not verbose else None,
        stderr=subprocess.DEVNULL if not verbose else None)

def float_to_fraction_time(f: OffsetQL, *, limit_denom: int = m21.defaults.limitOffsetDenominator) -> Fraction:
    """Turn a float into a fraction
    limit_denom (int): Limits the denominator to be less than or equal to limit_denom

    Code referenced from music21.common.numberTools"""
    if not isinstance(f, Fraction):
        quotient, remainder = divmod(float(f), 1.)
        remainder = Fraction(remainder).limit_denominator(limit_denom)
        if quotient < -1:
            quotient += 1
            remainder = 1 - remainder
        elif quotient == -1:
            quotient = 0.0
            remainder = remainder - 1
    else:
        quotient = int(float(f))
        remainder = f - quotient
        if quotient < 0:
            remainder *= -1

    return int(quotient) + remainder
