import mido
import time


class MidiDevice:
    def __init__(self, output_num: int = 0):
        self.midi_outputs = mido.get_output_names()
        if not self.midi_outputs:
            raise RuntimeError("No MIDI output ports found")
        if output_num >= len(self.midi_outputs):
            raise ValueError(f"Invalid port number. Available ports: {len(self.midi_outputs)}")

        self.outport = mido.open_output(self.midi_outputs[output_num])
        self.channel = 0

    def send_note(self, note: int, duration: float, channel: int, velocity: int = 100):
        if not 0 <= note <= 127:
            raise ValueError("Note value must be between 0 and 127")

        note_on = mido.Message('note_on', note=note, velocity=velocity,
                               channel=channel, time=duration)
        note_off = mido.Message('note_off', note=note, velocity=velocity,
                                channel=channel, time=duration)
        print("send note: ", note)
        print("channel:", channel)
        print("outport:", self.outport)
        self.outport.send(note_on)
        time.sleep(duration)
        self.outport.send(note_off)

    def set_channel(self, channel: int):
        if not 0 <= channel <= 15:
            raise ValueError("Channel must be between 0 and 15.")
        self.channel = channel

    def close(self):
        self.outport.close()