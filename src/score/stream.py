from ..audio import Audio
from ..util import is_ipython
from .base import M21Wrapper, M21Object, IDType
from fractions import Fraction
from music21 import common
from music21.articulations import Accent, Staccato, Tenuto
from music21.articulations import Articulation
from music21.bar import Barline, Repeat
from music21.base import Music21Object as M21Object
from music21.chord import Chord
from music21.clef import Clef
from music21.common.types import OffsetQL, StepName
from music21.duration import Duration, GraceDuration, AppoggiaturaDuration
from music21.dynamics import Dynamic
from music21.expressions import Expression, Trill, Turn, Mordent, InvertedMordent, Fermata, TextExpression
from music21.instrument import Instrument
from music21.interval import Interval
from music21.key import KeySignature, Key
from music21.meter.base import TimeSignature
from music21.midi.translate import streamToMidiFile
from music21.note import NotRest, Note, Rest, Lyric, GeneralNote
from music21.stream.base import Stream, Score, Part, Measure, Opus, Voice, PartStaff
from typing import TypeVar, Generic, Iterable, Literal
import base64
import copy
import music21 as m21
import subprocess
import tempfile


class M21Score(M21Wrapper[Score]):
    """A score is a special wrapper for a music21 Score object. A score must contain parts which contain measures.
    This wrapper provides methods to access the parts and measures of the score.

    Score parts can additionally contain instruments since this seems to be a common use case in music21.

    Maybe we will support those 1-2 repeats in the future, but for now assume no repeats"""
    def sanity_check(self):
        # This checks the score as a generic stream, which indirectly asserts that a score cannot contain other scores
        check_stream(self._data)

        # A score can only contain parts
        # More accurately, it can only contain parts and metadata
        for part in self._data.iter():
            assert not isinstance(part, (
                Articulation, Barline, Clef, Dynamic, KeySignature, TimeSignature, GeneralNote,
                Instrument, Interval, Voice, Score, Measure, Opus
            )), f"Score can only contain parts and other special objects, not {part.__class__.__name__}"

            if isinstance(part, Part):
                for measure in part.iter():
                    assert not isinstance(measure, (
                        Articulation, Barline, Dynamic, GeneralNote, Interval, Voice, Score, Opus
                    )), f"Parts inside a score can only contain measures and other special objects, not {measure.__class__.__name__}"

        # Makes sure that all the part offsets are the same
        nparts = self.nparts
        for offset, parts in self._data.measureOffsetMap().items():
            assert len(parts) == nparts, f"Measure {offset} does not have the same number of parts as the score. {len(parts)} != {self.nparts}"

    def _sanitize_in_place(self):
        sanitize_m21object(self._data)
        self._fix_measure_numbers_in_place()
        self._check_measure_numbers()
        return self

    def __iter__(self):
        return self._data.iter()

    @property
    def notes(self):
        """Returns an iterator of notes in the stream"""
        ls = [n for n in self._data.recurse().notes if isinstance(n, Note)]
        ids = set()
        ls: list[Note] = []
        for n in self._data.recurse().notes:
            if isinstance(n, Note) and n.id not in ids:
                ls.append(n)
            ids.add(n.id)
        return ls

    @property
    def notes_and_rests(self):
        """Returns an iterator of notes and rests in the stream"""
        return [n for n in self._data.recurse().notesAndRests if isinstance(n, (Note, Chord, Rest))]

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

    def _normalize_audio_in_place(self):
        """Make all the notes in the stream have the same volume. Returns self"""
        for n in self._data.recurse().getElementsByClass((Note, Chord, Dynamic)):
            if isinstance(n, (Note, Chord)):
                n.volume = 0.5
            elif isinstance(n, Dynamic) and n.activeSite is not None:
                n.activeSite.remove(n)
        return self

    def to_audio(self,
                 sample_rate: int = 44100,
                 soundfont_path: str = "~/.fluidsynth/default_sound_font.sf2",
                 verbose: bool = False):
        """Convert a music21 Stream object to our Audio object."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mid") as f1,
            tempfile.NamedTemporaryFile(suffix=".wav") as f2
        ):
            self.copy()._normalize_audio_in_place().write_to_midi(f1.name)
            _convert_midi_to_wav(f1.name, f2.name, soundfont_path, sample_rate, verbose)
            return Audio.load(f2.name)

    def play(self):
        """A shorthand for self.to_audio().play()"""
        return self.to_audio().play()

    def _remove_all_grace_notes_in_place(self):
        """Remove all grace notes in the stream"""
        return _remove_all_grace_notes_in_place(self._data)

    @classmethod
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        return cls(_parse(path, Score))

    @property
    def parts(self):
        """Returns the parts of the score as an iterator of parts."""
        return self._data.parts

    @property
    def nparts(self):
        """Returns the number of parts in this score"""
        return len(self._data.parts)

    def measure_numbers(self):
        """Returns a list of measure numbers in the score. This list must be sorted"""
        measure_numbers: set[int] = set()
        for part in self._data.parts:
            for measure in part:
                if isinstance(measure, Measure):
                    measure_numbers.add(measure.number)
        assert all(x >= 0 for x in measure_numbers), "Measure numbers must be non-negative"
        return sorted(measure_numbers)

    @property
    def has_pickup(self):
        """Returns True if the score has a pickup measure. Will return False if the score has less than 3 measures since
        it is impossible to have a pickup measure in that case."""
        nmeasures = len(self._data.measureOffsetMap().keys())
        if nmeasures < 3:
            return False
        return m21.repeat.RepeatFinder(self._data).hasPickup()

    def get_measure(self, part_idx: int, measure_number: int) -> Measure:
        """Grabs a single measure specified by measure number"""
        if measure_number not in self.measure_numbers():
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        m = self._data.parts[part_idx].measure(measure_number)
        if m is None:
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        return m

    def _fix_measure_numbers_in_place(self):
        """Fix the measure numbers in the score to make it contiguous. This will expand repeats (when repeats are supported)
        Pickup measures will be labelled as measure 0."""
        ## TODO support repeats
        measure_map_keys = self._data.measureOffsetMap()
        offsets = sorted(measure_map_keys.keys())

        bar_number = 0 if self.has_pickup else 1
        for offset in offsets:
            for measure in measure_map_keys[offset]:
                measure.number = bar_number
            bar_number += 1
        return self

    def _check_measure_numbers(self):
        """Check if the measure numbers in the score are contiguous and start from 1. Pickup measures are allowed to start from 0.

        If any of the checks fail, an AssertionError will be raised."""
        measure_numbers = set(self.measure_numbers())

        if self.has_pickup:
            assert len(measure_numbers) > 1, "Score must have at least one measure"
            assert measure_numbers == set(range(max(measure_numbers) + 1)), "Measure numbers must be contiguous"
        elif len(measure_numbers) > 0:
            assert measure_numbers == set(range(1, max(measure_numbers) + 1)), "Measure numbers must be contiguous"

        for part in self._data.iter():
            if isinstance(part, Part):
                part_measure_number: set[int] = set()
                for measure in part.iter():
                    if isinstance(measure, Measure):
                        part_measure_number.add(measure.number)
                assert part_measure_number == measure_numbers, f"Part {part.id} does not have the same measure numbers as the score. {part_measure_number ^ measure_numbers}"

    def _convert_to_partitura(self):
        """Convert the score to a Partitura object."""
        import partitura as pt
        # The load_music21 method doesnt seem to work properly. This is more consistent
        tmp_path = self._data.write("musicxml")
        return pt.load_score(tmp_path)

    def get_note_representation_list(self):
        """Returns a list of NoteRepresentation objects for each note in the score

        The note representations are sorted by onset_beat and then pitch"""
        from ..analysis.representation import NoteRepresentation
        from partitura.utils.music import ensure_notearray
        extended_score_note_array = ensure_notearray(
            self._convert_to_partitura(),
            include_pitch_spelling=True, # adds 3 fields: step, alter, octave
            include_key_signature=True, # adds 2 fields: ks_fifths, ks_mode
            include_time_signature=True, # adds 2 fields: ts_beats, ts_beat_type
            include_metrical_position=True, # adds 3 fields: is_downbeat, rel_onset_div, tot_measure_div
            include_grace_notes=True # adds 2 fields: is_grace, grace_type
        )
        reps = [NoteRepresentation.from_array(x) for x in extended_score_note_array]
        return sorted(reps, key = lambda x: (x.onset_beat, x.pitch))

    @classmethod
    def from_tiny_notation(cls, notation: str):
        """Create a score from a tiny notation string"""
        tnc = m21.tinyNotation.Converter()

        class ChordState(m21.tinyNotation.State):
            def affectTokenAfterParse(self, n):
                super(ChordState, self).affectTokenAfterParse(n)
                return None # do not append Note object

            def end(self):
                ch = Chord(self.affectedTokens)
                ch.duration = self.affectedTokens[0].duration
                return ch

        tnc.bracketStateMapping['chord'] = ChordState
        tnc.load(f"tinyNotation: {notation}")
        return M21Score(Score(tnc.parse().stream))

Q = TypeVar("Q", bound=Stream)
def _parse(path: str, expected_type: type[Q]) -> Q:
    """Read a music21 Stream object from an XML file or a MIDI file."""
    # Purely for convenience
    test_cases = {
        "-test.prelude": "resources/scores/Prelude in C Major.mid",
        "-test.1079": "resources/scores/Musical Offering BWV 1079.mxl",
        "-test.fugue": "resources/scores/fugue.mxl",
        "-test.minuet": "resources/scores/Minuet_in_G_Major_Bach.mxl",
        "-test.furelise": "resources/scores/Bagatelle_No._25_in_A_minor__Fur_Elise.mid",
        "-test.bs1": "resources/scores/Beethoven Op 2 No 1.mxl"
    }
    if path in test_cases:
        path = test_cases[path]
    stream = m21.converter.parse(path)
    if not isinstance(stream, expected_type):
        raise ValueError(f"The file {path} is parsed as a {stream.__class__.__name__}, expecting {expected_type}.")

    return stream

### Checks ###

_ALLOWED_ARTICULATION = (Accent, Staccato, Tenuto)
_ALLOWED_EXPRESSION = (Trill, Turn, Mordent, InvertedMordent, Fermata, TextExpression)
_ALLOWED_BARLINE_TYPES = ("regular", "double", "final", "repeat", "heavy-light")
_ALLOWED_DYNAMICS = ("ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "fp")

def check_note_or_chord(obj: Note | Chord):
    assert all(p.isTwelveTone() for p in obj.pitches), "All pitches must be 12-tone"
    assert all(0 <= p.ps < 128 for p in obj.pitches), "MIDI index must be within 0-127"

def check_rest(obj: Rest):
    assert obj.duration.quarterLength > 0, "Rest must have a positive duration"

def check_expression(expression: Expression):
    assert expression.quarterLength == 0.0, "Expressions must have a duration of 0.0"
    assert isinstance(expression, _ALLOWED_EXPRESSION), f"Expression not supported: {expression}"

    if isinstance(expression, Trill):
        assert expression.accidental is None or expression.accidental.alter in (-1, 0, 1), f"Only trills with accidentals of -1, 0, 1 are supported, found: {expression.accidental}"
        assert expression.direction in ("up", "down"), f"Only up and down trills are supported, found: {expression.direction}"

    if isinstance(expression, Turn):
        assert expression.upperAccidental is None or expression.upperAccidental.alter in (-1, 0, 1), f"Only turns with accidentals of -1, 0, 1 are supported, found: {expression.upperAccidental}"
        assert expression.lowerAccidental is None or expression.lowerAccidental.alter in (-1, 0, 1), f"Only turns with accidentals of -1, 0, 1 are supported, found: {expression.lowerAccidental}"

    if isinstance(expression, Mordent):
        assert expression.direction in ("up", "down"), f"Only upper and lower mordents are supported, found: {expression.direction}"
        assert expression.accidental is None or expression.accidental.alter in (-1, 0, 1), f"Only mordents with accidentals of -1, 0, 1 are supported, found: {expression.accidental}"

    if isinstance(expression, Fermata):
        assert expression.shape == "normal", "Only normal fermatas are supported"


def check_barline(barline: Barline) -> None:
    assert barline.quarterLength == 0.0

def check_articulation(articulation: Articulation):
    """Checks if the articulation is supported"""
    assert isinstance(articulation, _ALLOWED_ARTICULATION), f"Articulation not supported: {articulation}"

def check_time_signature(ts: TimeSignature):
    assert ts.numerator in (2, 3, 4, 6, 9, 12)
    assert ts.denominator in (2, 4, 8)
    assert ts.quarterLength == 0.0

def check_key_signature(ks: KeySignature):
    assert ks.sharps in range(-7, 8)
    assert not ks.isNonTraditional
    assert ks.quarterLength == 0.0
    if isinstance(ks, Key):
        assert ks.mode in ("major", "minor")
        assert ks.tonic.isTwelveTone()

def check_interval(interval: Interval):
    assert False, "Do you really get an interval object inside a score?"
    assert interval.semitones == int(interval.semitones)
    specifier = interval.specifier
    assert specifier is not None and specifier.niceName in ("Perfect", "Major", "Minor", "Augmented", "Diminished")

def check_clef(clef: Clef):
    assert clef.name in ("treble", "bass")
    assert clef.octaveChange == 0

def check_dynamics(dynamics: Dynamic):
    assert dynamics.value in _ALLOWED_DYNAMICS
    assert dynamics.quarterLength == 0.0

def check_stream(stream: Stream):
    assert isinstance(stream, Score) or stream.activeSite is not None, "Stream must be attached to a site, except for the top level Score"
    for children in stream:
        try:
            check_obj(children, raise_assertion_error=True)
        except AssertionError:
            # Remove the children
            if not stream.activeSite:
                raise
            stream.activeSite.remove(children)
            print(f"Removed {children} from {stream} due to sanity check failure")

def check_score(score: Score):
    assert False, "Score should not be checked recursively"

def check_opus(opus: Opus):
    assert False, "Opus is not supported"

_CHECKS = {
    Note: check_note_or_chord,
    Chord: check_note_or_chord,
    Rest: check_rest,
    Expression: check_expression,
    Barline: check_barline,
    Articulation: check_articulation,
    TimeSignature: check_time_signature,
    KeySignature: check_key_signature,
    Interval: check_interval,   # Not sure if this is needed
    Clef: check_clef,
    Dynamic: check_dynamics,
    Instrument: lambda x: ...,
    Part: check_stream,
    Measure: check_stream,
    Score: check_score,
    Opus: check_opus,
    Stream: check_stream
}

def is_type_allowed(obj: M21Object):
    if isinstance(obj, Stream) and not isinstance(obj, Opus):
        return True
    for t in _CHECKS:
        if isinstance(obj, t):
            return True
    return False

def check_obj(obj: M21Object, raise_assertion_error: bool = False):
    for t in _CHECKS:
        if isinstance(obj, t):
            try:
                _CHECKS[t](obj)
                return True
            except AssertionError as e:
                if raise_assertion_error:
                    raise e
                return False
    return False

### Sanitize Methods ###

def sanitize_note_chord_or_rest(obj: Note | Chord | Rest):
    obj.lyrics.clear()

    obj.articulations = [a for a in obj.articulations if isinstance(a, _ALLOWED_ARTICULATION)] # type: ignore
    obj.expressions = [e for e in obj.expressions if isinstance(e, _ALLOWED_EXPRESSION)] # type: ignore

    if isinstance(obj, Note):
        obj.duration = Duration(obj.duration.quarterLength)

def sanitize_instrument(instrument: Instrument):
    piano = Instrument('piano')
    instrument.__dict__.update(piano.__dict__)
    return instrument

def sanitize_barline(barline: Barline):
    if barline.type not in _ALLOWED_BARLINE_TYPES:
        barline.type = "regular"

def sanitize_stream(stream: Stream):
    _remove_all_grace_notes_in_place(stream)
    for el in stream:
        # assert isinstance(el, M21Object), f"Element {el} is not a music21 object"
        if not is_type_allowed(el) or not check_obj(el):
            el.activeSite.remove(el)
            continue
        # Sanitize child
        sanitize_m21object(el)

def sanitize_m21object(obj: M21Object):
    if isinstance(obj, Stream):
        sanitize_stream(obj)
    elif isinstance(obj, (Note, Chord, Rest)):
        sanitize_note_chord_or_rest(obj)
    elif isinstance(obj, Instrument):
        sanitize_instrument(obj)
    elif isinstance(obj, Barline):
        sanitize_barline(obj)

### Other utility functions ###

def _remove_all_grace_notes_in_place(stream: Stream):
    def is_grace_note(n: Note | Chord):
        return isinstance(n.duration, GraceDuration)

    for el in stream.recurse():
        should_remove = isinstance(el, (Note, Chord)) and is_grace_note(el)
        if should_remove:
            assert el.activeSite is not None
            el.activeSite.remove(el)
    return stream

def _convert_midi_to_wav(input_path: str, output_path: str, soundfont_path="~/.fluidsynth/default_sound_font.sf2", sample_rate=44100, verbose=False):
    subprocess.call(['fluidsynth', '-ni', soundfont_path, input_path, '-F', output_path, '-r', str(sample_rate)],
        stdout=subprocess.DEVNULL if not verbose else None,
        stderr=subprocess.DEVNULL if not verbose else None)

def _float_to_fraction_time(f: OffsetQL, *, limit_denom: int = m21.defaults.limitOffsetDenominator, eps: float = 1e-6) -> Fraction:
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

def load_score_from_corpus(corpus_name: str, movement_number: int | None = None, **kwargs) -> M21Score:
    """Loads a piece from the music21 corpus"""
    from .stream import M21Score
    corpus = m21.corpus.parse(corpus_name, movement_number, **kwargs)

    if isinstance(corpus, Score):
        return M21Score(corpus)

    assert isinstance(corpus, Part), f"Unexpected type: {type(corpus)}"
    return M21Score(Score([corpus]))
