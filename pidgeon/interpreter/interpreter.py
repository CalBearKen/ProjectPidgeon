"""Interpreter for message validation and enrichment."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from pidgeon.core.config import Config
from pidgeon.core.models import MessageEnvelope, MessageHeader, TaskType, ActorRole
from pidgeon.core.queue_factory import QueueFactory

logger = logging.getLogger(__name__)


class Interpreter:
    """Interpreter validates and enriches task messages.
    
    The Interpreter:
    - Consumes from Task Queue
    - Validates messages against schemas
    - Enriches with routing metadata (TTL, priority, target queue)
    - Transforms between protocol formats (future: MCP/A2A/ACP)
    - Publishes to Structured Task Queue
    - Sends validation errors to DLQ
    """
    
    def __init__(
        self,
        config: Config,
        queue_factory: QueueFactory,
        interpreter_id: str = "interpreter-001"
    ):
        """Initialize Interpreter.
        
        Args:
            config: Configuration object
            queue_factory: Factory for creating queues
            interpreter_id: Unique identifier for this interpreter instance
        """
        self.config = config
        self.queue_factory = queue_factory
        self.interpreter_id = interpreter_id
        
        self.task_queue = None
        self.structured_queues: Dict[str, Any] = {}
        
        self._running = False
    
    async def start(self) -> None:
        """Start the interpreter service."""
        logger.info(f"Starting Interpreter: {self.interpreter_id}")
        
        # Create task queue
        self.task_queue = await self.queue_factory.create_queue("task")
        
        self._running = True
        
        # Start consuming
        await self._consume_tasks()
    
    async def stop(self) -> None:
        """Stop the interpreter service."""
        logger.info("Stopping Interpreter")
        self._running = False
        
        if self.task_queue:
            await self.task_queue.close()
        
        for queue in self.structured_queues.values():
            await queue.close()
    
    async def _consume_tasks(self) -> None:
        """Consume and process task messages."""
        logger.info("Starting task consumer")
        
        async def handle_task(message: MessageEnvelope) -> None:
            try:
                await self._process_task(message)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
        
        await self.task_queue.consume(handle_task, consumer_group="interpreter")
    
    async def _process_task(self, message: MessageEnvelope) -> None:
        """Process and enrich task message."""
        task_type = message.header.task_type
        correlation_id = message.header.correlation_id
        
        # Handle both enum and string task types
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        
        logger.info(f"Processing task {message.header.message_id} ({task_type_str})")
        
        # Validate message
        validation_result = self._validate_task(message)
        if not validation_result['valid']:
            logger.warning(f"Task validation failed: {validation_result['errors']}")
            await self._handle_validation_error(message, validation_result['errors'])
            return
        
        # Enrich message with routing metadata
        enriched_message = self._enrich_message(message)
        
        # Get target queue for task type
        target_queue = await self._get_structured_queue(task_type)
        
        # Publish to structured task queue
        await target_queue.publish(enriched_message)
        
        # Handle both enum and string task types
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        logger.debug(f"Published enriched task to {task_type_str} queue")
    
    def _validate_task(self, message: MessageEnvelope) -> Dict[str, Any]:
        """Validate task message against schema.
        
        Args:
            message: Message to validate
            
        Returns:
            Validation result dict with 'valid' and 'errors' keys
        """
        errors = []
        
        # Check required fields
        if not message.payload:
            errors.append("Empty payload")
        
        if 'task_id' not in message.payload:
            errors.append("Missing task_id")
        
        if 'task_type' not in message.payload:
            errors.append("Missing task_type")
        
        # Task type specific validation
        task_type = message.header.task_type
        
        if task_type == TaskType.EXTRACTION:
            if 'input_data' not in message.payload:
                errors.append("EXTRACTION task missing input_data")
        
        elif task_type == TaskType.SUMMARIZATION:
            if 'input_data' not in message.payload:
                errors.append("SUMMARIZATION task missing input_data")
        
        elif task_type == TaskType.ANALYSIS:
            if 'input_data' not in message.payload:
                errors.append("ANALYSIS task missing input_data")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _enrich_message(self, message: MessageEnvelope) -> MessageEnvelope:
        """Enrich message with routing and execution metadata.
        
        Args:
            message: Original message
            
        Returns:
            Enriched message
        """
        task_type = message.header.task_type
        
        # Handle both enum and string task types
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        
        # Get routing configuration for this task type
        routing_config = self.config.get_routing_config(task_type_str)
        
        if routing_config:
            # Override TTL if configured
            if 'timeout_ms' in routing_config:
                message.header.ttl_ms = routing_config['timeout_ms']
            
            # Override max retries if configured
            if 'max_retries' in routing_config:
                message.header.max_retries = routing_config['max_retries']
            
            # Set priority if configured
            if 'priority' in routing_config:
                message.header.priority = routing_config['priority']
        
        # Update actor role to interpreter
        message.header.actor_role = ActorRole.INTERPRETER
        
        # Add enrichment metadata
        if 'enrichment' not in message.payload:
            message.payload['enrichment'] = {}
        
        message.payload['enrichment']['interpreter_id'] = self.interpreter_id
        message.payload['enrichment']['enriched_at'] = datetime.utcnow().isoformat()
        message.payload['enrichment']['routing_config'] = routing_config
        
        return message
    
    async def _get_structured_queue(self, task_type: TaskType) -> Any:
        """Get or create structured task queue for task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Queue instance
        """
        # Handle both enum and string task types
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        queue_name = f"structured_task.{task_type_str.lower()}"
        
        if queue_name not in self.structured_queues:
            self.structured_queues[queue_name] = await self.queue_factory.create_queue(queue_name)
            logger.info(f"Created structured queue: {queue_name}")
        
        return self.structured_queues[queue_name]
    
    async def _handle_validation_error(self, message: MessageEnvelope, errors: list) -> None:
        """Handle validation error by moving message to DLQ.
        
        Args:
            message: Invalid message
            errors: List of validation errors
        """
        # Add error details to payload
        message.payload['validation_errors'] = errors
        message.payload['validation_failed_at'] = datetime.utcnow().isoformat()
        
        # Move to DLQ
        await self.task_queue.move_to_dlq(message)
        
        logger.warning(f"Moved invalid message {message.header.message_id} to DLQ")


