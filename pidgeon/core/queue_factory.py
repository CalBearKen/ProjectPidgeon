"""Factory for creating queue instances based on configuration."""

import logging
from typing import Dict, Any, Optional

import redis.asyncio as aioredis

from pidgeon.core.queue_interface import QueueInterface
from pidgeon.core.config import Config
from pidgeon.implementations.memory_queue import InMemoryQueue
from pidgeon.implementations.redis_queue import RedisQueue

logger = logging.getLogger(__name__)


class QueueFactory:
    """Factory for creating queue instances.
    
    This factory allows swapping queue backends without changing component code.
    """
    
    def __init__(self, config: Config):
        """Initialize factory with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._redis_client: Optional[aioredis.Redis] = None
    
    async def _get_redis_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._redis_client is None:
            redis_config = {
                'host': self.config.get('queue.redis.host', 'localhost'),
                'port': self.config.get('queue.redis.port', 6379),
                'db': self.config.get('queue.redis.db', 0),
                'decode_responses': False,  # We handle serialization
                'max_connections': self.config.get('queue.redis.max_connections', 10)
            }
            
            self._redis_client = await aioredis.from_url(
                f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}",
                max_connections=redis_config['max_connections'],
                decode_responses=False
            )
            logger.info("Created Redis client connection")
        
        return self._redis_client
    
    async def create_queue(self, queue_name: str) -> QueueInterface:
        """Create a queue instance based on configuration.
        
        Args:
            queue_name: Name of the queue to create
            
        Returns:
            Queue implementation instance
        """
        backend = self.config.queue_backend
        
        if backend == "memory":
            max_size = self.config.get('queue.memory.max_size', 10000)
            logger.debug(f"Creating in-memory queue: {queue_name}")
            return InMemoryQueue(queue_name, max_size=max_size)
        
        elif backend == "redis":
            redis_client = await self._get_redis_client()
            stream_prefix = self.config.get('queue.redis.stream_prefix', 'pidgeon')
            logger.debug(f"Creating Redis queue: {queue_name}")
            return RedisQueue(queue_name, redis_client, stream_prefix)
        
        elif backend == "kafka":
            # Kafka implementation would go here
            raise NotImplementedError("Kafka backend not yet implemented")
        
        else:
            raise ValueError(f"Unknown queue backend: {backend}")
    
    async def close(self) -> None:
        """Close all connections."""
        if self._redis_client is not None:
            await self._redis_client.close()
            logger.info("Closed Redis client connection")


