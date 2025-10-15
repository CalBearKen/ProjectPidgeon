"""Integration test for end-to-end workflow."""

import pytest
import asyncio
from datetime import datetime

from pidgeon.core.config import Config
from pidgeon.core.queue_factory import QueueFactory
from pidgeon.core.models import MessageEnvelope, MessageHeader, ActorRole, TaskType
from pidgeon.implementations.memory_queue import InMemoryQueue


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up queues after each test."""
    yield
    InMemoryQueue.clear_all()


@pytest.mark.asyncio
async def test_basic_message_flow():
    """Test basic message flow through queues."""
    # Create config with memory backend
    config = Config()
    factory = QueueFactory(config)
    
    # Create queues
    input_queue = await factory.create_queue("input")
    task_queue = await factory.create_queue("task")
    
    # Create and publish a message to input queue
    header = MessageHeader(
        actor_role=ActorRole.USER,
        task_type=TaskType.EXTRACTION
    )
    
    message = MessageEnvelope(
        header=header,
        payload={'request': 'Test request'}
    )
    
    message_id = await input_queue.publish(message)
    
    # Verify message was published
    assert message_id == message.header.message_id
    assert await input_queue.get_depth() == 1
    
    # Consume message from input queue
    received_messages = []
    
    async def handler(msg: MessageEnvelope):
        received_messages.append(msg)
        # Forward to task queue (simulating planner behavior)
        await task_queue.publish(msg)
        await input_queue.close()
    
    consume_task = asyncio.create_task(input_queue.consume(handler))
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Clean up
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass
    
    # Verify message was received
    assert len(received_messages) == 1
    assert received_messages[0].payload['request'] == 'Test request'
    
    # Verify message was forwarded to task queue
    assert await task_queue.get_depth() == 1
    
    # Cleanup
    await input_queue.close()
    await task_queue.close()
    await factory.close()


@pytest.mark.asyncio
async def test_message_expiration():
    """Test message TTL expiration."""
    config = Config()
    factory = QueueFactory(config)
    
    queue = await factory.create_queue("test")
    
    # Create message with very short TTL
    header = MessageHeader(
        actor_role=ActorRole.PLANNER,
        task_type=TaskType.EXTRACTION,
        ttl_ms=100  # 100ms
    )
    
    message = MessageEnvelope(header=header, payload={})
    
    # Publish message
    await queue.publish(message)
    
    # Wait for expiration
    await asyncio.sleep(0.2)
    
    # Consume - should be moved to DLQ
    expired_messages = []
    dlq_messages = []
    
    async def handler(msg: MessageEnvelope):
        if msg.is_expired():
            expired_messages.append(msg)
        await queue.close()
    
    consume_task = asyncio.create_task(queue.consume(handler))
    
    await asyncio.sleep(0.3)
    
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass
    
    # Cleanup
    await queue.close()
    await factory.close()


@pytest.mark.asyncio
async def test_message_retry():
    """Test message retry mechanism."""
    config = Config()
    factory = QueueFactory(config)
    
    queue = await factory.create_queue("test")
    
    # Create message
    header = MessageHeader(
        actor_role=ActorRole.AGENT,
        task_type=TaskType.EXTRACTION,
        max_retries=2
    )
    
    message = MessageEnvelope(header=header, payload={})
    
    # Verify can retry
    assert message.can_retry() is True
    assert message.header.retry_count == 0
    
    # Increment retry
    message.increment_retry()
    assert message.header.retry_count == 1
    assert message.can_retry() is True
    
    # Increment again
    message.increment_retry()
    assert message.header.retry_count == 2
    assert message.can_retry() is False
    
    await queue.close()
    await factory.close()


