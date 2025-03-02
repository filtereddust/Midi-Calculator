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

        # Define LCD dimensions as class variables
        self.lcd_width = 16
        self.lcd_height = 2

        self.lcd = CharLCD(
            pin_rs=25, pin_rw=24, pin_e=23,
            pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM,
            cols=self.lcd_width, rows=self.lcd_height
        )
        self.current_page = 0
        self.pages = ['MIDI', 'NOTE', 'TIME', 'SCALE']
        self.params = {
            'MIDI': ['channel', 'port'],
            'NOTE': ['note', 'duration'],
            'TIME': ['bpm', 'pattern_length', 'steps_per_bar'],
            'SCALE': ['root', 'type', 'start_oct', 'end_oct', 'apply']
        }
        # Define display priorities and abbreviations
        self.param_abbreviations = {
            'pattern_length': 'pattern',
            'steps_per_bar': 'steps#',
            'start_oct': 'start',
            'end_oct': 'end',
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

    def format_parameter_text(self, param, value, selected=False, editing=False):
        """
        Format parameter text intelligently based on available space.

        Args:
            param: Parameter name
            value: Parameter value
            selected: Whether this parameter is selected
            editing: Whether this parameter is being edited

        Returns:
            Formatted text string that fits within LCD width
        """
        # Selection indicator
        prefix = '*' if selected else ' '

        # Try full parameter name first
        param_text = f"{prefix}{param}:{value}"

        # If it doesn't fit and we have an abbreviation, use that
        if len(param_text) > self.lcd_width and param in self.param_abbreviations:
            param_text = f"{prefix}{self.param_abbreviations[param]}:{value}"

        ###### This solution is a little messy, for final product each truncation should be properly accounted for.
        # If still too long, use intelligent truncation
        if len(param_text) > self.lcd_width:
            # Calculate available space after prefix, colon and value
            value_str = str(value)
            value_len = len(value_str)

            # Calculate maximum parameter name length
            # (LCD width - prefix - colon - value)
            max_param_len = self.lcd_width - 1 - 1 - value_len

            if max_param_len >= 3:  # Ensure minimum readable length
                # Truncate parameter name while keeping as much as possible
                truncated_param = param[:max_param_len]
                param_text = f"{prefix}{truncated_param}:{value}"
            else:
                # Last resort: truncate value if parameter is more important
                max_value_len = self.lcd_width - 1 - 1 - 3  # Keep at least 3 chars of param
                if max_value_len >= 2:  # Ensure value is still meaningful
                    truncated_param = param[:3]
                    truncated_value = value_str[:max_value_len]
                    param_text = f"{prefix}{truncated_param}:{truncated_value}"
                else:
                    # Extreme case: just show shortened versions of both
                    param_text = f"{prefix}{param[:3]}:{value_str[:2]}"

        # Handle editing mode by adding cursor indicator
        if editing and len(param_text) < self.lcd_width:
            param_text += "_"

        return param_text[:self.lcd_width]  # Ensure it fits

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
        """Display timing parameters with text formatting"""
        # Get the visible parameters based on the current scroll offset
        time_params_keys = list(self.time_params.keys())
        visible_params = time_params_keys[self.param_scroll_offset:self.param_scroll_offset + 2]

        for i, param in enumerate(visible_params):
            # Get the current value of the parameter
            value = str(self.time_params[param])

            # Determine if this parameter is selected
            selected = param == self.params['TIME'][self.current_param_index]

            # Handle editing mode
            if selected and self.editing:
                display_value = self.edit_buffer
            else:
                display_value = value

            # Format text
            param_text = self.format_parameter_text(
                param,
                display_value,
                selected=selected,
                editing=(selected and self.editing)
            )

            # Set cursor position and display the text
            self.lcd.cursor_pos = (i, 0)
            self.lcd.write_string(param_text)

    def display_scale(self):
        """Display scale parameters with smart text formatting"""
        # Get the visible parameters based on the current scroll offset
        scale_params_keys = list(self.scale_params.keys())
        visible_params = scale_params_keys[self.param_scroll_offset:self.param_scroll_offset + 2]

        for i, param in enumerate(visible_params):
            # Get the current value of the parameter
            value = str(self.scale_params[param])

            # Determine if this parameter is selected
            selected = param == self.params['SCALE'][self.current_param_index]

            # Handle editing mode
            if selected and self.editing:
                if param in ['root', 'type']:
                    display_value = f"{value} [<>]"
                elif param == 'apply':
                    # For 'apply' parameter, indicate it can be toggled using scrolling
                    display_value = f"{value} [<>]"
                else:
                    display_value = self.edit_buffer
            else:
                display_value = value

            # Format text intelligently using our new function
            param_text = self.format_parameter_text(
                param,
                display_value,
                selected=selected,
                editing=(selected and self.editing)
            )

            # Set cursor position and display the text
            self.lcd.cursor_pos = (i, 0)
            self.lcd.write_string(param_text)

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

        # Update selected parameter with wrap-around
        old_index = self.current_param_index
        self.current_param_index = (self.current_param_index - 1) % max_params

        # For pages with scrolling parameters
        if page in ['TIME', 'SCALE']:
            # If we're moving up and already at top of visible window, scroll up
            if old_index == self.param_scroll_offset:
                self.param_scroll_offset = (self.param_scroll_offset - 1) % max_params
                # If we're at the last parameter, set scroll offset to show last parameters
                if self.current_param_index == max_params - 1:
                    self.param_scroll_offset = max(0, max_params - 2)

        self.update_display()

    def next_param(self):
        page = self.pages[self.current_page]
        max_params = len(self.params[page])

        # Update selected parameter with wrap-around
        old_index = self.current_param_index
        self.current_param_index = (self.current_param_index + 1) % max_params

        # For pages with scrolling parameters
        if page in ['TIME', 'SCALE']:
            # If we're moving down and at bottom of visible window, scroll down
            if old_index == self.param_scroll_offset + 1:
                self.param_scroll_offset = (self.param_scroll_offset + 1) % max_params
                # If we've wrapped to first parameter, reset scroll offset to 0
                if self.current_param_index == 0:
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







