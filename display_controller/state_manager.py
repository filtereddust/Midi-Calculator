# display_controller/state_manager.py
from typing import Dict, Any, Optional, List
from midi.scales import MidiScale

class StateManager:
    """
    Manages the state of the display interface, including pages, parameters,
    and user input.
    """
    
    def __init__(self):
        # Define LCD dimensions 
        self.lcd_width = 16
        self.lcd_height = 2
        
        # Page and parameter navigation
        self.current_page = 0
        self.pages = ['MIDI', 'NOTE', 'TIME', 'SCALE']
        self.params = {
            'MIDI': ['channel', 'port'],
            'NOTE': ['note', 'duration'],
            'TIME': ['bpm', 'pattern_length', 'steps_per_bar'],
            'SCALE': ['root', 'type', 'start_oct', 'end_oct', 'apply']
        }
        
        # Parameter abbreviations for display
        self.param_abbreviations = {
            'pattern_length': 'pattern',
            'steps_per_bar': 'steps#',
            'start_oct': 'start',
            'end_oct': 'end',
        }
        
        # Parameter values
        self.current_param_index = 0
        self.current_port_idx = 0
        self.note_params = {'note': None, 'duration': 0.5}
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
        
        # Edit state
        self.editing = False
        self.edit_buffer = ""
        
        # Scroll state for displaying parameters
        self.param_scroll_offset = 0
        
        # State change observers
        self._observers = []
    
    def register_observer(self, callback):
        """Register a function to be called when state changes"""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def unregister_observer(self, callback):
        """Remove an observer function"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self):
        """Notify all observers that state has changed"""
        for callback in self._observers:
            callback()
    
    # Page navigation
    def next_page(self):
        """Move to the next page"""
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.current_param_index = 0
        self.param_scroll_offset = 0
        self._notify_observers()
        
    def prev_page(self):
        """Move to the previous page"""
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.current_param_index = 0
        self.param_scroll_offset = 0
        self._notify_observers()
    
    # Parameter navigation
    def next_param(self):
        """Move to the next parameter on current page"""
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
        
        self._notify_observers()
    
    def prev_param(self):
        """Move to the previous parameter on current page"""
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
        
        self._notify_observers()
    
    # Edit mode
    def toggle_edit_mode(self):
        """Toggle edit mode for the current parameter"""
        self.editing = not self.editing
        if not self.editing:  # Exiting edit mode
            self.edit_buffer = ""
        self._notify_observers()
    
    def update_edit_buffer(self, key: str):
        """Add a character to the edit buffer"""
        if not self.editing:
            return
        
        # Handle different key types
        if key == '.' and '.' not in self.edit_buffer:
            self.edit_buffer += key
        elif key.isdigit() and len(self.edit_buffer) < 4:
            self.edit_buffer += key
        
        self._notify_observers()
    
    def remove_last_char(self):
        """Remove the last character from the edit buffer"""
        if self.editing and self.edit_buffer:
            self.edit_buffer = self.edit_buffer[:-1]
            self._notify_observers()
    
    # Parameter scrolling
    def scroll_options(self, direction: str):
        """
        Scroll through available options for parameters with preset choices
        
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
            self._notify_observers()
    
    def _scroll_port_options(self, direction: str):
        """Scroll through available MIDI ports"""
        # This requires access to midi_device, so this will be implemented
        # in the DisplayController that has access to midi_device
        pass
    
    def _scroll_note_options(self, direction: str):
        """Scroll through available note options"""
        valid_notes = list(MidiScale.NOTE_TO_MIDI.keys())
        current_idx = valid_notes.index(self.scale_params['root'])
        if direction == 'prev':
            new_idx = (current_idx - 1) % len(valid_notes)
        else:
            new_idx = (current_idx + 1) % len(valid_notes)
        self.scale_params['root'] = valid_notes[new_idx]
    
    def _scroll_scale_type_options(self, direction: str):
        """Scroll through available scale types"""
        valid_types = [attr.replace('_INTERVALS', '')
                      for attr in dir(MidiScale)
                      if attr.endswith('_INTERVALS')]
        current_idx = valid_types.index(self.scale_params['type'])
        if direction == 'prev':
            new_idx = (current_idx - 1) % len(valid_types)
        else:
            new_idx = (current_idx + 1) % len(valid_types)
        self.scale_params['type'] = valid_types[new_idx]
    
    def _scroll_boolean_option(self, direction: str):
        """Toggle boolean value regardless of direction"""
        self.scale_params['apply'] = not self.scale_params['apply']
    
    # State accessors
    def get_current_page(self) -> str:
        """Get the name of the current page"""
        return self.pages[self.current_page]
    
    def get_current_param(self) -> str:
        """Get the name of the currently selected parameter"""
        page = self.pages[self.current_page]
        return self.params[page][self.current_param_index]
    
    def get_param_value(self, page: str, param: str) -> Any:
        """Get the value of a specific parameter"""
        if page == 'MIDI' and param == 'channel':
            # This will need to be handled by DisplayController
            return None
        elif page == 'MIDI' and param == 'port':
            # This will need to be handled by DisplayController
            return None
        elif page == 'NOTE':
            return self.note_params[param]
        elif page == 'TIME':
            return self.time_params[param]
        elif page == 'SCALE':
            return self.scale_params[param]
        
        return None
    
    def get_visible_params(self, page: str) -> List[str]:
        """Get list of parameters visible on screen based on scroll offset"""
        if page not in self.params:
            return []
        
        params_list = self.params[page]
        return params_list[self.param_scroll_offset:self.param_scroll_offset + self.lcd_height]

    # Helper for parameter formatting
    def format_parameter_text(self, param: str, value: Any, selected: bool = False, editing: bool = False) -> str:
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
