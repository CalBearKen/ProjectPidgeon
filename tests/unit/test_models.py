"""Unit tests for core message models."""

import pytest
from datetime import datetime, timedelta

from pidgeon.core.models import (
    MessageHeader, MessageEnvelope, TaskDefinition, TaskResult,
    WorkflowState, TaskType, ActorRole, TaskStatus
)


class TestMessageHeader:
    """Test MessageHeader model."""
    
    def test_create_header_with_defaults(self):
        """Test creating header with default values."""
        header = MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION
        )
        
        assert header.message_id is not None
        assert header.correlation_id is not None
        assert header.priority == 5
        assert header.ttl_ms == 30000
        assert header.retry_count == 0
        assert header.max_retries == 3
    
    def test_create_header_with_custom_values(self):
        """Test creating header with custom values."""
        header = MessageHeader(
            actor_role=ActorRole.AGENT,
            task_type=TaskType.SUMMARIZATION,
            priority=8,
            ttl_ms=60000,
            max_retries=5
        )
        
        assert header.priority == 8
        assert header.ttl_ms == 60000
        assert header.max_retries == 5


class TestMessageEnvelope:
    """Test MessageEnvelope model."""
    
    def test_create_envelope(self):
        """Test creating message envelope."""
        header = MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION
        )
        
        envelope = MessageEnvelope(
            header=header,
            payload={'test': 'data'}
        )
        
        assert envelope.header == header
        assert envelope.payload == {'test': 'data'}
    
    def test_to_dict(self):
        """Test converting envelope to dictionary."""
        header = MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION
        )
        
        envelope = MessageEnvelope(
            header=header,
            payload={'test': 'data'}
        )
        
        data = envelope.to_dict()
        assert 'header' in data
        assert 'payload' in data
        assert data['payload']['test'] == 'data'
    
    def test_from_dict(self):
        """Test creating envelope from dictionary."""
        data = {
            'header': {
                'message_id': 'test-123',
                'correlation_id': 'corr-456',
                'actor_role': 'planner',
                'task_type': 'EXTRACTION',
                'priority': 5,
                'ttl_ms': 30000,
                'schema_version': 'v1.0',
                'enqueue_ts': datetime.utcnow().isoformat(),
                'retry_count': 0,
                'max_retries': 3
            },
            'payload': {'test': 'data'}
        }
        
        envelope = MessageEnvelope.from_dict(data)
        assert envelope.header.message_id == 'test-123'
        assert envelope.payload['test'] == 'data'
    
    def test_is_expired(self):
        """Test checking if message is expired."""
        header = MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION,
            ttl_ms=1000  # 1 second
        )
        header.enqueue_ts = datetime.utcnow() - timedelta(seconds=2)
        
        envelope = MessageEnvelope(header=header, payload={})
        
        assert envelope.is_expired() is True
    
    def test_can_retry(self):
        """Test checking if message can be retried."""
        header = MessageHeader(
            actor_role=ActorRole.PLANNER,
            task_type=TaskType.EXTRACTION,
            max_retries=3
        )
        
        envelope = MessageEnvelope(header=header, payload={})
        
        assert envelope.can_retry() is True
        
        envelope.header.retry_count = 3
        assert envelope.can_retry() is False


class TestWorkflowState:
    """Test WorkflowState model."""
    
    def test_create_workflow(self):
        """Test creating workflow state."""
        workflow = WorkflowState(correlation_id='test-123')
        
        assert workflow.workflow_id is not None
        assert workflow.correlation_id == 'test-123'
        assert workflow.status == TaskStatus.PENDING
        assert len(workflow.pending_tasks) == 0
    
    def test_add_pending_task(self):
        """Test adding pending task."""
        workflow = WorkflowState(correlation_id='test-123')
        workflow.add_pending_task('task-1')
        
        assert 'task-1' in workflow.pending_tasks
    
    def test_mark_completed(self):
        """Test marking task as completed."""
        workflow = WorkflowState(correlation_id='test-123')
        workflow.add_pending_task('task-1')
        
        result = TaskResult(
            task_id='task-1',
            status=TaskStatus.SUCCESS,
            output_data={'result': 'success'}
        )
        
        workflow.mark_completed('task-1', result)
        
        assert 'task-1' not in workflow.pending_tasks
        assert 'task-1' in workflow.completed_tasks
        assert 'task-1' in workflow.task_results
    
    def test_is_complete(self):
        """Test checking if workflow is complete."""
        workflow = WorkflowState(correlation_id='test-123')
        workflow.add_pending_task('task-1')
        
        assert workflow.is_complete() is False
        
        result = TaskResult(
            task_id='task-1',
            status=TaskStatus.SUCCESS,
            output_data={}
        )
        workflow.mark_completed('task-1', result)
        
        assert workflow.is_complete() is True


