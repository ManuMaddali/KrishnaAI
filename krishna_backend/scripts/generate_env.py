#!/usr/bin/env python3
"""
Generate a secure .env file for KrishnaAI

This script helps users generate a secure .env file with random keys
and guides them through the process of obtaining API keys.
"""

import os
import secrets
import argparse
import logging
import shutil
import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_flask_secret():
    """Generate a secure Flask secret key"""
    return secrets.token_hex(32)

def get_openai_key():
    """Get the OpenAI API key from the user"""
    print("\nOpenAI API Key")
    print("--------------")
    print("You need an OpenAI API key to use KrishnaAI.")
    print("If you don't have one, you can get it from: https://platform.openai.com/api-keys")
    
    key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    return key

def get_cors_origins():
    """Get CORS origins from the user"""
    print("\nCORS Origins")
    print("------------")
    print("Specify which domains can access your API (comma-separated).")
    print("For local development, you can use: http://localhost:5000,http://127.0.0.1:5000")
    
    default = "http://localhost:5000,http://127.0.0.1:5000"
    origins = input(f"Enter CORS origins (press Enter for default: {default}): ").strip()
    
    if not origins:
        origins = default
    
    return origins

def generate_env_file(output_path, overwrite=False):
    """Generate a .env file with secure values"""
    env_path = Path(output_path)
    
    # Check if the file already exists
    if env_path.exists() and not overwrite:
        logger.error(f"File {env_path} already exists. Use --force to overwrite.")
        return False
    
    # Create parent directories if they don't exist
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get values from user or generate them
    openai_key = get_openai_key()
    flask_secret = generate_flask_secret()
    cors_origins = get_cors_origins()
    
    # Create the .env file content
    env_content = f"""# KrishnaAI Configuration
# Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# API Keys (Required)
OPENAI_API_KEY={openai_key}

# Security Settings
FLASK_SECRET_KEY={flask_secret}

# OpenAI Model Configuration
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.6
OPENAI_MAX_TOKENS=500

# CORS Settings
CORS_ALLOWED_ORIGINS={cors_origins}

# Database Settings
DATABASE_PATH=db/krishna_memory.db
"""
    
    # Write the .env file
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    logger.info(f"Generated .env file at {env_path}")
    
    # Print additional instructions
    if not openai_key:
        logger.warning("""
⚠️ OpenAI API key is missing!
You will need to edit the .env file and add your key before using KrishnaAI.
Get your key from: https://platform.openai.com/api-keys
""")
    
    return True

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Generate a secure .env file for KrishnaAI")
    parser.add_argument(
        "--output", "-o", 
        default=".env", 
        help="Path to output .env file (default: .env)"
    )
    parser.add_argument(
        "--force", "-f", 
        action="store_true", 
        help="Overwrite existing .env file"
    )
    
    args = parser.parse_args()
    
    try:
        success = generate_env_file(args.output, args.force)
        
        if success:
            print("""
✅ .env file generated successfully.

Next steps:
1. Start KrishnaAI with: python -m krishna_backend.main
2. Access the web interface at: http://localhost:5000
""")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"Error generating .env file: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main()) 