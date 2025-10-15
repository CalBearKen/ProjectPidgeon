"""LLM Planner for workflow orchestration and task decomposition."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import orjson

from pidgeon.core.config import Config
from pidgeon.core.models import (
    MessageEnvelope, MessageHeader, TaskDefinition, TaskResult,
    WorkflowState, TaskType, ActorRole, TaskStatus
)
from pidgeon.core.queue_factory import QueueFactory
from pidgeon.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class LLMPlanner:
    """LLM Planner orchestrates workflows by decomposing tasks and synthesizing results.
    
    The Planner:
    - Consumes user requests from Input Queue
    - Decomposes requests into executable task sequences
    - Publishes tasks to Task Queue
    - Consumes results from Result Queue
    - Adapts plans based on intermediate results
    - Synthesizes final outputs
    - Maintains workflow state in Redis
    """
    
    def __init__(
        self,
        config: Config,
        queue_factory: QueueFactory,
        llm_gateway: LLMGateway,
        planner_id: str = "planner-001"
    ):
        """Initialize Planner.
        
        Args:
            config: Configuration object
            queue_factory: Factory for creating queues
            llm_gateway: Gateway for LLM access
            planner_id: Unique identifier for this planner instance
        """
        self.config = config
        self.queue_factory = queue_factory
        self.llm = llm_gateway
        self.planner_id = planner_id
        
        self.input_queue = None
        self.task_queue = None
        self.result_queue = None
        
        # Workflow state storage (in-memory for now, Redis in production)
        self.workflows: Dict[str, WorkflowState] = {}
        
        self._running = False
    
    async def start(self) -> None:
        """Start the planner service."""
        logger.info(f"Starting LLM Planner: {self.planner_id}")
        
        # Create queues
        self.input_queue = await self.queue_factory.create_queue("input")
        self.task_queue = await self.queue_factory.create_queue("task")
        self.result_queue = await self.queue_factory.create_queue("result")
        
        self._running = True
        
        # Run input and result consumers concurrently
        await asyncio.gather(
            self._consume_input(),
            self._consume_results(),
            return_exceptions=True
        )
    
    async def stop(self) -> None:
        """Stop the planner service."""
        logger.info("Stopping LLM Planner")
        self._running = False
        
        if self.input_queue:
            await self.input_queue.close()
        if self.task_queue:
            await self.task_queue.close()
        if self.result_queue:
            await self.result_queue.close()
    
    async def _consume_input(self) -> None:
        """Consume and process input messages."""
        logger.info("Starting input consumer")
        
        async def handle_input(message: MessageEnvelope) -> None:
            try:
                await self._process_input(message)
            except Exception as e:
                logger.error(f"Error processing input: {e}")
        
        await self.input_queue.consume(handle_input, consumer_group="planner_input")
    
    async def _consume_results(self) -> None:
        """Consume and process result messages."""
        logger.info("Starting result consumer")
        
        async def handle_result(message: MessageEnvelope) -> None:
            try:
                await self._process_result(message)
            except Exception as e:
                logger.error(f"Error processing result: {e}")
        
        await self.result_queue.consume(handle_result, consumer_group="planner_result")
    
    async def _process_input(self, message: MessageEnvelope) -> None:
        """Process input message and create workflow."""
        user_request = message.payload.get('request', '')
        correlation_id = message.header.correlation_id
        
        logger.info(f"Processing input for correlation {correlation_id}: {user_request[:100]}...")
        
        # Create workflow state
        workflow = WorkflowState(correlation_id=correlation_id)
        self.workflows[correlation_id] = workflow
        
        # Decompose request into tasks
        tasks = await self.decompose_into_tasks(user_request, correlation_id)
        
        # Publish tasks
        for task in tasks:
            workflow.add_pending_task(task.task_id)
            await self._publish_task(task, correlation_id)
        
        logger.info(f"Created workflow {workflow.workflow_id} with {len(tasks)} tasks")
    
    async def decompose_into_tasks(self, user_request: str, correlation_id: str) -> List[TaskDefinition]:
        """Decompose user request into executable tasks using LLM.
        
        Args:
            user_request: User's natural language request
            correlation_id: Workflow correlation ID
            
        Returns:
            List of task definitions
        """
        system_prompt = """You are a workflow planner for an AI agent system. 
Given a user request, break it down into a sequence of tasks. Each task should be one of:
- EXTRACTION: Extract text or data from documents
- SUMMARIZATION: Summarize text content
- ANALYSIS: Analyze data and generate insights
- FACT_CHECK: Verify facts and claims

Respond with a JSON array of tasks in this format:
[
  {"task_type": "EXTRACTION", "input_data": {"document_url": "..."}, "description": "..."},
  {"task_type": "SUMMARIZATION", "input_data": {"text": "..."}, "description": "..."}
]
"""
        
        prompt = f"User request: {user_request}\n\nBreak this down into executable tasks:"
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse LLM response
            task_data = orjson.loads(response.content)
            
            tasks = []
            for task_spec in task_data:
                task = TaskDefinition(
                    task_type=TaskType(task_spec['task_type']),
                    input_data=task_spec.get('input_data', {}),
                    requirements={'description': task_spec.get('description', '')}
                )
                tasks.append(task)
            
            logger.info(f"Decomposed request into {len(tasks)} tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Error decomposing tasks: {e}")
            # Fallback to simple extraction task
            return [TaskDefinition(
                task_type=TaskType.EXTRACTION,
                input_data={'request': user_request},
                requirements={'description': 'Process user request'}
            )]
    
    async def _publish_task(self, task: TaskDefinition, correlation_id: str) -> None:
        """Publish task to task queue."""
        header = MessageHeader(
            correlation_id=correlation_id,
            actor_role=ActorRole.PLANNER,
            task_type=task.task_type,
            priority=5
        )
        
        message = MessageEnvelope(
            header=header,
            payload={
                'task_id': task.task_id,
                'task_type': task.task_type.value,
                'input_data': task.input_data,
                'requirements': task.requirements,
                'constraints': task.constraints
            }
        )
        
        await self.task_queue.publish(message)
        logger.debug(f"Published task {task.task_id} ({task.task_type.value})")
    
    async def _process_result(self, message: MessageEnvelope) -> None:
        """Process result message from an agent."""
        correlation_id = message.header.correlation_id
        result_payload = message.payload
        
        # Get workflow
        workflow = self.workflows.get(correlation_id)
        if workflow is None:
            logger.warning(f"No workflow found for correlation {correlation_id}")
            return
        
        # Parse result
        task_result = TaskResult(
            task_id=result_payload['task_id'],
            status=TaskStatus(result_payload['status']),
            output_data=result_payload.get('output_data', {}),
            metadata=result_payload.get('metadata', {}),
            error_details=result_payload.get('error_details'),
            processing_time_ms=result_payload.get('processing_time_ms'),
            confidence_score=result_payload.get('confidence_score'),
            agent_id=result_payload.get('agent_id')
        )
        
        logger.info(f"Received result for task {task_result.task_id}: {task_result.status.value}")
        
        # Update workflow state
        if task_result.status == TaskStatus.SUCCESS:
            workflow.mark_completed(task_result.task_id, task_result)
        else:
            workflow.mark_failed(task_result.task_id, task_result)
        
        # Check if workflow is complete
        if workflow.is_complete():
            await self._finalize_workflow(workflow)
    
    async def _finalize_workflow(self, workflow: WorkflowState) -> None:
        """Finalize workflow and generate final result."""
        logger.info(f"Finalizing workflow {workflow.workflow_id}")
        
        # Collect all results
        all_results = []
        for task_id, result in workflow.task_results.items():
            all_results.append({
                'task_id': task_id,
                'status': result.status.value,
                'output': result.output_data
            })
        
        # Synthesize final result using LLM
        final_result = await self._synthesize_results(all_results)
        workflow.final_result = final_result
        workflow.status = TaskStatus.SUCCESS if not workflow.has_failures() else TaskStatus.PARTIAL
        
        logger.info(f"Workflow {workflow.workflow_id} complete: {workflow.status.value}")
        
        # In a real implementation, would publish final result somewhere
        # For now, just log it
        logger.info(f"Final result: {final_result}")
    
    async def _synthesize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize final result from task results using LLM.
        
        Args:
            results: List of task results
            
        Returns:
            Synthesized final result
        """
        system_prompt = """You are synthesizing results from multiple AI agents into a coherent final response.
Combine the outputs logically and provide a comprehensive answer to the original user request."""
        
        results_text = orjson.dumps(results, option=orjson.OPT_INDENT_2).decode()
        prompt = f"Task results:\n{results_text}\n\nProvide a synthesized final response:"
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=2000
            )
            
            return {
                'synthesis': response.content,
                'individual_results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return {
                'synthesis': 'Error synthesizing results',
                'individual_results': results,
                'error': str(e)
            }


