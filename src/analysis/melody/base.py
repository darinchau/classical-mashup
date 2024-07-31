import music21 as m21
from ...audio.m21score import (
    M21Note, M21Chord, M21Rest, M21Part, M21Wrapper,
    Note, Rest, Chord, KeySignature, TimeSignature, M21Object, Stream
)
from ...audio.m21score.util import check_obj as _check_obj
from typing import TypeVar

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

    replacements = []

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
            replacements.append((el, top_note))

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
