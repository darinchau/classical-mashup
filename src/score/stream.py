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

GraceNoteType = Literal["grace", "nachschlagen"]
class GraceNoteContext(Stream):
    # A context to store grace notes. The implementation is similar to SpannerStorage
    def __init__(self, elements: Sequence[Note | Chord], parent: Note | Chord, _type: GraceNoteType, **keywords):
        self.parent = parent
        self._type = _type
        super().__init__(elements, **keywords)

    @property
    def note_type(self) -> GraceNoteType:
        if self._type == "grace":
            return "grace"
        elif self._type == "nachschlagen":
            return "nachschlagen"
        else:
            raise ValueError(f"Unknown grace note type {self._type}")

    def _reprInternal(self):
        # This is a hack to make the repr look nice
        tc = type(self.parent)
        return f'for {tc.__module__}.{tc.__qualname__}'

    def coreSelfActiveSite(self, el):
        # Never set the active site of a GraceNoteContext
        # This overrides the default behavior of music21
        pass

    def coreStoreAtEnd(self, element, setActiveSite=True):
        raise NotImplementedError("GraceNoteContext cannot store elements at the end")

    def replace(self, target: M21Object,  replacement: M21Object, *, recurse: bool = False, allDerived: bool = True) -> None:
        if replacement in self:
            self.remove(target)
            return
        super().replace(target, replacement, recurse=recurse, allDerived=allDerived)

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
        copied_note, stream = _add_grace_note(self.copy(), note, grace_notes, "grace", slur=slur, appoggiatura=appoggiatura, override_priority=override_priority)
        return stream

    def add_nachschlagen(self, note: M21Note | M21Chord, grace_notes: Iterable[M21Note | M21Chord], *, override_priority: bool = False):
        """Adds a nachschlagen to a note. A nachschlagen is the little flourish notes after a trill that indicates the resolve of a trill."""
        copied_note, stream = _add_grace_note(self.copy(), note, grace_notes, "nachschlagen", slur=False, appoggiatura=True, override_priority=override_priority)
        return stream

    def _sanitize_in_place(self):
        # This seems to lead to weird behavior
        # TODO investigate about this tying over bars and measures
        # case in point test 1079 measure 15
        # self._data.stripTies(inPlace = True)
        # self._data.makeTies(inPlace = True)
        for el in self._data.iter():
            if not is_type_allowed(el):
                el.activeSite.remove(el)
                continue
            if not check_obj(el):
                el.activeSite.remove(el)
                continue
            wrap(el)._sanitize_in_place() # Sanitize child
        return

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

    def measure(self, measure_number: int):
        """Grabs a single measure specified by measure number"""
        return M21Score(self._data.measure(measure_number))

    def measure_range(self, start: int, end: int):
        """Grabs a range of measure specified by measure number"""
        return M21Score(self._data.measures(start, end))

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

def _add_grace_note(new_stream: M21StreamWrapper, note: M21Note | M21Chord, grace_notes: Iterable[M21Note | M21Chord], _type: GraceNoteType, *,
                   slur: bool = True,
                   appoggiatura: bool = False,
                   override_priority: bool = False):
    # Find the corresponding note in the copied stream
    copied_note = [n for n in new_stream._data.recurse().notes if n.derivation.origin is not None and n.derivation.origin.id == note.id]
    if not copied_note:
        raise ValueError(f"Note {note.id} not an element in the stream.")
    copied_note = copied_note[0]

    # Perform some checks on copied_note. We perform type checks on the ._data to account for subclasses
    assert len(copied_note.pitches) > 0
    assert all(p.isTwelveTone() for p in copied_note.pitches)
    assert isinstance(copied_note, (Note, Chord)), f"Note {copied_note} is not a Note or Chord object ({copied_note.__class__.__name__})"
    assert not isinstance(copied_note.duration, (m21.duration.GraceDuration, m21.duration.AppoggiaturaDuration)), f"Note {copied_note} is a grace note"
    copied_note = _wrap_upcast(copied_note)
    active_site = copied_note._data.activeSite
    assert active_site is not None, f"Note {copied_note.id} is not active"

    existing_ctx = active_site.getElementsByClass(GraceNoteContext)
    if existing_ctx is not None:
        for ctx in existing_ctx:
            if ctx.parent == copied_note._data:
                raise ValueError(f"Note {note.id} ({note.name}) already has grace notes. Repeated calls to add_grace_note is not supported yet.")

    # Gets the grace notes
    for x in grace_notes:
        x._data.getGrace(appoggiatura=appoggiatura, inPlace=True)
    grace_notes = [x for x in grace_notes if x is not None]

    # Initialize a grace note context to store the grace notes
    ctx = GraceNoteContext([x._data for x in grace_notes], parent=copied_note._data, _type=_type)
    active_site.insert(0.0, ctx)

    offset = copied_note._data.getOffsetBySite(active_site)
    for i, gn in enumerate(reversed(grace_notes)):
        active_site.insert(offset, gn._data)
        if override_priority:
            if _type == "grace":
                gn._data.priority = copied_note._data.priority - i - 1
            else:
                gn._data.priority = copied_note._data.priority + i + 1

    if slur:
        sl = m21.spanner.Slur([gn._data for gn in grace_notes] + [copied_note._data])
        active_site.insert(0.0, sl)
    return copied_note, new_stream

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
