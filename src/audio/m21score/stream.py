from typing import TypeVar, Generic, Iterable
import tempfile
import music21 as m21
from music21.stream.base import Stream, Score, Part, Measure
from music21.note import Note, Rest
from music21.chord import Chord
from music21.midi.translate import streamToMidiFile
from .base import M21Wrapper
from .note import M21Note, M21Rest, M21Chord
from .util import wrap, play_binary_midi_m21, convert_midi_to_wav
from ...util import is_ipython
from ..audio import Audio

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
        assert isinstance(copied_note, (Note, Chord)), f"Note {copied_note} is not a Note or Chord object ({copied_note.__class__.__name__})"
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
