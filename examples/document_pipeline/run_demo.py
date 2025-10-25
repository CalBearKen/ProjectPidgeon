"""Document analysis pipeline demo.

This demonstrates a complete workflow:
1. User submits document analysis request
2. Planner decomposes into EXTRACTION → SUMMARIZATION → ANALYSIS
3. Interpreter validates and routes tasks
4. Agents process tasks
5. Results flow back to Planner
6. Planner synthesizes final output
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pidgeon.core.config import Config
from pidgeon.core.models import MessageEnvelope, MessageHeader, ActorRole, TaskType
from pidgeon.core.queue_factory import QueueFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def submit_request(input_queue, request: str) -> str:
    """Submit a user request to the input queue.
    
    Args:
        input_queue: Input queue instance
        request: User request string
        
    Returns:
        Correlation ID for tracking the workflow
    """
    header = MessageHeader(
        actor_role=ActorRole.USER,
        task_type=TaskType.CUSTOM  # Will be decomposed by planner
    )
    
    message = MessageEnvelope(
        header=header,
        payload={'request': request}
    )
    
    await input_queue.publish(message)
    correlation_id = message.header.correlation_id
    
    logger.info(f"Submitted request with correlation ID: {correlation_id}")
    logger.info(f"Request: {request}")
    
    return correlation_id


async def monitor_queues(queue_factory, duration_seconds: int = 30):
    """Monitor queue depths during workflow execution.
    
    Args:
        queue_factory: Queue factory for accessing queues
        duration_seconds: How long to monitor
    """
    logger.info(f"Monitoring queues for {duration_seconds} seconds...")
    
    queue_names = [
        "input",
        "task",
        "structured_task.extraction",
        "structured_task.summarization",
        "structured_task.analysis",
        "result",
        "dead_letter"
    ]
    
    queues = {}
    for name in queue_names:
        try:
            queues[name] = await queue_factory.create_queue(name)
        except Exception as e:
            logger.warning(f"Could not create queue {name}: {e}")
    
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
        logger.info("=== Queue Depths ===")
        
        for name, queue in queues.items():
            try:
                depth = await queue.get_depth()
                if depth > 0:
                    logger.info(f"  {name}: {depth} messages")
            except Exception as e:
                logger.warning(f"  {name}: error reading depth ({e})")
        
        await asyncio.sleep(5)
    
    # Close monitoring queues
    for queue in queues.values():
        await queue.close()


async def main():
    """Run the document pipeline demo."""
    logger.info("="*60)
    logger.info("Pidgeon Protocol - Document Analysis Pipeline Demo")
    logger.info("="*60)
    logger.info("")
    logger.info("IMPORTANT: This script runs OUTSIDE Docker and connects to")
    logger.info("Docker containers via localhost:6379. Make sure you have:")
    logger.info("1. Docker containers running: docker-compose up")
    logger.info("2. Redis accessible on localhost:6379")
    logger.info("")
    
    # Load configuration
    config = Config()
    logger.info(f"Queue backend: {config.queue_backend}")
    
    # Override Redis host for external connections to Docker
    # When running outside Docker, we need to connect to localhost:6379
    # instead of the Docker service name 'redis'
    if config.queue_backend == "redis":
        # Override the Redis host to localhost for external connections
        config._settings['queue']['redis']['host'] = 'localhost'
        logger.info("Overriding Redis host to 'localhost' for external connection to Docker")
    
    # Create queue factory
    queue_factory = QueueFactory(config)
    
    # Create input queue
    try:
        input_queue = await queue_factory.create_queue("input")
        logger.info("Successfully connected to Redis and created input queue")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error("Make sure Docker containers are running with: docker-compose up")
        logger.error("And that Redis is accessible on localhost:6379")
        return
    
    # Import sample data
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from sample_data import Q4_2024_SALES_REPORT
    
    # Sample document analysis request with actual data
    request = f"""
    Analyze the quarterly sales report for Q4 2024.
    Extract key metrics, summarize the main findings, and provide
    an analysis of trends and recommendations for Q1 2025.
    
    Document content:
    {Q4_2024_SALES_REPORT}
    """
    
    try:
        # Submit request
        correlation_id = await submit_request(input_queue, request)
        
        logger.info("")
        logger.info("Request submitted! The workflow will proceed as follows:")
        logger.info("1. Planner decomposes request into tasks")
        logger.info("2. Interpreter validates and routes tasks")
        logger.info("3. Agents process: EXTRACTION → SUMMARIZATION → ANALYSIS")
        logger.info("4. Results flow back to Planner")
        logger.info("5. Planner synthesizes final output")
        logger.info("")
        logger.info("NOTE: This demo submits the request. To see it processed,")
        logger.info("you need to run the following services in separate terminals:")
        logger.info("  - python -m pidgeon.planner")
        logger.info("  - python -m pidgeon.interpreter")
        logger.info("  - python -m pidgeon.agents --type extraction")
        logger.info("  - python -m pidgeon.agents --type summarization")
        logger.info("  - python -m pidgeon.agents --type analysis")
        logger.info("  - python -m pidgeon.supervisor (optional)")
        logger.info("")
        
        # Monitor queues for a bit
        await monitor_queues(queue_factory, duration_seconds=15)
        
        logger.info("")
        logger.info("Demo complete! Check the logs of each service to see the workflow.")
        logger.info(f"Track your workflow with correlation ID: {correlation_id}")
        
    finally:
        await input_queue.close()
        await queue_factory.close()


if __name__ == "__main__":
    asyncio.run(main())


