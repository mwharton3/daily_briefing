import os
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import anthropic


class BriefingGenerator:
    """Generates daily briefings using Claude API with extended thinking."""

    def __init__(self, prompt_file: str = None):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"

        # Set default prompt file location
        if prompt_file is None:
            prompt_file = os.path.join(os.path.dirname(__file__), "prompt.md")
        self.prompt_file = prompt_file

    def load_prompt_template(self) -> str:
        """
        Load the prompt template from the markdown file.

        Returns:
            String containing the prompt template
        """
        try:
            with open(self.prompt_file, 'r') as f:
                content = f.read()

            # Extract only the content before the --- separator (if it exists)
            # This allows users to add notes/instructions after the separator
            if '---' in content:
                content = content.split('---')[0]

            return content.strip()
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Prompt template file not found at {self.prompt_file}. "
                "Please ensure prompt.md exists in the lambda directory."
            )
        except Exception as e:
            raise Exception(f"Failed to load prompt template: {str(e)}")

    def generate_briefing(self) -> Dict[str, Any]:
        """
        Generate a daily briefing using Claude with extended thinking.

        Returns:
            Dict containing the briefing content and metadata
        """
        today = datetime.now().strftime("%B %d, %Y")

        # Load and format the prompt template
        prompt_template = self.load_prompt_template()
        prompt = prompt_template.format(date=today)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000
                },
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract the text content (skip thinking blocks)
            briefing_content = ""
            thinking_content = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    briefing_content += block.text

            return {
                "date": today,
                "briefing": briefing_content,
                "thinking_summary": thinking_content[:500] if thinking_content else None,
                "model": self.model,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            raise Exception(f"Failed to generate briefing: {str(e)}")
