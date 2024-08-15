import numpy as np
from ..score import M21Score
from partitura.musicanalysis.pitch_spelling import ps13s1 as ps
import numpy as np

def predict_spelling(s: M21Score):
    note_reps = s.get_note_representation_list()

    arr = np.array([
        (note.onset_beat, note.duration_beat, note.onset_quarter, note.duration_quarter,
        note.onset_div, note.duration_div, note.pitch, note.voice, note.id,
        note.step, note.alter, note.octave,
        "", 0, 0)
    for note in note_reps], dtype = (
        [('onset_beat', float), ('duration_beat', float), ('onset_quarter', float), ('duration_quarter', float),
        ('onset_div', float), ('duration_div', float), ('pitch', int), ('voice', int), ('id', str),
        ("real_spelling_step", "U1"), ("real_spelling_alter", int), ("real_spelling_octave", int),
        ("pred_spelling_step", "U1"), ("pred_spelling_alter", int), ("pred_spelling_octave", int)]
    ))

    step, alter, octave = ps(arr)

    arr["pred_spelling_step"] = step
    arr["pred_spelling_alter"] = alter
    arr["pred_spelling_octave"] = octave

    unequal_idx = np.bitwise_or(arr["pred_spelling_step"] != arr["real_spelling_step"], arr["pred_spelling_alter"] != arr["real_spelling_alter"], arr["pred_spelling_octave"] != arr["real_spelling_octave"])
    accuracy = 1 - np.sum(unequal_idx) / len(unequal_idx)

    # for note in arr[unequal_idx]:
    #     print(f"Onset: {note["onset_quarter"]} (Bar: {note["onset_quarter"] // 4 + 1}) {note["real_spelling_step"]}{note["real_spelling_alter"]} ({note["real_spelling_octave"]}) -> {note["pred_spelling_step"]}{note["pred_spelling_alter"]} ({note["pred_spelling_octave"]})")
    return arr, accuracy
