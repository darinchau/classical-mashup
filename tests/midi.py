from unittest.mock import patch, call, Mock

import pytest

from src.audio.midi.midi import MidiConnector, Message
from src.audio.midi.types import NoteOff, SysEx
from src.audio.midi.utils import get_status_value
from src.audio.midi.types import (NoteOff, NoteOn, PolyphonicAftertouch,
                        ControlChange, ChannelAftertouch, ProgramChange,
                        PitchBend, SysEx, MidiMessageType)


def get_bytes(integer):
    assert isinstance(integer, int)
    return integer.to_bytes(1, 'big')

@pytest.fixture
def message():
    note_off = NoteOff(35, 127)
    return Message(note_off, 1)


@pytest.fixture
def midi_bytes():
    values = [220, 100, 35]
    return [get_bytes(value) for value in values]


@patch('src.audio.midi.midi.Serial', autospec=True)
def test_write(mock_serial, message):
    """Check if 'write' method from serial.Serial is called as expected."""
    conn = MidiConnector('/path/to/serial/port')

    conn.write(message)

    expected_calls = [call().write(data) for data in message.bytes_content]
    assert mock_serial.method_calls == expected_calls


@patch('src.audio.midi.midi.Serial', autospec=True)
def test_read_standard(mock_serial):
    """3 bytes expected"""
    reader = Mock()
    reader.side_effect = [bytes([value]) for value in [128, 35, 65]]
    conn = MidiConnector('/path/to/serial/port', test=True, read_func=reader)

    message = conn.read()

    assert isinstance(message, Message)
    assert isinstance(message.type, NoteOff)
    assert message.channel == 1
    assert message.note_number == 35
    assert message.velocity == 65


@pytest.fixture
def note_off_msg():
    note_off = NoteOff(10, 100)
    return Message(note_off, 1)


@pytest.fixture
def sysex_msg():
    """A SysEx message with 4 bytes of random data with manufacturer ID #35."""
    sysex = SysEx(35, 0x12, 0xac, 0x9a, 0x8d)
    return Message(sysex)


def test_message_content(note_off_msg):
    assert len(note_off_msg) == 3
    assert note_off_msg[0] == 128  # status byte of NoteOff sent on channel 1
    assert note_off_msg[1] == 10
    assert note_off_msg[2] == 100

    assert note_off_msg.content == [128, 10, 100]
    assert note_off_msg.bytes_content == [bytes([c])
                                          for c in note_off_msg.content]

    assert not hasattr(note_off_msg, 'control_number')
    assert hasattr(note_off_msg, 'note_number')
    assert hasattr(note_off_msg, 'velocity')
    assert note_off_msg.note_number == note_off_msg[1]
    assert note_off_msg.velocity == note_off_msg[2]



def test_sysex_content(sysex_msg):
    assert len(sysex_msg) == 7  # ID + 4 bytes of data + start byte + end byte
    assert sysex_msg[0] == 0xf0  # SysEx start byte
    assert sysex_msg[1] == 35
    assert sysex_msg[-1] == 0xf7  # SysEx end byte

@pytest.fixture
def note_off():
    return NoteOff(10, 120)


@pytest.fixture
def note_on():
    return NoteOn(20, 110)


@pytest.fixture
def polyphonic_aftertouch():
    return PolyphonicAftertouch(30, 50)


@pytest.fixture
def control_change():
    return ControlChange(72, 40)


@pytest.fixture
def channel_aftertouch():
    return ChannelAftertouch(90)


@pytest.fixture
def program_change():
    return ProgramChange(1)


@pytest.fixture
def pitch_bend():
    return PitchBend(127, 64)


@pytest.fixture
def sysex():
    return SysEx(35, 120, 255, 90)


def test_note_off(note_off):
    assert isinstance(note_off, MidiMessageType)
    assert note_off.data1 == note_off.note_number == 10
    assert note_off.data2 == note_off.velocity == 120
    assert not hasattr(note_off, 'value')


def test_note_on(note_on):
    assert isinstance(note_on, MidiMessageType)
    assert note_on.data1 == note_on.note_number == 20
    assert note_on.data2 == note_on.velocity == 110
    assert not hasattr(note_on, 'value')


def test_polyphonic_aftertouch(polyphonic_aftertouch):
    assert isinstance(polyphonic_aftertouch, MidiMessageType)
    assert polyphonic_aftertouch.data1 == polyphonic_aftertouch.note_number == 30
    assert polyphonic_aftertouch.data2 == polyphonic_aftertouch.pressure == 50
    assert not hasattr(note_on, 'value')


def test_control_change(control_change):
    assert isinstance(control_change, MidiMessageType)
    assert control_change.data1 == control_change.control_number == 72
    assert control_change.data2 == control_change.value == 40
    assert not hasattr(control_change, 'velocity')


def test_channel_aftertouch(channel_aftertouch):
    assert isinstance(channel_aftertouch, MidiMessageType)
    assert channel_aftertouch.data1 == channel_aftertouch.pressure == 90
    assert channel_aftertouch.data2 is None


def test_program_change(program_change):
    assert isinstance(program_change, MidiMessageType)
    assert program_change.data1 == 0  # program_number - 1
    assert program_change.data2 is None
    assert program_change.program_number == 1


def test_pitch_bend(pitch_bend):
    assert isinstance(pitch_bend, MidiMessageType)
    assert pitch_bend.data1 == pitch_bend.lsbyte == 127
    assert pitch_bend.data2 == pitch_bend.msbyte == 64


def test_sysex(sysex):
    assert isinstance(sysex, MidiMessageType)
    assert sysex.data1 == sysex.manufacturer_id == 35
    assert sysex.data2 == [120, 255, 90]
