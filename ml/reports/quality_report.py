"""
Quality Report

Report generator for data quality analysis.
"""

from typing import Any

from ml.reports.base import BaseReport


class QualityReport(BaseReport):
    """Report generator for data quality metrics"""

    def __init__(self):
        super().__init__(
            title="Data Quality Report", description="Data quality metrics and analysis"
        )

    def collect_data(self, quality_metrics: dict[str, Any], **kwargs) -> None:
        """Collect quality metrics"""
        self.data = quality_metrics

    def generate_html(self) -> str:
        """Generate HTML quality report"""
        html = self._generate_html_header()
        html += '<div class="section"><h2>Quality Metrics</h2>\n'

        if "missing_values" in self.data:
            html += "<h3>Missing Values</h3>\n"
            headers = ["Column", "Missing Count", "Missing Rate"]
            rows = [
                [col, str(count), f"{rate:.2%}"] for col, count, rate in self.data["missing_values"]
            ]
            html += self._format_table_html(headers, rows)

        html += "</div>\n"
        html += self._generate_html_footer()
        return html

    def generate_markdown(self) -> str:
        """Generate Markdown quality report"""
        md = self._generate_markdown_header()
        md += "## Quality Metrics\n\n"

        if "missing_values" in self.data:
            md += "### Missing Values\n\n"
            headers = ["Column", "Missing Count", "Missing Rate"]
            rows = [
                [col, str(count), f"{rate:.2%}"] for col, count, rate in self.data["missing_values"]
            ]
            md += self._format_table_markdown(headers, rows)

        return md
