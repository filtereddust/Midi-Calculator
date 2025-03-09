# persistence/persistence_manager.py
import json
import os
import logging
import time
from typing import Dict, Any, List, Optional


class PersistenceManager:
    """
    Manages application state persistence, saving and loading
    patterns, scales, and settings.
    """
    
    def __init__(self, data_directory: str = 'data'):
        """
        Initialize the persistence manager.
        
        Args:
            data_directory: Directory to store persistence files
        """
        self.data_directory = data_directory
        self.logger = logging.getLogger('midi_calculator.persistence')
        
        # Create directories if they don't exist
        os.makedirs(os.path.join(data_directory, 'patterns'), exist_ok=True)
        os.makedirs(os.path.join(data_directory, 'scales'), exist_ok=True)
        os.makedirs(os.path.join(data_directory, 'state'), exist_ok=True)
    
    def save_pattern(self, name: str, pattern_data: Dict) -> bool:
        """
        Save a sequencer pattern.
        
        Args:
            name: Pattern name
            pattern_data: Pattern data dictionary
            
        Returns:
            bool: True if pattern was saved successfully, False otherwise
        """
        return self._save_data('patterns', name, pattern_data)
    
    def load_pattern(self, name: str) -> Optional[Dict]:
        """
        Load a sequencer pattern.
        
        Args:
            name: Pattern name
            
        Returns:
            Dict or None: Pattern data dictionary if found, None otherwise
        """
        return self._load_data('patterns', name)
    
    def list_patterns(self) -> List[str]:
        """
        List available saved patterns.
        
        Returns:
            List of pattern names
        """
        return self._list_files('patterns')
    
    def save_scale(self, name: str, scale_data: Dict) -> bool:
        """
        Save a scale configuration.
        
        Args:
            name: Scale name
            scale_data: Scale data dictionary
            
        Returns:
            bool: True if scale was saved successfully, False otherwise
        """
        return self._save_data('scales', name, scale_data)
    
    def load_scale(self, name: str) -> Optional[Dict]:
        """
        Load a scale configuration.
        
        Args:
            name: Scale name
            
        Returns:
            Dict or None: Scale data dictionary if found, None otherwise
        """
        return self._load_data('scales', name)
    
    def list_scales(self) -> List[str]:
        """
        List available saved scales.
        
        Returns:
            List of scale names
        """
        return self._list_files('scales')
    
    def save_state(self) -> bool:
        """
        Save current application state with automatic timestamp name.
        
        Returns:
            bool: True if state was saved successfully, False otherwise
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"state_{timestamp}"
        
        # State would be collected from various components in actual implementation
        state_data = {
            'timestamp': timestamp,
            'midi': {},
            'sequencer': {},
            'display': {}
        }
        
        return self._save_data('state', name, state_data)
    
    def load_last_state(self) -> Optional[Dict]:
        """
        Load the most recent saved state.
        
        Returns:
            Dict or None: State data dictionary if found, None otherwise
        """
        state_files = self._list_files('state')
        if not state_files:
            return None
        
        # Find most recent state file by timestamp in name
        latest_state = sorted(state_files)[-1]
        return self._load_data('state', latest_state)
    
    def auto_save(self, interval: int = 300) -> None:
        """
        Start automatic state saving at regular intervals.
        
        Args:
            interval: Time between auto-saves in seconds (default: 5 minutes)
        """
        # This would normally be implemented as a separate thread
        # or scheduled task, but for simplicity we'll just define the interface
        self.logger.info(f"Auto-save would be enabled with {interval}s interval")
    
    def _save_data(self, category: str, name: str, data: Dict) -> bool:
        """
        Save data to a JSON file.
        
        Args:
            category: Data category (patterns, scales, state)
            name: Data name
            data: Data dictionary
            
        Returns:
            bool: True if data was saved successfully, False otherwise
        """
        try:
            file_path = os.path.join(self.data_directory, category, f"{name}.json")
            
            # Add metadata
            data_with_meta = {
                'metadata': {
                    'name': name,
                    'created': time.time(),
                    'version': '1.0'
                },
                'data': data
            }
            
            with open(file_path, 'w') as f:
                json.dump(data_with_meta, f, indent=2)
            
            self.logger.info(f"Saved {category}/{name}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving {category}/{name}: {str(e)}")
            return False
    
    def _load_data(self, category: str, name: str) -> Optional[Dict]:
        """
        Load data from a JSON file.
        
        Args:
            category: Data category (patterns, scales, state)
            name: Data name
            
        Returns:
            Dict or None: Data dictionary if found, None otherwise
        """
        try:
            # Strip extension if provided
            name = name.replace('.json', '')
            file_path = os.path.join(self.data_directory, category, f"{name}.json")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"{category}/{name} not found")
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Return just the data portion, not the metadata
            if 'data' in data:
                self.logger.info(f"Loaded {category}/{name}")
                return data['data']
            else:
                # Legacy format support
                self.logger.info(f"Loaded {category}/{name} (legacy format)")
                return data
        except Exception as e:
            self.logger.error(f"Error loading {category}/{name}: {str(e)}")
            return None
    
    def _list_files(self, category: str) -> List[str]:
        """
        List files in a category directory.
        
        Args:
            category: Data category (patterns, scales, state)
            
        Returns:
            List of file names without extension
        """
        try:
            dir_path = os.path.join(self.data_directory, category)
            files = [f.replace('.json', '') for f in os.listdir(dir_path) 
                    if f.endswith('.json')]
            return sorted(files)
        except Exception as e:
            self.logger.error(f"Error listing {category}: {str(e)}")
            return []
