#!/usr/bin/env python3
"""
NutriBot Main Entry Point

Initializes database, sets up logging, and starts the Flask server.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import setup_logging, validate_config, print_config
from src.database.schema import init_db
from loguru import logger


def initialize_system():
    """Initialize all system components"""
    logger.info("🚀 Initializing NutriBot...")
    
    # 1. Setup logging
    setup_logging()
    
    # 2. Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        logger.info("💡 Please check your .env file and ensure required variables are set")
        sys.exit(1)
    
    # 3. Print configuration
    print_config()
    
    # 4. Initialize database
    try:
        logger.info("📊 Initializing database...")
        init_db()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    
    logger.success("✅ System initialization complete")


def start_server():
    """Start the Flask webhook server"""
    import threading
    import asyncio
    from src.server.webhook import app, loop, start_async_loop
    from src.config import HOST, PORT, FLASK_DEBUG
    
    logger.info("🌐 Starting webhook server...")
    
    # Start async loop in background thread
    loop_thread = threading.Thread(target=start_async_loop, daemon=True)
    loop_thread.start()
    
    logger.success(f"✅ Server ready at http://{HOST}:{PORT}")
    logger.info("📱 Webhook endpoint: /webhook/whatsapp")
    logger.info("🏥 Health check: /health")
    logger.info("\nPress CTRL+C to stop\n")
    
    # Run Flask app
    try:
        app.run(
            host=HOST,
            port=PORT,
            debug=FLASK_DEBUG
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    # ASCII Art Banner
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███╗   ██╗██╗   ██╗████████╗██████╗ ██╗██████╗  ██████╗████████╗   ║
║   ████╗  ██║██║   ██║╚══██╔══╝██╔══██╗██║██╔══██╗██╔═══██╗╚══██╔══╝   ║
║   ██╔██╗ ██║██║   ██║   ██║   ██████╔╝██║██████╔╝██║   ██║   ██║      ║
║   ██║╚██╗██║██║   ██║   ██║   ██╔══██╗██║██╔══██╗██║   ██║   ██║      ║
║   ██║ ╚████║╚██████╔╝   ██║   ██║  ██║██║██████╔╝╚██████╔╝   ██║      ║
║   ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝    ╚═╝      ║
║                                                           ║
║         Proprietary Agentic Medical RAG System            ║
║              Clinical Dietitian AI Assistant              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Initialize system
    initialize_system()
    
    # Start server
    start_server()


if __name__ == "__main__":
    main()
