# events/event_publisher.py
import time
import logging
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    """Types of events that can be published"""
    MIDI_NOTE = auto()
    MIDI_CONTROL = auto()
    MIDI_CLOCK = auto()
    SEQUENCER_STEP = auto()
    SEQUENCER_STATE = auto()
    DISPLAY_UPDATE = auto()
    USER_INPUT = auto()
    SCALE_CHANGE = auto()
    ERROR = auto()
    CONFIG_CHANGE = auto()
    STATE_CHANGE = auto()


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    source: str
    timestamp: float
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class EventPublisher:
    """
    Publishes events to registered subscribers.
    Central hub for application events.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one event publisher exists"""
        if cls._instance is None:
            cls._instance = super(EventPublisher, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the event publisher if it hasn't been already"""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('midi_calculator.events')
        self.subscribers = {event_type: [] for event_type in EventType}
        self.event_history = []
        self.max_history = 100
        self._initialized = True
        self.logger.info("EventPublisher initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)
            self.logger.debug(f"Subscribed to {event_type.name}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            self.logger.debug(f"Unsubscribed from {event_type.name}")
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        """
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Log event
        self.logger.debug(f"Event: {event.type.name} from {event.source}")
        
        # Notify subscribers
        if event.type in self.subscribers:
            for callback in self.subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event subscriber: {str(e)}")
    
    def create_and_publish(self, 
                          event_type: EventType, 
                          source: str, 
                          data: Dict[str, Any] = None) -> Event:
        """
        Create and publish an event in one step.
        
        Args:
            event_type: Type of event
            source: Source of the event
            data: Event data
            
        Returns:
            The created event
        """
        event = Event(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=data or {}
        )
        self.publish(event)
        return event
    
    def get_recent_events(self, count: int = 10, event_type: EventType = None) -> List[Event]:
        """
        Get recent events, optionally filtered by type.
        
        Args:
            count: Maximum number of events to return
            event_type: Optional filter by event type
            
        Returns:
            List of events
        """
        if event_type:
            filtered = [e for e in self.event_history if e.type == event_type]
            return filtered[-count:]
        return self.event_history[-count:]
