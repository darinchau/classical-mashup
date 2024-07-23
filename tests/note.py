# Basic tests about notes

from src.audio.music_score import Note, midi_to_note_name, midi_to_freq
import pytest

def test_note():
    assert midi_to_note_name(60) == "C4"
    assert midi_to_note_name(69) == "A4"
    assert midi_to_note_name(21) == "A0"
    try:
        midi_to_note_name(128)
        assert False
    except AssertionError:
        pass

    assert midi_to_freq(69) == 440
