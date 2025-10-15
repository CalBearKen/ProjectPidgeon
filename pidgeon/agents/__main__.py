"""Entry point for running agent services."""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

import redis.asyncio as aioredis

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pidgeon.core.config import Config
from pidgeon.core.queue_factory import QueueFactory
from pidgeon.core.models import TaskType
from pidgeon.gateway.llm_gateway import LLMGateway
from pidgeon.agents.extraction_agent import ExtractionAgent
from pidgeon.agents.summarization_agent import SummarizationAgent
from pidgeon.agents.analysis_agent import AnalysisAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run an agent service."""
    parser = argparse.ArgumentParser(description='Run a Pidgeon agent')
    parser.add_argument(
        '--type',
        choices=['extraction', 'summarization', 'analysis'],
        required=True,
        help='Type of agent to run'
    )
    parser.add_argument(
        '--id',
        default=None,
        help='Agent ID (auto-generated if not specified)'
    )
    
    args = parser.parse_args()
    
    agent_type = args.type
    agent_id = args.id or f"{agent_type}-agent-001"
    
    logger.info(f"=== Starting Pidgeon Agent: {agent_type} ({agent_id}) ===")
    
    # Load configuration
    config = Config()
    
    # Create queue factory
    queue_factory = QueueFactory(config)
    
    # Create Redis client for LLM cache if needed
    redis_client = None
    llm_gateway = None
    
    if agent_type in ['summarization', 'analysis']:
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
        
        llm_gateway = LLMGateway(config, redis_client)
    
    # Create appropriate agent
    if agent_type == 'extraction':
        agent = ExtractionAgent(agent_id, config, queue_factory)
    elif agent_type == 'summarization':
        agent = SummarizationAgent(agent_id, config, queue_factory, llm_gateway)
    elif agent_type == 'analysis':
        agent = AnalysisAgent(agent_id, config, queue_factory, llm_gateway)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    try:
        # Start agent
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        # Cleanup
        await agent.stop()
        await queue_factory.close()
        if redis_client:
            await redis_client.close()
        
        # Print final stats
        stats = agent.get_stats()
        logger.info(f"Agent final stats: {stats}")
        logger.info("Agent shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())


