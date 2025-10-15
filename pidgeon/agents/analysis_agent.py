"""Analysis agent for data analysis and insight generation."""

import asyncio
import logging
from typing import Dict, Any

from pidgeon.agents.base_agent import BaseAgent
from pidgeon.core.models import TaskType
from pidgeon.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for analyzing data and generating insights."""
    
    def __init__(self, agent_id: str, config, queue_factory, llm_gateway: LLMGateway):
        """Initialize analysis agent.
        
        Args:
            agent_id: Unique agent identifier
            config: Configuration object
            queue_factory: Queue factory
            llm_gateway: LLM gateway for analysis
        """
        super().__init__(agent_id, TaskType.ANALYSIS, config, queue_factory)
        self.llm = llm_gateway
    
    async def process_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis task.
        
        Args:
            task_payload: Task data containing data to analyze
            
        Returns:
            Dictionary with analysis results
        """
        input_data = task_payload.get('input_data', {})
        data_to_analyze = input_data.get('data', '')
        analysis_type = input_data.get('analysis_type', 'general')
        
        logger.info(f"Analyzing data (type: {analysis_type})")
        
        # Use LLM for analysis
        system_prompt = """You are a data analyst. Provide clear, actionable insights 
from the data. Focus on patterns, trends, and recommendations.

At the end of your analysis, on a new line, add: CONFIDENCE: [0.0-1.0]
where you rate your confidence in the analysis based on data quality and completeness."""
        
        prompt = f"Analyze the following data and provide insights:\n\n{data_to_analyze}"
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.6,
                max_tokens=800
            )
            
            analysis = response.content
            
            # Extract confidence score if provided by LLM
            confidence_score = 0.75  # Default
            if 'CONFIDENCE:' in analysis:
                try:
                    confidence_line = [line for line in analysis.split('\n') if 'CONFIDENCE:' in line][0]
                    confidence_score = float(confidence_line.split('CONFIDENCE:')[1].strip())
                    # Remove confidence line from analysis
                    analysis = '\n'.join([line for line in analysis.split('\n') if 'CONFIDENCE:' not in line]).strip()
                except (ValueError, IndexError):
                    pass
            
            # Calculate confidence based on response quality if not provided
            if confidence_score == 0.75:
                # Base confidence on response length and data provided
                response_quality = min(len(analysis) / 500, 1.0)  # Longer = more detailed
                data_quality = min(len(data_to_analyze) / 1000, 1.0)  # More data = higher confidence
                confidence_score = round((response_quality * 0.6 + data_quality * 0.4), 2)
                confidence_score = max(0.5, min(0.95, confidence_score))  # Clamp between 0.5 and 0.95
            
            return {
                'analysis': analysis,
                'analysis_type': analysis_type,
                'model': response.model,
                'tokens_used': response.tokens_used,
                'confidence_score': confidence_score
            }
            
        except Exception as e:
            logger.error(f"Error generating analysis: {e}")
            
            # Fallback simple analysis
            return {
                'analysis': f"Analysis of {analysis_type} data. [Fallback mode due to error]",
                'analysis_type': analysis_type,
                'method': 'fallback',
                'error': str(e),
                'confidence_score': 0.5
            }


