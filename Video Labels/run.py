#!/usr/bin/env python3
"""
Video Labels Organizer - Main Entry Point
Run this file to start the application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import App
import tkinter as tk

if __name__ == "__main__":
    app = App()
    app.mainloop() 