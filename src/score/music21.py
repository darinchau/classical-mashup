from __future__ import annotations

from src.score.standard import NoteElement

from ..audio import Audio
from ..util import is_ipython
from .base import ScoreRepresentation
from .standard import StandardScore, StandardScoreElement, NoteElement, DynamicsType, ExpressionType
from .standard import (
    KeySignature as StandardKeySignature,
    TimeSignature as StandardTimeSignature,
    Tempo as StandardTempo,
    Dynamics as StandardDynamics,
    Expression as StandardExpression,
    TextExpression as StandardTextExpression,
)
from .simplenote import SimpleNote
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
from music21.tempo import MetronomeMark
from typing import TypeVar, Generic, Iterable, Literal
import base64
import copy
import music21 as m21
import subprocess
import tempfile
import warnings

_MUSIC21_SETUP = False

def setup():
    from music21 import environment
    global _MUSIC21_SETUP
    if _MUSIC21_SETUP:
        return

    us = environment.UserSettings()
    us['musescoreDirectPNGPath'] = '/usr/bin/mscore'
    us['directoryScratch'] = '/tmp'

    _MUSIC21_SETUP = True

setup()

class M21Score(ScoreRepresentation):
    """A score is a special wrapper for a music21 Score object. A score must contain parts which contain measures.
    This wrapper provides methods to access the parts and measures of the score.

    Score parts can additionally contain instruments since this seems to be a common use case in music21.

    Maybe we will support those 1-2 repeats in the future, but for now assume no repeats"""
    def __init__(self, obj: Score, *, skip_check: bool = False):
        self._data = obj
        if not skip_check:
            self.sanity_check()

    def __eq__(self, value: M21Score) -> bool:
        return self._data == value._data

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

    def sanitize(self):
        """Return a sanitized version of the object."""
        return self.copy()._sanitize_in_place()

    def __iter__(self):
        return self._data.iter()

    def to_standard(self) -> StandardScore:
        score = StandardScore()
        for el in self._data.recurse().getElementsByClass((Note, Chord, KeySignature, TimeSignature, MetronomeMark, Expression, Dynamic, Articulation)):
            offset = get_offset_to_score(el, self)
            if offset is None:
                warnings.warn(f"Unable to get offset: {el}")
                continue
            offset = float(offset)
            if isinstance(el, Note):
                score.insert(NoteElement(
                    onset = offset,
                    duration = float(el.duration.quarterLength),
                    note_name = SimpleNote.from_note(el),
                    octave = el.pitch.implicitOctave,
                    voice = 0, # TODO support multiple voices
                ))
            elif isinstance(el, Chord):
                for p in el.pitches:
                    score.insert(NoteElement(
                        onset=offset,
                        duration=float(el.duration.quarterLength),
                        note_name=SimpleNote.from_pitch(p),
                        octave=p.implicitOctave,
                        voice = 0
                    ))
            elif isinstance(el, Key):
                mode = 1 if el.mode == "minor" else 0 if el.mode == "major" else -1
                score.insert(StandardKeySignature(
                    onset=offset,
                    nsharps=el.sharps,
                    mode = mode
                ))
            elif isinstance(el, KeySignature):
                score.insert(StandardKeySignature(
                    onset=offset,
                    nsharps=el.sharps,
                    mode=-1
                ))
            elif isinstance(el, TimeSignature):
                if el.numerator is None or el.denominator is None:
                    continue
                score.insert(StandardTimeSignature(
                    onset=offset,
                    beats=el.numerator,
                    beat_type=el.denominator
                ))
            elif isinstance(el, MetronomeMark):
                score.insert(StandardTempo(
                    onset=offset,
                    note_value=int(el.referent.quarterLength), # type: ignore
                    tempo=el.number,
                ))
            elif isinstance(el, TextExpression):
                score.insert(StandardTextExpression(
                    onset=offset,
                    text = el.content
                ))
            elif isinstance(el, _ALLOWED_EXPRESSION):
                score.insert(StandardExpression.from_str(
                    onset=offset,
                    expression=el.__class__.__name__
                ))
            elif isinstance(el, Dynamic):
                if el.value not in _ALLOWED_DYNAMICS:
                    warnings.warn(f"Dynamic {el.value} not supported")
                    continue
                score.insert(StandardDynamics.from_str(
                    onset=offset,
                    dynamics=el.value
                ))
        return score

    @classmethod
    def from_standard(cls, score: StandardScore) -> M21Score:
        raise NotImplementedError

    @property
    def duration(self) -> Duration:
        """Return a view of the duration object of the underlying m21 object."""
        duration = self._data.duration
        return duration

    @property
    def quarter_length(self) -> OffsetQL:
        """Return the duration of the object in quarter length."""
        return self.duration.quarterLength

    def copy(self):
        """Return a deep copy of the object."""
        return copy.deepcopy(self)

    def show(self, fmt = None, invert = True):
        """Calls the show method of the music21 object. Refer to the music21 documentation for more information.

        If invert is True and we are currently in IPython using the default fmt=None, then the output color will be inverted. This is useful for having a dark mode IDE."""
        if is_ipython() and fmt is None:
            from ..display import display_score
            display_score(self._data, invert_color=invert, skip_display=False)
            return
        return self._data.show(fmt)

    def __repr__(self):
        return f"<|{self._data.__repr__()}|>"

    @property
    def id(self) -> int | str:
        """Returns a unique ID object representing this object"""
        return self._data.id

    @property
    def offset(self) -> OffsetQL:
        """Returns the offset of the note/chord with respect to its active site"""
        return self._data.offset

    @property
    def notes(self):
        """Returns an iterator of a view of the notes in the stream"""
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
        """Returns an iterator of view of notes and rests in the stream"""
        return [n for n in self._data.recurse().notesAndRests if isinstance(n, (Note, Chord, Rest))]

    def to_audio(self, sample_rate: int = 44100, soundfont_path: str = "~/.fluidsynth/default_sound_font.sf2", verbose: bool = False):
        """Convert the score to an audio object."""
        return stream_to_audio(self._data, sample_rate, soundfont_path, verbose)

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

    ### Helper conversion methods ###
    def to_partitura(self):
        """Returns a list of NoteRepresentation objects for each note in the score

        The note representations are sorted by onset_beat and then pitch"""
        from .partitura import PartituraNote, PartituraScore
        from partitura.utils.music import ensure_notearray
        import partitura as pt
        # The load_music21 method doesnt seem to work properly. This is more consistent
        tmp_path = self._data.write("musicxml")
        extended_score_note_array = ensure_notearray(
            pt.load_score(tmp_path),
            include_pitch_spelling=True, # adds 3 fields: step, alter, octave
            include_key_signature=True, # adds 2 fields: ks_fifths, ks_mode
            include_time_signature=True, # adds 2 fields: ts_beats, ts_beat_type
            include_metrical_position=True, # adds 3 fields: is_downbeat, rel_onset_div, tot_measure_div
            include_grace_notes=True # adds 2 fields: is_grace, grace_type
        )
        reps = [PartituraNote.from_array(x) for x in extended_score_note_array]
        return PartituraScore(extended_score_note_array)

    def note_elements(self) -> Iterable[NoteElement]:
        return self.to_partitura().note_elements()

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
_ALLOWED_BARLINE_TYPES = ("regular", "final")
_ALLOWED_DYNAMICS = ("ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "fp")

def check_note_or_chord(obj: Note | Chord):
    assert all(p.isTwelveTone() for p in obj.pitches), "All pitches must be 12-tone"
    assert all(0 <= p.ps < 128 for p in obj.pitches), "MIDI index must be within 0-127"

def check_rest(obj: Rest):
    assert obj.duration.quarterLength > 0, "Rest must have a positive duration"

def check_expression(expression: Expression):
    allowed_class_names = set(x.__name__ for x in _ALLOWED_EXPRESSION)
    expected_class_names = StandardExpression.get_allowed_expressions()
    assert allowed_class_names == expected_class_names, f"Expression mismatch: {expected_class_names} != {allowed_class_names}"
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
    assert set(_ALLOWED_DYNAMICS) == StandardDynamics.get_allowed_dynamics() # I don't know where else to check this
    assert dynamics.value in _ALLOWED_DYNAMICS, f"Dynamic not supported: {dynamics.value}"
    assert dynamics.quarterLength == 0.0, f"Dynamics must have a duration of 0.0 {dynamics.duration}"

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

def stream_to_audio(stream: Stream, sample_rate: int = 44100, soundfont_path: str = "~/.fluidsynth/default_sound_font.sf2", verbose: bool = False):
    """Convert a music21 Stream object to our Audio object."""
    s2 = copy.deepcopy(stream)
    for n in s2.recurse().getElementsByClass((Note, Chord, Dynamic)):
        if isinstance(n, (Note, Chord)):
            n.volume = 0.5
        elif isinstance(n, Dynamic) and n.activeSite is not None:
            n.activeSite.remove(n)
    with (
        tempfile.NamedTemporaryFile(suffix=".mid") as f1,
        tempfile.NamedTemporaryFile(suffix=".wav") as f2
    ):
        file = streamToMidiFile(s2, addStartDelay=True)
        file.open(f1.name, "wb")
        try:
            file.write()
        finally:
            file.close()
        _convert_midi_to_wav(f1.name, f2.name, soundfont_path, sample_rate, verbose)
        return Audio.load(f2.name)

def load_score_from_corpus(corpus_name: str, movement_number: int | None = None, **kwargs) -> M21Score:
    """Loads a piece from the music21 corpus"""
    corpus = m21.corpus.parse(corpus_name, movement_number, **kwargs)

    if isinstance(corpus, Score):
        return M21Score(corpus)

    assert isinstance(corpus, Part), f"Unexpected type: {type(corpus)}"
    return M21Score(Score([corpus]))

def get_offset_to_score(obj: GeneralNote, site: M21Score) -> OffsetQL | None:
    return get_offset_to_site(obj, site._data)

def get_offset_to_site(obj: GeneralNote, site: Stream) -> OffsetQL | None:
    x: M21Object = obj
    offset = Fraction()
    while x.activeSite is not None:
        offset += x.offset
        x = x.activeSite
        if x is site:
            return offset
    return None

class MergeViolation(Exception):
    """Reports a violation in the merging of two measures"""
    pass

class NoteGroup:
    isRest = False

    def __init__(self, notes: list[m21.note.Note | m21.chord.Chord | m21.note.Rest]):
        self.notes = notes

# Assume the following rule:
# If at the same bar, all 4 voices are active, then voices 2 and 3 becomes the alto voice
# and voice 4 becomes the bass. Voice 1 will always be the soprano voice.
# If at the same bar, only 3 voices are active, then voice 2 becomes the alto voice and voice 3
# becomes the bass.
# Try to merge the voices according to this rule. If the merge is successful, then it is practically
# a 3 part score. If not, then it is a 4 part score.
def measures_all_rest(m: Measure) -> bool:
    """Returns True if all notes in the measure are rests"""
    cum_dur = 0.
    for n in m.notesAndRests:
        if not n.isRest:
            return False
        cum_dur += n.duration.quarterLength
    return cum_dur == m.barDuration.quarterLength

def fix_rest_and_clef(parts: Iterable[Part]):
    """Fixes the rests and clefs in the parts. This function will:
    - Replace measures that are entirely rests with a single rest that spans the entire measure
    - Replace the clef with the best clef for the part

    The `parts` argument will NOT be deep copied
    Returns a new M21Score object with the fixed parts"""
    sanitized_parts = list(parts)
    for part in sanitized_parts:
        sanitize_stream(part)

    for data in sanitized_parts:
        data.makeRests(inPlace=True, fillGaps=True)

        for elem in data.getElementsByClass(Measure):
            if measures_all_rest(elem):
                measure_quarter_length = elem.barDuration.quarterLength
                whole_beat_rest_measure = Measure(number = elem.number)
                whole_beat_rest_measure.append(m21.note.Rest(measure_quarter_length))
                data.replace(elem, whole_beat_rest_measure)

        clef = m21.clef.bestClef(data, recurse=True)
        existing_clef = data.getElementsByClass(m21.clef.Clef)
        if existing_clef:
            data.remove(existing_clef[0])
        data.insert(0, clef)

    # Sanitize a second time to remove any rests that violate rules
    new_score = Score()
    for part in sanitized_parts:
        sanitize_stream(part)
        new_score.insert(0., part)

    return M21Score(new_score)

def offset_to_score(obj: M21Object, score: M21Score):
    """Get the offset of the object in the score"""
    cum = 0.
    x = obj
    while x.activeSite is not None:
        cum += x.offset
        x = x.activeSite
        if x is score._data:
            return cum
    raise ValueError(f"Object {obj} is not in the score")

def get_part(obj: M21Object, score: M21Score | None = None) -> str | None:
    """Get the part of the object in the score"""
    x = obj
    while x.activeSite is not None:
        x = x.activeSite
        if isinstance(x, Part):
            return str(x.id)
        if score is None or x is score._data:
            # We have reached the top of the active site hierarchy
            break
    raise ValueError(f"Object {obj} is not in the score")

def get_part_offset_event(new_score: M21Score):
    """Get the events in each part at each offset. Returns a dictionary where the keys are the part names
    and the values are a list of tuples (offset, NoteHead) sorted by offset"""
    part_lookup: dict[str, Part] = {}
    for i, part in enumerate(new_score._data.getElementsByClass(Part)):
        part_lookup[str(part.id)] = part

    # At offset = offset, what is happening in each part?
    # We will store this information in a sorted list to query efficiently.
    part_offset_events: dict[str, list[tuple[float, m21.note.Note | m21.note.Rest | m21.chord.Chord]]] = {part_name: [] for part_name in part_lookup}
    for x in new_score._data.recurse().getElementsByClass([
        m21.note.Note, m21.note.Rest, m21.chord.Chord
    ]):
        assert isinstance(x, (m21.note.Note, m21.note.Rest, m21.chord.Chord))
        part_of_x = get_part(x, new_score)
        if part_of_x is None:
            continue
        part_offset_events[part_of_x].append((offset_to_score(x, new_score), x))

    for event in part_offset_events:
        part_offset_events[event].sort(key=lambda x: x[0])

    return part_offset_events

def get_note_on_or_before_offset(target_offset: OffsetQL, measure: Measure):
    notes = measure.recurse().getElementsByClass([
        m21.note.Note, m21.note.Rest, m21.chord.Chord
    ]).matchingElements()

    elements = [(offset, x) for x in notes if (offset := get_offset_to_site(x, measure)) is not None]
    elements.sort(key=lambda x: x[0])

    for offset, note in reversed(elements):
        if offset <= target_offset:
            assert isinstance(note, (m21.note.Note, m21.note.Rest, m21.chord.Chord))
            return note, offset
    return None, None

def merge_measures(measure1: Measure, measure2: Measure, *, tuplet_upper_bound: int = 41):
    """Merge two measures together. The measures must be of the same length. We will report a merge violation if
    two simultaneous notes that are not rests and have different durations"""
    # TODO Add a shortcut where if one of the bar has a bar rest then clone and return the other bar directly
    merged_part = measure1.cloneEmpty("merge_measures")
    offset = Fraction()
    while offset < measure1.barDuration.quarterLength:
        note1, offset1 = get_note_on_or_before_offset(offset, measure1)
        note2, offset2 = get_note_on_or_before_offset(offset, measure2)
        if note1 is None or note2 is None or offset1 is None or offset2 is None:
            break

        # Convert to fractions because otherwise floating point antics might happen
        offset1 = float_to_fraction_time(offset1, limit_denom=tuplet_upper_bound)
        offset2 = float_to_fraction_time(offset2, limit_denom=tuplet_upper_bound)

        # Do a small sanity check: if offset is at 0, then both offsets should be 0
        if offset == 0:
            assert offset1 == 0 and offset2 == 0

        # Now compare the starting offset, if they are not the same,
        # then at least one of them is a rest, otherwise it is a
        # merge violation
        if offset1 != offset2:
            if not note1.isRest and not note2.isRest:
                raise MergeViolation(f"Merge violation: {note1} and {note2} are not rests")
            elif (note1.isRest and offset2 < offset1) or (note2.isRest and offset1 < offset2):
                ... # Do nothing, we can just skip the rest

            # Otherwise add the note
            elif note1.isRest:
                merged_part.insert(offset, note2)
            else:
                assert note2.isRest
                merged_part.insert(offset, note1)

        # If both offsets are equal,
        # If note 1 is not a rest and note 2 is not a rest
        # Then they must have the same duration. In this case
        # we can make a chord out of them
        # Otherwise it is a merge violation
        elif not note1.isRest and not note2.isRest:
            if note1.duration.quarterLength != note2.duration.quarterLength:
                raise MergeViolation(f"Merge violation: Note durations do not match: {note1.duration.quarterLength} != {note2.duration.quarterLength }")
            chord = m21.chord.Chord(sorted(set(note1.pitches + note2.pitches)))
            chord.duration = note1.duration
            merged_part.insert(offset, chord)


        elif note1.isRest and note2.isRest:
            if note1.duration.quarterLength < note2.duration.quarterLength:
                merged_part.insert(offset, note1)
            else:
                merged_part.insert(offset, note2)

        elif note1.isRest and not note2.isRest:
            merged_part.insert(offset, note2)

        else:
            assert note2.isRest and not note1.isRest
            merged_part.insert(offset, note1)

        # Increment the offset
        next_measure1_event = offset1 + float_to_fraction_time(note1.duration.quarterLength, limit_denom=tuplet_upper_bound)
        next_measure2_event = offset2 + float_to_fraction_time(note2.duration.quarterLength, limit_denom=tuplet_upper_bound)
        offset = min(next_measure1_event, next_measure2_event)

    return merged_part

def separate_voices(score: M21Score):
    parts = M21Score(score.sanitize()._data.voicesToParts()).parts
    new_score = fix_rest_and_clef(parts)

    # TODO support other number of parts
    if len(parts) in (2, 3):
        return new_score
    if len(parts) != 4:
        raise ValueError("Expected 2, 3, or 4 parts")

    parts = new_score.parts
    soprano = parts[0].cloneEmpty("separate_voices")
    alto = parts[1].cloneEmpty("separate_voices")
    bass = parts[2].cloneEmpty("separate_voices")

    try:
        for i in new_score.measure_numbers():
            offset = offset_to_score(new_score.get_measure(0, i), new_score)
            soprano.insert(offset, new_score.get_measure(0, i))
            if not measures_all_rest(new_score.get_measure(3, i)):
                measure1 = new_score.get_measure(1, i)
                measure2 = new_score.get_measure(2, i)
                merged_measure = merge_measures(measure1, measure2)
                alto.insert(offset, merged_measure)
                bass.insert(offset, new_score.get_measure(3, i))
            else:
                alto.insert(offset, new_score.get_measure(1, i))
                bass.insert(offset, new_score.get_measure(2, i))
    except MergeViolation as e:
        # If there is a merge violation, then we will just return the original parts
        # Fix again just in case we accidentally modified the original parts
        return fix_rest_and_clef(parts)

    return fix_rest_and_clef([soprano, alto, bass])
