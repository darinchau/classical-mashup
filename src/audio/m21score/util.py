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
from ..audio import Audio
import warnings
from typing import Generic, TypeVar, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import M21Wrapper

T = TypeVar("T", bound=M21Object, covariant=True)
def wrap(obj: T) -> M21Wrapper[T]:
    """Attempts to wrap a music21 object into a wrapper class in the best possible way.
    Not advisable to use this function directly. Use the wrapper classes directly instead."""
    from . import (
        M21Note, M21Rest, M21Chord, M21Part, M21Score, M21Measure, M21Interval, M21Key,
        M21KeySignature, M21TimeSignature, M21StreamWrapper, M21Clef, M21Slur, M21Wrapper
    )
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
        (Slur, M21Slur),
        (Clef, M21Clef),
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
