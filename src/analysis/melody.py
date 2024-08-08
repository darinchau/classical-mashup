import music21 as m21
import copy
from ..score import (
    M21Wrapper, M21Note, M21Chord, M21Rest, M21Part, M21Score, M21Measure, M21StreamWrapper,
    M21TimeSignature, M21KeySignature, M21Key, M21Interval, M21Slur, M21BassClef, M21Dynamics, M21TrebleClef,
    M21Object
)

from music21.stream.base import Stream
from music21.note import Note, Rest
from music21.chord import Chord
from music21.key import KeySignature
from music21.meter.base import TimeSignature
from music21.pitch import Pitch
from ..score.util import check_obj as _check_obj
from typing import TypeVar
import warnings

def _cum_offset(obj: M21Object) -> float:
    """Returns the cumulative offset of the object in the score"""
    cum = 0.
    while obj.activeSite is not None:
        cum += obj.offset
        obj = obj.activeSite
    return cum

def _copy_part_with_classes(obj: M21Part, classes: tuple[type, ...]) -> M21Part:
    """Helper method that copies a stream recursively, keeping only the specified classes"""
    new_stream = obj.copy()
    assert isinstance(new_stream._data, Stream)
    for el in new_stream._data.recurse():
        if not isinstance(el, classes) and not isinstance(el, Stream):
            el.activeSite.remove(el)
    return new_stream

def _sanitize(part: M21Part) -> M21Part:
    """Sanitize a music21 Part object to make it suitable for use as a melody.
    Internally makes a copy of the part and removes all elements that are not suitable for a melody.

    For the list of restrictions, see the Melody class.
    - For chords, only the top note is kept
    - For key signatures, only the first one is kept
    - For time signatures, only the first one is kept. Will raise an error if this causes a change in time signature.
    """
    # Do a first pass to remove anything thats definitely illegal
    # Cannot use removeByNotOfClass because it does not remove recursively
    filter_list = [Note, Rest, Chord, KeySignature, TimeSignature]
    new_part = _copy_part_with_classes(part, tuple(filter_list))
    new_part._sanitize_in_place()

    replacements: list[tuple[M21Object, M21Object | None]] = []

    try:
        first_keysig = new_part._data.getElementsByClass(KeySignature).__next__()
        if _cum_offset(first_keysig) > 0:
            first_keysig = None
    except StopIteration:
        first_keysig = None

    try:
        first_timesig = new_part._data.getElementsByClass(TimeSignature).__next__()
        if _cum_offset(first_timesig) > 0:
            first_timesig = None
    except StopIteration:
        first_timesig = None

    for el in new_part._data.recurse():
        if isinstance(el, Chord):
            # Only keep the top note
            top_note = M21Chord(el).top_note
            assert el.activeSite is not None
            replacements.append((el, top_note._data))

        elif isinstance(el, KeySignature):
            if first_keysig is None or el != first_keysig:
                # The first condition matches if the key signature is not placed at the beginning
                # Remove it
                assert el.activeSite is not None
                replacements.append((el, None))

        elif isinstance(el, TimeSignature):
            if first_timesig is None or el != first_timesig:
                # The first condition matches if the time signature is not placed at the beginning
                # Remove it
                assert el.activeSite is not None
                replacements.append((el, None))

    # Make the replacements
    for old, new in replacements:
        assert old.activeSite is not None
        if new is None:
            old.activeSite.remove(old)
        else:
            old.activeSite.replace(old, new)

    # Add a time signature at the beginning if it is missing
    if first_timesig is None:
        new_part._data.insert(0, TimeSignature('4/4'))

    # Add a key signature at the beginning if it is missing
    if first_keysig is None:
        new_part._data.insert(0, KeySignature(0))
    return new_part

class Melody:
    """A melody is a sequence of notes that is perceived as a single coherent entity.
    Internally, it is stored as a Music21 Part object with some restrictions and some other useful information.

    Restrictions:
        - The melody must only contain notes and rests.
        - The melody must not contain any articulations, grace notes, or dynamic markings
        - The melody must not contain any chords
        - The melody must not contain any key or time signature changes (aka. the melody must be in a single key and time signature at the beginning)
    """

    _TOO_LOW_THRESHOLD = 24 # E below middle C
    _TOO_HIGH_THRESHOLD = 34 # A above middle C

    def __init__(self, part: M21Part):
        self._part = _sanitize(part)

    @property
    def has_pickup(self):
        try:
            self._part.measure(0)
            return True
        except (IndexError, ValueError):
            return False

    @property
    def range(self) -> M21Interval:
        """Returns the underlying Music21 Part object"""
        # The analyze function is typed incorrectly, so use an asssert to make sure it is correct
        interval = self._part._data.analyze('range')
        assert isinstance(interval, m21.interval.Interval)
        return M21Interval(interval)

    @property
    def pitch_range(self) -> tuple[Pitch, Pitch]:
        """Returns the lowest and highest notes in the melody"""
        key = lambda x: (x.ps, x.diatonicNoteNum)
        return (
            copy.deepcopy(min(self._part._data.pitches, key=key)),
            copy.deepcopy(max(self._part._data.pitches, key=key))
        )

    @property
    def part(self) -> M21Part:
        """Returns a copy of the underlying Music21 Part object"""
        return self._part.copy()

    @property
    def best_clef(self) -> M21TrebleClef | M21BassClef:
        """Returns the best clef for the melody"""
        too_low = self.pitch_range[0].ps < self._TOO_LOW_THRESHOLD # E below middle C
        too_high = self.pitch_range[1].ps > self._TOO_HIGH_THRESHOLD # A above middle C
        if too_low and not too_high:
            return M21BassClef.get()

        if not too_low:
            return M21TrebleClef.get()

        # TODO implement a divide and conquer or smth to find the best clef for each section of the melody
        warnings.warn(f"Melody span is too awkward to determine the best clef. Returning treble clef.")
        return M21TrebleClef.get()

    def show(self, fmt = None):
        """Shows the melody using music21"""
        self._part.show(fmt=fmt)

    def to_audio(self):
        """Converts the melody to an audio signal"""
        return self._part.to_audio()
