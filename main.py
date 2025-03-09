# main.py
from midi.device import MidiDevice
from sequencer.sequencer import StepSequencer
from display_controller import DisplayController
import RPi.GPIO as GPIO
import time
import logging
import os

def setup_logging():
    """Set up logging for the MIDI Calculator application"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/midi_calculator.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger('midi_calculator')
    logger.info("MIDI Calculator starting up")
    return logger

def main():
    """Main application entry point"""
    logger = setup_logging()
    
    try:
        logger.info("Initializing MIDI device")
        midi_device = MidiDevice(0)
        
        logger.info("Initializing sequencer")
        sequencer = StepSequencer(midi_device)
        
        logger.info("Initializing display controller")
        display = DisplayController(midi_device, sequencer)
        
        # Main application loop
        logger.info("Entering main loop")
        while True:
            time.sleep(0.1)  # Small sleep to prevent CPU hogging
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        logger.info("Shutting down")
        
        # Clean up resources
        if 'display' in locals():
            display.close()
        if 'midi_device' in locals():
            midi_device.close()
        GPIO.cleanup()
        
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
