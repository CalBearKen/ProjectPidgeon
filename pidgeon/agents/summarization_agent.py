"""Summarization agent for text summarization using LLM."""

import logging
from typing import Dict, Any

from pidgeon.agents.base_agent import BaseAgent
from pidgeon.core.models import TaskType
from pidgeon.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class SummarizationAgent(BaseAgent):
    """Agent for summarizing text content using LLM."""
    
    def __init__(self, agent_id: str, config, queue_factory, llm_gateway: LLMGateway):
        """Initialize summarization agent.
        
        Args:
            agent_id: Unique agent identifier
            config: Configuration object
            queue_factory: Queue factory
            llm_gateway: LLM gateway for text generation
        """
        super().__init__(agent_id, TaskType.SUMMARIZATION, config, queue_factory)
        self.llm = llm_gateway
    
    async def process_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process summarization task.
        
        Args:
            task_payload: Task data containing text to summarize
            
        Returns:
            Dictionary with summary
        """
        input_data = task_payload.get('input_data', {})
        text_to_summarize = input_data.get('text', '')
        
        if not text_to_summarize:
            # Check if there's extracted_text from a previous step
            text_to_summarize = input_data.get('extracted_text', '')
        
        logger.info(f"Summarizing text ({len(text_to_summarize)} chars)")
        
        # Use LLM to generate summary
        system_prompt = "You are a concise summarization assistant. Provide clear, accurate summaries."
        prompt = f"Summarize the following text:\n\n{text_to_summarize}"
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.5,
                max_tokens=500
            )
            
            summary = response.content
            
            return {
                'summary': summary,
                'original_length': len(text_to_summarize),
                'summary_length': len(summary),
                'compression_ratio': len(summary) / len(text_to_summarize) if text_to_summarize else 0,
                'model': response.model,
                'tokens_used': response.tokens_used
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback to simple truncation
            summary = text_to_summarize[:500] + "..." if len(text_to_summarize) > 500 else text_to_summarize
            
            return {
                'summary': summary,
                'original_length': len(text_to_summarize),
                'summary_length': len(summary),
                'method': 'fallback_truncation',
                'error': str(e)
            }


