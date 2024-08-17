# A static module that provides functions to work with scales.
from __future__ import annotations
from typing import Literal
from functools import lru_cache
import re
import music21 as m21
import numpy as np
from ..score.simplenote import LINE_OF_FIFTH, SimpleNote

class ChordLabel(m21.note.Lyric):
    """A class that represents a chord label. Subclasses music21.note.Lyric so it can be added onto a note."""
    pass

_C_index = np.where(LINE_OF_FIFTH["note_name"] == "C")[0][0]
@lru_cache(maxsize=24)
def get_scales(scale: str):
    """Returns a mapping of scale names to the notes in the scale. Majors are majors and minors are harmonic minors.

    If you want natural minors, use MinorN"""
    if not is_scale_supported(scale):
        raise ValueError(f"Invalid scale {scale}")
    note_name, major_minor = scale.split(" ")
    self_abs_idx = SimpleNote(note_name).index + _C_index
    if  major_minor == "Major":
        arr = np.array([0, 2, 4, -1, 1, 3, 5])
    elif major_minor == "Minor":
        arr = np.array([0, 2, -3, -1, 1, -4, 5])
    elif major_minor == "MinorN":
        arr = np.array([0, 2, -3, -1, 1, -4, -2])
    else:
        raise ValueError(f"Invalid scale {scale}")
    return [SimpleNote(entry) for entry in LINE_OF_FIFTH[self_abs_idx + arr]]

_IS_SCALE_NAME = re.compile(r"^[CDEFGAB](#|x|b{1,2})? M(ajor|inor|inorN)$")
def is_scale_supported(scale: str):
    """Returns a list of supported scales."""
    return _IS_SCALE_NAME.match(scale) is not None
