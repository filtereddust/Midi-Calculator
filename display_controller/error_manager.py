# display_controller/error_manager.py
import time
import logging
from typing import Optional, Callable


class ErrorManager:
    """
    Enhanced error management for LCD display with logging capabilities
    and configurable error display behavior.
    """
    
    def __init__(self, lcd_display, error_display_duration: float = 1.0):
        """
        Initialize the error manager.
        
        Args:
            lcd_display: LCD display object with clear() and write_string() methods
            error_display_duration: How long to display errors (seconds)
        """
        self.lcd = lcd_display
        self.error_displayed = False
        self.error_start_time = 0
        self.error_display_duration = error_display_duration
        self.error_history = []  # Store recent errors
        self.max_history = 10    # Maximum number of errors to keep in history
        self._on_error_callback = None
        
        # Set up logging
        self.logger = logging.getLogger('midi_calculator.error')
        
    def set_callback(self, callback: Callable[[str], None]):
        """Set a callback to be called when an error occurs"""
        self._on_error_callback = callback
        
    def show_error(self, message: str, log_level: str = 'error', details: Optional[str] = None):
        """
        Display and log an error message.
        
        Args:
            message: Short error message to display
            log_level: Logging level ('debug', 'info', 'warning', 'error', 'critical')
            details: Optional detailed error information for logging only
        """
        # Display on LCD
        self.lcd.clear()
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string("Error:")
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(message[:16])  # Truncate to LCD width
        
        # Set error state
        self.error_displayed = True
        self.error_start_time = time.time()
        
        # Add to history (with timestamp)
        error_entry = {
            'timestamp': time.time(),
            'message': message,
            'details': details
        }
        self.error_history.append(error_entry)
        
        # Keep history within size limit
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Log the error
        log_method = getattr(self.logger, log_level.lower(), self.logger.error)
        if details:
            log_method(f"{message} - Details: {details}")
        else:
            log_method(message)
            
        # Trigger callback if set
        if self._on_error_callback:
            self._on_error_callback(message)
    
    def clear_error(self) -> bool:
        """
        Clear the error display if it's been shown for long enough.
        
        Returns:
            bool: True if the error was cleared, False otherwise
        """
        if self.error_displayed and (time.time() - self.error_start_time) > self.error_display_duration:
            self.error_displayed = False
            return True
        return False
    
    def get_recent_errors(self, count: int = 5):
        """
        Get the most recent errors.
        
        Args:
            count: Number of recent errors to return
            
        Returns:
            List of error entries
        """
        return self.error_history[-count:]
