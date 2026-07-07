"""
Base Report

Abstract base class for report generators with common interface.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ReportFormat(str, Enum):
    """Report output formats"""

    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


class BaseReport(ABC):
    """
    Abstract base class for report generators.

    All report generators must inherit from this class and implement
    the generate methods for each supported format.
    """

    def __init__(self, title: str, description: str | None = None):
        """
        Initialize report generator.

        Args:
            title: Report title
            description: Report description
        """
        self.title = title
        self.description = description or f"Report: {title}"
        self.generated_at = datetime.utcnow()
        self.data: dict[str, Any] = {}

    @abstractmethod
    def collect_data(self, **kwargs) -> None:
        """
        Collect data for report generation.

        Args:
            **kwargs: Report-specific parameters
        """
        pass

    @abstractmethod
    def generate_html(self) -> str:
        """
        Generate HTML report.

        Returns:
            HTML content as string
        """
        pass

    @abstractmethod
    def generate_markdown(self) -> str:
        """
        Generate Markdown report.

        Returns:
            Markdown content as string
        """
        pass

    def generate_json(self) -> str:
        """
        Generate JSON report.

        Returns:
            JSON content as string
        """
        report_data = {
            "title": self.title,
            "description": self.description,
            "generated_at": self.generated_at.isoformat() + "Z",
            "data": self.data,
        }

        return json.dumps(report_data, indent=2, default=str)

    def generate(self, format: ReportFormat, **kwargs) -> str:
        """
        Generate report in specified format.

        Args:
            format: Report format
            **kwargs: Report-specific parameters

        Returns:
            Report content as string
        """
        # Collect data first
        self.collect_data(**kwargs)

        # Generate in requested format
        if format == ReportFormat.HTML:
            return self.generate_html()
        elif format == ReportFormat.MARKDOWN:
            return self.generate_markdown()
        elif format == ReportFormat.JSON:
            return self.generate_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save(self, output_path: Path, format: ReportFormat, **kwargs) -> Path:
        """
        Generate and save report to file.

        Args:
            output_path: Output file path (extension added automatically)
            format: Report format
            **kwargs: Report-specific parameters

        Returns:
            Path to saved file
        """
        content = self.generate(format, **kwargs)

        # Add appropriate extension
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix(f".{format.value}")

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _generate_html_header(self) -> str:
        """Generate common HTML header"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .meta {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .status-success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .status-warning {{
            color: #f39c12;
            font-weight: bold;
        }}
        .status-error {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .metric {{
            display: inline-block;
            background: #ecf0f1;
            padding: 8px 12px;
            margin: 4px;
            border-radius: 4px;
        }}
        .code {{
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        .section {{
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{self.title}</h1>
        <div class="meta">
            <strong>Description:</strong> {self.description}<br>
            <strong>Generated:</strong> {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
"""

    def _generate_html_footer(self) -> str:
        """Generate common HTML footer"""
        return """
    </div>
</body>
</html>"""

    def _generate_markdown_header(self) -> str:
        """Generate common Markdown header"""
        return f"""# {self.title}

**Description:** {self.description}  
**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

"""

    def _format_table_html(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str | None = None,
    ) -> str:
        """Format table as HTML"""
        html = ""
        if title:
            html += f"<h3>{title}</h3>\n"

        html += "<table>\n"
        html += "<thead><tr>\n"
        for header in headers:
            html += f"  <th>{header}</th>\n"
        html += "</tr></thead>\n<tbody>\n"

        for row in rows:
            html += "<tr>\n"
            for cell in row:
                html += f"  <td>{cell}</td>\n"
            html += "</tr>\n"

        html += "</tbody>\n</table>\n"
        return html

    def _format_table_markdown(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str | None = None,
    ) -> str:
        """Format table as Markdown"""
        md = ""
        if title:
            md += f"### {title}\n\n"

        # Headers
        md += "| " + " | ".join(headers) + " |\n"
        md += "|" + "|".join(["---"] * len(headers)) + "|\n"

        # Rows
        for row in rows:
            md += "| " + " | ".join(str(cell) for cell in row) + " |\n"

        md += "\n"
        return md
