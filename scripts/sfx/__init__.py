"""Deterministic sound design for motion pieces: voices, a seeded score, a stereo room, a high-pass and a loudness target
measured by FFmpeg. NumPy synthesis, plus an optional recorded music bed (sfx/music.py). The command-line entry point is
scripts/build_soundtrack.py; plan and cue formats are documented in sfx/schedule.py.
"""
from .core import SR, Score
from .master import duck_envelope, ffmpeg_measure, high_pass, independent_ebur128, master_to_target, room, write_wav
from .schedule import DEFAULT_ROLE_VOICES, normalize_hits, render
from .voices import LAYERS, VOICES

__all__ = [
    "SR", "Score", "VOICES", "LAYERS", "DEFAULT_ROLE_VOICES", "normalize_hits", "render", "room", "duck_envelope",
    "high_pass", "ffmpeg_measure", "independent_ebur128", "master_to_target", "write_wav",
]
