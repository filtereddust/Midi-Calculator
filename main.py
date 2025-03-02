# main.py
from midi.device import MidiDevice
from sequencer.sequencer import StepSequencer
from display_controller import DisplayController
import RPi.GPIO as GPIO
import time



def main():
   try:
       print("try to run")
       midi_device = MidiDevice(0)
       sequencer = StepSequencer(midi_device)
       display = DisplayController(midi_device, sequencer)
       display.update_display()
       
       while True:
           time.sleep(0.1)
           
   except Exception as e:
       print("error")
       print(f"Error: {e}")
   finally:

       if 'display' in locals():
           display.close()
       if 'midi_device' in locals():
           midi_device.close()
       GPIO.cleanup()

           
if __name__ == "__main__":
    main()