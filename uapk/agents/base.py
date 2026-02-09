"""
Base Agent Framework
All autonomous agents inherit from BaseAgent.
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from uapk.audit import audit_event
from uapk.policy import check_policy, PolicyResult


class BaseAgent(ABC):
    """Base class for all autonomous agents"""

    def __init__(self, agent_id: str, manifest: Any):
        self.agent_id = agent_id
        self.manifest = manifest

        # Find agent profile in manifest
        self.profile = None
        for profile in manifest.aiOsModules.agentProfiles:
            if profile.agentId == agent_id:
                self.profile = profile
                break

        if not self.profile:
            raise ValueError(f"Agent profile not found for {agent_id}")

    def check_tool_permission(self, tool: str) -> PolicyResult:
        """Check if agent is allowed to use a tool"""
        return check_policy(
            agent_id=self.agent_id,
            action=f"use_tool_{tool}",
            tool=tool
        )

    def audit(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        decision: Optional[str] = None
    ):
        """Log an audit event for this agent's action"""
        return audit_event(
            event_type="agent_action",
            action=action,
            params=params,
            result=result,
            decision=decision,
            agent_id=self.agent_id
        )

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic.
        Must be implemented by subclasses.
        """
        pass
