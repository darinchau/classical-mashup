import copy
import typing
import music21 as m21
from music21.stream.base import Stream, Score, Measure
from ..score import M21Score

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
