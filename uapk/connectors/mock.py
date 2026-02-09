"""
MockConnector (M1.3)
Mock connector for testing without external dependencies.
"""
from typing import Dict, Any
from uapk.connectors.base import ToolConnector


class MockConnector(ToolConnector):
    """
    Mock connector that returns deterministic responses.
    Used for testing and development.
    """

    def validate_config(self):
        """Mock connector has no required config"""
        pass

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute mock action (returns deterministic response).

        Args:
            action: Action identifier
            params: Parameters

        Returns:
            Mocked success response
        """
        # Return deterministic mock response
        response_template = self.config.get('response_template', {})

        if response_template:
            # Use configured template
            return {
                'success': True,
                'data': response_template,
                'mock': True
            }

        # Default mock response
        return {
            'success': True,
            'data': {
                'action': action,
                'params': params,
                'result': 'mock_success',
                'message': f'Mock connector executed action: {action}'
            },
            'mock': True
        }
