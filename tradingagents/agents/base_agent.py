"""
Base agent abstract class for all trading agents.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Abstract base class for all trading agents."""
    
    def __init__(self, name: str, model: Optional[str] = None):
        self.name = name
        self.model = model
        self.logger = logging.getLogger(f"agent.{name}")
        
    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return agent output.
        
        Args:
            input_data: Dictionary containing input data for the agent
            
        Returns:
            Dictionary containing agent analysis/decision
        """
        pass
        
    def _log_input(self, input_data: Dict[str, Any]):
        """Log input data for debugging."""
        self.logger.debug(f"Input data: {json.dumps(input_data, indent=2)}")
        
    def _log_output(self, output_data: Dict[str, Any]):
        """Log output data for debugging."""
        self.logger.debug(f"Output data: {json.dumps(output_data, indent=2)}")
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with input validation and logging.
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Agent output with metadata
        """
        start_time = datetime.now()
        
        try:
            self._log_input(input_data)
            
            # Execute agent logic
            result = await self.run(input_data)
            
            # Add metadata
            output = {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "input": input_data,
                "output": result
            }
            
            self._log_output(output)
            return output
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            return {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "error": str(e),
                "input": input_data,
                "output": None
            } 