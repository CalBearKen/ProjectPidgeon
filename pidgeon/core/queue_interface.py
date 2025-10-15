"""Abstract queue interface for backend-agnostic message passing."""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Awaitable

from pidgeon.core.models import MessageEnvelope


class QueueInterface(ABC):
    """Abstract base class for message queue implementations.
    
    This interface allows swapping queue backends (Memory, Redis, Kafka)
    without changing component code.
    """
    
    def __init__(self, queue_name: str):
        """Initialize queue with a name.
        
        Args:
            queue_name: Name of the queue
        """
        self.queue_name = queue_name
    
    @abstractmethod
    async def publish(self, message: MessageEnvelope, priority: Optional[int] = None) -> str:
        """Publish a message to the queue.
        
        Args:
            message: Message envelope to publish
            priority: Optional priority override (1-10, 10 is highest)
            
        Returns:
            Message ID assigned by the queue
        """
        pass
    
    @abstractmethod
    async def consume(
        self,
        handler: Callable[[MessageEnvelope], Awaitable[None]],
        consumer_group: Optional[str] = None,
        block_ms: int = 1000
    ) -> None:
        """Consume messages from the queue.
        
        This method runs indefinitely, processing messages as they arrive.
        
        Args:
            handler: Async function to process each message
            consumer_group: Consumer group name for competing consumers
            block_ms: Milliseconds to block waiting for messages
        """
        pass
    
    @abstractmethod
    async def ack(self, message_id: str) -> None:
        """Acknowledge successful message processing.
        
        Args:
            message_id: ID of the message to acknowledge
        """
        pass
    
    @abstractmethod
    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Negative acknowledge - message processing failed.
        
        Args:
            message_id: ID of the message that failed
            requeue: Whether to requeue the message for retry
        """
        pass
    
    @abstractmethod
    async def get_depth(self) -> int:
        """Get current queue depth (number of pending messages).
        
        Returns:
            Number of messages in queue
        """
        pass
    
    @abstractmethod
    async def move_to_dlq(self, message: MessageEnvelope) -> None:
        """Move a message to the Dead Letter Queue.
        
        Args:
            message: Message that failed processing
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close queue connections and clean up resources."""
        pass


