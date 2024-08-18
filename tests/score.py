import pytest
from src.score import M21Score, StandardScore, SimpleNote, NoteElement, PartituraScore, ScoreRepresentation


def get_standard_test_cases():
    yield M21Score.parse("-test.1079")

def test_m21_conformance():
    for score in get_standard_test_cases():
        s = M21Score.from_score(score)
        assert s.to_standard() == s.conform().to_standard()

def test_m21_to_partitura():
    for score in get_standard_test_cases():
        s = M21Score.from_score(score)
        p = s.to_partitura()
        assert PartituraScore(p.to_note_array()) == s.to_partitura()
