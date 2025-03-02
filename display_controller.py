import RPi.GPIO as GPIO
from RPLCD import CharLCD
import keyboard
import time
import mido
from midi.scales import MidiScale


class InputValidator:
    @staticmethod
    def validate_channel(value):
        try:
            val = int(value)
            return 0 <= val <= 15, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_note(value):
        try:
            val = int(value)
            return 0 <= val <= 127, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_duration(value):
        try:
            val = float(value)
            return val > 0, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_port_index(value, max_ports):
        try:
            val = int(value)
            return 0 <= val < max_ports, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_scale_root(value, valid_notes):
        """Validates if a note is a valid root note"""
        return value in valid_notes, value

    @staticmethod
    def validate_scale_type(value, valid_types):
        """Validates if scale type is supported"""
        return value in valid_types, value

    @staticmethod
    def validate_octave(value):
        """Validates octave is within MIDI range"""
        try:
            val = int(value)
            return -2 <= val <= 8, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_boolean(value):
        """Validates boolean value"""
        return value in [True, False], value

    @staticmethod
    def validate_bpm(value):
        try:
            val = int(value)
            return 20 <= val <= 300, val
        except ValueError:
            return False, None

    @staticmethod
    def validate_pattern_length(value, max_steps):
        try:
            val = int(value)
            return 1 <= val <= max_steps, val
        except ValueError:
            return False, None


class DisplayError:
    def __init__(self, lcd):
        self.lcd = lcd
        self.error_displayed = False
        self.error_start_time = 0
        self.error_display_duration = 0.5  # seconds

    def show_error(self, message):
        self.lcd.clear()
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string("Error:")
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(message[:16])  # Truncate to LCD width
        self.error_displayed = True
        self.error_start_time = time.time()

    def clear_error(self):
        if self.error_displayed and (time.time() - self.error_start_time) > self.error_display_duration:
            self.error_displayed = False
            return True
        return False


class DisplayController:

    # Initialization and Setup

    def __init__(self, midi_device, sequencer):
        self.midi_device = midi_device
        self.sequencer = sequencer
        self.lcd = CharLCD(
            pin_rs=25, pin_rw=24, pin_e=23,
            pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM,
            cols=16, rows=2
        )
        self.current_page = 0
        self.pages = ['MIDI', 'NOTE', 'TIME', 'SCALE']
        self.params = {
            'MIDI': ['channel', 'port'],
            'NOTE': ['note', 'duration'],
            'TIME': ['bpm', 'pattern_length', 'steps_per_bar'],
            'SCALE': ['root', 'type', 'start_oct', 'end_oct', 'apply']
        }
        self.current_param_index = 0
        self.note_params = {'note': None, 'duration': 0.5}
        self.editing = False
        self.edit_buffer = ""
        self.current_port_idx = 0
        self.validator = InputValidator()
        self.error_handler = DisplayError(self.lcd)
        self.last_update = time.time()
        self.update_interval = 0.1  # 100ms refresh rate

        self.time_params = {
            'bpm': 120,
            'pattern_length': 16,
            'steps_per_bar': 16
        }
        self.scale_params = {
            'root': 'C',
            'type': 'MAJOR',
            'start_oct': 2,
            'end_oct': 4,
            'apply': False
        }
        self.param_scroll_offset = 0  # Track scrolling position for parameters
        self.setup_keyboard()

    def setup_keyboard(self):
        # page nav
        keyboard.on_press_key(',', lambda _: self.prev_page())  # "<"
        keyboard.on_press_key('.', lambda _: self.next_page())  # ">"

        # Parameter Navigation
        keyboard.on_press_key('left', lambda _: self.prev_param())
        keyboard.on_press_key('right', lambda _: self.next_param())
        keyboard.on_press_key('up', lambda _: self.prev_param())
        keyboard.on_press_key('down', lambda _: self.next_param())

        # Option Scrolling (for lists of choices)
        keyboard.on_press_key('[', lambda _: self.scroll_options('prev'))
        keyboard.on_press_key(']', lambda _: self.scroll_options('next'))

        # Edit Controls
        keyboard.on_press_key('enter', lambda _: self.handle_enter())
        keyboard.on_press_key('backspace', lambda _: self.handle_backspace())

        # Playback Controls
        keyboard.on_press_key('q', lambda _: self.start_scale_playback())
        keyboard.on_press_key('w', lambda _: self.stop_scale_playback())

        # number input
        for key in '0123456789.':
            keyboard.on_press_key(key, lambda e: self.handle_number(e.name))

    def close(self):
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string("Shutting down...")
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string("Goodbye!")
        time.sleep(1)
        self.lcd.clear()
        self.lcd.close()

    # Display State Management
    def update_display(self):
        if self.error_handler.error_displayed:
            if self.error_handler.clear_error():
                self.last_update = time.time()
                self.lcd.clear()
                self._update_current_page()
        else:
            self.last_update = time.time()
            self.lcd.clear()
            self._update_current_page()

    def _update_current_page(self):
        """Helper method to update the current page display"""
        if self.pages[self.current_page] == 'MIDI':
            self.display_midi()
        elif self.pages[self.current_page] == 'NOTE':
            self.display_note()
        elif self.pages[self.current_page] == 'TIME':
            self.display_time()
        elif self.pages[self.current_page] == 'SCALE':
            self.display_scale()

    def display_midi(self):
        self.lcd.cursor_pos = (0, 0)
        channel_str = f"CH:{self.midi_device.channel}"
        port_str = f"Port:{self.midi_device.midi_outputs[self.current_port_idx][:8]}"

        if self.current_param_index == 0:
            if self.editing:
                channel_str = f"CH:{self.edit_buffer}"
                if len(self.edit_buffer) < 3:
                    channel_str += "_"
            self.lcd.write_string(f"*{channel_str}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f" {port_str}")
        else:  # Port parameter
            if self.editing:
                port_str = f"Port:{self.midi_device.midi_outputs[self.current_port_idx][:6]} [<>]"
            self.lcd.write_string(f" {channel_str}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f"*{port_str}")

    def display_note(self):
        note = str(self.note_params['note']) if self.note_params['note'] else '---'
        dur = str(self.note_params['duration'])

        if self.current_param_index == 0:  # Note parameter
            if self.editing:
                note = self.edit_buffer
                if len(self.edit_buffer) < 3:
                    note += "_"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f"*Note:{note}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f" Dur:{dur}")
        else:  # Duration parameter
            if self.editing:
                dur = self.edit_buffer
                if len(self.edit_buffer) < 3:
                    dur += "_"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f" Note:{note}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f"*Dur:{dur}")

    def display_time(self):
        """Display timing parameters with scrolling support"""
        visible_params = list(self.time_params.keys())[self.param_scroll_offset:self.param_scroll_offset + 2]

        for i, param in enumerate(visible_params):
            self.lcd.cursor_pos = (i, 0)
            value = str(self.time_params[param])

            if param == self.params['TIME'][self.current_param_index]:
                if self.editing:
                    value = self.edit_buffer + '_' if len(self.edit_buffer) < 3 else self.edit_buffer
                prefix = '*'
            else:
                prefix = ' '

            param_text = f"{prefix}{param[:5]}:{value}"
            self.lcd.write_string(param_text[:16])

    def display_scale(self):
        visible_params = list(self.scale_params.keys())[self.param_scroll_offset:self.param_scroll_offset + 2]

        for i, param in enumerate(visible_params):
            self.lcd.cursor_pos = (i, 0)
            value = str(self.scale_params[param])

            if param == self.params['SCALE'][self.current_param_index]:
                if self.editing:
                    if param in ['root', 'type']:
                        value = f"{value} [<>]"
                    else:
                        value = self.edit_buffer + '_' if len(self.edit_buffer) < 3 else self.edit_buffer
                prefix = '*'
            else:
                prefix = ' '

            param_text = f"{prefix}{param[:5]}:{value}"
            self.lcd.write_string(param_text[:16])

    def start_scale_playback(self):
        """Start the sequencer playback"""
        try:
            # Generate scale using current parameters
            scale = MidiScale.generate_scale(
                self.scale_params['root'],
                self.scale_params['type'],
                self.scale_params['start_oct'],
                self.scale_params['end_oct']
            )
            # Start playback with default chances
            self.sequencer.start_scale_playback(scale, note_chance=0.5, octave_chance=0.5)
            self.error_handler.show_error("Started")
        except Exception as e:
            self.error_handler.show_error("Scale error")
        


    def stop_scale_playback(self):
        """Stop the sequencer playback"""
        print("stop test")
        self.sequencer.stop_scale_playback()
        self.error_handler.show_error("Stopped")

    # Navigation
    def prev_page(self):
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.current_param_index = 0
        self.param_scroll_offset = 0
        self.update_display()
        self.update_display()

    def next_page(self):
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.current_param_index = 0
        self.param_scroll_offset = 0
        self.update_display()

    def prev_param(self):
        page = self.pages[self.current_page]
        max_params = len(self.params[page])

        # Update selected parameter
        old_index = self.current_param_index
        self.current_param_index = (self.current_param_index - 1) % max_params

        # For pages with scrolling parameters
        if page in ['TIME', 'SCALE']:
            # If we're moving up and already at top of visible window, scroll up
            if old_index == self.param_scroll_offset:
                self.param_scroll_offset = max(0, self.param_scroll_offset - 1)
            # If we wrapped around to bottom, show last two parameters
            elif old_index == 0:
                self.param_scroll_offset = max(0, max_params - 2)

        self.update_display()

    def next_param(self):
        page = self.pages[self.current_page]
        max_params = len(self.params[page])

        # Update selected parameter
        old_index = self.current_param_index
        self.current_param_index = (self.current_param_index + 1) % max_params

        # For pages with scrolling parameters
        if page in ['TIME', 'SCALE']:
            # If we're moving down and at bottom of visible window, scroll down
            if old_index == self.param_scroll_offset + 1:
                self.param_scroll_offset = min(max_params - 2, self.param_scroll_offset + 1)
            # If we wrapped around to top, show first two parameters
            elif old_index == max_params - 1:
                self.param_scroll_offset = 0

        self.update_display()

    # Parameter editing

    def toggle_edit(self):
        self.editing = not self.editing
        if not self.editing:  # Exiting edit mode
            if self.edit_buffer:  # Only update if new input
                self.save_param(self.edit_buffer)
                self.edit_buffer = ""
            # Play note regardless if entering or exiting edit mode
            if (self.pages[self.current_page] == 'NOTE' and
                    self.params['NOTE'][self.current_param_index] == 'note' and
                    self.note_params['note'] is not None):
                self.midi_device.send_note(
                    self.note_params['note'],
                    self.note_params['duration'],
                    self.midi_device.channel
                )
        self.update_display()

    def save_param(self, value):
        if not value:
            return

        page = self.pages[self.current_page]
        param = self.params[page][self.current_param_index]

        try:
            if param == 'channel':
                valid, val = self.validator.validate_channel(value)
                if valid:
                    self.midi_device.set_channel(val)
                else:
                    self.error_handler.show_error("Invalid channel")

            elif param == 'port':
                valid, val = self.validator.validate_port_index(value, len(self.midi_device.midi_outputs))
                if valid:
                    self.midi_device.outport.close()
                    self.midi_device.outport = mido.open_output(self.midi_device.midi_outputs[val])
                else:
                    self.error_handler.show_error("Invalid port")

            elif param == 'note':
                valid, val = self.validator.validate_note(value)
                if valid:
                    self.note_params['note'] = val
                else:
                    self.error_handler.show_error("Invalid note")

            elif param == 'duration':
                valid, val = self.validator.validate_duration(value)
                if valid:
                    self.note_params['duration'] = val
                else:
                    self.error_handler.show_error("Invalid duration")

            elif page == 'TIME':
                if param == 'bpm':
                    valid, val = self.validator.validate_bpm(value)
                    if valid:
                        self.time_params['bpm'] = val
                        self.sequencer.set_bpm(val)
                    else:
                        self.error_handler.show_error("Invalid BPM")
                elif param == 'pattern_length':
                    valid, val = self.validator.validate_pattern_length(value, self.sequencer.max_steps)
                    if valid:
                        self.time_params['pattern_length'] = val
                        self.sequencer.set_channel_steps(self.midi_device.channel, val)
                    else:
                        self.error_handler.show_error("Invalid length")

            elif page == 'SCALE':
                if param == 'root':
                    valid_notes = list(MidiScale.NOTE_TO_MIDI.keys())
                    valid, val = self.validator.validate_scale_root(value, valid_notes)
                    if valid:
                        self.scale_params['root'] = val
                    else:
                        self.error_handler.show_error("Invalid root")

                elif param == 'type':
                    valid_types = [attr.replace('_INTERVALS', '')
                                   for attr in dir(MidiScale)
                                   if attr.endswith('_INTERVALS')]
                    valid, val = self.validator.validate_scale_type(value, valid_types)
                    if valid:
                        self.scale_params['type'] = val
                    else:
                        self.error_handler.show_error("Invalid type")

                elif param in ['start_oct', 'end_oct']:
                    valid, val = self.validator.validate_octave(value)
                    if valid:
                        if param == 'start_oct' and val > self.scale_params['end_oct']:
                            self.error_handler.show_error("Start > End oct")
                        elif param == 'end_oct' and val < self.scale_params['start_oct']:
                            self.error_handler.show_error("End < Start oct")
                        else:
                            self.scale_params[param] = val
                    else:
                        self.error_handler.show_error("Invalid octave")

                elif param == 'apply':
                    self.scale_params['apply'] = not self.scale_params['apply']  # Toggle boolean

                # Apply scale changes if all parameters are valid
                if all(self.scale_params.values()):
                    try:
                        scale = MidiScale.generate_scale(
                            self.scale_params['root'],
                            self.scale_params['type'],
                            self.scale_params['start_oct'],
                            self.scale_params['end_oct']
                        )

                        if self.scale_params['apply']:
                            # Flatten scale into single list of notes
                            all_notes = [note for octave in scale.values() for note in octave]
                            self.sequencer.apply_scale_to_pattern(all_notes)
                    except Exception as e:
                        self.error_handler.show_error("Scale error")

        except Exception as e:
            self.error_handler.show_error("Input error")

    def update_param(self):
        self.toggle_edit()
        self.update_display()

    # Scrolling
    def scroll_options(self, direction):
        """
        Scroll through available options for parameters with preset choices
        Only works when in edit mode

        Args:
            direction (str): 'prev' or 'next'
        """
        if not self.editing:
            return

        page = self.pages[self.current_page]
        param = self.params[page][self.current_param_index]

        # Define which parameters have scrollable options
        option_handlers = {
            'MIDI': {
                'port': self._scroll_port_options,
            },
            'SCALE': {
                'root': self._scroll_note_options,
                'type': self._scroll_scale_type_options,
                'apply': self._scroll_boolean_option,
            }

        }

        # Call appropriate scroll handler if it exists
        if page in option_handlers and param in option_handlers[page]:
            option_handlers[page][param](direction)
            self.update_display()

    def _scroll_port_options(self, direction):
        if direction == 'prev':
            self.current_port_idx = (self.current_port_idx - 1) % len(self.midi_device.midi_outputs)
        else:
            self.current_port_idx = (self.current_port_idx + 1) % len(self.midi_device.midi_outputs)
        # Update MIDI port
        self.midi_device.outport.close()
        self.midi_device.outport = mido.open_output(self.midi_device.midi_outputs[self.current_port_idx])

    def _scroll_note_options(self, direction):
        valid_notes = list(MidiScale.NOTE_TO_MIDI.keys())
        current_idx = valid_notes.index(self.scale_params['root'])
        if direction == 'prev':
            new_idx = (current_idx - 1) % len(valid_notes)
        else:
            new_idx = (current_idx + 1) % len(valid_notes)
        self.scale_params['root'] = valid_notes[new_idx]

    def _scroll_scale_type_options(self, direction):
        valid_types = [attr.replace('_INTERVALS', '')
                       for attr in dir(MidiScale)
                       if attr.endswith('_INTERVALS')]
        current_idx = valid_types.index(self.scale_params['type'])
        if direction == 'prev':
            new_idx = (current_idx - 1) % len(valid_types)
        else:
            new_idx = (current_idx + 1) % len(valid_types)
        self.scale_params['type'] = valid_types[new_idx]

    def _scroll_boolean_option(self, direction):
        """Toggle boolean value regardless of direction"""
        self.scale_params['apply'] = not self.scale_params['apply']

    # Input Handling

    def handle_enter(self):
        if self.editing:
            self.toggle_edit()  # Save and exit edit mode
        else:
            self.toggle_edit()  # Enter edit mode

    def handle_number(self, key):
        if self.editing:
            page = self.pages[self.current_page]
            param = self.params[page][self.current_param_index]

            if key == '.' and '.' not in self.edit_buffer:
                self.edit_buffer += key
            elif key.isdigit() and len(self.edit_buffer) < 4:
                self.edit_buffer += key

            self.update_display()

    def handle_backspace(self):
        if self.editing and self.edit_buffer:
            self.edit_buffer = self.edit_buffer[:-1]
            self.update_display()







