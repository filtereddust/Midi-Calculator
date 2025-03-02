import threading
import random
import time


class StepSequencer:
    def __init__(self, midi_device, bpm=120, steps_per_bar=16, max_steps=64):
        self.midi_device = midi_device
        self.bpm = bpm
        self.steps_per_bar = steps_per_bar
        self.max_steps = max_steps
        self.step_time = 60 / (bpm * (steps_per_bar / 4))
        self.running = False
        self.playback_step = 0  # Current step during playback
        self.edit_step = 0  # Current step being edited
        self.event = threading.Event()

        # Multi-channel pattern storage
        # Format: {channel: {step: {'active': bool, 'note': int, 'velocity': int}}}
        self.patterns = {}
        for channel in range(16):  # MIDI has 16 channels
            self.patterns[channel] = {
                step: {
                    'active': False,
                    'note': None,
                    'velocity': 100
                } for step in range(max_steps)
            }
        self.channel_lengths = {channel: steps_per_bar for channel in range(16)}

        self.current_scale = None
        self.current_octave = 3  # Default octave
        self.scale_playback = False
        self.scale_thread = None

    def set_step(self, channel: int, step: int, active: bool, note: int = None, velocity: int = 100):
        """Set parameters for a specific step in a channel's pattern"""
        if not (0 <= channel <= 15):
            raise ValueError("Channel must be between 0 and 15")
        if not (0 <= step < self.max_steps):
            raise ValueError(f"Step must be between 0 and {self.max_steps - 1}")
        if note is not None and not (0 <= note <= 127):
            raise ValueError("Note must be between 0 and 127")
        if not (0 <= velocity <= 127):
            raise ValueError("Velocity must be between 0 and 127")

        self.patterns[channel][step] = {
            'active': active,
            'note': note,
            'velocity': velocity
        }

    def get_step(self, channel: int, step: int) -> dict:
        """Get parameters for a specific step in a channel's pattern"""
        if not (0 <= channel <= 15):
            raise ValueError("Channel must be between 0 and 15")
        if not (0 <= step < self.max_steps):
            raise ValueError(f"Step must be between 0 and {self.max_steps - 1}")

        return self.patterns[channel][step].copy()

    def clear_channel(self, channel: int):
        """Clear all steps in a channel's pattern"""
        if not (0 <= channel <= 15):
            raise ValueError("Channel must be between 0 and 15")

        self.patterns[channel] = {
            step: {
                'active': False,
                'note': None,
                'velocity': 100
            } for step in range(self.max_steps)
        }

    # Modify set_channel_steps to ensure proper length setting:
    def set_channel_steps(self, channel: int, steps: int):
        """Set number of steps for a specific channel"""
        if not (0 <= channel <= 15):
            raise ValueError("Channel must be between 0 and 15")
        if not (1 <= steps <= self.max_steps):
            raise ValueError(f"Steps must be between 1 and {self.max_steps}")

        self.channel_lengths[channel] = steps

        # Preserve existing steps up to new length, clear the rest
        current_pattern = self.patterns[channel]
        new_pattern = {}

        for step in range(self.max_steps):
            if step < steps:
                new_pattern[step] = current_pattern[step] if step in current_pattern else {
                    'active': False,
                    'note': None,
                    'velocity': 100
                }
            else:
                new_pattern[step] = {
                    'active': False,
                    'note': None,
                    'velocity': 100
                }

        self.patterns[channel] = new_pattern

    def play_step(self, step: int):
        """Play all active notes for the current step across all channels"""
        for channel in range(16):
            step_data = self.patterns[channel][step]
            if step_data['active'] and step_data['note'] is not None:
                self.midi_device.send_note(
                    step_data['note'],
                    self.step_time * 0.9,  # Slightly shorter than step time to prevent notes bleeding
                    channel,
                    step_data['velocity']
                )

    def start(self):
        """Start the sequencer"""
        if not self.running:
            self.running = True
            self.sequencer_thread = threading.Thread(target=self._run)
            self.sequencer_thread.start()

    def stop(self):
        """Stop the sequencer"""
        self.running = False
        if hasattr(self, "sequencer_thread"):
            self.sequencer_thread.join()

    def _run(self):
        """Main sequencer loop"""
        while self.running:
            start_time = time.time()
            self.play_step(self.playback_step)

            elapsed = time.time() - start_time
            sleep_time = max(0, self.step_time - elapsed)
            time.sleep(sleep_time)

            # Use the current channel's length for playback
            current_length = self.channel_lengths[0]  # Default to first channel
            self.playback_step = (self.playback_step + 1) % current_length

    def set_bpm(self, bpm: int):
        """Update the BPM and recalculate step time"""
        if bpm <= 0:
            raise ValueError("BPM must be greater than 0")
        self.bpm = bpm
        self.step_time = 60 / (bpm * (self.steps_per_bar / 4))

    def copy_channel_pattern(self, source_channel: int, target_channel: int):
        """Copy pattern from one channel to another"""
        if not (0 <= source_channel <= 15 and 0 <= target_channel <= 15):
            raise ValueError("Channels must be between 0 and 15")

        self.patterns[target_channel] = {
            step: self.patterns[source_channel][step].copy()
            for step in range(self.max_steps)
        }

    def play_random_scale(self, note_chance=0.5, octave_chance=0.5, channel=0):
        """Continuously play random notes from the current scale"""
        while self.scale_playback and self.current_scale:
            rand_value = random.random()  # Generate value between 0.0 and 1.0
            if rand_value <= note_chance:  # Note will only play if random value is less than or equal to chance
                octave_rand = random.random()  # Separate random value for octave
                if octave_rand <= octave_chance:
                    possible_octaves = list(self.current_scale.keys())
                    self.current_octave = random.choice(possible_octaves)

                if self.current_octave in self.current_scale:
                    note = random.choice(self.current_scale[self.current_octave])
                    self.midi_device.send_note(
                        note,
                        self.step_time * 0.9,
                        channel=self.midi_device.channel, # Use the current active channe
                        velocity=random.randint(70, 100)
                    )

            time.sleep(self.step_time)

    def start_scale_playback(self, scale_dict, note_chance=0.5, octave_chance=0.5,channel=0):
        self.current_scale = scale_dict
        self.current_octave = min(scale_dict.keys())
        self.scale_playback = True
        self.scale_thread = threading.Thread(
            target=self.play_random_scale,
            args=(note_chance, octave_chance,channel),
            daemon=True
        )
        self.scale_thread.start()

    def stop_scale_playback(self):
        """Stop random scale playback"""
        self.scale_playback = False
        if self.scale_thread:
            self.scale_thread = None

    def apply_random_pattern_from_scale(self, channel: int, scale_dict: dict, note_chance=0.5, octave_chance=0.5):
        """Apply random notes from scale to pattern"""
        pattern_length = self.channel_lengths[channel]
        self.clear_channel(channel)

        # Initialize with default octave
        current_octave = min(scale_dict.keys())

        for step in range(pattern_length):
            # Check note chance
            if random.random() <= note_chance:
                # Check octave chance
                if random.random() <= octave_chance:
                    possible_octaves = list(scale_dict.keys())
                    current_octave = random.choice(possible_octaves)

                # Get notes from current octave
                if current_octave in scale_dict:
                    note = random.choice(scale_dict[current_octave])
                    self.patterns[channel][step] = {
                        'active': True,
                        'note': note,
                        'velocity': random.randint(80, 100)
                    }