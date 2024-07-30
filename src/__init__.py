_MUSIC21_SETUP = False

def setup():
    from music21 import environment
    global _MUSIC21_SETUP
    if _MUSIC21_SETUP:
        return

    us = environment.UserSettings()
    us['musescoreDirectPNGPath'] = '/usr/bin/mscore'
    us['directoryScratch'] = '/tmp'

    _MUSIC21_SETUP = True

from .audio import Audio
from .audio.m21score import M21Note, M21Chord, M21Rest, M21Part, M21Score
