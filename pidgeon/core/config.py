"""Configuration loader for Pidgeon Protocol."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for Pidgeon Protocol."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files. Defaults to ./config
        """
        # Load environment variables
        load_dotenv()
        
        self.config_dir = config_dir or Path("config")
        self._settings: Dict[str, Any] = {}
        self._agent_routing: Dict[str, Any] = {}
        
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load configuration files."""
        settings_path = self.config_dir / "settings.yaml"
        routing_path = self.config_dir / "agent_routing.yaml"
        
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                self._settings = yaml.safe_load(f)
                self._substitute_env_vars(self._settings)
        
        if routing_path.exists():
            with open(routing_path, 'r') as f:
                self._agent_routing = yaml.safe_load(f)
    
    def _substitute_env_vars(self, config: Any) -> None:
        """Recursively substitute environment variables in config."""
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    config[key] = os.getenv(env_var, "")
                elif isinstance(value, (dict, list)):
                    self._substitute_env_vars(value)
        elif isinstance(config, list):
            for item in config:
                self._substitute_env_vars(item)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'queue.redis.host')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self._settings
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_routing_config(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Get routing configuration for a task type.
        
        Args:
            task_type: Task type (e.g., 'EXTRACTION')
            
        Returns:
            Routing configuration dictionary
        """
        return self._agent_routing.get('task_types', {}).get(task_type)
    
    def get_queue_name(self, queue_type: str) -> str:
        """Get queue name from configuration.
        
        Args:
            queue_type: Queue type (input, task, result, dlq)
            
        Returns:
            Queue name
        """
        return self._agent_routing.get('queues', {}).get(queue_type, queue_type)
    
    @property
    def queue_backend(self) -> str:
        """Get configured queue backend."""
        return self.get('queue.backend', 'memory')
    
    @property
    def state_backend(self) -> str:
        """Get configured state backend."""
        return self.get('state.backend', 'redis')
    
    @property
    def llm_default_provider(self) -> str:
        """Get default LLM provider."""
        return self.get('llm.default_provider', 'openai')


