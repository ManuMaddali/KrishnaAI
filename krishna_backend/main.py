#!/usr/bin/env python3
"""
KrishnaAI Backend - A wise friend you can text with for spiritual guidance
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import before loading config to avoid circular imports
from krishna_backend.core.config import config
from krishna_backend.api.app import run_app

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="KrishnaAI Backend Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind the server to")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    args = parse_args()
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed. Please check your .env file.")
        sys.exit(1)
    
    # Log configuration status
    logger.info("Configuration loaded successfully")
    logger.info(f"API Key configured: {'Yes' if config.OPENAI_API_KEY else 'No'}")
    logger.info(f"Using model: {config.OPENAI_MODEL}")
    logger.info(f"Database path: {config.DATABASE_PATH}")
    logger.info(f"CORS allowed origins: {config.CORS_ALLOWED_ORIGINS}")
    
    # Start the Flask application
    logger.info(f"Starting server on {args.host}:{args.port} (debug={args.debug})")
    run_app(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 