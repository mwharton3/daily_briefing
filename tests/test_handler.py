import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import json

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from handler import handler, send_email, send_error_notification


class TestHandler(unittest.TestCase):
    """Test cases for Lambda handler function."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
        os.environ["RECIPIENT_EMAIL"] = "recipient@example.com"
        os.environ["SENDER_EMAIL"] = "sender@example.com"

    def tearDown(self):
        """Clean up after tests."""
        for key in ["ANTHROPIC_API_KEY", "RECIPIENT_EMAIL", "SENDER_EMAIL"]:
            if key in os.environ:
                del os.environ[key]

    @patch('handler.send_email')
    @patch('handler.BriefingGenerator')
    def test_handler_success(self, mock_generator_class, mock_send_email):
        """Test successful handler execution."""
        # Mock briefing data
        mock_briefing_data = {
            "date": "January 13, 2026",
            "briefing": "Test briefing content",
            "timestamp": "2026-01-13T08:00:00",
            "model": "claude-opus-4-20250514"
        }

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_briefing.return_value = mock_briefing_data
        mock_generator_class.return_value = mock_generator

        # Mock email sending
        mock_send_email.return_value = {"success": True, "message_id": "test-123"}

        # Call handler
        result = handler({}, None)

        # Verify response
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["date"], "January 13, 2026")
        self.assertTrue(body["email_sent"])

        # Verify mocks were called
        mock_generator.generate_briefing.assert_called_once()
        mock_send_email.assert_called_once_with(mock_briefing_data)

    @patch('handler.send_error_notification')
    @patch('handler.BriefingGenerator')
    def test_handler_generation_failure(self, mock_generator_class, mock_send_error):
        """Test handler when briefing generation fails."""
        # Mock generator to raise exception
        mock_generator = Mock()
        mock_generator.generate_briefing.side_effect = Exception("Generation failed")
        mock_generator_class.return_value = mock_generator

        # Call handler
        result = handler({}, None)

        # Verify error response
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("Failed to generate daily briefing", body["message"])
        self.assertIn("Generation failed", body["error"])

        # Verify error notification was attempted
        mock_send_error.assert_called_once()

    @patch('handler.boto3.client')
    def test_send_email_success(self, mock_boto_client):
        """Test successful email sending."""
        # Mock SES client
        mock_ses = Mock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        briefing_data = {
            "date": "January 13, 2026",
            "briefing": "Test briefing",
            "timestamp": "2026-01-13T08:00:00",
            "model": "claude-opus-4-20250514"
        }

        result = send_email(briefing_data)

        self.assertTrue(result["success"])
        self.assertEqual(result["message_id"], "test-message-id")

        # Verify SES was called correctly
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        self.assertEqual(call_kwargs["Source"], "sender@example.com")
        self.assertEqual(call_kwargs["Destination"]["ToAddresses"][0], "recipient@example.com")
        self.assertIn("Daily Briefing", call_kwargs["Message"]["Subject"]["Data"])

    def test_send_email_missing_config(self):
        """Test send_email fails with missing configuration."""
        del os.environ["RECIPIENT_EMAIL"]

        briefing_data = {
            "date": "January 13, 2026",
            "briefing": "Test",
            "timestamp": "2026-01-13T08:00:00",
            "model": "claude-opus-4-20250514"
        }

        with self.assertRaises(ValueError) as context:
            send_email(briefing_data)

        self.assertIn("RECIPIENT_EMAIL", str(context.exception))

    @patch('handler.boto3.client')
    def test_send_error_notification(self, mock_boto_client):
        """Test error notification sending."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses

        send_error_notification("Test error message")

        # Verify SES was called
        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        self.assertIn("Failed", call_kwargs["Message"]["Subject"]["Data"])
        self.assertIn("Test error message", call_kwargs["Message"]["Body"]["Text"]["Data"])


if __name__ == '__main__':
    unittest.main()
