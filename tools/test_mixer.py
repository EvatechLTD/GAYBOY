"""Mixer controls and versioned pattern storage regression entry point.

The event-pool suite supersedes the former64-step raw-array fixture. Live
transport timing and stress controls are measured by test_mixer_live.py.
"""
import runpy
runpy.run_path('tools/test_patterns_256.py',run_name='__main__')
