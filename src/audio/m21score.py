# Provides a wrapper for music21's Score class with some convenience functions

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
from music21.stream.base import Stream, Score, Part, Opus
import subprocess
from .audio import Audio
import warnings

class M21NoteTree:
    def __init__(self, start: Fraction, end: Fraction, obj: m21.base.Music21Object, children: list[M21NoteTree] | None = None):
        self.start = start
        self.end = end
        self.obj = obj
        self.children = children

    def make_repr(self, indent: int = 4):
        def make_repr_recursive(elem: M21NoteTree, current_indent: int):
            indent_str = " " * current_indent
            s = f"{indent_str}({elem.start} - {elem.end}) {elem.obj}"
            if elem.children is None:
                return s

            strs = [s]
            for c in elem.children:
                strs.append(make_repr_recursive(c, current_indent=current_indent+indent))
            return "\n".join(strs)
        return make_repr_recursive(self, 0)

    def __repr__(self):
        return self.make_repr(indent = 4)

class M21Score:
    def __init__(self, score: Score):
        if len(score.parts) != 2:
            warnings.warn(f"Expected 2 parts in a score but found {len(score.parts)}. Not a big deal but might break future code.")
        # TODO investigate and add support for parts / opus
        self._data = score

    @classmethod
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        # Purely for convenience
        test_cases = {
            "-test1": "resources/scores/Prelude in C Major.mid",
            "-test2": "resources/scores/Musical Offering BWV 1079.mxl"
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

    def make_tree(self):
        return make_tree(self._data)

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

def float_to_fraction_time(f: float | Fraction, *, limit_denom: int = m21.defaults.limitOffsetDenominator) -> Fraction:
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

def _build_tree_recursive(stream: Stream) -> list[M21NoteTree]:
    def pack_elem(in_element):
        start = in_element.getOffsetBySite(stream)
        start_timestamp = float_to_fraction_time(start)
        end = start + in_element.duration.quarterLength
        end_timestamp = float_to_fraction_time(end)
        return start_timestamp, end_timestamp

    children: list[M21NoteTree] = []
    for element in stream:
        start_timestamp, end_timestamp = pack_elem(element)
        if isinstance(element, Stream):
            c = _build_tree_recursive(element)
            children.append(M21NoteTree(start_timestamp, end_timestamp, element, children=c))
        else:
            children.append(M21NoteTree(start_timestamp, end_timestamp, element))
    return children

def make_tree(stream: Stream):
    return M21NoteTree(Fraction(), float_to_fraction_time(stream.duration.quarterLength), stream, _build_tree_recursive(stream))
