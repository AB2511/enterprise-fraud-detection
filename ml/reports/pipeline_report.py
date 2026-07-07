"""
Pipeline Report

Report generator for pipeline execution results.
"""

from typing import Any

from ml.reports.base import BaseReport


class PipelineReport(BaseReport):
    """Report generator for pipeline results"""

    def __init__(self):
        super().__init__(
            title="Pipeline Execution Report", description="Results of pipeline execution"
        )

    def collect_data(self, pipeline_summary: dict[str, Any], **kwargs) -> None:
        """Collect pipeline execution data"""
        self.data = pipeline_summary

    def generate_html(self) -> str:
        """Generate HTML pipeline report"""
        html = self._generate_html_header()
        html += f"""
        <div class="section">
            <h2>Pipeline Summary</h2>
            <div class="metric">Status: <span class="status-{'success' if self.data.get('status') == 'success' else 'error'}">{self.data.get('status', 'unknown').upper()}</span></div>
            <div class="metric">Total Stages: <strong>{self.data.get('total_stages', 0)}</strong></div>
            <div class="metric">Completed: <strong>{self.data.get('completed_stages', 0)}</strong></div>
            <div class="metric">Failed: <strong>{self.data.get('failed_stages', 0)}</strong></div>
            <div class="metric">Duration: <strong>{self.data.get('duration_seconds', 0):.1f}s</strong></div>
        </div>
        """
        html += self._generate_html_footer()
        return html

    def generate_markdown(self) -> str:
        """Generate Markdown pipeline report"""
        md = self._generate_markdown_header()
        md += "## Pipeline Summary\n\n"
        md += f"- **Status:** {self.data.get('status', 'unknown').upper()}\n"
        md += f"- **Total Stages:** {self.data.get('total_stages', 0)}\n"
        md += f"- **Completed:** {self.data.get('completed_stages', 0)}\n"
        md += f"- **Failed:** {self.data.get('failed_stages', 0)}\n"
        md += f"- **Duration:** {self.data.get('duration_seconds', 0):.1f}s\n\n"
        return md
