"""Entry point for running the LLM Planner service."""

import asyncio
import logging
import sys
from pathlib import Path

import redis.asyncio as aioredis

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pidgeon.core.config import Config
from pidgeon.core.queue_factory import QueueFactory
from pidgeon.gateway.llm_gateway import LLMGateway
from pidgeon.planner.planner import LLMPlanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the LLM Planner service."""
    logger.info("=== Starting Pidgeon LLM Planner ===")
    
    # Load configuration
    config = Config()
    
    # Create queue factory
    queue_factory = QueueFactory(config)
    
    # Create Redis client for LLM cache (if using Redis backend)
    redis_client = None
    if config.queue_backend == "redis":
        redis_config = {
            'host': config.get('state.redis.host', 'localhost'),
            'port': config.get('state.redis.port', 6379),
            'db': config.get('state.redis.db', 1)
        }
        redis_client = await aioredis.from_url(
            f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}",
            decode_responses=False
        )
    
    # Create LLM gateway
    llm_gateway = LLMGateway(config, redis_client)
    
    # Create planner
    planner = LLMPlanner(config, queue_factory, llm_gateway)
    
    try:
        # Start planner
        await planner.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        # Cleanup
        await planner.stop()
        await queue_factory.close()
        if redis_client:
            await redis_client.close()
        logger.info("Planner shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())


