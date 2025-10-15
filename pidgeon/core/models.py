"""Core message models for the Pidgeon Protocol."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Enumeration of task types."""
    EXTRACTION = "EXTRACTION"
    SUMMARIZATION = "SUMMARIZATION"
    ANALYSIS = "ANALYSIS"
    FACT_CHECK = "FACT_CHECK"
    CUSTOM = "CUSTOM"


class ActorRole(str, Enum):
    """Enumeration of actor roles in the system."""
    PLANNER = "planner"
    INTERPRETER = "interpreter"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    USER = "user"


class TaskStatus(str, Enum):
    """Enumeration of task execution statuses."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"
    TIMEOUT = "TIMEOUT"


class MessageHeader(BaseModel):
    """Header for all Pidgeon Protocol messages."""
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: Optional[str] = Field(default=None, description="MCP context identifier")
    
    actor_role: ActorRole
    task_type: TaskType
    
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10, 10 is highest")
    ttl_ms: int = Field(default=30000, description="Time-to-live in milliseconds")
    schema_version: str = Field(default="v1.0")
    
    enqueue_ts: datetime = Field(default_factory=datetime.utcnow)
    processing_ts: Optional[datetime] = None
    
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    
    class Config:
        use_enum_values = True


class MessageEnvelope(BaseModel):
    """Complete message envelope for Pidgeon Protocol."""
    
    header: MessageHeader
    payload: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = Field(default=None, description="Cryptographic signature for message integrity")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        """Create message from dictionary."""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has exceeded its TTL."""
        if self.header.enqueue_ts is None:
            return False
        
        elapsed_ms = (datetime.utcnow() - self.header.enqueue_ts).total_seconds() * 1000
        return elapsed_ms > self.header.ttl_ms
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.header.retry_count < self.header.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.header.retry_count += 1


class TaskDefinition(BaseModel):
    """Definition of a task to be executed by an agent."""
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    input_data: Dict[str, Any] = Field(default_factory=dict)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result of task execution by an agent."""
    
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    status: TaskStatus
    output_data: Dict[str, Any] = Field(default_factory=dict)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    
    processing_time_ms: Optional[float] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    agent_id: Optional[str] = None


class WorkflowState(BaseModel):
    """State of a workflow being orchestrated by the Planner."""
    
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    pending_tasks: list[str] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    
    task_results: Dict[str, TaskResult] = Field(default_factory=dict)
    final_result: Optional[Dict[str, Any]] = None
    
    def add_pending_task(self, task_id: str) -> None:
        """Add a task to pending list."""
        if task_id not in self.pending_tasks:
            self.pending_tasks.append(task_id)
            self.updated_at = datetime.utcnow()
    
    def mark_completed(self, task_id: str, result: TaskResult) -> None:
        """Mark a task as completed."""
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)
        self.task_results[task_id] = result
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, task_id: str, result: TaskResult) -> None:
        """Mark a task as failed."""
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)
        if task_id not in self.failed_tasks:
            self.failed_tasks.append(task_id)
        self.task_results[task_id] = result
        self.updated_at = datetime.utcnow()
    
    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        return len(self.pending_tasks) == 0
    
    def has_failures(self) -> bool:
        """Check if any tasks have failed."""
        return len(self.failed_tasks) > 0


