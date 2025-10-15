"""Unit tests for InMemoryQueue implementation."""

import pytest
import asyncio

from pidgeon.core.models import MessageEnvelope, MessageHeader, ActorRole, TaskType
from pidgeon.implementations.memory_queue import InMemoryQueue


@pytest.fixture
def message():
    """Create a test message."""
    header = MessageHeader(
        actor_role=ActorRole.PLANNER,
        task_type=TaskType.EXTRACTION
    )
    return MessageEnvelope(header=header, payload={'test': 'data'})


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up queues after each test."""
    yield
    InMemoryQueue.clear_all()


@pytest.mark.asyncio
async def test_publish_message(message):
    """Test publishing a message."""
    queue = InMemoryQueue("test_queue")
    
    message_id = await queue.publish(message)
    
    assert message_id == message.header.message_id
    assert await queue.get_depth() == 1


@pytest.mark.asyncio
async def test_consume_message(message):
    """Test consuming a message."""
    queue = InMemoryQueue("test_queue")
    await queue.publish(message)
    
    received_messages = []
    
    async def handler(msg: MessageEnvelope):
        received_messages.append(msg)
        await queue.close()  # Stop after first message
    
    # Start consuming in background
    consume_task = asyncio.create_task(queue.consume(handler))
    
    # Wait a bit for message to be processed
    await asyncio.sleep(0.1)
    
    # Cancel if still running
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass
    
    assert len(received_messages) == 1
    assert received_messages[0].payload['test'] == 'data'


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that messages are consumed in priority order."""
    queue = InMemoryQueue("test_queue")
    
    # Create messages with different priorities
    msg_low = MessageEnvelope(
        header=MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION,
            priority=3
        ),
        payload={'priority': 'low'}
    )
    
    msg_high = MessageEnvelope(
        header=MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION,
            priority=9
        ),
        payload={'priority': 'high'}
    )
    
    # Publish low priority first, then high
    await queue.publish(msg_low)
    await queue.publish(msg_high)
    
    received_messages = []
    
    async def handler(msg: MessageEnvelope):
        received_messages.append(msg)
        if len(received_messages) == 2:
            await queue.close()
    
    consume_task = asyncio.create_task(queue.consume(handler))
    
    await asyncio.sleep(0.2)
    
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass
    
    # High priority should be consumed first
    if len(received_messages) >= 1:
        assert received_messages[0].payload['priority'] == 'high'


@pytest.mark.asyncio
async def test_get_depth():
    """Test getting queue depth."""
    queue = InMemoryQueue("test_queue")
    
    assert await queue.get_depth() == 0
    
    msg = MessageEnvelope(
        header=MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION
        ),
        payload={}
    )
    
    await queue.publish(msg)
    assert await queue.get_depth() == 1
    
    await queue.publish(msg)
    assert await queue.get_depth() == 2


