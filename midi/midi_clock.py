# midi/clock.py
import time
import threading
import mido
import logging
from typing import Callable, Optional
from events.event_publisher import EventPublisher, EventType, Event


class MidiClock:
    """
    Handles MIDI clock synchronization, both as master and slave.
    Allows sequencer to sync to external MIDI clock or generate clock.
    """
    
    PPQN = 24  # Pulses Per Quarter Note - standard MIDI timing
    
    def __init__(self, midi_device):
        """
        Initialize the MIDI clock manager.
        
        Args:
            midi_device: MidiDevice instance to use for I/O
        """
        self.midi_device = midi_device
        self.logger = logging.getLogger('midi_calculator.clock')
        self.event_publisher = EventPublisher()
        
        # Clock state
        self.is_master = True        # Whether we're generating or following clock
        self.running = False         # Whether clock is running
        self.tempo = 120.0           # BPM
        self.pulse_count = 0         # Counter for clock pulses
        self.last_pulse_time = 0     # Time of last pulse
        self.ppqn = self.PPQN        # Pulses per quarter note
        
        # Sync state
        self.pulse_interval = 60.0 / (self.tempo * self.ppqn)  # Time between pulses
        self.sync_drift = 0.0        # Timing drift when slaved
        self.sync_source = None      # MIDI port providing sync
        
        # Thread control
        self.clock_thread = None
        self.stop_flag = threading.Event()
        
        # Callbacks
        self.on_pulse = None
        self.on_beat = None
        self.on_bar = None
        
        # Beat/bar counting
        self.beats_per_bar = 4
        self.current_beat = 0
        self.current_bar = 0
    
    def start(self) -> None:
        """Start the MIDI clock"""
        if self.running:
            return
            
        self.running = True
        self.stop_flag.clear()
        
        if self.is_master:
            # Master mode - generate clock
            self.logger.info("Starting MIDI clock as master")
            self.clock_thread = threading.Thread(target=self._run_master_clock)
            self.clock_thread.daemon = True
            self.clock_thread.start()
        else:
            # Slave mode - listen for clock
            self.logger.info("Starting MIDI clock as slave")
            self._start_slave_clock()
    
    def stop(self) -> None:
        """Stop the MIDI clock"""
        if not self.running:
            return
            
        self.logger.info("Stopping MIDI clock")
        self.running = False
        self.stop_flag.set()
        
        if self.clock_thread:
            self.clock_thread.join(timeout=1.0)
            self.clock_thread = None
            
        # Reset counters
        self.pulse_count = 0
        self.current_beat = 0
        self.current_bar = 0
    
    def set_tempo(self, bpm: float) -> None:
        """
        Set the clock tempo (only affects master mode).
        
        Args:
            bpm: Tempo in beats per minute
        """
        if bpm <= 0:
            self.logger.warning(f"Invalid tempo: {bpm}")
            return
            
        self.tempo = bpm
        self.pulse_interval = 60.0 / (self.tempo * self.ppqn)
        self.logger.info(f"Tempo set to {bpm} BPM")
        
        # Publish event
        self.event_publisher.create_and_publish(
            EventType.MIDI_CLOCK,
            "clock",
            {"tempo": bpm, "source": "internal"}
        )
    
    def set_master(self, is_master: bool) -> None:
        """
        Set whether we're master or slave.
        
        Args:
            is_master: True to generate clock, False to follow external clock
        """
        if self.is_master == is_master:
            return
            
        was_running = self.running
        
        # Stop current mode
        if self.running:
            self.stop()
            
        # Switch mode
        self.is_master = is_master
        self.logger.info(f"Clock mode set to {'master' if is_master else 'slave'}")
        
        # Restart if needed
        if was_running:
            self.start()
    
    def set_sync_source(self, port_name: str) -> bool:
        """
        Set external clock source for slave mode.
        
        Args:
            port_name: MIDI input port name
            
        Returns:
            bool: True if source was set successfully, False otherwise
        """
        if port_name not in mido.get_input_names():
            self.logger.warning(f"MIDI input port not found: {port_name}")
            return False
            
        self.sync_source = port_name
        self.logger.info(f"Sync source set to {port_name}")
        
        # Restart slave mode if already running
        if self.running and not self.is_master:
            self.stop()
            self.start()
            
        return True
    
    def set_beat_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for beat events.
        
        Args:
            callback: Function to call on each beat
        """
        self.on_beat = callback
    
    def set_bar_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for bar events.
        
        Args:
            callback: Function to call on each bar
        """
        self.on_bar = callback
    
    def set_pulse_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for individual clock pulses.
        
        Args:
            callback: Function to call on each pulse
        """
        self.on_pulse = callback
    
    def send_start(self) -> None:
        """Send MIDI start message and reset counters"""
        if self.is_master and self.midi_device:
            self.midi_device.outport.send(mido.Message('start'))
            self.logger.debug("Sent MIDI start")
    
    def send_stop(self) -> None:
        """Send MIDI stop message"""
        if self.is_master and self.midi_device:
            self.midi_device.outport.send(mido.Message('stop'))
            self.logger.debug("Sent MIDI stop")
    
    def send_continue(self) -> None:
        """Send MIDI continue message"""
        if self.is_master and self.midi_device:
            self.midi_device.outport.send(mido.Message('continue'))
            self.logger.debug("Sent MIDI continue")
    
    def _run_master_clock(self) -> None:
        """Master clock main loop"""
        self.logger.debug("Master clock thread started")
        
        # Send initial messages
        self.send_start()
        
        # Reset counters
        self.pulse_count = 0
        self.current_beat = 0
        self.current_bar = 0
        
        last_time = time.time()
        
        while self.running and not self.stop_flag.is_set():
            current_time = time.time()
            elapsed = current_time - last_time
            
            if elapsed >= self.pulse_interval:
                # Send clock pulse
                if self.midi_device:
                    self.midi_device.outport.send(mido.Message('clock'))
                
                # Handle pulse
                self._handle_pulse()
                
                # Update timing
                last_time = current_time
                
                # Sleep for a fraction of the interval to reduce CPU usage
                # but still maintain accuracy
                time.sleep(self.pulse_interval * 0.2)
            else:
                # Sleep a small amount to reduce CPU usage
                time.sleep(0.001)
    
    def _start_slave_clock(self) -> None:
        """Set up slave clock listener"""
        if not self.sync_source:
            self.logger.warning("No sync source set for slave mode")
            return
            
        try:
            # Open input port
            self.inport = mido.open_input(self.sync_source)
            
            # Set up callback
            self.inport.callback = self._handle_midi_message
            
            self.logger.debug(f"Slave clock listening on {self.sync_source}")
        except Exception as e:
            self.logger.error(f"Error setting up slave clock: {str(e)}")
    
    def _handle_midi_message(self, message) -> None:
        """
        Handle incoming MIDI message for slave clock.
        
        Args:
            message: MIDI message
        """
        if not self.running or self.is_master:
            return
            
        if message.type == 'clock':
            # Handle clock pulse
            self._handle_pulse()
        elif message.type == 'start':
            # Reset counters
            self.pulse_count = 0
            self.current_beat = 0
            self.current_bar = 0
            self.logger.debug("Received MIDI start")
            
            # Publish event
            self.event_publisher.create_and_publish(
                EventType.MIDI_CLOCK,
                "clock",
                {"message": "start", "source": "external"}
            )
        elif message.type == 'stop':
            self.logger.debug("Received MIDI stop")
            
            # Publish event
            self.event_publisher.create_and_publish(
                EventType.MIDI_CLOCK,
                "clock",
                {"message": "stop", "source": "external"}
            )
    
    def _handle_pulse(self) -> None:
        """Handle a single clock pulse and update counters"""
        # Calculate tempo if in slave mode
        current_time = time.time()
        if self.last_pulse_time > 0:
            # Update timing info
            pulse_time = current_time - self.last_pulse_time
            
            if not self.is_master:
                # Estimate tempo from pulse timing
                estimated_tempo = 60.0 / (pulse_time * self.ppqn)
                # Apply smoothing
                self.tempo = self.tempo * 0.95 + estimated_tempo * 0.05
                # Recalculate pulse interval
                self.pulse_interval = 60.0 / (self.tempo * self.ppqn)
        
        self.last_pulse_time = current_time
        
        # Increment pulse counter
        self.pulse_count += 1
        
        # Check for beat
        if self.pulse_count % self.ppqn == 0:
            self._handle_beat()
        
        # Call pulse callback if set
        if self.on_pulse:
            self.on_pulse()
            
        # Publish pulse event every 6 pulses (16th note) to reduce overhead
        if self.pulse_count % 6 == 0:
            self.event_publisher.create_and_publish(
                EventType.MIDI_CLOCK,
                "clock",
                {
                    "pulse": self.pulse_count,
                    "tempo": self.tempo,
                    "beat": self.current_beat,
                    "bar": self.current_bar
                }
            )
    
    def _handle_beat(self) -> None:
        """Handle beat completion and update counters"""
        # Increment beat counter
        self.current_beat += 1
        
        # Check for bar
        if self.current_beat >= self.beats_per_bar:
            self.current_beat = 0
            self.current_bar += 1
            
            # Call bar callback if set
            if self.on_bar:
                self.on_bar()
                
            # Publish bar event
            self.event_publisher.create_and_publish(
                EventType.MIDI_CLOCK,
                "clock",
                {"bar": self.current_bar}
            )
        
        # Call beat callback if set
        if self.on_beat:
            self.on_beat()
            
        # Publish beat event
        self.event_publisher.create_and_publish(
            EventType.MIDI_CLOCK,
            "clock",
            {"beat": self.current_beat, "bar": self.current_bar}
        )
