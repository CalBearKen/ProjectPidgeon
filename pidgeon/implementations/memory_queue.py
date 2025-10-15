"""In-memory queue implementation for development and testing."""

import asyncio
import logging
from typing import Callable, Optional, Awaitable, Dict
from datetime import datetime

from pidgeon.core.queue_interface import QueueInterface
from pidgeon.core.models import MessageEnvelope

logger = logging.getLogger(__name__)


class InMemoryQueue(QueueInterface):
    """In-memory queue implementation using asyncio.PriorityQueue.
    
    This implementation is suitable for:
    - Local development
    - Unit testing
    - Single-process deployments
    
    Note: Messages are not persisted and will be lost on process restart.
    """
    
    # Shared queues across all instances (class variable)
    _queues: Dict[str, asyncio.PriorityQueue] = {}
    _message_store: Dict[str, MessageEnvelope] = {}
    _dlq_name = "dead_letter"
    
    def __init__(self, queue_name: str, max_size: int = 10000):
        """Initialize in-memory queue.
        
        Args:
            queue_name: Name of the queue
            max_size: Maximum queue size
        """
        super().__init__(queue_name)
        self.max_size = max_size
        self._running = False
        
        # Create queue if it doesn't exist
        if queue_name not in self._queues:
            self._queues[queue_name] = asyncio.PriorityQueue(maxsize=max_size)
        
        self._queue = self._queues[queue_name]
    
    async def publish(self, message: MessageEnvelope, priority: Optional[int] = None) -> str:
        """Publish message to in-memory queue."""
        # Use provided priority or message header priority
        msg_priority = priority if priority is not None else message.header.priority
        
        # Update enqueue timestamp
        message.header.enqueue_ts = datetime.utcnow()
        
        # Store message
        self._message_store[message.header.message_id] = message
        
        # Priority queue uses lowest number = highest priority, so invert
        inverted_priority = 11 - msg_priority
        
        try:
            # Put (priority, message_id) tuple
            await self._queue.put((inverted_priority, message.header.message_id))
            logger.debug(f"Published message {message.header.message_id} to {self.queue_name}")
            return message.header.message_id
        except asyncio.QueueFull:
            logger.error(f"Queue {self.queue_name} is full")
            raise
    
    async def consume(
        self,
        handler: Callable[[MessageEnvelope], Awaitable[None]],
        consumer_group: Optional[str] = None,
        block_ms: int = 1000
    ) -> None:
        """Consume messages from in-memory queue."""
        self._running = True
        logger.info(f"Starting consumer for queue {self.queue_name}")
        
        while self._running:
            try:
                # Wait for message with timeout
                timeout = block_ms / 1000.0
                priority, message_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=timeout
                )
                
                # Retrieve message
                message = self._message_store.get(message_id)
                if message is None:
                    logger.warning(f"Message {message_id} not found in store")
                    continue
                
                # Update processing timestamp
                message.header.processing_ts = datetime.utcnow()
                
                # Check if message is expired
                if message.is_expired():
                    logger.warning(f"Message {message_id} expired, moving to DLQ")
                    await self.move_to_dlq(message)
                    await self.ack(message_id)
                    continue
                
                try:
                    # Process message
                    await handler(message)
                    await self.ack(message_id)
                    
                except Exception as e:
                    logger.error(f"Error processing message {message_id}: {e}")
                    await self.nack(message_id, requeue=message.can_retry())
                    
            except asyncio.TimeoutError:
                # No messages available, continue polling
                continue
            except asyncio.CancelledError:
                logger.info(f"Consumer for {self.queue_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in consumer: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def ack(self, message_id: str) -> None:
        """Acknowledge message processing."""
        # Remove from message store
        if message_id in self._message_store:
            del self._message_store[message_id]
            logger.debug(f"Acknowledged message {message_id}")
    
    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Negative acknowledge message."""
        message = self._message_store.get(message_id)
        if message is None:
            return
        
        if requeue and message.can_retry():
            # Increment retry count and requeue
            message.increment_retry()
            logger.info(f"Requeuing message {message_id}, retry {message.header.retry_count}")
            await self.publish(message)
        else:
            # Move to DLQ
            logger.warning(f"Message {message_id} exceeded retries, moving to DLQ")
            await self.move_to_dlq(message)
            await self.ack(message_id)
    
    async def get_depth(self) -> int:
        """Get current queue depth."""
        return self._queue.qsize()
    
    async def move_to_dlq(self, message: MessageEnvelope) -> None:
        """Move message to dead letter queue."""
        if self._dlq_name not in self._queues:
            self._queues[self._dlq_name] = asyncio.PriorityQueue(maxsize=self.max_size)
        
        dlq = self._queues[self._dlq_name]
        
        # Add to DLQ with lowest priority
        try:
            await dlq.put((10, message.header.message_id))
            self._message_store[message.header.message_id] = message
            logger.info(f"Moved message {message.header.message_id} to DLQ")
        except asyncio.QueueFull:
            logger.error("Dead Letter Queue is full!")
    
    async def close(self) -> None:
        """Stop consuming and cleanup."""
        self._running = False
        logger.info(f"Closed queue {self.queue_name}")
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all queues (useful for testing)."""
        cls._queues.clear()
        cls._message_store.clear()


