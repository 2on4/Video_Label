#!/usr/bin/env python3
"""
Launcher for Modern Video Labels Organizer
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from modern_main import main
    main()
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1) 