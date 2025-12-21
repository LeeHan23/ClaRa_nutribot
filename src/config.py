"""
Centralized Configuration for NutriBot

Loads environment variables and provides configuration constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import sys

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
VECTOR_DIR = DATA_DIR / "clara_vectors"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/nutribot.db")

# Server Configuration
FLASK_ENV = os.getenv("FLASK_ENV", "development")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# Debounce Configuration
MESSAGE_DEBOUNCE_SECONDS = float(os.getenv("MESSAGE_DEBOUNCE_SECONDS", "3"))

# CLaRa Model Configuration
CLARA_MODEL_PATH = os.getenv("CLARA_MODEL_PATH", "./models/clara-phi4-mini")
CLARA_VECTOR_STORE_PATH = os.getenv("CLARA_VECTOR_STORE_PATH", str(VECTOR_DIR))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "nutribot.log"))


def setup_logging():
    """Configure logging with loguru"""
    # Remove default logger
    logger.remove()
    
    # Add console logger with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True
    )
    
    # Add file logger
    logger.add(
        LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    logger.info("✅ Logging configured")


def validate_config():
    """Validate required configuration"""
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set")
    
    # Twilio is optional for testing
    if not TWILIO_ACCOUNT_SID:
        logger.warning("⚠️ TWILIO_ACCOUNT_SID not set - WhatsApp integration will not work")
    
    if not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️ TWILIO_AUTH_TOKEN not set - WhatsApp integration will not work")
    
    if errors:
        logger.error("❌ Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError("Configuration validation failed")
    
    logger.success("✅ Configuration validated")


# Configuration summary
def print_config():
    """Print configuration summary"""
    logger.info("📋 NutriBot Configuration:")
    logger.info(f"  Database: {DATABASE_URL}")
    logger.info(f"  OpenAI Model: {OPENAI_MODEL}")
    logger.info(f"  Server: {HOST}:{PORT}")
    logger.info(f"  Debounce: {MESSAGE_DEBOUNCE_SECONDS}s")
    logger.info(f"  PDF Directory: {PDF_DIR}")
    logger.info(f"  Log File: {LOG_FILE}")
    
    if TWILIO_ACCOUNT_SID:
        logger.info(f"  WhatsApp: {TWILIO_WHATSAPP_NUMBER}")
    else:
        logger.warning("  WhatsApp: Not configured")
