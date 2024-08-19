import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass
import typing
from ..score import StandardScore, ScoreRepresentation

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
        """Converts the predicted note to a SimpleNote"""
        from scales import SimpleNote
        return SimpleNote.from_step_alter(self.pred_step, self.pred_alter)

    @property
    def is_accurate(self):
        """Returns true if the predicted note is accurate"""
        return self.pred_alter == self.real_alter and self.pred_octave == self.real_octave and self.pred_step == self.real_step

def chromatic_pitch_from_midi(midi_pitch: NDArray[PitchType]):
    return midi_pitch - 21


def chroma_from_chromatic_pitch(chromatic_pitch: NDArray[PitchType]):
    return np.mod(chromatic_pitch, 12)


def pitch_class_from_chroma(chroma: NDArray):
    return np.mod(chroma - 3, 12)


def compute_chroma_array(chromatic_pitch: NDArray[np.int_]) -> NDArray[np.int_]:
    return chroma_from_chromatic_pitch(chromatic_pitch).astype(int)


def compute_chroma_vector_array(chroma_array: NDArray[np.int_], K_pre: int, K_post: int) -> NDArray[np.int_]:
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

# The morph pitch is the diatonic pitch class of the note. Middle C is 23.
# Refer to partitura.musicanalysis.predict_spelling implementation
# and the original paper for more info
def compute_morph_array(chroma_array: NDArray[np.int_], chroma_vector_array: NDArray[np.int_]):
    n = len(chroma_array)
    morph_array = np.empty((n, 7), dtype=int)

    init_morph = np.array([0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6], dtype=int)
    c0 = chroma_array[0]
    m0 = init_morph[c0]

    morph_int = np.array([0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6], dtype=int)

    tonic_morph_for_tonic_chroma = np.mod(
        m0 - morph_int[np.mod(c0 - np.arange(12), 12)], 7
    )

    tonic_chroma_set_for_morph = [[] for _ in range(7)]

    for j in range(n):
        morph_for_tonic_chroma = np.mod(
            morph_int[np.mod(chroma_array[j] - np.arange(12), 12)]
            + tonic_morph_for_tonic_chroma,
            7,
        )
        tonic_chroma_set_for_morph = [[] for _ in range(7)]

        for m in range(7):
            for ct in range(12):
                if morph_for_tonic_chroma[ct] == m:
                    tonic_chroma_set_for_morph[m].append(ct)

        for m in range(7):
            morph_array[j, m] = sum(
                [chroma_vector_array[j, ct] for ct in tonic_chroma_set_for_morph[m]]
            )
    return morph_array

def compute_morphetic_pitch(chromatic_pitch: NDArray[np.int_], morph_array: NDArray[np.int_]):
    n = len(chromatic_pitch)
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

def predict_spelling(score: ScoreRepresentation, context_window: tuple[int, int] = (10, 40)):
    """Performs stage 1 of Meredith's ps13 algorithm. Assumes the note representations are sorted (i.e. straight from s.get_note_representation())"""
    notes = list(score.note_elements())
    onset = np.array([n.onset for n in notes], dtype=np.float64)
    pitch = np.array([n.pitch_number for n in notes], dtype=np.int64)
    duration = np.array([n.duration for n in notes], dtype=np.float64)

    # ocp = onset, chromatic pitch
    chromatic_pitch = chromatic_pitch_from_midi(pitch)

    # Shape (n,). arr[i] is the chroma of the ith note, where C is 0
    chroma_array = compute_chroma_array(chromatic_pitch)

    # Shape (n, 12). arr[i] is the chroma vector of the ith note, where C is 0
    # aka the number of notes in the context window
    chroma_vector_array = compute_chroma_vector_array(
        chroma_array=chroma_array, K_pre=context_window[0], K_post=context_window[1]
    )

    # Shape (n,, 7). arr[i, k] is the morph strength of 'k' of the ith note, where A is 0
    # So for example arr[3, 0] is the morph strength of A for the 3rd note
    morph_array = compute_morph_array(
        chroma_array=chroma_array, chroma_vector_array=chroma_vector_array
    )
    morph_array = morph_array.argmax(axis=1)

    # Shape (n,). arr[i] is the morphetic pitch of the ith note i.e. the morphetic pitch implied by the morph and the pitch number
    morphetic_pitch = compute_morphetic_pitch(chromatic_pitch, morph_array)

    step, alter, octave = chromatic_pitch_to_pitch_name(chromatic_pitch, morphetic_pitch.reshape(-1,))

    notes = [PredictedNote(
        onset_beat=note.onset,
        pitch=note.pitch_number,
        duration_beat=note.duration,
        pred_step=s,
        pred_alter=a,
        pred_octave=o,
        real_step=note.step,
        real_alter=note.alter,
        real_octave=note.octave,
    ) for note, s, a, o in zip(notes, step, alter, octave)]

    return notes
