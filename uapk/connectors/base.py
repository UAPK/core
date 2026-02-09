"""
Base ToolConnector Class (M1.3)
Abstract base for all connector implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class ToolConnector(ABC):
    """
    Abstract base class for tool connectors.
    Connectors execute external tools with policy enforcement and SSRF protection.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration from manifest.

        Args:
            config: Connector configuration dict from manifest
        """
        self.config = config
        self.name = config.get('name', 'unnamed')
        self.connector_type = config.get('type', 'unknown')

        # Validate configuration
        self.validate_config()

    @abstractmethod
    def validate_config(self):
        """
        Validate connector configuration.
        Raise ValueError if configuration is invalid.
        """
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action with given parameters.

        Args:
            action: Action name/identifier
            params: Action parameters

        Returns:
            Result dict with 'success' (bool) and 'data' or 'error'
        """
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default"""
        return self.config.get(key, default)
