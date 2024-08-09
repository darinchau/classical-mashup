from typing import TypeVar, Generic, Iterable
import tempfile
import music21 as m21
from music21.articulations import Articulation
from music21.bar import Barline
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
        for children in self:
            pass

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
            if not is_type_allowed(el):
                el.activeSite.remove(el)
                continue
            if not check_obj(el):
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
        for n in self._data.recurse().getElementsByClass((Note, Chord)):
            assert isinstance(n, (Note, Chord))
            n.volume = 0.5
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
            wrap(self._data.leftBarline)._sanitize_in_place()
        if self._data.rightBarline is not None:
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

        # Check the well-orderedness of measures
        # Skip this check if there are no measures
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
    def parse(cls, path: str):
        """Read a music21 Stream object from an XML file or a MIDI file."""
        return cls(_parse(path, Score))

    def play(self):
        """Play the score inside Jupyter."""
        assert is_ipython(), "This function can only be called inside Jupyter."
        play_binary_midi_m21(self.to_binary_midi())

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
        """Returns True if the score has a pickup measure"""
        m = self.measure_numbers()
        if not m:
            return False
        return m[0] == 0

    def get_measure(self, part_idx: int, measure_number: int) -> M21Measure:
        """Grabs a single measure specified by measure number"""
        if measure_number not in self.measure_numbers():
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        m = self._data.parts[part_idx].measure(measure_number)
        if m is None:
            raise ValueError(f"Measure {measure_number} does not exist in the score.")
        return M21Measure(m)

    def _convert_to_partitura(self):
        """Convert the score to a Partitura object."""
        import partitura as pt
        tmp_path = self._data.write("musicxml")
        return pt.load_score(tmp_path)

Q = TypeVar("Q", bound=Stream)
def _parse(path: str, expected_type: type[Q]) -> Q:
    """Read a music21 Stream object from an XML file or a MIDI file."""
    # Purely for convenience
    test_cases = {
        "-test.prelude": "resources/scores/Prelude in C Major.mid",
        "-test.1079": "resources/scores/Musical Offering BWV 1079.mxl"
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
