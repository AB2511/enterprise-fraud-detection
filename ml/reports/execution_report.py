"""
Execution Report

Report generator for execution summaries.
"""

from typing import Any

from ml.reports.base import BaseReport


class ExecutionReport(BaseReport):
    """Report generator for execution summaries"""

    def __init__(self):
        super().__init__(
            title="Execution Summary Report",
            description="Summary of execution results and performance",
        )

    def collect_data(self, execution_data: dict[str, Any], **kwargs) -> None:
        """Collect execution data"""
        self.data = execution_data

    def generate_html(self) -> str:
        """Generate HTML execution report"""
        html = self._generate_html_header()
        html += '<div class="section"><h2>Execution Summary</h2>\n'

        for key, value in self.data.items():
            formatted_key = key.replace("_", " ").title()
            html += f'<div class="metric">{formatted_key}: <strong>{value}</strong></div>\n'

        html += "</div>\n"
        html += self._generate_html_footer()
        return html

    def generate_markdown(self) -> str:
        """Generate Markdown execution report"""
        md = self._generate_markdown_header()
        md += "## Execution Summary\n\n"

        for key, value in self.data.items():
            formatted_key = key.replace("_", " ").title()
            md += f"- **{formatted_key}:** {value}\n"

        return md + "\n"
