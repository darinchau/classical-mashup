# Basic tests about notes

from src.score import *
from src.analysis.melody import Melody
import music21 as m21
from music21.note import Note
from music21.stream.base import Part, Measure, Score
from music21.meter.base import TimeSignature
from music21 import corpus, converter
from src.analysis.melody import _sanitize

def test_note_transposition():
    # Tests the transposition of notes
    note1 = M21Note(Note("A4"))
    note2 = note1.transpose(3)
    assert note1.midi_index == 69
    assert note2.midi_index == 72

def test_basic_parse():
    # Tests basic M21Score parsing
    c = M21Score.parse("-test.prelude")
    assert c.quarter_length == 140
    assert c.get_measure(0, 1).notes[0].name == "G4"

def test_duration_immutability():
    # Tests that the duration object is immutable
    c = M21Score.parse("-test.prelude")
    assert c.quarter_length == 140
    c.duration.quarterLength = 150 # Duration should return a copy of the duration object
    # so this code is counterintuitive but as long as we avoid this type of mutable patterns
    # I think it might actually be easier to use
    assert c.quarter_length == 140

def test_get_next_note():
    # Tests the get_next_note function
    s = M21Part.parse("tinynotation: 4/4 c4 d e f g a b c' b a g2")
    assert s.notes[3].get_next_note() == s.notes[4]
    assert s.notes[5].get_next_note() == s.notes[6]

def test_sanitize_basic():
    # Tests the basic functionality of the sanitize function for a melody
    p = load_part_from_corpus('bach/bwv66.6')
    s = _sanitize(p)

    idx = 0
    assert p._data.recurse()[idx].__class__.__name__ == "Instrument"
    assert s._data.recurse()[idx].__class__.__name__ != "Instrument"

def test_sanitize_grace_note():
    m = Measure()
    m.append(TimeSignature('4/4'))
    m.repeatAppend(m21.note.Note('C5'), 4)
    d = m21.note.Note('D5', type='eighth')
    dGrace = d.getGrace()
    m.number = 1
    m.insert(2.0, dGrace)
    s = Score([
        Part([m])
    ])
    s = M21Score(s)
    assert len(s.notes) == 5
    s._remove_all_grace_notes_in_place()
    assert len(s.notes) == 4

# def test_sanitize_strip_ties():
#     part = converter.parse('tinyNotation: 2/4 d4. e8~ e4 d4~ d8 f4.')
#     assert isinstance(part, Part)
#     m = Melody(M21Part(part))
#     assert len(m._part.notes) == 4

def test_sanitize_bar_line():
    s = M21Score.parse("-test.1079")
    s.parts[0].measure(2)._data.rightBarline = 'none'
    assert s.parts[0].measure(2)._data.rightBarline.type == 'none'
    assert s.sanitize().parts[0].measure(2)._data.rightBarline.type == 'regular'

def test_sanitize_measure_numbers():
    s = M21Score.parse("-test.1079")

    # Scramble measure numbers
    import random
    for p in s._data.parts:
        for m in p.getElementsByClass(Measure):
            m.number = random.randint(1, 1000)

    s._fix_measure_numbers_in_place()
    s._check_measure_numbers()
