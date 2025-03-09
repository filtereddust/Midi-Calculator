# display_controller/display_renderer.py
import time
from typing import Optional

class DisplayRenderer:
    """
    Handles the rendering of content to the LCD display.
    """
    
    def __init__(self, lcd_display, state_manager, lcd_width: int = 16, lcd_height: int = 2):
        """
        Initialize the display renderer.
        
        Args:
            lcd_display: LCD display object with clear(), cursor_pos and write_string() methods
            state_manager: StateManager instance to get display content from
            lcd_width: Width of the LCD in characters
            lcd_height: Height of the LCD in lines
        """
        self.lcd = lcd_display
        self.state_manager = state_manager
        self.lcd_width = lcd_width
        self.lcd_height = lcd_height
        self.last_update = time.time()
        self.update_interval = 0.1  # 100ms refresh rate
        self.midi_device = None  # Will be set by DisplayController
        
    def set_midi_device(self, midi_device):
        """Set the MIDI device reference"""
        self.midi_device = midi_device
    
    def update_display(self, force: bool = False):
        """
        Update the LCD display with current state.
        
        Args:
            force: Force update even if update interval hasn't elapsed
        """
        current_time = time.time()
        if not force and (current_time - self.last_update) < self.update_interval:
            return
            
        self.last_update = current_time
        self.lcd.clear()
        
        # Delegate to appropriate page renderer
        current_page = self.state_manager.get_current_page()
        if current_page == 'MIDI':
            self._render_midi_page()
        elif current_page == 'NOTE':
            self._render_note_page()
        elif current_page == 'TIME':
            self._render_time_page()
        elif current_page == 'SCALE':
            self._render_scale_page()
    
    def _render_midi_page(self):
        """Render the MIDI configuration page"""
        if not self.midi_device:
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string("MIDI device not set")
            return
            
        channel_str = f"CH:{self.midi_device.channel}"
        try:
            port_str = f"Port:{self.midi_device.midi_outputs[self.state_manager.current_port_idx][:8]}"
        except (IndexError, AttributeError):
            port_str = "Port: Not found"
        
        curr_param = self.state_manager.get_current_param()
        
        if curr_param == 'channel':
            # Editing channel
            if self.state_manager.editing:
                channel_str = f"CH:{self.state_manager.edit_buffer}"
                if len(self.state_manager.edit_buffer) < 3:
                    channel_str += "_"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f"*{channel_str}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f" {port_str}")
        else:  # Port parameter
            if self.state_manager.editing:
                port_str = f"Port:{self.midi_device.midi_outputs[self.state_manager.current_port_idx][:6]} [<>]"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f" {channel_str}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f"*{port_str}")
    
    def _render_note_page(self):
        """Render the note player page"""
        note = str(self.state_manager.note_params['note']) if self.state_manager.note_params['note'] else '---'
        dur = str(self.state_manager.note_params['duration'])
        
        curr_param = self.state_manager.get_current_param()
        
        if curr_param == 'note':  # Note parameter
            if self.state_manager.editing:
                note = self.state_manager.edit_buffer
                if len(self.state_manager.edit_buffer) < 3:
                    note += "_"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f"*Note:{note}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f" Dur:{dur}")
        else:  # Duration parameter
            if self.state_manager.editing:
                dur = self.state_manager.edit_buffer
                if len(self.state_manager.edit_buffer) < 3:
                    dur += "_"
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f" Note:{note}")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f"*Dur:{dur}")
    
    def _render_time_page(self):
        """Render the timing configuration page"""
        # Get the visible parameters based on the current scroll offset
        visible_params = self.state_manager.get_visible_params('TIME')
        
        for i, param in enumerate(visible_params):
            # Get the current value of the parameter
            value = str(self.state_manager.time_params[param])
            
            # Determine if this parameter is selected
            selected = param == self.state_manager.get_current_param()
            
            # Handle editing mode
            if selected and self.state_manager.editing:
                display_value = self.state_manager.edit_buffer
            else:
                display_value = value
            
            # Format text
            param_text = self.state_manager.format_parameter_text(
                param,
                display_value,
                selected=selected,
                editing=(selected and self.state_manager.editing)
            )
            
            # Set cursor position and display the text
            self.lcd.cursor_pos = (i, 0)
            self.lcd.write_string(param_text)
    
    def _render_scale_page(self):
        """Render the scale configuration page"""
        # Get the visible parameters based on the current scroll offset
        visible_params = self.state_manager.get_visible_params('SCALE')
        
        for i, param in enumerate(visible_params):
            # Get the current value of the parameter
            value = str(self.state_manager.scale_params[param])
            
            # Determine if this parameter is selected
            selected = param == self.state_manager.get_current_param()
            
            # Handle editing mode
            if selected and self.state_manager.editing:
                if param in ['root', 'type']:
                    display_value = f"{value} [<>]"
                elif param == 'apply':
                    # For 'apply' parameter, indicate it can be toggled using scrolling
                    display_value = f"{value} [<>]"
                else:
                    display_value = self.state_manager.edit_buffer
            else:
                display_value = value
            
            # Format text intelligently
            param_text = self.state_manager.format_parameter_text(
                param,
                display_value,
                selected=selected,
                editing=(selected and self.state_manager.editing)
            )
            
            # Set cursor position and display the text
            self.lcd.cursor_pos = (i, 0)
            self.lcd.write_string(param_text)
