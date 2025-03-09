# display_controller/input_validator.py
from typing import Tuple, Union, List, Any


class InputValidator:
    """
    Validates user input for various MIDI parameters.
    Returns a tuple of (is_valid, validated_value) for each validation method.
    """
    
    @staticmethod
    def validate_channel(value: Union[str, int]) -> Tuple[bool, Union[int, None]]:
        """Validate MIDI channel (0-15)"""
        try:
            val = int(value)
            return 0 <= val <= 15, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_note(value: Union[str, int]) -> Tuple[bool, Union[int, None]]:
        """Validate MIDI note (0-127)"""
        try:
            val = int(value)
            return 0 <= val <= 127, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_duration(value: Union[str, float]) -> Tuple[bool, Union[float, None]]:
        """Validate note duration (must be positive)"""
        try:
            val = float(value)
            return val > 0, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_port_index(value: Union[str, int], max_ports: int) -> Tuple[bool, Union[int, None]]:
        """Validate port index (0 to max_ports-1)"""
        try:
            val = int(value)
            return 0 <= val < max_ports, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_scale_root(value: str, valid_notes: List[str]) -> Tuple[bool, Union[str, None]]:
        """Validate scale root note"""
        return value in valid_notes, value if value in valid_notes else None

    @staticmethod
    def validate_scale_type(value: str, valid_types: List[str]) -> Tuple[bool, Union[str, None]]:
        """Validate scale type"""
        return value in valid_types, value if value in valid_types else None

    @staticmethod
    def validate_octave(value: Union[str, int]) -> Tuple[bool, Union[int, None]]:
        """Validate octave is within MIDI range (-2 to 8)"""
        try:
            val = int(value)
            return -2 <= val <= 8, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_boolean(value: Any) -> Tuple[bool, bool]:
        """Validate boolean value"""
        if isinstance(value, bool):
            return True, value
        elif isinstance(value, str):
            if value.lower() in ('true', 't', 'yes', 'y', '1'):
                return True, True
            elif value.lower() in ('false', 'f', 'no', 'n', '0'):
                return True, False
        return False, False

    @staticmethod
    def validate_bpm(value: Union[str, int]) -> Tuple[bool, Union[int, None]]:
        """Validate BPM (20-300)"""
        try:
            val = int(value)
            return 20 <= val <= 300, val
        except (ValueError, TypeError):
            return False, None

    @staticmethod
    def validate_pattern_length(value: Union[str, int], max_steps: int) -> Tuple[bool, Union[int, None]]:
        """Validate pattern length (1 to max_steps)"""
        try:
            val = int(value)
            return 1 <= val <= max_steps, val
        except (ValueError, TypeError):
            return False, None
            
    @staticmethod
    def validate_steps_per_bar(value: Union[str, int]) -> Tuple[bool, Union[int, None]]:
        """Validate steps per bar (typically 1-64)"""
        try:
            val = int(value)
            return 1 <= val <= 64, val
        except (ValueError, TypeError):
            return False, None
