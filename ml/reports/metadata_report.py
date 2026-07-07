"""
Metadata Report

Report generator for dataset and pipeline metadata.
"""

from typing import Any

from ml.reports.base import BaseReport


class MetadataReport(BaseReport):
    """Report generator for metadata summaries"""

    def __init__(self):
        super().__init__(
            title="Metadata Summary Report",
            description="Overview of datasets and pipeline metadata",
        )

    def collect_data(self, metadata_summary: dict[str, Any], **kwargs) -> None:
        """Collect metadata summary"""
        self.data = metadata_summary

    def generate_html(self) -> str:
        """Generate HTML metadata report"""
        html = self._generate_html_header()
        html += '<div class="section"><h2>Metadata Overview</h2>\n'

        for key, value in self.data.items():
            html += f'<div class="metric">{key.replace("_", " ").title()}: <strong>{value}</strong></div>\n'

        html += "</div>\n"
        html += self._generate_html_footer()
        return html

    def generate_markdown(self) -> str:
        """Generate Markdown metadata report"""
        md = self._generate_markdown_header()
        md += "## Metadata Overview\n\n"

        for key, value in self.data.items():
            md += f"- **{key.replace('_', ' ').title()}:** {value}\n"

        return md + "\n"
