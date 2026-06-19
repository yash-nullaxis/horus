"""
report_builder.py — Generates a sequential Markdown report from journey analyses.

Produces a timestamped Markdown document with embedded screenshots
and AI-generated analysis for each dashboard section.
"""

import os
from datetime import datetime


class ReportBuilder:
    """Builds a sequential Markdown report from dashboard walkthrough results."""

    def __init__(self, title: str, output_dir: str = "reports"):
        self.title = title
        self.output_dir = output_dir
        self.timestamp = datetime.now()
        self.sections: list[dict] = []
        self.executive_summary: str | None = None

        os.makedirs(output_dir, exist_ok=True)

    def add_section(self, name: str, screenshot_path: str, analysis: str, step_index: int):
        """Add a completed analysis section to the report."""
        self.sections.append({
            "index": step_index,
            "name": name,
            "screenshot": screenshot_path,
            "analysis": analysis,
        })

    def set_executive_summary(self, summary: str):
        """Set the executive summary content."""
        self.executive_summary = summary

    def build(self) -> str:
        """Generate the full Markdown report and write it to disk. Returns the file path."""
        date_str = self.timestamp.strftime("%Y-%m-%d")
        time_str = self.timestamp.strftime("%H:%M:%S")
        filename = f"report_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(self.output_dir, filename)

        lines = []

        # ── Header ────────────────────────────────────────────────────
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(f"**Generated:** {date_str} at {time_str}  ")
        lines.append(f"**Sections:** {len(self.sections)}  ")
        lines.append(f"**Mode:** AI-Powered Dashboard Walkthrough  ")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Table of Contents ─────────────────────────────────────────
        lines.append("## Table of Contents")
        lines.append("")
        if self.executive_summary:
            lines.append("- [Executive Summary](#executive-summary)")
        for section in self.sections:
            anchor = self._to_anchor(section["name"])
            lines.append(f"- [{section['index']}. {section['name']}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Executive Summary (if enabled) ────────────────────────────
        if self.executive_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(self.executive_summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        # ── Sections ──────────────────────────────────────────────────
        for section in self.sections:
            lines.append(f"## {section['index']}. {section['name']}")
            lines.append("")

            # Embed screenshot with relative path
            rel_screenshot = os.path.relpath(section["screenshot"], self.output_dir)
            lines.append(f"![{section['name']}]({rel_screenshot})")
            lines.append("")

            # AI Analysis
            lines.append("### Analysis")
            lines.append("")
            lines.append(section["analysis"])
            lines.append("")
            lines.append("---")
            lines.append("")

        # ── Footer ────────────────────────────────────────────────────
        lines.append("---")
        lines.append(f"*Report generated automatically by AI Report Generator on {date_str}.*")

        # Write to file
        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"\n  📄 Report saved: {filepath}")
        return filepath

    @staticmethod
    def _to_anchor(text: str) -> str:
        """Convert a section name to a Markdown anchor ID."""
        return text.lower().replace(" ", "-").replace("—", "").replace(":", "").replace("&", "").strip("-")
