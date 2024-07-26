# Basic tests about notes

from src.audio.m21score import *

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
