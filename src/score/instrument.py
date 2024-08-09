from music21.instrument import Instrument
from music21.instrument import (
    KeyboardInstrument, Organ, Harmonica, StringInstrument, WoodwindInstrument, BrassInstrument, Percussion
)
from .base import M21Wrapper

class M21Instrument(M21Wrapper[Instrument]):
    def sanity_check(self):
        return super().sanity_check()

    def _sanitize_in_place(self):
        super()._sanitize_in_place()
        piano = Instrument('piano')
        self._data.__dict__.update(piano.__dict__)

    @property
    def name(self):
        return self._data.instrumentName

    @property
    def family(self):
        if isinstance(self._data, KeyboardInstrument):
            return "keyboard"
        if isinstance(self._data, Organ):
            return "organ"
        if isinstance(self._data, Harmonica):
            return "harmonica"
        if isinstance(self._data, StringInstrument):
            return "string"
        if isinstance(self._data, WoodwindInstrument):
            return "woodwind"
        if isinstance(self._data, BrassInstrument):
            return "brass"
        if isinstance(self._data, Percussion):
            return "percussion"
        return ""

    @property
    def part_id(self):
        """Returns the part ID of the instrument"""
        return self._data.partId

    @property
    def part_name(self):
        """Returns the part name of the instrument"""
        return self._data.partName

    @property
    def part_abbr(self):
        """Returns the part abbreviation of the instrument"""
        return self._data.partAbbreviation

    @property
    def midi_program(self):
        """Returns the MIDI program number of the instrument"""
        return self._data.midiProgram

    @property
    def midi_channel(self):
        """Returns the MIDI channel of the instrument"""
        return self._data.midiChannel

    @property
    def instrument_id(self):
        """Returns the instrument ID of the instrument"""
        return self._data.instrumentId

    @property
    def instrument_abbr(self):
        """Returns the instrument number of the instrument"""
        return self._data.instrumentAbbreviation

    @property
    def lowest_note(self):
        """Returns the lowest note of the instrument"""
        return self._data.lowestNote

    @property
    def highest_note(self):
        """Returns the highest note of the instrument"""
        return self._data.highestNote

_ALLOWED = (
    (Instrument, M21Instrument),
)
