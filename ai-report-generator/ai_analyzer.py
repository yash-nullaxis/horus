"""
ai_analyzer.py — Vision AI client for analyzing dashboard screenshots.

Sends screenshots to Google Gemini with domain-specific prompts
and returns structured analysis text.
"""

import base64
import os
from pathlib import Path

from google import genai
from google.genai import types


class AIAnalyzer:
    """Sends dashboard screenshots to a vision model for analysis."""

    def __init__(self, model: str = "gemini-2.5-flash", system_prompt: str = ""):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set.\n"
                "Set it with: export GEMINI_API_KEY='your-key-here'\n"
                "Get a key from: https://aistudio.google.com/apikey"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        print(f"  AI Analyzer initialized (model: {model})")

    def analyze_screenshot(self, screenshot_path: str, prompt: str) -> str:
        """
        Send a screenshot to the vision model with a contextual prompt.

        Args:
            screenshot_path: Path to the PNG screenshot file.
            prompt: The analysis prompt describing what to focus on.

        Returns:
            The AI's analysis as a string.
        """
        image_bytes = Path(screenshot_path).read_bytes()

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        types.Part.from_text(text=prompt),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        return response.text.strip()

    def generate_executive_summary(self, all_analyses: list[dict], prompt: str) -> str:
        """
        Generate an executive summary from all individual chart analyses.

        Args:
            all_analyses: List of dicts with 'name' and 'analysis' keys.
            prompt: The executive summary prompt.

        Returns:
            The executive summary as a string.
        """
        # Build a combined context from all analyses
        context_parts = []
        for i, section in enumerate(all_analyses, 1):
            context_parts.append(f"### Section {i}: {section['name']}\n{section['analysis']}")

        combined_context = "\n\n---\n\n".join(context_parts)

        full_prompt = (
            f"Here are the individual chart-by-chart analyses from the dashboard walkthrough:\n\n"
            f"{combined_context}\n\n"
            f"---\n\n"
            f"{prompt}"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=full_prompt)],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.4,
                max_output_tokens=3000,
            ),
        )

        return response.text.strip()
