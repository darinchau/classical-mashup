import copy
import typing
import music21 as m21
from music21.stream.base import Stream, Score, Measure
from music21.note import Note, Rest, GeneralNote
from music21.pitch import Pitch
from ..util import NATURAL
from ..score import M21Score
from .scales import ChordLabel, get_scales, get_supported_scale_names, SimpleNote

def chordify_cleanup(s: M21Score) -> M21Score:
    """Remove ties, articulations, expressions, and lyrics from notes in a chordified score.

    In the first part, the bass notes are put onto octave 4, and the other notes are put onto octave 5.
    In the second part, the chord notes are put onto octave 5, and the other notes are put onto octave 5.
    In the third part, the bass notes are put onto octave 3."""
    part = s.sanitize()._data.chordify()
    part = part.stripTies()

    all_note_part = part.cloneEmpty("chordify_cleanup")
    chord_part = part.cloneEmpty("chordify_cleanup")
    bass_part = part.cloneEmpty("chordify_cleanup")

    for measure in part.getElementsByClass(Measure):
        all_note_measure = measure.cloneEmpty("chordify_cleanup")
        bass_measure = measure.cloneEmpty("chordify_cleanup")
        chord_measure = measure.cloneEmpty("chordify_cleanup")

        all_note_part.insert(measure.offset, all_note_measure)
        bass_part.insert(measure.offset, bass_measure)
        chord_part.insert(measure.offset, chord_measure)

        for el in measure.notesAndRests:
            new_note = copy.deepcopy(el)
            all_note_measure.insert(el.offset, new_note)

            # Cleanup new note
            if not new_note.isRest:
                new_note.tie = None
                new_note.expressions = []
                new_note.articulations = []
                new_note.lyrics = []

                if len(new_note.pitches) == 1:
                    new_note.pitches[0].octave = 5
                else:
                    bass = min(new_note.pitches, key=lambda x: (x.ps, x.diatonicNoteNum))
                    bass.octave = 4
                    for p in new_note.pitches:
                        if p is not bass:
                            p.octave = 5

            # Create bass note from new note
            bass_note = copy.deepcopy(new_note)
            bass_measure.insert(el.offset, bass_note)
            if not new_note.isRest:
                bass_note.pitches = (bass_note.pitches[0],)
                bass_note.pitches[0].octave = 3

            # Create chord note from new note
            chord_note = copy.deepcopy(new_note)
            chord_measure.insert(el.offset, chord_note)
            if not new_note.isRest:
                chord_note.pitches[0].octave = 5
                new_pitches = []
                for p in sorted(chord_note.pitches, key=lambda x: (x.ps, x.diatonicNoteNum)):
                    if new_pitches and p.ps == new_pitches[-1].ps:
                        continue
                    new_pitches.append(p)

                chord_note.pitches = tuple(new_pitches)

    bass_part.insert(0, m21.clef.BassClef())
    return M21Score(Score([all_note_part, chord_part, bass_part]))

def label_obvious_chords(note: GeneralNote, scale_ctx: str) -> ChordLabel:
    """Labels all obvious chords that fall within a certain scale

    Assume the note is from the top line aka the base note is on the 4th octave and the other notes are on the 5th octave

    - Can be a rest => will return empty chord label
    - Can be a one note chord => will return a special chord label for now '1N'
    - If it is a major/minor triad, return the figure bass label
    - In the case where a root position major triad ought to return an empty figure bass label, we will spell that as 3
    - If it is a 7th chord, return the figure bass label
    - Other chords will return some special tokens for now

    - - Two note chords will return a special chord label for now '2N'
    - - Chords with a bass note not in the scale will return a special chord label for now 'NC'
    - - Chords that do not have a bass note will return a special chord label for now 'NB'
    - - Chords that are not obvious will return a special chord label for now 'UN'
    """
    if scale_ctx not in get_supported_scale_names():
        raise ValueError(f"{scale_ctx} is not a scale.")

    if note.isRest:
        return ChordLabel()

    if len(note.pitches) == 1:
        return ChordLabel("1N")

    if len(note.pitches) == 2:
        # Skip labelling for now because well its not obvious
        return ChordLabel("2N")

    def _get_bass_note(note: GeneralNote) -> Pitch | None:
        for x in note.pitches:
            if x.octave == 4:
                return x
        return None

    bass_note = _get_bass_note(note)
    if bass_note is None:
        return ChordLabel("NB")

    current_scale = get_scales()[scale_ctx]
    if SimpleNote.from_pitch(bass_note) not in current_scale:
        return ChordLabel("NC")

    bass_note_scale_idx = current_scale.index(SimpleNote.from_pitch(bass_note))

    # Determine the steps
    chord_note_steps = set([
        (x.diatonicNoteNum - bass_note.diatonicNoteNum) % 7 + 1
        for x in note.pitches if x.octave == 5
    ])
    if 1 in chord_note_steps:
        chord_note_steps.remove(1)

    if len(chord_note_steps) == 0:
        return ChordLabel("1N")

    if len(chord_note_steps) == 1:
        return ChordLabel("2N")

    accidentals: dict[int, list[str]] = {} # keys are the scale steps, values are the accidentals
    for x in note.pitches:
        if x.octave != 5:
            continue
        note_scale_idx = (x.diatonicNoteNum - bass_note.diatonicNoteNum) % 7 + 1
        if note_scale_idx not in chord_note_steps:
            continue
        if note_scale_idx not in accidentals:
            accidentals[note_scale_idx] = []

        # Find the expected accidentals first
        expected = current_scale[(bass_note_scale_idx + note_scale_idx - 1) % 7].alter

        # Handle naturals separately
        alter = int(x.accidental.alter if x.accidental else 0)
        if alter not in (-2, -1, 0, 1, 2):
            raise ValueError(f"Unexpected accidental {x.accidental} for note {x}")

        if alter == 0 and expected != 0:
            accidentals[note_scale_idx].append(NATURAL)

        elif alter != 0 and alter != expected:
            symbol = {
                2: "x",
                1: "#",
                -1: "b",
                -2: "bb"
            }[alter]
            accidentals[note_scale_idx].append(symbol)

    possible_labels = {
        (4, 2): [{2, 4}, {2, 4, 6}],
        (4, 3): [{3, 4}, {3, 4, 6}],
        (6, 5): [{5, 6}, {3, 5, 6}],
        (7,): [{7}, {7, 5}, {7, 3}, {7, 5, 3}],
        (6, 4): [{4, 6}],
        (6,): [{3, 6}],
        (3,): [{3, 5}]
    }
    step_labels = None
    for label, steps in possible_labels.items():
        if chord_note_steps in steps:
            step_labels = label

    if step_labels is None:
        return ChordLabel("UN")

    labels = []
    for x in sorted(chord_note_steps, reverse=True):
        assert x in accidentals
        if not accidentals[x] and x in step_labels:
            labels.append(str(x))
        else:
            for symbol in accidentals[x]:
                labels.append(symbol + str(x))

    return ChordLabel("\n".join(labels))
