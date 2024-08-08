from src.score import M21Score
from src.score.stream import _parse
import music21 as m21
from music21.stream.base import PartStaff, Part, Measure, Score
from src.score import M21Object, M21Part
from music21.note import GeneralNote
from src.score import M21StreamWrapper, M21Measure
from music21.common.types import OffsetQL

NoteHead = m21.note.Note | m21.note.Rest | m21.chord.Chord

# Assume the following rule:
# If at the same bar, all 4 voices are active, then voices 2 and 3 becomes the alto voice
# and voice 4 becomes the bass. Voice 1 will always be the soprano voice.
# If at the same bar, only 3 voices are active, then voice 2 becomes the alto voice and voice 3
# becomes the bass.
# Try to merge the voices according to this rule. If the merge is successful, then it is practically
# a 3 part score. If not, then it is a 4 part score.
def measures_all_rest(m: Measure):
    """Returns True if all notes in the measure are rests"""
    cum_dur = 0.
    for n in m.notesAndRests:
        if not n.isRest:
            return False
        cum_dur += n.duration.quarterLength
    return cum_dur == m.barDuration.quarterLength

def fix_rest_and_clef(parts: list[M21Part]):
    """Fixes the rests and clefs in the parts. This function will:
    - Replace measures that are entirely rests with a single rest that spans the entire measure
    - Replace the clef with the best clef for the part

    Returns a new M21Score object with the fixed parts"""
    n_parts = len(parts)

    for i in range(n_parts):
        parts[i]._sanitize_in_place()
        parts[i]._data.makeRests(inPlace=True, fillGaps=True)

        data = parts[i]._data

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

    new_score = M21Score(Score())
    for part in parts:
        new_score._data.insert(0., part.sanitize()._data)

    return new_score

def offset_to_score(obj: NoteHead, score: M21Score):
    """Get the offset of the object in the score"""
    cum = 0.
    x: M21Object = obj
    while x.activeSite is not None:
        cum += x.offset
        x = x.activeSite
        if x is score._data:
            break
    return cum

def get_part(obj: NoteHead, score: M21Score) -> str | None:
    """Get the part of the object in the score"""
    x: M21Object = obj
    while x.activeSite is not None:
        x = x.activeSite
        if isinstance(x, Part):
            return str(x.id)
        if x is score._data:
            # We have reached the top of the active site hierarchy
            break
    return None

def get_part_offset_event(new_score: M21Score):
    """Get the events in each part at each offset. Returns a dictionary where the keys are the part names
    and the values are a list of tuples (offset, NoteHead) sorted by offset"""
    part_lookup: dict[str, Part] = {}
    for i, part in enumerate(new_score._data.getElementsByClass(Part)):
        part_lookup[str(part.id)] = part

    # At offset = offset, what is happening in each part?
    # We will store this information in a sorted list to query efficiently.
    part_offset_events: dict[str, list[tuple[float, NoteHead]]] = {part_name: [] for part_name in part_lookup}
    for x in new_score._data.recurse().getElementsByClass([
        m21.note.Note, m21.note.Rest, m21.chord.Chord
    ]):
        x: NoteHead
        part_of_x = get_part(x, new_score)
        if part_of_x is None:
            continue
        part_offset_events[part_of_x].append((offset_to_score(x, new_score), x))

    for event in part_offset_events:
        part_offset_events[event].sort(key=lambda x: x[0])

    return part_offset_events

def get_offset_to_site(obj: GeneralNote, site: M21StreamWrapper) -> float | None:
    x: M21Object = obj
    offset = 0.
    while x.activeSite is not None:
        offset += x.offset
        x = x.activeSite
        if x is site._data:
            return offset
    return None

def get_note_on_or_before_offset(target_offset: float, measure: M21Measure):
    notes = measure._data.recurse().getElementsByClass([
        m21.note.Note, m21.note.Rest, m21.chord.Chord
    ]).matchingElements()

    elements = [(offset, x) for x in notes if (offset := get_offset_to_site(x, measure)) is not None]
    elements.sort(key=lambda x: x[0])

    for offset, note in reversed(elements):
        if offset <= target_offset:
            assert isinstance(note, (m21.note.Note, m21.note.Rest, m21.chord.Chord))
            return note, offset
    return None, None

class MergeViolation(Exception):
    """Reports a violation in the merging of two measures"""
    pass

def merge_measures(measure1: M21Measure, measure2: M21Measure):
    """Merge two measures together. The measures must be of the same length. We will report a merge violation if
    two simultaneous notes that are not rests and have different durations"""
    merged_part = measure1._data.cloneEmpty("merge_measures")
    offset = 0.
    while offset < measure1.bar_duration.quarterLength:
        note1, offset1 = get_note_on_or_before_offset(offset, measure1)
        note2, offset2 = get_note_on_or_before_offset(offset, measure2)
        if note1 is None or note2 is None or offset1 is None or offset2 is None:
            break

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
        next_measure1_event = offset1 + note1.duration.quarterLength
        next_measure2_event = offset2 + note2.duration.quarterLength
        offset = min(next_measure1_event, next_measure2_event)

    return merged_part
