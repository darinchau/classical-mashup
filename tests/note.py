# Basic tests about notes

from src.audio.m21score import *
from music21 import corpus, converter
from src.analysis.melody.base import _sanitize

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
    assert c.measures(1, 2).parts[0].notes[0].name == "G4"

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

def test_grace_note():
    part = M21Part.parse("tinynotation: 4/4 c4 d e f g a b c' b a g2")

    n =  part.notes[0]
    gn = M21Note.from_name("F#").set_duration(1/2)

    part2 = part.add_grace_note(n, [
        gn,
    ])

    assert part2.notes[0] == gn

    try:
        part3 = part2.add_nachschlagen(part2.notes[1], [
            M21Note.from_name("G#").set_duration(1/2)
        ])
        assert False, "Should not be able to add grace note repeatedly"
    except ValueError:
        pass

    part3 = part2.add_grace_note(part2.notes[3], [
        M21Note.from_name("G#4").set_duration(1/4)
    ])

    assert part3.notes[1]._data.offset == 2.0

def test_sanitize_basic():
    # Tests the basic functionality of the sanitize function for a melody
    p = load_part_from_corpus('bach/bwv66.6')
    s = _sanitize(p)

    idx = 0
    assert p._data.recurse()[idx].__class__.__name__ == "Instrument"
    assert s._data.recurse()[idx].__class__.__name__ != "Instrument"

def test_sanitize_grace_note():
    part = M21Part.parse("tinynotation: 4/4 c4 d e f g a b c' b a g2")

    part._sanitize_in_place()

    n =  part.notes[0]
    gn = M21Note.from_name("F#").set_duration(1/2)

    part2 = part.add_grace_note(n, [
        gn,
    ])

    assert part2.notes[0] == gn
    part2._sanitize_in_place()
    assert part2.notes[0] == gn
