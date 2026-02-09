"""
Workflow Engine
Executes multi-step workflows defined in the manifest.
"""
from typing import Dict, Any, List
import asyncio

from uapk.manifest_schema import WorkflowDefinition
from uapk.audit import audit_event


class WorkflowEngine:
    """Execute workflows as defined in manifest"""

    def __init__(self, manifest: Any, agents: Dict[str, Any]):
        self.manifest = manifest
        self.agents = agents  # Map of agent_id -> agent instance
        self.workflows = {wf.workflowId: wf for wf in manifest.aiOsModules.workflows}

    async def execute_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a workflow by ID.

        Args:
            workflow_id: ID of workflow to execute
            context: Initial context for workflow

        Returns:
            Final context after all steps
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self.workflows[workflow_id]

        audit_event(
            event_type="workflow",
            action=f"start_workflow_{workflow_id}",
            params={"workflow_id": workflow_id, "context": context}
        )

        result_context = context.copy()

        # Execute steps sequentially
        for i, step in enumerate(workflow.steps):
            action = step.get("action")
            agent_id = step.get("agent")
            gated = step.get("gated", False)

            audit_event(
                event_type="workflow",
                action=f"workflow_step_{action}",
                params={"workflow_id": workflow_id, "step": i, "agent": agent_id}
            )

            # Check if this step is gated (requires approval)
            if gated:
                # In production, create HITL request and wait
                # For now, skip gated steps in dry_run
                if self.manifest.executionMode == "dry_run":
                    audit_event(
                        event_type="workflow",
                        action=f"workflow_step_gated_{action}",
                        params={"workflow_id": workflow_id, "step": i},
                        decision="SKIP"
                    )
                    continue

            # Execute agent action
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                try:
                    step_result = await agent.execute(result_context)
                    result_context.update(step_result)
                except Exception as e:
                    audit_event(
                        event_type="workflow",
                        action=f"workflow_step_failed_{action}",
                        params={"workflow_id": workflow_id, "step": i, "error": str(e)},
                        decision="FAIL"
                    )

                    # Handle escalation policy
                    if workflow.escalationPolicy:
                        # In production, trigger escalation
                        pass

                    raise

        audit_event(
            event_type="workflow",
            action=f"complete_workflow_{workflow_id}",
            params={"workflow_id": workflow_id},
            result=result_context
        )

        return result_context


async def run_workflow(
    workflow_id: str,
    context: Dict[str, Any],
    manifest: Any,
    agents: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function to run a workflow"""
    engine = WorkflowEngine(manifest, agents)
    return await engine.execute_workflow(workflow_id, context)
