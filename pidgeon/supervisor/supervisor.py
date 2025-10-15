"""Supervisor for monitoring and policy enforcement."""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from pidgeon.core.config import Config
from pidgeon.core.queue_factory import QueueFactory

logger = logging.getLogger(__name__)


class QueueMetrics:
    """Metrics for a queue."""
    
    def __init__(self):
        self.depth = 0
        self.messages_processed = 0
        self.errors = 0
        self.last_check = datetime.utcnow()


class Supervisor:
    """Supervisor monitors queues and enforces reliability policies.
    
    The Supervisor:
    - Monitors all queue depths and message flows
    - Tracks message processing times
    - Enforces retry policies with exponential backoff
    - Detects anomalies (queue depth spikes, error rate increases)
    - Implements circuit breakers for system protection
    - Logs all events to audit trail
    """
    
    def __init__(
        self,
        config: Config,
        queue_factory: QueueFactory,
        supervisor_id: str = "supervisor-001"
    ):
        """Initialize Supervisor.
        
        Args:
            config: Configuration object
            queue_factory: Factory for creating queues
            supervisor_id: Unique identifier for this supervisor instance
        """
        self.config = config
        self.queue_factory = queue_factory
        self.supervisor_id = supervisor_id
        
        # Monitoring configuration
        self.monitoring_interval = config.get('supervisor.monitoring_interval_seconds', 5)
        self.anomaly_detection_enabled = config.get('supervisor.anomaly_detection_enabled', True)
        self.circuit_breaker_enabled = config.get('supervisor.circuit_breaker_enabled', True)
        self.circuit_breaker_threshold = config.get('supervisor.circuit_breaker_threshold', 5)
        self.circuit_breaker_timeout = config.get('supervisor.circuit_breaker_timeout_seconds', 60)
        
        # Metrics storage
        self.queue_metrics: Dict[str, QueueMetrics] = defaultdict(QueueMetrics)
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Queues to monitor
        self.monitored_queues: Dict[str, Any] = {}
        
        self._running = False
    
    async def start(self) -> None:
        """Start the supervisor service."""
        logger.info(f"Starting Supervisor: {self.supervisor_id}")
        
        # Create queues to monitor
        await self._initialize_monitored_queues()
        
        self._running = True
        
        # Start monitoring loop
        await self._monitoring_loop()
    
    async def stop(self) -> None:
        """Stop the supervisor service."""
        logger.info("Stopping Supervisor")
        self._running = False
        
        for queue in self.monitored_queues.values():
            await queue.close()
    
    async def _initialize_monitored_queues(self) -> None:
        """Initialize queues to monitor."""
        queue_names = [
            "input",
            "task",
            "result",
            "structured_task.extraction",
            "structured_task.summarization",
            "structured_task.analysis",
            "dead_letter"
        ]
        
        for queue_name in queue_names:
            try:
                queue = await self.queue_factory.create_queue(queue_name)
                self.monitored_queues[queue_name] = queue
                logger.info(f"Monitoring queue: {queue_name}")
            except Exception as e:
                logger.warning(f"Could not create queue {queue_name} for monitoring: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Starting monitoring loop")
        
        while self._running:
            try:
                # Collect metrics
                await self._collect_metrics()
                
                # Check for anomalies
                if self.anomaly_detection_enabled:
                    await self._detect_anomalies()
                
                # Check circuit breakers
                if self.circuit_breaker_enabled:
                    await self._check_circuit_breakers()
                
                # Log summary
                await self._log_metrics_summary()
                
                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _collect_metrics(self) -> None:
        """Collect metrics from all monitored queues."""
        for queue_name, queue in self.monitored_queues.items():
            try:
                depth = await queue.get_depth()
                
                metrics = self.queue_metrics[queue_name]
                metrics.depth = depth
                metrics.last_check = datetime.utcnow()
                
            except Exception as e:
                logger.warning(f"Error collecting metrics for {queue_name}: {e}")
    
    async def _detect_anomalies(self) -> None:
        """Detect anomalies in queue metrics."""
        for queue_name, metrics in self.queue_metrics.items():
            # Check for abnormal queue depth
            if metrics.depth > 1000:
                logger.warning(
                    f"ANOMALY: Queue {queue_name} has high depth: {metrics.depth}"
                )
                # Could trigger alerts here
            
            # Check for stale queues (no updates in long time)
            time_since_check = (datetime.utcnow() - metrics.last_check).total_seconds()
            if time_since_check > 60:
                logger.warning(
                    f"ANOMALY: Queue {queue_name} not checked in {time_since_check}s"
                )
    
    async def _check_circuit_breakers(self) -> None:
        """Check and update circuit breaker states."""
        current_time = datetime.utcnow()
        
        for queue_name, breaker_state in list(self.circuit_breakers.items()):
            if breaker_state['status'] == 'open':
                # Check if timeout has elapsed
                if current_time >= breaker_state['open_until']:
                    # Try to close circuit breaker
                    breaker_state['status'] = 'half_open'
                    logger.info(f"Circuit breaker for {queue_name} entering half-open state")
            
            elif breaker_state['status'] == 'half_open':
                # Monitor for success to fully close
                metrics = self.queue_metrics[queue_name]
                if metrics.errors == 0:
                    breaker_state['status'] = 'closed'
                    breaker_state['failure_count'] = 0
                    logger.info(f"Circuit breaker for {queue_name} closed")
    
    def record_failure(self, queue_name: str) -> None:
        """Record a failure for circuit breaker tracking.
        
        Args:
            queue_name: Name of the queue where failure occurred
        """
        if queue_name not in self.circuit_breakers:
            self.circuit_breakers[queue_name] = {
                'status': 'closed',
                'failure_count': 0,
                'open_until': None
            }
        
        breaker = self.circuit_breakers[queue_name]
        breaker['failure_count'] += 1
        
        # Check if threshold exceeded
        if breaker['failure_count'] >= self.circuit_breaker_threshold:
            if breaker['status'] == 'closed':
                # Open circuit breaker
                breaker['status'] = 'open'
                breaker['open_until'] = datetime.utcnow() + timedelta(
                    seconds=self.circuit_breaker_timeout
                )
                logger.warning(
                    f"Circuit breaker OPENED for {queue_name} "
                    f"(failures: {breaker['failure_count']})"
                )
    
    def is_circuit_open(self, queue_name: str) -> bool:
        """Check if circuit breaker is open for a queue.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            True if circuit is open, False otherwise
        """
        if queue_name not in self.circuit_breakers:
            return False
        
        return self.circuit_breakers[queue_name]['status'] == 'open'
    
    async def _log_metrics_summary(self) -> None:
        """Log summary of current metrics."""
        summary_lines = ["=== Queue Metrics Summary ==="]
        
        for queue_name, metrics in self.queue_metrics.items():
            summary_lines.append(
                f"  {queue_name}: depth={metrics.depth}, "
                f"processed={metrics.messages_processed}, "
                f"errors={metrics.errors}"
            )
        
        logger.info("\n".join(summary_lines))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot.
        
        Returns:
            Dictionary of metrics by queue name
        """
        return {
            queue_name: {
                'depth': metrics.depth,
                'messages_processed': metrics.messages_processed,
                'errors': metrics.errors,
                'last_check': metrics.last_check.isoformat()
            }
            for queue_name, metrics in self.queue_metrics.items()
        }


