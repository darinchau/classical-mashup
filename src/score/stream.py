from typing import TypeVar, Generic, Iterable
import tempfile
import music21 as m21
from music21.articulations import Articulation
from music21.bar import Barline, Repeat
from music21.base import Music21Object as M21Object
from music21.dynamics import Dynamic
from music21.instrument import Instrument
from music21.stream.base import Stream, Score, Part, Measure, Opus, Voice, PartStaff
from music21.note import Note, Rest, GeneralNote
from music21.chord import Chord
from music21.meter.base import TimeSignature
from music21.midi.translate import streamToMidiFile
from music21.duration import Duration
from music21.common.types import OffsetQL, StepName
from music21.key import KeySignature, Key
from music21.interval import Interval
from music21.clef import Clef
from .base import M21Wrapper, M21Object, IDType
from .note import M21Note, M21Rest, M21Chord, _wrap_upcast
from .util import wrap, play_binary_midi_m21, convert_midi_to_wav, is_type_allowed, check_obj
from ..util import is_ipython
from ..audio import Audio
from typing import Literal, Sequence
import copy

T = TypeVar("T", bound=Stream)
class M21StreamWrapper(M21Wrapper[T]):
    """Wrapper for music21 Stream object. Provides methods to iterate over the stream."""
    def sanity_check(self):
        super().sanity_check()
        for children in self._data:
            try:
                wrap(children) # Performs sanity check recursively
            except AssertionError:
                # Remove the children
                if not self._data.activeSite:
                    raise
                self._data.activeSite.remove(children)
                print(f"Removed {children} from {self._data} due to sanity check failure")

    def __iter__(self):
        for children in self._data:
            yield wrap(children)

    @property
    def notes(self):
        """Returns an iterator of notes in the stream"""
        ls = [M21Note(n) for n in self._data.recurse().notes if isinstance(n, Note)]
        ids = set()
        ls: list[M21Note] = []
        for n in self._data.recurse().notes:
            if isinstance(n, Note) and n.id not in ids:
                ls.append(M21Note(n))
            ids.add(n.id)
        return ls

    @property
    def rests(self):
        """Returns an iterator of rests in the stream"""
        return [M21Rest(n) for n in self._data.recurse().notes if isinstance(n, Rest)]

    def show(self, fmt = None):
        """Calls the show method of the music21 Stream object. Refer to the music21 documentation for more information."""
        return self._data.show(fmt)

    def _sanitize_in_place(self):
        super()._sanitize_in_place()
        # This seems to lead to weird behavior
        # TODO investigate about this tying over bars and measures
        # case in point test 1079 measure 15
        # self._data.stripTies(inPlace = True)
        # self._data.makeTies(inPlace = True)
        # TODO support grace notes
        self._remove_all_grace_notes_in_place()
        for el in self._data.iter():
            if not is_type_allowed(el) or not check_obj(el):
                el.activeSite.remove(el)
                continue
            wrap(el)._sanitize_in_place() # Sanitize child
        return self

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
            convert_midi_to_wav(f1.name, f2.name, soundfont_path, sample_rate, verbose)
            return Audio.load(f2.name)

    def play(self):
        """A shorthand for self.to_audio().play()"""
        return self.to_audio().play()

    def _remove_all_grace_notes_in_place(self):
        """Remove all grace notes in the stream"""
        from .note import _wrap_upcast
        for el in self._data.recurse():
            should_remove = (isinstance(el, (Note, Chord)) and _wrap_upcast(el).is_grace)
            if should_remove:
                assert el.activeSite is not None
                el.activeSite.remove(el)
        return self

class M21Measure(M21StreamWrapper[Measure]):
    """Wrapper for a music21 Measure object"""
    @property
    def bar_duration(self):
        """Returns the duration of this measure

        This is different from the duration of the object, since illegal/malformed measures can have its sum of its parts not equal to the whole.
        Refer to the music21 documentation for more information."""
        x = self._data.barDuration
        assert isinstance(x, m21.duration.Duration)
        return copy.deepcopy(x)

    def _sanitize_in_place(self):
        super()._sanitize_in_place()
        if self._data.leftBarline is not None:
            if isinstance(self._data.leftBarline, Repeat):
                self._data.leftBarline = Barline("regular")
            wrap(self._data.leftBarline)._sanitize_in_place()
        if self._data.rightBarline is not None:
            if isinstance(self._data.leftBarline, Repeat):
                self._data.leftBarline = Barline("regular")
            wrap(self._data.rightBarline)._sanitize_in_place()
        return self

class M21Part(M21StreamWrapper[Part]):
    """Wrapper for music21 Part object"""
    @classmethod
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        return cls(_parse(path, Part))

    def measure(self, measure_number: int):
        """Grabs a single measure specified by measure number"""
        measure = self._data.measure(measure_number)
        if measure is None:
            raise ValueError(f"Measure {measure_number} does not exist in the part.")
        return M21Measure(measure)

    def pretty(self):
        """Returns a prettified string representation of the part"""
        import partitura as pt
        score = M21Score(Score([
            self._data
        ]))._convert_to_partitura()
        return score.parts[0].pretty()


class M21Score(M21StreamWrapper[Score]):
    """A score is a special wrapper for a music21 Score object. A score must contain parts which contain measures.
    This wrapper provides methods to access the parts and measures of the score.

    Score parts can additionally contain instruments since this seems to be a common use case in music21.

    Maybe we will support those 1-2 repeats in the future, but for now assume no repeats"""
    def sanity_check(self):
        super().sanity_check()
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

    @classmethod
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        return cls(_parse(path, Score))

    @property
    def parts(self):
        """Returns the parts of the score as a list of Parts wrapper."""
        return [M21Part(x) for x in self._data.parts]

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

    def get_measure(self, part_idx: int, measure_number: int) -> M21Measure:
        """Grabs a single measure specified by measure number"""
        if measure_number not in self.measure_numbers():
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        m = self._data.parts[part_idx].measure(measure_number)
        if m is None:
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        return M21Measure(m)

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

    def _sanitize_in_place(self):
        super()._sanitize_in_place()
        self._fix_measure_numbers_in_place()
        self._check_measure_numbers()
        return self

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

_ALLOWED = (
    (Measure, M21Measure),
    (Part, M21Part),
    (Score, M21Score),
    (Stream, M21StreamWrapper)
)
