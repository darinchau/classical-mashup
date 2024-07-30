import music21 as m21
from ...audio.m21score import (
    M21Note, M21Chord, M21Rest, M21Part,

    Note, Rest, Chord, KeySignature, TimeSignature
)

def _sanitize(part: M21Part) -> M21Part:
    """Sanitize a music21 Part object to make it suitable for use as a melody.
    Internally makes a copy of the part and removes all elements that are not suitable for a melody."""
    new_part = part.copy()
    new_part._data.removeByNotOfClass([Note, Rest, Chord, KeySignature, TimeSignature])
    return new_part

class Melody:
    """A melody is a sequence of notes that is perceived as a single coherent entity.
    Internally, it is stored as a Music21 Part object with some restrictions and some other useful information.

    Restrictions:
        - The melody must only contain notes and rests.
        - The melody must not contain any articulations, grace notes, or dynamic markings
        - The melody must not contain any chords
    """
