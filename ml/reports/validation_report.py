"""
Validation Report

Report generator for data validation results.
"""

from ml.reports.base import BaseReport
from ml.validation.validators import ValidationCheck


class ValidationReport(BaseReport):
    """
    Report generator for validation results.

    Generates reports from validation check results showing
    pass/fail status, error details, and summary statistics.
    """

    def __init__(self):
        super().__init__(
            title="Data Validation Report", description="Results of data validation checks"
        )

    def collect_data(self, validation_results: list[ValidationCheck], **kwargs) -> None:
        """
        Collect validation data.

        Args:
            validation_results: List of ValidationCheck objects
        """
        # Summary statistics
        total_checks = len(validation_results)
        passed_checks = sum(1 for check in validation_results if check.passed)
        failed_checks = total_checks - passed_checks

        # Categorize by severity
        critical_failures = [
            check
            for check in validation_results
            if not check.passed and check.severity == "critical"
        ]
        error_failures = [
            check for check in validation_results if not check.passed and check.severity == "error"
        ]
        warnings = [
            check
            for check in validation_results
            if not check.passed and check.severity == "warning"
        ]

        self.data = {
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "critical_failures": len(critical_failures),
                "error_failures": len(error_failures),
                "warnings": len(warnings),
                "overall_status": "PASS" if failed_checks == 0 else "FAIL",
            },
            "checks": [check.to_dict() for check in validation_results],
            "critical_failures": [check.to_dict() for check in critical_failures],
            "error_failures": [check.to_dict() for check in error_failures],
            "warnings": [check.to_dict() for check in warnings],
        }

    def generate_html(self) -> str:
        """Generate HTML validation report"""
        html = self._generate_html_header()

        # Summary section
        summary = self.data["summary"]
        status_class = "status-success" if summary["overall_status"] == "PASS" else "status-error"

        html += f"""
        <div class="section">
            <h2>Summary</h2>
            <div class="metric">Total Checks: <strong>{summary['total_checks']}</strong></div>
            <div class="metric">Passed: <span class="status-success">{summary['passed_checks']}</span></div>
            <div class="metric">Failed: <span class="status-error">{summary['failed_checks']}</span></div>
            <div class="metric">Warnings: <span class="status-warning">{summary['warnings']}</span></div>
            <div class="metric">Overall Status: <span class="{status_class}">{summary['overall_status']}</span></div>
        </div>
        """

        # Critical failures
        if self.data["critical_failures"]:
            html += '<div class="section"><h2>Critical Failures</h2>\n'
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["critical_failures"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            html += self._format_table_html(headers, rows)
            html += "</div>\n"

        # Error failures
        if self.data["error_failures"]:
            html += '<div class="section"><h2>Errors</h2>\n'
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["error_failures"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            html += self._format_table_html(headers, rows)
            html += "</div>\n"

        # Warnings
        if self.data["warnings"]:
            html += '<div class="section"><h2>Warnings</h2>\n'
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["warnings"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            html += self._format_table_html(headers, rows)
            html += "</div>\n"

        # All checks
        html += '<div class="section"><h2>All Validation Checks</h2>\n'
        headers = ["Check Name", "Status", "Severity", "Message"]
        rows = []
        for check in self.data["checks"]:
            status_icon = "✅" if check["passed"] else "❌"
            status = f"{status_icon} {'PASS' if check['passed'] else 'FAIL'}"
            rows.append([check["name"], status, check["severity"].upper(), check["message"]])
        html += self._format_table_html(headers, rows)
        html += "</div>\n"

        html += self._generate_html_footer()
        return html

    def generate_markdown(self) -> str:
        """Generate Markdown validation report"""
        md = self._generate_markdown_header()

        # Summary
        summary = self.data["summary"]
        md += "## Summary\n\n"
        md += f"- **Total Checks:** {summary['total_checks']}\n"
        md += f"- **Passed:** {summary['passed_checks']}\n"
        md += f"- **Failed:** {summary['failed_checks']}\n"
        md += f"- **Warnings:** {summary['warnings']}\n"
        md += f"- **Overall Status:** **{summary['overall_status']}**\n\n"

        # Critical failures
        if self.data["critical_failures"]:
            md += "## Critical Failures\n\n"
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["critical_failures"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            md += self._format_table_markdown(headers, rows)

        # Error failures
        if self.data["error_failures"]:
            md += "## Errors\n\n"
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["error_failures"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            md += self._format_table_markdown(headers, rows)

        # Warnings
        if self.data["warnings"]:
            md += "## Warnings\n\n"
            headers = ["Check Name", "Message", "Details"]
            rows = []
            for check in self.data["warnings"]:
                details = ", ".join(f"{k}: {v}" for k, v in check.get("details", {}).items())
                rows.append([check["name"], check["message"], details or "N/A"])
            md += self._format_table_markdown(headers, rows)

        # All checks
        md += "## All Validation Checks\n\n"
        headers = ["Check Name", "Status", "Severity", "Message"]
        rows = []
        for check in self.data["checks"]:
            status_icon = "✅" if check["passed"] else "❌"
            status = f"{status_icon} {'PASS' if check['passed'] else 'FAIL'}"
            rows.append([check["name"], status, check["severity"].upper(), check["message"]])
        md += self._format_table_markdown(headers, rows)

        return md
