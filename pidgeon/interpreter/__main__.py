"""Entry point for running the Interpreter service."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pidgeon.core.config import Config
from pidgeon.core.queue_factory import QueueFactory
from pidgeon.interpreter.interpreter import Interpreter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the Interpreter service."""
    logger.info("=== Starting Pidgeon Interpreter ===")
    
    # Load configuration
    config = Config()
    
    # Create queue factory
    queue_factory = QueueFactory(config)
    
    # Create interpreter
    interpreter = Interpreter(config, queue_factory)
    
    try:
        # Start interpreter
        await interpreter.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        # Cleanup
        await interpreter.stop()
        await queue_factory.close()
        logger.info("Interpreter shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())


