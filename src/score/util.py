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
from music21.articulations import Tenuto, Accent, Staccato
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
from ..audio import Audio
import warnings
from typing import Generic, TypeVar, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import M21Wrapper
    from .stream import M21Score, M21Part

def get_lookup() -> tuple[tuple[type[M21Object], type[M21Wrapper]], ...]:
    """Returns a list of all the allowed classes and their corresponding wrapper classes"""
    from .articulation import _ALLOWED as articulation_lookup
    from .expressions import _ALLOWED as expression_lookup
    from .symbol import _ALLOWED as symbol_lookup
    from .note import _ALLOWED as note_lookup
    from .stream import _ALLOWED as stream_lookup
    from .barline import _ALLOWED as barline_lookup
    from .instrument import _ALLOWED as instrument_lookup

    return articulation_lookup + expression_lookup + symbol_lookup + note_lookup + stream_lookup + barline_lookup + instrument_lookup

T = TypeVar("T", bound=M21Object, covariant=True)
def wrap(obj: T) -> M21Wrapper[T]:
    """Attempts to wrap a music21 object into a wrapper class in the best possible way.
    Not advisable to use this function directly. Use the wrapper classes directly instead."""
    from .base import M21Wrapper
    for cls, wrapper in get_lookup():
        if isinstance(obj, cls):
            return wrapper(obj)
    return M21Wrapper(obj)

def is_type_allowed(obj: M21Object):
    """Checks if the object is allowed to be wrapped"""
    from .stream import GraceNoteContext
    classes = tuple(cls for cls, _ in get_lookup()) + (GraceNoteContext,)
    return isinstance(obj, classes)

def check_obj(obj: M21Object) -> bool:
    """Checks if the object is valid for use for our purposes, i.e. it fits in our restrictions"""
    try:
        _ = wrap(obj)
        return True
    except AssertionError:
        return False

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

def float_to_fraction_time(f: OffsetQL, *, limit_denom: int = m21.defaults.limitOffsetDenominator, eps: float = 1e-6) -> Fraction:
    """Turn a float into a fraction
    limit_denom (int): Limits the denominator to be less than or equal to limit_denom

    Code referenced from music21.common.numberTools"""
    if not isinstance(f, Fraction):
        quotient, remainder = divmod(float(f), 1.)

        # Convert and check if the conversion is accurate. If it is not, then there are no matches
        rem = Fraction(remainder).limit_denominator(limit_denom)
        if abs(remainder - rem) > eps:
            raise ValueError(f"Could not convert {f} to a fraction with denominator limited to {limit_denom}")
        remainder = rem

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

def load_score_from_corpus(corpus_name: str, movement_number: int | None = None, sanitize: bool = True, **kwargs) -> M21Score:
    """Loads a piece from the music21 corpus"""
    from .stream import M21Score, M21Part
    corpus = m21.corpus.parse(corpus_name, movement_number, **kwargs)

    if isinstance(corpus, Score):
        return M21Score(corpus)

    assert isinstance(corpus, Part), f"Unexpected type: {type(corpus)}"
    return M21Score(Score([corpus]))

def load_part_from_corpus(corpus_name: str, movement_number: int | None = None, sanitize: bool = True, **kwargs) -> M21Part:
    """Loads a part from the music21 corpus. If it is a score, returns the first part"""
    from .stream import M21Part
    corpus = m21.corpus.parse(corpus_name, movement_number, **kwargs)

    if isinstance(corpus, Score):
        return M21Part(corpus.parts[0])

    assert isinstance(corpus, Part), f"Unexpected type: {type(corpus)}"
    return M21Part(corpus)
