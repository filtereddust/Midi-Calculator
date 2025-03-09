# config/config_manager.py
import json
import os
import logging
from typing import Dict, Any, Optional

class ConfigManager:
    """
    Manages application configuration settings with save/load capabilities.
    """
    
    DEFAULT_CONFIG = {
        'midi': {
            'default_channel': 0,
            'default_port': 0,
        },
        'sequencer': {
            'default_bpm': 120,
            'default_steps_per_bar': 16,
            'default_pattern_length': 16,
            'max_steps': 64,
        },
        'display': {
            'error_display_duration': 1.0,
            'update_interval': 0.1,
        },
        'scales': {
            'default_root': 'C',
            'default_type': 'MAJOR',
            'default_start_octave': 2,
            'default_end_octave': 4,
        }
    }
    
    def __init__(self, config_file: str = 'config.json'):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.logger = logging.getLogger('midi_calculator.config')
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            bool: True if configuration was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge loaded config with defaults (preserving defaults for missing values)
                self._merge_configs(self.config, loaded_config)
                self.logger.info(f"Loaded configuration from {self.config_file}")
                return True
            else:
                self.logger.info(f"Config file {self.config_file} not found, using defaults")
                self.save_config()  # Create the default config file
                return False
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            bool: True if configuration was saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value
        """
        try:
            return self.config[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
            
        Returns:
            bool: True if value was set successfully, False otherwise
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            return True
        except Exception as e:
            self.logger.error(f"Error setting config value: {str(e)}")
            return False
    
    def _merge_configs(self, target: Dict, source: Dict) -> None:
        """
        Recursively merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._merge_configs(target[key], value)
            else:
                # Otherwise just update the value
                target[key] = value
