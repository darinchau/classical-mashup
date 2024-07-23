# Classical Mashup

This repository contains the code used for my MPhil research project: "Classical Music Mashup with Music Theory-Informed Algorithms and Generative AI". The project aims to develop a system that can generate mashups of classical music pieces by using music theory-informed algorithms and generative AI. The system is implemented in Python, implements a note-based system for representing piano music that can be converted to WAV, MIDI, and music score. The system uses the music21 library for music theory operations.

# Installation

You need some extra packages and musescore to run the various functions of music21 properly.
```
sudo add-apt-repository ppa:mscore-ubuntu/mscore-stable -y
sudo apt-get update
sudo apt-get install musescore
sudo apt-get install xvfb
```

You need fluidsynth to run the midi2wav function.
```
sudo apt install -y fluidsynth
```
