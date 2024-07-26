# Basic tests about notes

from src.audio.m21score import *
from music21 import corpus, converter

def test_note_transposition():
    note1 = M21Note(Note("A4"))
    note2 = note1.transpose(3)
    assert note1.midi_index == 69
    assert note2.midi_index == 72

def test_prelude_1():
    c = M21Score.parse("-test.prelude")
    assert c.quarter_length == 140
    assert c.measures(1, 2).parts[0].notes[0].name == "G4"

def test_immutability_duration():
    c = M21Score.parse("-test.prelude")
    c.duration.quarterLength = 150 # Duration should return a copy of the duration object
    # so this code is counterintuitive but as long as we avoid this type of mutable patterns
    # I think it might actually be easier to use
    assert c.quarter_length == 140

def test_get_next_note():
    p = converter.parse("tinynotation: 4/4 c4 d e f g a b c' b a g2")
    s = M21Part(p)
    assert s.notes[3].get_next_note() == s.notes[4]
    assert s.notes[5].get_next_note() == s.notes[6]

def test_grace_note():
    p = converter.parse("tinynotation: 4/4 c4 d e f g a b c' b a g2")
    part = M21Part(p)

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
