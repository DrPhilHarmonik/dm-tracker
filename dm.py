#!/usr/bin/env python3
"""DM Tracker - CLI resource for Dungeon Masters."""
import sys
import os

# Run from project dir so relative imports work
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == "__main__":
    main()
