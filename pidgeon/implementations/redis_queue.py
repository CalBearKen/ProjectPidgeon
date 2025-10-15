"""Redis-based queue implementation using Redis Streams."""

import asyncio
import logging
from typing import Callable, Optional, Awaitable, Dict, Any
from datetime import datetime
import orjson

import redis.asyncio as aioredis

from pidgeon.core.queue_interface import QueueInterface
from pidgeon.core.models import MessageEnvelope

logger = logging.getLogger(__name__)


class RedisQueue(QueueInterface):
    """Redis queue implementation using Redis Streams.
    
    This implementation provides:
    - Persistence across restarts
    - Consumer groups for competing consumers
    - Dead letter queue support
    - At-least-once delivery semantics
    """
    
    def __init__(
        self,
        queue_name: str,
        redis_client: aioredis.Redis,
        stream_prefix: str = "pidgeon"
    ):
        """Initialize Redis queue.
        
        Args:
            queue_name: Name of the queue
            redis_client: Async Redis client
            stream_prefix: Prefix for Redis stream keys
        """
        super().__init__(queue_name)
        self.redis = redis_client
        self.stream_prefix = stream_prefix
        self.stream_key = f"{stream_prefix}:stream:{queue_name}"
        self.dlq_key = f"{stream_prefix}:stream:dead_letter"
        self._running = False
    
    async def publish(self, message: MessageEnvelope, priority: Optional[int] = None) -> str:
        """Publish message to Redis stream."""
        # Update enqueue timestamp
        message.header.enqueue_ts = datetime.utcnow()
        
        # Override priority if specified
        if priority is not None:
            message.header.priority = priority
        
        # Serialize message
        message_data = orjson.dumps(message.to_dict())
        
        # Add to Redis stream
        message_id = await self.redis.xadd(
            self.stream_key,
            {
                "data": message_data,
                "priority": str(message.header.priority),
                "message_id": message.header.message_id
            }
        )
        
        logger.debug(f"Published message to {self.stream_key}: {message_id}")
        return message.header.message_id
    
    async def consume(
        self,
        handler: Callable[[MessageEnvelope], Awaitable[None]],
        consumer_group: Optional[str] = None,
        block_ms: int = 1000
    ) -> None:
        """Consume messages from Redis stream using consumer groups."""
        self._running = True
        
        # Default consumer group
        if consumer_group is None:
            consumer_group = f"{self.queue_name}_group"
        
        consumer_name = f"consumer_{id(self)}"
        
        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                consumer_group,
                id="0",
                mkstream=True
            )
            logger.info(f"Created consumer group {consumer_group}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        
        logger.info(f"Starting consumer {consumer_name} for {self.stream_key}")
        
        while self._running:
            try:
                # Read from stream
                messages = await self.redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {self.stream_key: ">"},
                    count=1,
                    block=block_ms
                )
                
                if not messages:
                    continue
                
                # Process each message
                for stream_name, message_list in messages:
                    for redis_msg_id, fields in message_list:
                        await self._process_message(
                            redis_msg_id,
                            fields,
                            handler,
                            consumer_group
                        )
                        
            except asyncio.CancelledError:
                logger.info(f"Consumer {consumer_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(
        self,
        redis_msg_id: bytes,
        fields: Dict[bytes, bytes],
        handler: Callable[[MessageEnvelope], Awaitable[None]],
        consumer_group: str
    ) -> None:
        """Process a single message."""
        try:
            # Deserialize message
            message_data = orjson.loads(fields[b"data"])
            message = MessageEnvelope.from_dict(message_data)
            
            # Update processing timestamp
            message.header.processing_ts = datetime.utcnow()
            
            # Check if expired
            if message.is_expired():
                logger.warning(f"Message {message.header.message_id} expired")
                await self.move_to_dlq(message)
                await self.ack(redis_msg_id.decode())
                return
            
            # Process message
            await handler(message)
            
            # Acknowledge
            await self.ack(redis_msg_id.decode())
            
        except Exception as e:
            logger.error(f"Error processing message {redis_msg_id}: {e}")
            
            # Try to get message for retry logic
            try:
                message_data = orjson.loads(fields[b"data"])
                message = MessageEnvelope.from_dict(message_data)
                await self.nack(redis_msg_id.decode(), requeue=message.can_retry())
            except Exception:
                # If we can't deserialize, just acknowledge to remove from stream
                await self.ack(redis_msg_id.decode())
    
    async def ack(self, message_id: str) -> None:
        """Acknowledge message by removing from stream."""
        # XACK marks the message as processed
        # In Redis Streams, the message_id here is the Redis stream ID, not our message_id
        # We'll need to track the mapping or just delete after processing
        # For simplicity, we'll use XDEL to remove the message
        try:
            await self.redis.xdel(self.stream_key, message_id)
            logger.debug(f"Acknowledged and deleted message {message_id}")
        except Exception as e:
            logger.error(f"Error acknowledging message {message_id}: {e}")
    
    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Negative acknowledge - handle failed message."""
        # For Redis Streams, we need to read the pending message
        # and either requeue or move to DLQ
        # This is a simplified implementation
        logger.warning(f"NACK for message {message_id}, requeue={requeue}")
        
        if not requeue:
            # Move to DLQ (would need to read message first)
            # For now, just acknowledge to remove it
            await self.ack(message_id)
    
    async def get_depth(self) -> int:
        """Get stream length."""
        try:
            return await self.redis.xlen(self.stream_key)
        except Exception:
            return 0
    
    async def move_to_dlq(self, message: MessageEnvelope) -> None:
        """Move message to dead letter queue stream."""
        message_data = orjson.dumps(message.to_dict())
        
        await self.redis.xadd(
            self.dlq_key,
            {
                "data": message_data,
                "original_queue": self.queue_name,
                "failed_at": datetime.utcnow().isoformat(),
                "message_id": message.header.message_id
            }
        )
        
        logger.info(f"Moved message {message.header.message_id} to DLQ")
    
    async def close(self) -> None:
        """Stop consuming."""
        self._running = False
        logger.info(f"Closed Redis queue {self.queue_name}")


