import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import sys
import tempfile

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from briefing_generator import BriefingGenerator


class TestBriefingGenerator(unittest.TestCase):
    """Test cases for BriefingGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["ANTHROPIC_API_KEY"] = "test-api-key"

        # Create a temporary prompt file for testing
        self.test_prompt = """Test prompt for {date}.

Please create a briefing.

---

This is a note that should be ignored."""

    def tearDown(self):
        """Clean up after tests."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_init_missing_api_key(self):
        """Test that initialization fails without API key."""
        del os.environ["ANTHROPIC_API_KEY"]

        with self.assertRaises(ValueError) as context:
            BriefingGenerator()

        self.assertIn("ANTHROPIC_API_KEY", str(context.exception))

    @patch('briefing_generator.anthropic.Anthropic')
    def test_init_with_api_key(self, mock_anthropic):
        """Test successful initialization with API key."""
        generator = BriefingGenerator()

        self.assertIsNotNone(generator.client)
        self.assertEqual(generator.model, "claude-opus-4-20250514")
        self.assertIsNotNone(generator.prompt_file)
        mock_anthropic.assert_called_once_with(api_key="test-api-key")

    @patch('briefing_generator.anthropic.Anthropic')
    def test_load_prompt_template(self, mock_anthropic):
        """Test loading prompt template from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.test_prompt)
            temp_file = f.name

        try:
            generator = BriefingGenerator(prompt_file=temp_file)
            template = generator.load_prompt_template()

            self.assertIn("Test prompt for {date}", template)
            self.assertIn("Please create a briefing.", template)
            # Check that content after --- is excluded
            self.assertNotIn("This is a note that should be ignored", template)
        finally:
            os.unlink(temp_file)

    @patch('briefing_generator.anthropic.Anthropic')
    def test_load_prompt_template_file_not_found(self, mock_anthropic):
        """Test loading prompt template when file doesn't exist."""
        generator = BriefingGenerator(prompt_file="/nonexistent/path.md")

        with self.assertRaises(FileNotFoundError) as context:
            generator.load_prompt_template()

        self.assertIn("Prompt template file not found", str(context.exception))

    @patch('briefing_generator.anthropic.Anthropic')
    def test_generate_briefing_success(self, mock_anthropic):
        """Test successful briefing generation."""
        # Create a temporary prompt file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.test_prompt)
            temp_file = f.name

        try:
            # Create mock response
            mock_text_block = Mock()
            mock_text_block.type = "text"
            mock_text_block.text = "This is your daily briefing content."

            mock_thinking_block = Mock()
            mock_thinking_block.type = "thinking"
            mock_thinking_block.thinking = "Deep thinking about the briefing..."

            mock_response = Mock()
            mock_response.content = [mock_thinking_block, mock_text_block]

            # Set up mock client
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            # Generate briefing
            generator = BriefingGenerator(prompt_file=temp_file)
            result = generator.generate_briefing()

            # Verify results
            self.assertIn("date", result)
            self.assertIn("briefing", result)
            self.assertIn("timestamp", result)
            self.assertIn("model", result)
            self.assertEqual(result["briefing"], "This is your daily briefing content.")
            self.assertEqual(result["model"], "claude-opus-4-20250514")
            self.assertIsNotNone(result["thinking_summary"])

            # Verify API was called correctly
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            self.assertEqual(call_kwargs["model"], "claude-opus-4-20250514")
            self.assertEqual(call_kwargs["max_tokens"], 16000)
            self.assertIn("thinking", call_kwargs)
            self.assertEqual(call_kwargs["thinking"]["type"], "enabled")
        finally:
            os.unlink(temp_file)

    @patch('briefing_generator.anthropic.Anthropic')
    def test_generate_briefing_api_error(self, mock_anthropic):
        """Test briefing generation handles API errors."""
        # Create a temporary prompt file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.test_prompt)
            temp_file = f.name

        try:
            # Set up mock to raise exception
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            generator = BriefingGenerator(prompt_file=temp_file)

            with self.assertRaises(Exception) as context:
                generator.generate_briefing()

            self.assertIn("Failed to generate briefing", str(context.exception))
        finally:
            os.unlink(temp_file)

    @patch('briefing_generator.anthropic.Anthropic')
    def test_generate_briefing_without_thinking(self, mock_anthropic):
        """Test briefing generation when no thinking block is returned."""
        # Create a temporary prompt file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.test_prompt)
            temp_file = f.name

        try:
            # Create mock response without thinking block
            mock_text_block = Mock()
            mock_text_block.type = "text"
            mock_text_block.text = "Briefing without thinking."

            mock_response = Mock()
            mock_response.content = [mock_text_block]

            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            generator = BriefingGenerator(prompt_file=temp_file)
            result = generator.generate_briefing()

            self.assertEqual(result["briefing"], "Briefing without thinking.")
            self.assertIsNone(result["thinking_summary"])
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
