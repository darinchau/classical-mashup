import pytest
from src.score import M21Score, StandardScore, SimpleNote, NoteElement, PartituraScore, ScoreRepresentation
from src.analysis.harmony import predict_spelling

def get_standard_test_cases():
    yield M21Score.parse("-test.1079")
    yield M21Score.parse("-test.fugue")

def test_m21_conformance():
    for score in get_standard_test_cases():
        s = M21Score.from_score(score)
        assert s.to_standard() == s.conform().to_standard()

def test_predict_spelling():
    s = M21Score.parse("-test.fugue")
    result = predict_spelling(s)
    assert sum(1 if x.is_accurate else 0 for x in result) / len(result) == 1.0
