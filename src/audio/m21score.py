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
from music21.common.types import OffsetQL
from music21.stream.base import Stream, Score, Part, Opus, Measure
from music21.note import Note, Rest
from music21.chord import Chord
import subprocess
from .audio import Audio
import warnings
from typing import Generic, TypeVar

T = TypeVar("T", bound=M21Object)
class M21Wrapper(Generic[T]):
    """The base wrapper class for music21 objects. All subclasses should inherit from this class."""
    def __init__(self, obj: T):
        self._data = obj
        self.sanity_check()

    def sanity_check(self):
        """A method to check certain properties on M21Objects. This poses certain guarantees on objects."""
        pass

    @property
    def duration(self) -> Duration:
        """Return the duration object of the underlying m21 object."""
        return self._data.duration

    @property
    def quarter_length(self) -> OffsetQL:
        """Return the duration of the object in quarter length."""
        return self.duration.quarterLength

    def copy(self):
        """Return a deep copy of the object."""
        return copy.deepcopy(self)

    def __repr__(self):
        return f"|<{self._data.__repr__()}>|"

class M21Note(M21Wrapper[Note]):
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

    def transpose(self, interval: str | int):
        note = self._data.transpose(interval, inPlace=False)
        assert note is not None
        return M21Note(note)

class M21Chord(M21Wrapper[Chord]):
    def sanity_check(self):
        for n in self.notes:
            n.sanity_check()

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
        return m21.roman.romanNumeralFromChord(self._data, key)


class M21Score(M21Wrapper[Score]):
    def __init__(self, score: Score):
        super().__init__(score)

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

    def show(self, fmt = None):
        """Calls the show method of the music21 Stream object. Refer to the music21 documentation for more information."""
        return self._data.show(fmt)

    @property
    def parts(self):
        """Returns the parts of the score as a list of Parts wrapper."""
        # TODO wrap each part in its own wrapper object, after we figure out the Parts and Measures wrapper
        return [M21Wrapper(x) for x in self._data.parts]

    def measure(self, measure_number: int):
        """Grabs a single measure specified by measure number"""
        return M21Wrapper(self._data.measure(measure_number))

    def measures(self, start: int, end: int):
        """Grabs a range of measure specified by measure number"""
        return M21Score(self._data.measures(start, end))

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
