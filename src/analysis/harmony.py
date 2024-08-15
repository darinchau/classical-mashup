from .representation import NoteRepresentation
import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass
import typing

STEPS = np.array(["A", "B", "C", "D", "E", "F", "G"])
UNDISPLACED_CHROMA = np.array([0, 2, 3, 5, 7, 8, 10], dtype=int)

PitchType = np.int64
OnsetType = np.float64
DurationType = np.float64
StepType = typing.Literal["A", "B", "C", "D", "E", "F", "G"]

@dataclass(frozen=True)
class PredictedNote:
    onset_beat: float
    duration_beat: float
    pitch: int
    real_step: StepType
    real_alter: int
    real_octave: int
    pred_step: StepType
    pred_alter: int
    pred_octave: int

    def to_simple_note(self):
        from scales import SimpleNote
        return SimpleNote.from_step_alter(self.pred_step, self.pred_alter)

def chromatic_pitch_from_midi(midi_pitch: NDArray[PitchType]):
    return midi_pitch - 21


def chroma_from_chromatic_pitch(chromatic_pitch: NDArray[PitchType]):
    return np.mod(chromatic_pitch, 12)


def pitch_class_from_chroma(chroma: NDArray):
    return np.mod(chroma - 3, 12)


def compute_chroma_array(sorted_ocp: NDArray) -> NDArray[PitchType]:
    return chroma_from_chromatic_pitch(sorted_ocp[:, 1]).astype(int)


def compute_chroma_vector_array(chroma_array: NDArray[PitchType], K_pre: int, K_post: int):
    """
    Computes the chroma frequency distribution within the context surrounding
    each note.
    """
    n = len(chroma_array)
    chroma_vector = np.zeros(12, dtype=int)

    for i in range(np.minimum(n, K_post)):
        chroma_vector[chroma_array[i]] = 1 + chroma_vector[chroma_array[i]]

    chroma_vector_list = [chroma_vector.copy()]

    for i in range(1, n):
        if i + K_post <= n:
            chroma_vector[chroma_array[i + K_post - 1]] = (
                1 + chroma_vector[chroma_array[i + K_post - 1]]
            )

        if i - K_pre > 0:
            chroma_vector[chroma_array[i - K_pre - 1]] = (
                chroma_vector[chroma_array[i - K_pre - 1]] - 1
            )

        chroma_vector_list.append(chroma_vector.copy())

    return np.array(chroma_vector_list)


def compute_morph_array(chroma_array, chroma_vector_array):
    n = len(chroma_array)
    # Line 1: Initialize morph array
    morph_array = np.empty(n, dtype=int)

    # Compute m0
    # Line 2
    init_morph = np.array([0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6], dtype=int)
    # Line 3
    c0 = chroma_array[0]
    # Line 4
    m0 = init_morph[c0]

    # Line 5
    morph_int = np.array([0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6], dtype=int)

    # Lines 6-8
    tonic_morph_for_tonic_chroma = np.mod(
        m0 - morph_int[np.mod(c0 - np.arange(12), 12)], 7
    )

    # Line 10
    tonic_chroma_set_for_morph = [[] for i in range(7)]

    # Line 11
    morph_strength = np.zeros(7, dtype=int)

    # Line 12
    for j in range(n):
        # Lines 13-15 (skipped line 9, since we do not need to
        # initialize morph_for_tonic_chroma)
        morph_for_tonic_chroma = np.mod(
            morph_int[np.mod(chroma_array[j] - np.arange(12), 12)]
            + tonic_morph_for_tonic_chroma,
            7,
        )
        # Lines 16-17
        tonic_chroma_set_for_morph = [[] for i in range(7)]

        # Line 18
        for m in range(7):
            # Line 19
            for ct in range(12):
                # Line 20
                if morph_for_tonic_chroma[ct] == m:
                    # Line 21
                    tonic_chroma_set_for_morph[m].append(ct)

        # Line 22
        for m in range(7):
            # Line 23
            morph_strength[m] = sum(
                [chroma_vector_array[j, ct] for ct in tonic_chroma_set_for_morph[m]]
            )

        # Line 24
        morph_array[j] = np.argmax(morph_strength)

    return morph_array


def compute_ocm_chord_list(sorted_ocp, chroma_array, morph_array):
    # Lines 1-3
    ocm_array = np.column_stack((sorted_ocp[:, 0], chroma_array, morph_array)).astype(int)

    # Alternative implementation of lines 4--9
    unique_onsets = np.unique(ocm_array[:, 0])
    unique_onset_idxs = [np.where(ocm_array[:, 0] == u) for u in unique_onsets]
    ocm_chord_list = [ocm_array[uix] for uix in unique_onset_idxs]

    return ocm_chord_list


def compute_morphetic_pitch(sorted_ocp: NDArray, morph_array: NDArray):
    """
    Compute morphetic pitch

    Parameters
    ----------
    sorted_ocp : array
       Sorted array of (onset in beats, chromatic pitch)
    morph_array : array
       Array of morphs

    Returns
    -------
    morphetic_pitch : array
        Morphetic pitch of the notes
    """
    n = len(sorted_ocp)
    chromatic_pitch = sorted_ocp[:, 1]
    morph = morph_array.reshape(-1, 1)

    morph_oct_1 = np.floor(chromatic_pitch / 12.0).astype(int)

    morph_octs = np.column_stack((morph_oct_1, morph_oct_1 + 1, morph_oct_1 - 1))

    chroma = np.mod(chromatic_pitch, 12)

    mps = morph_octs + (morph / 7)

    cp = (morph_oct_1 + (chroma / 12)).reshape(-1, 1)

    diffs = abs(cp - mps)

    best_morph_oct = morph_octs[np.arange(n), diffs.argmin(1)]

    morphetic_pitch = (
        morph.reshape(-1,) + 7 * best_morph_oct
    )

    return morphetic_pitch


def chromatic_pitch_to_pitch_name(chromatic_pitch: NDArray[PitchType], morphetic_pitch: NDArray[PitchType]):
    """Convert chromatic pitch to pitch name"""
    morph = np.mod(morphetic_pitch, 7)

    step = STEPS[morph]
    undisplaced_chroma = UNDISPLACED_CHROMA[morph]

    alter = chromatic_pitch - 12 * np.floor(morphetic_pitch / 7.0) - undisplaced_chroma

    asa_octave = np.floor(morphetic_pitch / 7)
    asa_octave[morph > 1] += 1
    return step, alter, asa_octave

def predict_spelling(note_reps: list[NoteRepresentation], context_window: tuple[int, int] = (10, 40)):
    note_array = np.array([
        (note.onset_beat, note.duration_beat, note.pitch, note.step, note.alter, note.octave, "", 0, 0)
    for note in note_reps], dtype = np.dtype(
        [('onset_beat', float), ('duration_beat', float), ('pitch', int),
         ('real_step', "U1"), ('real_alter', int), ('real_octave', int),
        ("pred_step", "U1"), ("pred_alter", int), ("pred_octave", int)]
    ))

    # Sort the notes by pitch and then by onset
    pitch_sort_idx = note_array["pitch"].argsort()
    onset_sort_idx = np.argsort(note_array[pitch_sort_idx]["onset_beat"], kind="mergesort")
    sort_idx = pitch_sort_idx[onset_sort_idx]

    reverse_idx = sort_idx.argsort()  # Reverse the sorting to get back to the original order

    # ocp = onset, chromatic pitch
    sorted_ocp = np.column_stack(
        (
            note_array[sort_idx]["onset_beat"],
            chromatic_pitch_from_midi(note_array[sort_idx]["pitch"]),
        )
    )

    chroma_array = compute_chroma_array(sorted_ocp=sorted_ocp)
    chroma_vector_array = compute_chroma_vector_array(
        chroma_array=chroma_array, K_pre=context_window[0], K_post=context_window[1]
    )
    morph_array = compute_morph_array(
        chroma_array=chroma_array, chroma_vector_array=chroma_vector_array
    )

    morphetic_pitch = compute_morphetic_pitch(sorted_ocp, morph_array)

    step, alter, octave = chromatic_pitch_to_pitch_name(
        sorted_ocp[:, 1],
        morphetic_pitch.reshape(-1,),
    )

    # sort back pitch names
    step = step[reverse_idx]
    alter = alter[reverse_idx]
    octave = octave[reverse_idx]

    note_array["pred_step"] = step
    note_array["pred_alter"] = alter
    note_array["pred_octave"] = octave

    return [PredictedNote(
        onset_beat=note["onset_beat"],
        duration_beat=note["duration_beat"],
        pitch=note["pitch"],
        real_step=note["real_step"],
        real_alter=note["real_alter"],
        real_octave=note["real_octave"],
        pred_step=note["pred_step"],
        pred_alter=note["pred_alter"],
        pred_octave=note["pred_octave"]
    ) for note in note_array]
