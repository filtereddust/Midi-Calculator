import tkinter as tk
from tkinter import messagebox
import mido
from midi.scales import MidiScale
from midi.device import MidiDevice
from sequencer.sequencer import StepSequencer
import threading


class MidiDeviceGUI:
    def __init__(self, midi_device: MidiDevice):
        self.midi_device = midi_device
        self.sequencer = StepSequencer(midi_device)
        self.root = tk.Tk()
        self.root.title("MIDI Sequencer")

        # Initialize variables
        self.current_channel = tk.IntVar(value=0)
        self.edit_step = tk.IntVar(value=0)
        self.step_active = tk.BooleanVar(value=False)
        self.note_value = tk.StringVar(value="")
        self.pattern_length = tk.StringVar(value="16")
        self.playback_step_label = None
        self.update_timer = None
        self.bpm_var = tk.StringVar(value="120")
        self.apply_to_pattern_var = tk.BooleanVar(value=False)
        self.note_chance_var = tk.DoubleVar(value=0.5)
        self.octave_chance_var = tk.DoubleVar(value=0.5)

        self.setup_gui()

    def setup_gui(self):
        self.setup_midi_controls()
        self.setup_note_player()
        self.setup_scale_controls()
        self.setup_timing_controls()
        self.setup_step_controls()
        self.setup_transport_controls()

    def setup_midi_controls(self):
        control_frame = tk.LabelFrame(self.root, text="MIDI Controls")
        control_frame.pack(pady=5, padx=5, fill="x")

        # Port selection
        port_frame = tk.Frame(control_frame)
        port_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=self.midi_device.midi_outputs[0])
        tk.OptionMenu(port_frame, self.port_var,
                      *self.midi_device.midi_outputs,
                      command=self.change_port).pack(side=tk.LEFT)

        # Channel selection
        channel_frame = tk.Frame(control_frame)
        channel_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(channel_frame, text="Channel:").pack(side=tk.LEFT)
        channel_select = tk.Spinbox(
            channel_frame,
            from_=0,
            to=15,
            width=3,
            textvariable=self.current_channel,
            command=self.change_channel
        ).pack(side=tk.LEFT)

    def setup_note_player(self):
        note_frame = tk.LabelFrame(self.root, text="Note Player")
        note_frame.pack(pady=5, padx=5, fill="x")

        input_frame = tk.Frame(note_frame)
        input_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(input_frame, text="Note:").pack(side=tk.LEFT)
        self.note_entry = tk.Entry(input_frame, width=5)
        self.note_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(input_frame, text="Duration:").pack(side=tk.LEFT)
        self.duration_entry = tk.Entry(input_frame, width=5)
        self.duration_entry.insert(0, "0.5")
        self.duration_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(input_frame, text="Play Note",
                  command=self.play_note).pack(side=tk.LEFT, padx=5)

    def setup_scale_controls(self):
        scale_frame = tk.LabelFrame(self.root, text="Scale Generator")
        scale_frame.pack(pady=5, padx=5, fill="x")

        root_frame = tk.Frame(scale_frame)
        root_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(root_frame, text="Root:").pack(side=tk.LEFT)
        self.root_note_var = tk.StringVar(value="C")
        tk.OptionMenu(root_frame, self.root_note_var,
                      *list(MidiScale.NOTE_TO_MIDI.keys())).pack(side=tk.LEFT)

        tk.Label(root_frame, text="Type:").pack(side=tk.LEFT)
        self.scale_type_var = tk.StringVar(value="MAJOR")
        scale_types = [attr.replace('_INTERVALS', '')
                       for attr in dir(MidiScale)
                       if attr.endswith('_INTERVALS')]
        tk.OptionMenu(root_frame, self.scale_type_var,
                      *scale_types).pack(side=tk.LEFT)

        octave_frame = tk.Frame(scale_frame)
        octave_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(octave_frame, text="Start:").pack(side=tk.LEFT)
        self.start_octave_var = tk.IntVar(value=2)
        tk.Entry(octave_frame, textvariable=self.start_octave_var,
                 width=3).pack(side=tk.LEFT)

        tk.Label(octave_frame, text="End:").pack(side=tk.LEFT)
        self.end_octave_var = tk.IntVar(value=4)
        tk.Entry(octave_frame, textvariable=self.end_octave_var,
                 width=3).pack(side=tk.LEFT)

        tk.Button(octave_frame, text="Generate",
                  command=self.apply_scale).pack(side=tk.LEFT, padx=5)

        tk.Button(octave_frame, text="Load to Pattern",
                  command=lambda: self.apply_scale_to_current_pattern()).pack(side=tk.LEFT, padx=5)
        random_frame = tk.Frame(scale_frame)
        random_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(random_frame, text="Note Chance:").pack(side=tk.LEFT)
        tk.Scale(random_frame, from_=0, to=1, resolution=0.1,
                 variable=self.note_chance_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT)

        tk.Label(random_frame, text="Octave Chance:").pack(side=tk.LEFT)
        tk.Scale(random_frame, from_=0, to=1, resolution=0.1,
                 variable=self.octave_chance_var, orient=tk.HORIZONTAL).pack(side=tk.LEFT)

    def apply_scale_to_current_pattern(self):
        self.apply_to_pattern_var.set(True)
        self.apply_scale()
        self.apply_to_pattern_var.set(False)
    def setup_timing_controls(self):
        timing_frame = tk.LabelFrame(self.root, text="Timing")
        timing_frame.pack(pady=5, padx=5, fill="x")

        control_frame = tk.Frame(timing_frame)
        control_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(control_frame, text="BPM:").pack(side=tk.LEFT)
        tk.Entry(control_frame, textvariable=self.bpm_var,
                 width=5).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Set",
                  command=self.update_tempo).pack(side=tk.LEFT)

        tk.Label(control_frame, text="Pattern Length:").pack(side=tk.LEFT, padx=5)
        tk.Entry(control_frame, textvariable=self.pattern_length,
                 width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Set Length",
                  command=self.update_pattern_length).pack(side=tk.LEFT, padx=5)

    def setup_step_controls(self):
        step_frame = tk.LabelFrame(self.root, text="Step Editor")
        step_frame.pack(pady=5, padx=5, fill="x")

        nav_frame = tk.Frame(step_frame)
        nav_frame.pack(fill="x", padx=5, pady=2)

        tk.Button(nav_frame, text="◀", command=self.prev_step).pack(side=tk.LEFT)
        tk.Label(nav_frame, text="Edit Step:").pack(side=tk.LEFT, padx=2)
        self.step_label = tk.Label(nav_frame, textvariable=self.edit_step)
        self.step_label.pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="▶", command=self.next_step).pack(side=tk.LEFT)

        tk.Label(nav_frame, text="|").pack(side=tk.LEFT, padx=5)
        self.playback_step_label = tk.Label(nav_frame, text="Playing: --")
        self.playback_step_label.pack(side=tk.LEFT, padx=5)

        settings_frame = tk.Frame(step_frame)
        settings_frame.pack(fill="x", padx=5, pady=2)

        tk.Checkbutton(
            settings_frame,
            text="Step Active",
            variable=self.step_active,
            command=self.update_step
        ).pack(side=tk.LEFT, padx=5)

        tk.Label(settings_frame, text="Note:").pack(side=tk.LEFT, padx=5)
        note_entry = tk.Entry(
            settings_frame,
            textvariable=self.note_value,
            width=5
        )
        note_entry.pack(side=tk.LEFT, padx=2)
        tk.Button(
            settings_frame,
            text="Set Note",
            command=self.update_step
        ).pack(side=tk.LEFT, padx=5)

    def setup_transport_controls(self):
        transport_frame = tk.Frame(self.root)
        transport_frame.pack(pady=5)

        tk.Button(
            transport_frame,
            text="Play",
            command=self.start_playback
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            transport_frame,
            text="Stop",
            command=self.stop_playback
        ).pack(side=tk.LEFT, padx=2)

    # Method implementations from both classes
    def change_port(self, selection):
        port_index = self.midi_device.midi_outputs.index(selection)
        self.midi_device.outport.close()
        self.midi_device.outport = mido.open_output(self.midi_device.midi_outputs[port_index])

    def play_note(self):
        try:
            note = int(self.note_entry.get())
            duration = float(self.duration_entry.get())
            channel = self.current_channel.get()

            if 0 <= note <= 127 and duration > 0:
                threading.Thread(
                    target=self.midi_device.send_note,
                    args=(note, duration, channel),
                    daemon=True
                ).start()
            else:
                raise ValueError("Note must be 0-127 and duration must be positive")
        except ValueError as e:
            tk.messagebox.showerror(
                "Error",
                f"Invalid input: {str(e)}\nPlease enter a valid note (0-127) and duration (>0)"
            )

    def apply_scale(self):
        try:
            scale = MidiScale.generate_scale(
                self.root_note_var.get(),
                self.scale_type_var.get(),
                self.start_octave_var.get(),
                self.end_octave_var.get()
            )

            if self.apply_to_pattern_var.get():
                self.sequencer.stop_scale_playback()
                self.sequencer.apply_random_pattern_from_scale(
                    self.current_channel.get(),
                    scale,
                    self.note_chance_var.get(),
                    self.octave_chance_var.get()
                )
                self.load_step_data()
            else:
                self.sequencer.stop()
                self.sequencer.start_scale_playback(
                    scale,
                    self.note_chance_var.get(),
                    self.octave_chance_var.get()
                )
        except ValueError as e:
            tk.messagebox.showerror("Error", str(e))

    def update_tempo(self):
        try:
            new_bpm = int(self.bpm_var.get())
            if new_bpm > 0:
                self.sequencer.set_bpm(new_bpm)
            else:
                raise ValueError("BPM must be greater than 0")
        except ValueError as e:
            tk.messagebox.showerror("Error", f"Please enter a valid BPM value: {str(e)}")

    def start_playback(self):
        self.sequencer.start()
        self.start_playback_updates()

    def stop_playback(self):
        """Stop both sequencer and scale playback"""
        self.sequencer.stop()
        self.sequencer.stop_scale_playback()
        self.stop_playback_updates()

    def start_playback_updates(self):
        if self.update_timer is None:
            self.update_playback_display()

    def stop_playback_updates(self):
        if self.update_timer is not None:
            self.root.after_cancel(self.update_timer)
            self.update_timer = None
            self.playback_step_label.config(text="Playing: --")

    def update_playback_display(self):
        if self.sequencer.running:
            self.playback_step_label.config(text=f"Playing: {self.sequencer.playback_step + 1}")
            self.update_timer = self.root.after(50, self.update_playback_display)
        else:
            self.stop_playback_updates()

    def change_channel(self):
        self.load_step_data()

    def update_pattern_length(self):
        try:
            length = int(self.pattern_length.get())
            if 1 <= length <= self.sequencer.max_steps:
                self.sequencer.set_channel_steps(self.current_channel.get(), length)
            else:
                raise ValueError(f"Length must be between 1 and {self.sequencer.max_steps}")
        except ValueError as e:
            tk.messagebox.showerror("Error", str(e))

    def prev_step(self):
        current = self.edit_step.get()
        self.edit_step.set((current - 1) % int(self.pattern_length.get()))
        self.load_step_data()

    def next_step(self):
        current = self.edit_step.get()
        self.edit_step.set((current + 1) % int(self.pattern_length.get()))
        self.load_step_data()

    def load_step_data(self):
        try:
            step_data = self.sequencer.get_step(
                self.current_channel.get(),
                self.edit_step.get()
            )
            self.step_active.set(step_data['active'])
            self.note_value.set(str(step_data['note']) if step_data['note'] is not None else "")
        except ValueError as e:
            tk.messagebox.showerror("Error", str(e))

    def update_step(self):
        try:
            note = None
            if self.note_value.get().strip():
                note = int(self.note_value.get())
                if not 0 <= note <= 127:
                    raise ValueError("Note must be between 0 and 127")

            self.sequencer.set_step(
                channel=self.current_channel.get(),
                step=self.edit_step.get(),
                active=self.step_active.get(),
                note=note
            )
        except ValueError as e:
            tk.messagebox.showerror("Error", str(e))

    def run(self):
        self.root.mainloop()