from typing import Dict, List



class MidiScale:
    NOTE_TO_MIDI = {
        "A": 21, "A#": 22, "B": 23, "C": 24, "C#": 25, "D": 26,
        "D#": 27, "E": 28, "F": 29, "F#": 30, "G": 31, "G#": 32
    }

    MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
    MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]
    DORIAN_INTERVALS = [0, 2, 3, 5, 7, 9, 10]
    PHRYGIAN_INTERVALS = [0, 1, 3, 5, 7, 8, 10]
    LYDIAN_INTERVALS = [0, 2, 4, 6, 7, 9, 11]
    MIXOLYDIAN_INTERVALS = [0, 2, 4, 5, 7, 9, 10]
    LOCRIAN_INTERVALS = [0, 1, 3, 5, 6, 8, 10]
    HARMONIC_MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 11]
    MELODIC_MINOR_INTERVALS = [0, 2, 3, 5, 7, 9, 11]
    WHOLE_TONE_INTERVALS = [0, 2, 4, 6, 8, 10]
    CHROMATIC_INTERVALS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    PENTATONIC_MAJOR_INTERVALS = [0, 2, 4, 7, 9]
    PENTATONIC_MINOR_INTERVALS = [0, 3, 5, 7, 10]
    BLUES_INTERVALS = [0, 3, 5, 6, 7, 10]
    DIMINISHED_INTERVALS = [0, 2, 3, 5, 6, 8, 9, 11]

    @classmethod
    def generate_scale(cls, root_note: str, scale_type: str,
                       start_octave: int = 0, end_octave: int = 10) -> Dict[int, List[int]]:
        if root_note not in cls.NOTE_TO_MIDI:
            raise ValueError(f"Invalid root note '{root_note}'. Choose from {list(cls.NOTE_TO_MIDI.keys())}.")

        base_midi = cls.NOTE_TO_MIDI[root_note]
        interval_attr = f"{scale_type.upper()}_INTERVALS"

        if hasattr(cls, interval_attr):
            intervals = getattr(cls, interval_attr)
        else:
            raise ValueError(f"Unknown scale type: {scale_type}")

        scale = {}
        for octave in range(start_octave, end_octave + 1):
            base_note = base_midi + (octave * 12)
            notes = [base_note + interval for interval in intervals
                     if 0 <= base_note + interval <= 127]
            if notes:
                scale[octave] = notes

        return scale