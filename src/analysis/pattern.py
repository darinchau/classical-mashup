from typing import Callable
import numpy as np
from numpy.typing import NDArray
from ..score import ScoreRepresentation, M21Score, NoteElement
from .harmony import chromatic_pitch_from_midi

class SearchPattern:
    """A class representing a note pattern used for searching"""
    def __init__(self, target_dist: list[int], max_voice_leading_distance: int = 1, max_log_probability: float = 1):
        """
        :param target_dist: List of distances between notes
        :param max_voice_leading_distance: Maximum voice leading distance
        :param max_log_probability: Maximum log probability
        """
        self.target_dist = target_dist
        self.max_voice_leading_distance = max_voice_leading_distance
        self.max_log_probability = max_log_probability
        self.filters: list[Callable[[list[NoteElement], tuple[int, ...], float], bool]] = []

    def post_filter(self, notes: list[NoteElement], partial_neighbours: tuple[int, ...], probability: float) -> bool:
        for f in self.filters:
            if not f(notes, partial_neighbours, probability):
                return False
        return True

    def add_filter(self, f: Callable[[list[NoteElement], tuple[int, ...], float], bool]):
        self.filters.append(f)
        return self

class NotePatternSearcher:
    def __init__(self, notes: list[NoteElement]):
        """
        An object that calculates the voice leading probabilities between notes and searches for patterns
        :param notes: List of notes
        :param chromatic_pitch: Chromatic pitch array
        """
        # Rather than constructing a tree and doing all the weird stuff, we can just
        # calculate all pairs. This will be faster and easier to implement unless there
        # are some performance issues

        # TODO: consider well voices for voice leading
        # TODO deal with overlapping notes in offset probabilities

        # This distance index array is somewhat arbitrary
        # Can try changing values in the future
        # The idea is in the first pass, all notes within an octave are considered
        # likely. The notes further away are decayed exponentially
        # But since we are dealing with log probabilities, the decay becomes linear
        self.notes = notes
        self.pitch = np.array([n.pitch_number for n in notes], dtype=np.int64)
        self.onset = np.array([n.onset for n in notes], dtype=np.float64)
        self.duration = np.array([n.duration for n in notes], dtype=np.float64)

        chromatic_pitch = chromatic_pitch_from_midi(self.pitch)
        self.dist = chromatic_pitch[None, :] - chromatic_pitch[:, None]

        self.log_vlp = self.calculate_voice_leading_probabilities(self.pitch, self.onset, self.duration)

    @staticmethod
    def calculate_voice_leading_probabilities(pitch: NDArray[np.int_], onset: NDArray[np.float_], duration: NDArray[np.float_]) -> NDArray[np.float_]:
        """Returns a matrix of voice leading probabilities"""
        # note_distances[i, j] = Number of semitones that note j is higher than note i
        note_distances = pitch[None, :] - pitch[:, None]
        note_probabilities = (0.2 * (np.abs(note_distances) - 12)).astype(np.float64)
        note_probabilities[note_probabilities < 0] = 0

        # offset_distances[i, j] = Onset of note j - offset of note i
        offset_distances = onset[None, :] - (onset + duration)[:, None]
        offset_probabilities = (0.1 * offset_distances).astype(np.float64)

        # log_vlp[i, j] = log probability of voice leading from note i to note j
        log_vlp = note_probabilities + offset_probabilities
        log_vlp[offset_distances < 0] = 99

        return log_vlp

    def search(self, pattern: SearchPattern) -> tuple[NDArray[np.int_], NDArray[np.float_]]:
        neighbours = []
        for i, row in enumerate(self.dist):
            # Initialize candidates array
            note_candidates = [[] for _ in range(len(pattern.target_dist) + 1)]
            note_candidates[0] = [((i,), 0)]

            for j in range(i + 1, row.shape[0]):
                if self.onset[j] - self.onset[i] - self.duration[i] > pattern.max_voice_leading_distance:
                    break
                for k, td in enumerate(pattern.target_dist):
                    if row[j] != td:
                        continue
                    for nc, ncp in note_candidates[k]:
                        # Filter the patterns preemptively
                        new_probability = ncp + self.log_vlp[nc[-1], j]
                        if new_probability > pattern.max_log_probability:
                            continue
                        new_neighbours = nc + (j,)
                        if not pattern.post_filter(self.notes, new_neighbours, new_probability):
                            continue
                        note_candidates[k + 1].append((new_neighbours, new_probability))

            neighbours.extend([(nc, ncp) for nc, ncp in note_candidates[-1]])

        matches = np.array([n[0] for n in neighbours], dtype=np.int64)
        log_probabilities = np.array([n[1] for n in neighbours], dtype=np.float64)
        return matches, log_probabilities
