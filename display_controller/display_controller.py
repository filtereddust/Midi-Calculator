# display_controller/display_controller.py
from RPLCD import CharLCD
import RPi.GPIO as GPIO
import time
import mido
import logging
from typing import Dict, Any, Optional

from .state_manager import StateManager
from .input_manager import InputManager
from .display_renderer import DisplayRenderer
from .error_manager import ErrorManager
from .input_validator import InputValidator
from midi.scales import MidiScale


class DisplayController:
    """
    Main controller class that integrates all display system components
    and interfaces with MIDI and sequencer systems.
    """
    
    def __init__(self, midi_device, sequencer):
        """
        Initialize the display controller.
        
        Args:
            midi_device: MidiDevice instance to control
            sequencer: StepSequencer instance to control
        """
        # Set up logging
        self.logger = logging.getLogger('midi_calculator.display')
        self.logger.info("Initializing DisplayController")
        
        # Store device references
        self.midi_device = midi_device
        self.sequencer = sequencer
        
        # Initialize LCD hardware
        self.lcd_width = 16
        self.lcd_height = 2
        self.lcd = CharLCD(
            pin_rs=25, pin_rw=24, pin_e=23,
            pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM,
            cols=self.lcd_width, rows=self.lcd_height
        )
        
        # Initialize components
        self.state_manager = StateManager()
        self.validator = InputValidator()
        self.input_manager = InputManager(self.state_manager)
        self.display = DisplayRenderer(self.lcd, self.state_manager, self.lcd_width, self.lcd_height)
        self.error_handler = ErrorManager(self.lcd, error_display_duration=1.0)
        
        # Connect components
        self.display.set_midi_device(midi_device)
        self.state_manager.register_observer(self.on_state_changed)
        self.error_handler.set_callback(self.on_error)
        
        # Set up input handlers
        self.setup_input_handlers()
        
        # Initialize state with current MIDI device settings
        self.initialize_state()
        
        # Update display initially
        self.update_display()
    
    def initialize_state(self):
        """Initialize state with current MIDI device settings"""
        # Set MIDI device's current channel
        self.state_manager.channel = self.midi_device.channel
        
        # Set sequencer's current BPM
        self.state_manager.time_params['bpm'] = self.sequencer.bpm
        
        # Set pattern length for current channel
        channel = self.midi_device.channel
        if channel in self.sequencer.channel_lengths:
            self.state_manager.time_params['pattern_length'] = self.sequencer.channel_lengths[channel]
            
        # Set steps per bar
        self.state_manager.time_params['steps_per_bar'] = self.sequencer.steps_per_bar
    
    def setup_input_handlers(self):
        """Set up all input handlers"""
        # Register action handlers
        self.input_manager.register_action_handler('prev_page', self.state_manager.prev_page)
        self.input_manager.register_action_handler('next_page', self.state_manager.next_page)
        self.input_manager.register_action_handler('prev_param', self.state_manager.prev_param)
        self.input_manager.register_action_handler('next_param', self.state_manager.next_param)
        self.input_manager.register_action_handler('scroll_prev', lambda: self.handle_scroll('prev'))
        self.input_manager.register_action_handler('scroll_next', lambda: self.handle_scroll('next'))
        self.input_manager.register_action_handler('toggle_edit', self.handle_enter)
        self.input_manager.register_action_handler('backspace', self.input_manager.handle_backspace)
        self.input_manager.register_action_handler('start_playback', self.start_scale_playback)
        self.input_manager.register_action_handler('stop_playback', self.stop_scale_playback)
        self.input_manager.register_action_handler('number_input', self.handle_number)
        
        # Set up key mappings
        self.input_manager.setup_default_mappings()
        self.input_manager.setup_keyboard_listeners()
    
    def on_state_changed(self):
        """Called when state manager signals a state change"""
        self.update_display()
    
    def on_error(self, message: str):
        """Called when an error occurs"""
        self.logger.error(f"Display error: {message}")
    
    def update_display(self):
        """Update the display with current state"""
        if self.error_handler.error_displayed:
            if self.error_handler.clear_error():
                self.display.update_display(force=True)
        else:
            self.display.update_display()
    
    def handle_enter(self):
        """Handle enter key press"""
        if self.state_manager.editing:
            # Save parameter when exiting edit mode
            if self.state_manager.edit_buffer:  # Only update if new input
                self.save_param(self.state_manager.edit_buffer)
            
            # Play note if exiting note edit mode
            if (self.state_manager.get_current_page() == 'NOTE' and
                    self.state_manager.get_current_param() == 'note' and
                    self.state_manager.note_params['note'] is not None):
                self.midi_device.send_note(
                    self.state_manager.note_params['note'],
                    self.state_manager.note_params['duration'],
                    self.midi_device.channel
                )
        
        # Toggle edit mode
        self.state_manager.toggle_edit_mode()
    
    def handle_number(self, key: str):
        """Handle numeric input"""
        self.input_manager.handle_number_input(key)
    
    def handle_scroll(self, direction: str):
        """Handle scrolling through options"""
        # Handle port scrolling separately as it needs MIDI device
        if (self.state_manager.get_current_page() == 'MIDI' and
                self.state_manager.get_current_param() == 'port' and
                self.state_manager.editing):
            self._scroll_port_options(direction)
        else:
            self.state_manager.scroll_options(direction)
    
    def _scroll_port_options(self, direction: str):
        """Scroll through available MIDI ports"""
        if direction == 'prev':
            self.state_manager.current_port_idx = (self.state_manager.current_port_idx - 1) % len(self.midi_device.midi_outputs)
        else:
            self.state_manager.current_port_idx = (self.state_manager.current_port_idx + 1) % len(self.midi_device.midi_outputs)
        
        # Update MIDI port
        try:
            self.midi_device.outport.close()
            self.midi_device.outport = mido.open_output(self.midi_device.midi_outputs[self.state_manager.current_port_idx])
            self.update_display()
        except Exception as e:
            self.error_handler.show_error("Port error", details=str(e))
    
    def save_param(self, value: str):
        """
        Save parameter value after editing.
        
        Args:
            value: String value from edit buffer
        """
        if not value:
            return

        page = self.state_manager.get_current_page()
        param = self.state_manager.get_current_param()

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
                    self.state_manager.current_port_idx = val
                else:
                    self.error_handler.show_error("Invalid port")

            elif param == 'note':
                valid, val = self.validator.validate_note(value)
                if valid:
                    self.state_manager.note_params['note'] = val
                else:
                    self.error_handler.show_error("Invalid note")

            elif param == 'duration':
                valid, val = self.validator.validate_duration(value)
                if valid:
                    self.state_manager.note_params['duration'] = val
                else:
                    self.error_handler.show_error("Invalid duration")

            elif page == 'TIME':
                if param == 'bpm':
                    valid, val = self.validator.validate_bpm(value)
                    if valid:
                        self.state_manager.time_params['bpm'] = val
                        self.sequencer.set_bpm(val)
                    else:
                        self.error_handler.show_error("Invalid BPM")
                elif param == 'pattern_length':
                    valid, val = self.validator.validate_pattern_length(value, self.sequencer.max_steps)
                    if valid:
                        self.state_manager.time_params['pattern_length'] = val
                        self.sequencer.set_channel_steps(self.midi_device.channel, val)
                    else:
                        self.error_handler.show_error("Invalid length")
                elif param == 'steps_per_bar':
                    valid, val = self.validator.validate_steps_per_bar(value)
                    if valid:
                        self.state_manager.time_params['steps_per_bar'] = val
                        # TODO: Implement steps_per_bar in sequencer
                    else:
                        self.error_handler.show_error("Invalid steps")

            elif page == 'SCALE':
                if param == 'root':
                    valid_notes = list(MidiScale.NOTE_TO_MIDI.keys())
                    valid, val = self.validator.validate_scale_root(value, valid_notes)
                    if valid:
                        self.state_manager.scale_params['root'] = val
                    else:
                        self.error_handler.show_error("Invalid root")

                elif param == 'type':
                    valid_types = [attr.replace('_INTERVALS', '')
                                  for attr in dir(MidiScale)
                                  if attr.endswith('_INTERVALS')]
                    valid, val = self.validator.validate_scale_type(value, valid_types)
                    if valid:
                        self.state_manager.scale_params['type'] = val
                    else:
                        self.error_handler.show_error("Invalid type")

                elif param in ['start_oct', 'end_oct']:
                    valid, val = self.validator.validate_octave(value)
                    if valid:
                        if param == 'start_oct' and val > self.state_manager.scale_params['end_oct']:
                            self.error_handler.show_error("Start > End oct")
                        elif param == 'end_oct' and val < self.state_manager.scale_params['start_oct']:
                            self.error_handler.show_error("End < Start oct")
                        else:
                            self.state_manager.scale_params[param] = val
                    else:
                        self.error_handler.show_error("Invalid octave")

                # Apply scale changes if all parameters are valid
                if all([v is not None for k, v in self.state_manager.scale_params.items() if k != 'apply']):
                    try:
                        if self.state_manager.scale_params['apply']:
                            self.apply_scale_to_pattern()
                    except Exception as e:
                        self.error_handler.show_error("Scale error", details=str(e))

        except Exception as e:
            self.error_handler.show_error("Input error", details=str(e))
            
    def start_scale_playback(self):
        """Start the sequencer playback"""
        try:
            # Generate scale using current parameters
            scale = MidiScale.generate_scale(
                self.state_manager.scale_params['root'],
                self.state_manager.scale_params['type'],
                self.state_manager.scale_params['start_oct'],
                self.state_manager.scale_params['end_oct']
            )
            # Start playback with default chances
            self.sequencer.start_scale_playback(scale, note_chance=0.5, octave_chance=0.5)
            self.error_handler.show_error("Started", log_level='info')
        except Exception as e:
            self.error_handler.show_error("Scale error", details=str(e))

    def stop_scale_playback(self):
        """Stop the sequencer playback"""
        try:
            self.sequencer.stop_scale_playback()
            self.error_handler.show_error("Stopped", log_level='info')
        except Exception as e:
            self.error_handler.show_error("Stop error", details=str(e))
            
    def apply_scale_to_pattern(self):
        """Apply the current scale to the sequencer pattern"""
        try:
            scale = MidiScale.generate_scale(
                self.state_manager.scale_params['root'],
                self.state_manager.scale_params['type'],
                self.state_manager.scale_params['start_oct'],
                self.state_manager.scale_params['end_oct']
            )
            
            # Flatten scale into single list of notes
            all_notes = [note for octave in scale.values() for note in octave]
            
            # Let sequencer apply the scale to the pattern
            self.sequencer.apply_random_pattern_from_scale(
                self.midi_device.channel,
                scale,
                note_chance=0.5,
                octave_chance=0.5
            )
            
            self.error_handler.show_error("Scale applied", log_level='info')
        except Exception as e:
            self.error_handler.show_error("Apply error", details=str(e))
            
    def close(self):
        """Clean up resources on shutdown"""
        self.logger.info("Shutting down DisplayController")
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string("Shutting down...")
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string("Goodbye!")
        time.sleep(1)
        self.lcd.clear()
        self.lcd.close()
