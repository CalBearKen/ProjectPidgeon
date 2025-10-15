"""Base agent framework for domain-specific task processing."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from pidgeon.core.config import Config
from pidgeon.core.models import (
    MessageEnvelope, MessageHeader, TaskStatus, TaskType, ActorRole
)
from pidgeon.core.queue_factory import QueueFactory

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agent implementations.
    
    Agents are stateless workers that:
    - Subscribe to specific task types from Structured Task Queue
    - Process tasks atomically
    - Publish results to Result Queue
    - Handle errors gracefully with structured reporting
    """
    
    def __init__(
        self,
        agent_id: str,
        task_type: TaskType,
        config: Config,
        queue_factory: QueueFactory
    ):
        """Initialize agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            task_type: Type of tasks this agent processes
            config: Configuration object
            queue_factory: Factory for creating queues
        """
        self.agent_id = agent_id
        self.task_type = task_type
        self.config = config
        self.queue_factory = queue_factory
        
        self.task_queue = None
        self.result_queue = None
        
        self._running = False
        self._tasks_processed = 0
        self._tasks_succeeded = 0
        self._tasks_failed = 0
    
    async def start(self) -> None:
        """Start the agent service."""
        logger.info(f"Starting {self.__class__.__name__}: {self.agent_id}")
        
        # Create queues
        queue_name = f"structured_task.{self.task_type.value.lower()}"
        self.task_queue = await self.queue_factory.create_queue(queue_name)
        self.result_queue = await self.queue_factory.create_queue("result")
        
        self._running = True
        
        # Start consuming
        await self._consume_tasks()
    
    async def stop(self) -> None:
        """Stop the agent service."""
        logger.info(f"Stopping {self.__class__.__name__}")
        self._running = False
        
        if self.task_queue:
            await self.task_queue.close()
        if self.result_queue:
            await self.result_queue.close()
        
        logger.info(
            f"Agent {self.agent_id} final stats: "
            f"processed={self._tasks_processed}, "
            f"succeeded={self._tasks_succeeded}, "
            f"failed={self._tasks_failed}"
        )
    
    async def _consume_tasks(self) -> None:
        """Consume and process tasks from queue."""
        consumer_group = f"agent_{self.task_type.value.lower()}"
        
        async def handle_task(message: MessageEnvelope) -> None:
            await self._process_task_message(message)
        
        await self.task_queue.consume(handle_task, consumer_group=consumer_group)
    
    async def _process_task_message(self, message: MessageEnvelope) -> None:
        """Process a task message and publish result."""
        task_id = message.payload.get('task_id', 'unknown')
        start_time = datetime.utcnow()
        
        logger.info(f"Processing task {task_id}")
        self._tasks_processed += 1
        
        try:
            # Call agent-specific processing logic
            output_data = await self.process_task(message.payload)
            
            # Calculate processing time
            processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create success result
            result = self._create_result(
                task_id=task_id,
                correlation_id=message.header.correlation_id,
                status=TaskStatus.SUCCESS,
                output_data=output_data,
                processing_time_ms=processing_time_ms
            )
            
            self._tasks_succeeded += 1
            logger.info(f"Task {task_id} completed successfully in {processing_time_ms:.2f}ms")
            
        except Exception as e:
            # Calculate processing time
            processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create error result
            result = self._create_result(
                task_id=task_id,
                correlation_id=message.header.correlation_id,
                status=TaskStatus.ERROR,
                output_data={},
                processing_time_ms=processing_time_ms,
                error_details={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'retry_recommended': self._is_retriable_error(e)
                }
            )
            
            self._tasks_failed += 1
            logger.error(f"Task {task_id} failed: {e}")
        
        # Publish result
        await self.result_queue.publish(result)
    
    @abstractmethod
    async def process_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return output data.
        
        This method must be implemented by specific agent types.
        
        Args:
            task_payload: Task data from message payload
            
        Returns:
            Dictionary of output data
            
        Raises:
            Exception: If task processing fails
        """
        pass
    
    def _create_result(
        self,
        task_id: str,
        correlation_id: str,
        status: TaskStatus,
        output_data: Dict[str, Any],
        processing_time_ms: float,
        error_details: Optional[Dict[str, Any]] = None
    ) -> MessageEnvelope:
        """Create result message envelope.
        
        Args:
            task_id: ID of the task
            correlation_id: Workflow correlation ID
            status: Task execution status
            output_data: Output data from task
            processing_time_ms: Processing time in milliseconds
            error_details: Error details if task failed
            
        Returns:
            Message envelope with result
        """
        header = MessageHeader(
            correlation_id=correlation_id,
            actor_role=ActorRole.AGENT,
            task_type=self.task_type,
            priority=5
        )
        
        payload = {
            'task_id': task_id,
            'status': status.value,
            'output_data': output_data,
            'metadata': {
                'agent_id': self.agent_id,
                'agent_type': self.__class__.__name__,
                'processing_time_ms': processing_time_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        if error_details:
            payload['error_details'] = error_details
        
        return MessageEnvelope(header=header, payload=payload)
    
    def _is_retriable_error(self, error: Exception) -> bool:
        """Determine if an error is retriable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if error might succeed on retry
        """
        # Transient errors that might succeed on retry
        retriable_types = (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError
        )
        
        return isinstance(error, retriable_types)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics.
        
        Returns:
            Dictionary of agent statistics
        """
        return {
            'agent_id': self.agent_id,
            'agent_type': self.__class__.__name__,
            'task_type': self.task_type.value,
            'tasks_processed': self._tasks_processed,
            'tasks_succeeded': self._tasks_succeeded,
            'tasks_failed': self._tasks_failed,
            'success_rate': self._tasks_succeeded / self._tasks_processed if self._tasks_processed > 0 else 0
        }


