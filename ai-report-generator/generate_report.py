#!/usr/bin/env python3
"""
generate_report.py — AI-Powered Dashboard Walkthrough Report Generator

Navigates through a dashboard following a YAML-defined user journey,
captures screenshots at each step, sends them to a vision AI model,
and generates a sequential narrative report.

Usage:
    python generate_report.py                              # defaults: journey.yaml, headed mode
    python generate_report.py --journey custom.yaml        # custom journey file
    python generate_report.py --headless                   # run without visible browser
    python generate_report.py --model gemini-2.5-pro       # use a different model

Environment:
    GEMINI_API_KEY    — required, your Google AI Studio API key
"""

import argparse
import os
import sys
import time

import yaml
from dotenv import load_dotenv

from browser_driver import BrowserDriver
from ai_analyzer import AIAnalyzer
from report_builder import ReportBuilder


def load_journey(filepath: str) -> dict:
    """Load and parse the journey YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="AI-Powered Dashboard Walkthrough Report Generator"
    )
    parser.add_argument(
        "--journey", default="journey.yaml",
        help="Path to the journey YAML file (default: journey.yaml)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (no visible window)"
    )
    parser.add_argument(
        "--model", default=None,
        help="Override the vision AI model (e.g. gemini-2.5-pro)"
    )
    parser.add_argument(
        "--output", default="reports",
        help="Output directory for generated reports (default: reports)"
    )
    parser.add_argument(
        "--screenshots", default="screenshots",
        help="Directory for captured screenshots (default: screenshots)"
    )
    args = parser.parse_args()

    # Load environment variables (.env file in project root)
    load_dotenv()

    # ── Load Journey ──────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║      AI Dashboard Walkthrough Report Generator              ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    journey = load_journey(args.journey)
    title = journey.get("title", "Dashboard Analysis Report")
    app_url = journey["app_url"]
    steps = journey["steps"]
    ai_config = journey.get("ai", {})

    model_name = args.model or ai_config.get("model", "gemini-2.5-flash")
    system_prompt = ai_config.get("system_prompt", "")

    print(f"  Journey:    {args.journey}")
    print(f"  App URL:    {app_url}")
    print(f"  Steps:      {len(steps)}")
    print(f"  AI Model:   {model_name}")
    print(f"  Output:     {args.output}/")
    print()

    # ── Initialize Components ─────────────────────────────────────────
    print("─── Initializing ───────────────────────────────────────────────")
    browser = BrowserDriver(headless=args.headless)
    analyzer = AIAnalyzer(model=model_name, system_prompt=system_prompt)
    report = ReportBuilder(title=title, output_dir=args.output)

    # ── Launch Browser & Login ────────────────────────────────────────
    print("\n─── Browser Setup ──────────────────────────────────────────────")
    browser.launch()
    browser.navigate(app_url)

    if "login" in journey:
        browser.login(journey["login"])

    # ── Execute Journey Steps ─────────────────────────────────────────
    print("\n─── Running Journey ────────────────────────────────────────────")
    all_analyses = []

    for i, step in enumerate(steps, 1):
        step_name = step["name"]
        actions = step.get("actions", [])
        capture_mode = step.get("capture", "full_page")
        prompt = step.get("prompt", "Describe what you see in this dashboard screenshot.")

        print(f"\n  ┌─ Step {i}/{len(steps)}: {step_name}")
        print(f"  │")

        # Execute navigation actions
        if actions:
            browser.execute_actions(actions)

        # Capture screenshot
        screenshot_filename = f"step_{i:02d}_{_slugify(step_name)}.png"
        screenshot_path = os.path.join(args.screenshots, screenshot_filename)
        browser.capture_screenshot(screenshot_path, mode=capture_mode)

        # Send to AI for analysis
        print(f"  │  🤖 Analyzing with {model_name}...")
        try:
            analysis = analyzer.analyze_screenshot(screenshot_path, prompt)
            print(f"  │  ✅ Analysis complete ({len(analysis)} chars)")
        except Exception as e:
            analysis = f"*Analysis failed: {e}*"
            print(f"  │  ❌ Analysis failed: {e}")

        # Add to report
        report.add_section(
            name=step_name,
            screenshot_path=screenshot_path,
            analysis=analysis,
            step_index=i,
        )

        all_analyses.append({"name": step_name, "analysis": analysis})
        print(f"  └─ Done")

    # ── Executive Summary ─────────────────────────────────────────────
    exec_config = journey.get("executive_summary", {})
    if exec_config.get("enabled", False):
        print("\n─── Generating Executive Summary ───────────────────────────────")
        print("  🤖 Synthesizing all analyses...")
        try:
            exec_prompt = exec_config.get("prompt", "Write an executive summary.")
            summary = analyzer.generate_executive_summary(all_analyses, exec_prompt)
            report.set_executive_summary(summary)
            print(f"  ✅ Executive summary generated ({len(summary)} chars)")
        except Exception as e:
            print(f"  ❌ Executive summary failed: {e}")

    # ── Generate Report ───────────────────────────────────────────────
    print("\n─── Generating Report ──────────────────────────────────────────")
    report_path = report.build()

    # ── Cleanup ───────────────────────────────────────────────────────
    print("\n─── Cleanup ────────────────────────────────────────────────────")
    browser.close()

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║  ✅ Report generated: {report_path:<38} ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")


def _slugify(text: str) -> str:
    """Convert a section name to a safe filename slug."""
    return (
        text.lower()
        .replace(" ", "_")
        .replace("—", "_")
        .replace(":", "")
        .replace("&", "and")
        .replace("/", "_")
        .strip("_")
    )


if __name__ == "__main__":
    main()
