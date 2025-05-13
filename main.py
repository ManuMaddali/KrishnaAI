#!/usr/bin/env python3
"""
Entry point for KrishnaAI application.
This script imports and runs the main function from the krishna_backend package.
"""

import os
import sys

# Add the current directory to the Python path to allow importing the krishna_backend package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from krishna_backend.main import main
        main()
    except ImportError as e:
        print(f"Error importing krishna_backend package: {e}")
        print("Make sure you have installed all required dependencies with 'pip install -r requirements.txt'")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1) 