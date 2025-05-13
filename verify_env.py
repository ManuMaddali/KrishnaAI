#!/usr/bin/env python3
"""
Verify Krishna AI environment configuration
"""

import os
import sys
import argparse
import logging
import sqlite3
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def check_environment_files():
    """Check for environment files"""
    result = {
        ".env": os.path.exists(".env"),
        ".env.development": os.path.exists(".env.development"),
        ".env.production": os.path.exists(".env.production"),
    }
    
    for file, exists in result.items():
        status = "✅ Found" if exists else "❌ Missing"
        logger.info(f"{file}: {status}")
    
    return result


def check_database_connectivity(db_type, db_path=None, db_url=None):
    """Check database connectivity"""
    if db_type == "sqlite":
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()
                conn.close()
                logger.info(f"✅ SQLite database connection successful. Version: {version[0]}")
                return True
            except Exception as e:
                logger.error(f"❌ SQLite database connection failed: {str(e)}")
                return False
        else:
            logger.error("❌ SQLite database path not provided")
            return False
    
    elif db_type == "postgres":
        try:
            import psycopg2
            if db_url:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                conn.close()
                logger.info(f"✅ PostgreSQL database connection successful. Version: {version[0]}")
                return True
            else:
                logger.error("❌ PostgreSQL database URL not provided")
                return False
        except ImportError:
            logger.error("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
            return False
        except Exception as e:
            logger.error(f"❌ PostgreSQL database connection failed: {str(e)}")
            return False
    
    else:
        logger.error(f"❌ Unsupported database type: {db_type}")
        return False


def check_dependencies():
    """Check if required dependencies are installed"""
    dependencies = {
        "openai": False,
        "flask": False,
        "langchain": False,
        "psycopg2": False,
        "gunicorn": False,
    }
    
    # Check each dependency
    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
            logger.info(f"✅ {dep}: Installed")
        except ImportError:
            logger.info(f"❌ {dep}: Not installed")
    
    return dependencies


def check_openai_api_key():
    """Check if OpenAI API key is configured"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # Mask the API key for security
        masked_key = api_key[:4] + "..." + api_key[-4:]
        logger.info(f"✅ OpenAI API key configured: {masked_key}")
        return True
    else:
        logger.error("❌ OpenAI API key not found")
        return False


def check_environment_variables(environment):
    """Check environment-specific variables"""
    # Load environment file
    env_file = f".env.{environment}"
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
    
    required_vars = [
        "OPENAI_API_KEY",
        "FLASK_SECRET_KEY",
        "DATABASE_TYPE",
    ]
    
    # Add environment-specific variables
    if environment == "production":
        required_vars.extend([
            "DATABASE_URL",
            "CORS_ALLOWED_ORIGINS",
        ])
    
    results = {}
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if var in ["OPENAI_API_KEY", "FLASK_SECRET_KEY", "DATABASE_URL"]:
                masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                logger.info(f"✅ {var}: {masked_value}")
            else:
                logger.info(f"✅ {var}: {value}")
            results[var] = True
        else:
            logger.error(f"❌ {var}: Not configured")
            results[var] = False
    
    return results


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Verify Krishna AI environment configuration")
    parser.add_argument("--environment", "-e", default="development", 
                      choices=["development", "production"],
                      help="Environment to check (development or production)")
    args = parser.parse_args()
    
    environment = args.environment.lower()
    
    logger.info(f"Verifying {environment.upper()} environment configuration")
    logger.info("=" * 50)
    
    # Set environment variable
    os.environ["ENVIRONMENT"] = environment
    
    # Check for environment files
    logger.info("\nChecking environment files:")
    env_files = check_environment_files()
    
    # Check environment variables
    logger.info("\nChecking environment variables:")
    env_vars = check_environment_variables(environment)
    
    # Check dependencies
    logger.info("\nChecking dependencies:")
    deps = check_dependencies()
    
    # Check database connectivity
    logger.info("\nChecking database connectivity:")
    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
    db_path = os.getenv("DATABASE_PATH", "db/krishna_memory.db")
    db_url = os.getenv("DATABASE_URL")
    
    db_conn = check_database_connectivity(db_type, db_path, db_url)
    
    # Check OpenAI API key
    logger.info("\nChecking OpenAI API key:")
    api_key = check_openai_api_key()
    
    # Summary
    logger.info("\nSummary:")
    logger.info("=" * 50)
    all_good = all([
        env_files.get(f".env.{environment}", False),
        all(env_vars.values()),
        api_key,
        db_conn,
        # For production, make sure we have psycopg2 and gunicorn
        deps["psycopg2"] or environment != "production",
        deps["gunicorn"] or environment != "production",
    ])
    
    if all_good:
        logger.info(f"✅ {environment.upper()} environment is properly configured!")
    else:
        logger.error(f"❌ {environment.upper()} environment has configuration issues. Please fix them before proceeding.")
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main()) 