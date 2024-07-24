# Basic tests about notes

from src.audio.m21score import *

def test_note_transposition():
    note1 = M21Note(Note("A4"))
    note2 = note1.transpose(3)
    assert note1.midi_index == 69
    assert note2.midi_index == 72
