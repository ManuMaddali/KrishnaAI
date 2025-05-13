"""
Configuration module for Krishna AI backend
"""

import os
from pathlib import Path

# Debug mode for development
DEBUG_MODE = True

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SCRIPTURES_DIR = DATA_DIR / "scriptures"
DB_DIR = ROOT_DIR / "db"
DB_PATH = DB_DIR / "krishna_memory.db"

# Ensure necessary directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCRIPTURES_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# API settings
ALLOWED_ORIGINS = ['http://localhost:5000', 'http://127.0.0.1:5000', 'http://localhost:8000', 'http://127.0.0.1:8000']

# Rate limiting defaults 
DEFAULT_RATE_LIMIT = 30  # requests per minute
RESET_RATE_LIMIT = 10    # /reset endpoint
DELETE_RATE_LIMIT = 10   # /delete_conversation endpoint 