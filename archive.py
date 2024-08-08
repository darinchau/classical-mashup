import numpy as np
from src.score import M21Score
from src.score.stream import _parse
import music21 as m21
from music21.stream.base import PartStaff, Part, Measure, Score
from src.score import M21Object, M21Part
from music21.note import GeneralNote

def get_event_around_offset(part_events: list[tuple[float, GeneralNote]], target_offset: float):
    # Get event on or before target_offset
    # Get event after target_offset
    # Just use a linear search for now. Also we assume that 0 <= offset <= part length
    offset_before, note_before = None, None
    for offset, note in reversed(part_events):
        if offset <= target_offset:
            offset_before, note_before = offset, note
            break
    else:
        raise ValueError(f"No event found in part for offset {target_offset}")

    for offset, note in part_events:
        if offset > target_offset:
            return offset_before, note_before, offset, note
    return offset_before, note_before, None, None
