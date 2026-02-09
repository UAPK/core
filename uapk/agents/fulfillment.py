"""
Fulfillment Agent
Generates deliverable content using RAG and prompt templates.
"""
from typing import Dict, Any
from pathlib import Path
import random

from uapk.agents.base import BaseAgent
from uapk.cas import ContentAddressedStore


class FulfillmentAgent(BaseAgent):
    """Generates deliverables using KB context and templates"""

    def __init__(self, agent_id: str, manifest: Any):
        super().__init__(agent_id, manifest)
        self.cas = ContentAddressedStore()

    async def retrieve_kb_context(self, project_id: int, query: str) -> str:
        """
        Retrieve relevant KB context for the query.
        In a real implementation, this would use vector search.
        For now, we'll use a simple stub.
        """
        # Stub: return sample context
        return f"[KB Context for project {project_id}]\n\nThis is sample knowledge base content that would be retrieved via RAG."

    def generate_content(
        self,
        template: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate content using template and context.
        In production, this would call an LLM.
        For deterministic testing, we use a template fill.
        """
        # Fill template with context
        try:
            content = template.format(**context)
        except KeyError:
            # Fallback: simple concatenation
            content = f"# {context.get('title', 'Deliverable')}\n\n"
            content += f"{template}\n\n"
            content += f"KB Context:\n{context.get('kb_context', 'N/A')}\n\n"
            content += f"Request: {context.get('request_details', 'N/A')}\n"

        return content

    def export_to_pdf(self, markdown_content: str, output_path: str) -> str:
        """
        Export markdown to PDF.
        For simplicity, we'll create a minimal text file that represents a PDF.
        In production, use reportlab or markdown-to-pdf library.
        """
        # Simplified: write markdown to file (in production, convert to actual PDF)
        pdf_content = f"""% Generated Deliverable PDF
% OpsPilotOS

{markdown_content}
"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(pdf_content)

        return output_path

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fulfillment pipeline:
        1. Retrieve KB context
        2. Generate content from template
        3. Export to markdown
        4. Export to PDF
        5. Store artifacts in CAS
        """
        deliverable_id = context.get("deliverable_id")
        project_id = context.get("project_id")
        title = context.get("title", "Untitled Deliverable")
        request_details = context.get("request_details", "")

        self.audit("start_fulfillment", params={"deliverable_id": deliverable_id})

        # Step 1: Retrieve KB context
        kb_query = context.get("kb_query", title)
        kb_context = await self.retrieve_kb_context(project_id, kb_query)

        # Step 2: Generate content
        template = self.manifest.aiOsModules.promptTemplates.get(
            "generate_deliverable",
            "# {title}\n\n{request_details}\n\nKB Context:\n{kb_context}"
        )

        content_context = {
            "project_name": context.get("project_name", "Project"),
            "title": title,
            "request_details": request_details,
            "kb_context": kb_context
        }

        markdown_content = self.generate_content(template, content_context)

        # Step 3: Store markdown in CAS
        md_hash = self.cas.put_str(markdown_content)

        # Step 4: Export to PDF
        pdf_path = f"artifacts/deliverables/{deliverable_id}.pdf"
        self.export_to_pdf(markdown_content, pdf_path)

        # Step 5: Store PDF in CAS
        pdf_content = Path(pdf_path).read_bytes()
        pdf_hash = self.cas.put(pdf_content)

        result = {
            "deliverable_id": deliverable_id,
            "markdown_hash": md_hash,
            "pdf_hash": pdf_hash,
            "pdf_path": pdf_path,
            "status": "completed"
        }

        self.audit("complete_fulfillment", params={"deliverable_id": deliverable_id}, result=result)

        return result
