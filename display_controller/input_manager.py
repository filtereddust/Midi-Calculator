# display_controller/input_manager.py
import keyboard
from typing import Dict, Any, Callable


class InputManager:
    """
    Manages keyboard input and maps keys to functions.
    """
    
    def __init__(self, state_manager):
        """
        Initialize the input manager.
        
        Args:
            state_manager: StateManager instance to interact with
        """
        self.state_manager = state_manager
        self.action_handlers = {}  # Dictionary of action handlers
        self.key_mappings = {}     # Dictionary mapping keys to actions
        
    def register_action_handler(self, action: str, handler: Callable):
        """
        Register a handler function for a specific action.
        
        Args:
            action: Action identifier string
            handler: Function to call when the action is triggered
        """
        self.action_handlers[action] = handler
        
    def setup_default_mappings(self):
        """Set up default key mappings for MIDI Calculator"""
        # Page navigation
        self.map_key(',', 'prev_page')  # "<"
        self.map_key('.', 'next_page')  # ">"
        
        # Parameter navigation
        self.map_key('left', 'prev_param')
        self.map_key('right', 'next_param')
        self.map_key('up', 'prev_param')
        self.map_key('down', 'next_param')
        
        # Option scrolling (for lists of choices)
        self.map_key('[', 'scroll_prev')
        self.map_key(']', 'scroll_next')
        
        # Edit controls
        self.map_key('enter', 'toggle_edit')
        self.map_key('backspace', 'backspace')
        
        # Playback controls
        self.map_key('q', 'start_playback')
        self.map_key('w', 'stop_playback')
        
        # Number input
        for key in '0123456789.':
            self.map_key(key, 'number_input')
    
    def map_key(self, key: str, action: str):
        """
        Map a key to an action.
        
        Args:
            key: Keyboard key string
            action: Action identifier string
        """
        self.key_mappings[key] = action
    
    def setup_keyboard_listeners(self):
        """Set up all keyboard listeners based on current mappings"""
        # Clear any existing handlers first
        keyboard.unhook_all()
        
        # Set up handlers for each mapped key
        for key, action in self.key_mappings.items():
            # Use lambda with default arg to avoid late binding issues
            keyboard.on_press_key(key, lambda e, action=action: self.handle_key_press(e, action))
    
    def handle_key_press(self, e, action: str):
        """
        Handle a key press event.
        
        Args:
            e: Key event from keyboard library
            action: Action to perform
        """
        # Special case for number input
        if action == 'number_input':
            if 'number_input' in self.action_handlers:
                self.action_handlers['number_input'](e.name)
            return
            
        # Otherwise dispatch to appropriate handler
        if action in self.action_handlers:
            self.action_handlers[action]()
    
    def handle_number_input(self, key: str):
        """
        Handle numeric input.
        
        Args:
            key: Key that was pressed
        """
        self.state_manager.update_edit_buffer(key)
    
    def handle_backspace(self):
        """Handle backspace key press"""
        self.state_manager.remove_last_char()
    
    def handle_toggle_edit(self):
        """Handle enter key to toggle edit mode"""
        self.state_manager.toggle_edit_mode()
    
    def handle_scroll_options(self, direction: str):
        """
        Handle scrolling through options.
        
        Args:
            direction: 'prev' or 'next'
        """
        self.state_manager.scroll_options(direction)
