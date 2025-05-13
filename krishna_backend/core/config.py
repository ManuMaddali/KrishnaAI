import os
import logging
import secrets
from dotenv import load_dotenv
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the application with secure environment variable handling"""
    
    # Environment configuration
    ENVIRONMENT: str = "development"  # Default to development
    
    # OpenAI API Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.6
    OPENAI_MAX_TOKENS: int = 500
    
    # Flask Config
    FLASK_SECRET_KEY: Optional[str] = None
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    
    # CORS settings
    CORS_ALLOWED_ORIGINS: list = ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Security settings
    RATE_LIMIT_DEFAULT: str = "100/day;30/hour;5/minute"
    
    # Database settings
    DATABASE_TYPE: str = "sqlite"  # "sqlite" or "postgres"
    DATABASE_PATH: str = "db/krishna_memory.db"
    DATABASE_URL: Optional[str] = None  # For production PostgreSQL
    
    # Feature flags
    ENABLE_USER_ACCOUNTS: bool = False
    ENABLE_ANALYTICS: bool = False
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables with validation"""
        
        # Determine environment (defaults to development if not set)
        cls.ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
        logger.info(f"Loading configuration for environment: {cls.ENVIRONMENT}")
        
        # Load environment-specific .env file if it exists
        env_file = f".env.{cls.ENVIRONMENT}"
        if os.path.exists(env_file):
            logger.info(f"Loading environment variables from {env_file}")
            load_dotenv(env_file, override=True)
        
        # API Key Configuration
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not cls.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set in environment variables")
        
        # Flask Secret Key
        cls.FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
        if not cls.FLASK_SECRET_KEY:
            # Generate a secure random key if not provided
            cls.FLASK_SECRET_KEY = secrets.token_hex(32)
            logger.warning("FLASK_SECRET_KEY not found in environment. Generated a secure random key.")
        
        # Load model settings
        if os.getenv("OPENAI_MODEL"):
            cls.OPENAI_MODEL = os.getenv("OPENAI_MODEL")
        
        if os.getenv("OPENAI_TEMPERATURE"):
            try:
                cls.OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))
            except (ValueError, TypeError):
                logger.warning("Invalid OPENAI_TEMPERATURE value. Using default.")
        
        if os.getenv("OPENAI_MAX_TOKENS"):
            try:
                cls.OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS"))
            except (ValueError, TypeError):
                logger.warning("Invalid OPENAI_MAX_TOKENS value. Using default.")
        
        # Load CORS settings
        if os.getenv("CORS_ALLOWED_ORIGINS"):
            try:
                origins = os.getenv("CORS_ALLOWED_ORIGINS").split(",")
                cls.CORS_ALLOWED_ORIGINS = [origin.strip() for origin in origins]
            except Exception as e:
                logger.warning(f"Error parsing CORS_ALLOWED_ORIGINS: {e}")
        
        # Load database settings based on environment
        cls.DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite").lower()
        
        if cls.DATABASE_TYPE == "sqlite":
            if os.getenv("DATABASE_PATH"):
                cls.DATABASE_PATH = os.getenv("DATABASE_PATH")
        elif cls.DATABASE_TYPE == "postgres":
            cls.DATABASE_URL = os.getenv("DATABASE_URL")
            if not cls.DATABASE_URL and cls.ENVIRONMENT == "production":
                logger.error("DATABASE_URL is required for PostgreSQL in production environment")
        
        # Load feature flags
        if os.getenv("ENABLE_USER_ACCOUNTS"):
            cls.ENABLE_USER_ACCOUNTS = os.getenv("ENABLE_USER_ACCOUNTS").lower() == "true"
        
        if os.getenv("ENABLE_ANALYTICS"):
            cls.ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS").lower() == "true"
        
        return cls
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        missing = []
        
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
            
        if not cls.FLASK_SECRET_KEY:
            missing.append("FLASK_SECRET_KEY")
        
        # Database validation based on type
        if cls.DATABASE_TYPE == "postgres" and cls.ENVIRONMENT == "production":
            if not cls.DATABASE_URL:
                missing.append("DATABASE_URL")
        
        if missing:
            logger.error(f"Missing required configuration variables: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def is_production(cls):
        """Check if running in production environment"""
        return cls.ENVIRONMENT == "production"
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration based on environment"""
        if cls.DATABASE_TYPE == "sqlite":
            return {"type": "sqlite", "path": cls.DATABASE_PATH}
        elif cls.DATABASE_TYPE == "postgres":
            return {"type": "postgres", "url": cls.DATABASE_URL}
        else:
            logger.error(f"Unsupported database type: {cls.DATABASE_TYPE}")
            return {"type": "sqlite", "path": cls.DATABASE_PATH}  # Fallback to sqlite

# Load configuration from environment
config = Config.load_from_env() 