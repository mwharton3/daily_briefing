import os
import json
import boto3
import markdown
from typing import Dict, Any
from briefing_generator import BriefingGenerator


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for daily briefing generation.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response dictionary with status and details
    """
    print(f"Starting daily briefing generation")
    print(f"Event: {json.dumps(event)}")

    try:
        # Generate the briefing
        generator = BriefingGenerator()
        briefing_data = generator.generate_briefing()

        print(f"Briefing generated successfully for {briefing_data['date']}")

        # Send email with the briefing
        email_result = send_email(briefing_data)

        print(f"Email sent successfully: {email_result}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Daily briefing generated and sent successfully",
                "date": briefing_data["date"],
                "email_sent": email_result["success"]
            })
        }

    except Exception as e:
        error_msg = f"Error generating daily briefing: {str(e)}"
        print(error_msg)

        # Try to send error notification
        try:
            send_error_notification(error_msg)
        except Exception as email_error:
            print(f"Failed to send error notification: {str(email_error)}")

        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Failed to generate daily briefing",
                "error": str(e)
            })
        }


def send_email(briefing_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    Send the daily briefing via AWS SES.

    Args:
        briefing_data: Dictionary containing briefing content and metadata

    Returns:
        Dictionary with success status
    """
    ses_client = boto3.client('ses')

    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    sender_email = os.environ.get("SENDER_EMAIL")

    if not recipient_email or not sender_email:
        raise ValueError("RECIPIENT_EMAIL and SENDER_EMAIL environment variables are required")

    subject = f"Daily Briefing - {briefing_data['date']}"

    # Convert markdown to HTML
    briefing_html = markdown.markdown(
        briefing_data['briefing'],
        extensions=['tables', 'fenced_code', 'nl2br']
    )

    # Create HTML email body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .content h1, .content h2, .content h3 {{
                color: #444;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }}
            .content h1:first-child, .content h2:first-child, .content h3:first-child {{
                margin-top: 0;
            }}
            .content ul, .content ol {{
                margin: 1em 0;
                padding-left: 2em;
            }}
            .content li {{
                margin: 0.5em 0;
            }}
            .content p {{
                margin: 1em 0;
            }}
            .content code {{
                background: #e8e8e8;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }}
            .content pre {{
                background: #e8e8e8;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            .content blockquote {{
                border-left: 4px solid #667eea;
                margin: 1em 0;
                padding-left: 1em;
                color: #666;
            }}
            .content table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            .content th, .content td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            .content th {{
                background: #f0f0f0;
            }}
            .footer {{
                margin-top: 20px;
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Your Daily Briefing</h1>
            <p>{briefing_data['date']}</p>
        </div>
        <div class="content">
            {briefing_html}
        </div>
        <div class="footer">
            <p>Generated by Claude {briefing_data['model']}</p>
            <p>Timestamp: {briefing_data['timestamp']}</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_body = f"""
Daily Briefing - {briefing_data['date']}

{briefing_data['briefing']}

---
Generated by Claude {briefing_data['model']}
Timestamp: {briefing_data['timestamp']}
    """

    response = ses_client.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': [recipient_email]
        },
        Message={
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                },
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                }
            }
        }
    )

    return {
        "success": True,
        "message_id": response['MessageId']
    }


def send_error_notification(error_msg: str) -> None:
    """Send an error notification email."""
    ses_client = boto3.client('ses')

    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    sender_email = os.environ.get("SENDER_EMAIL")

    if not recipient_email or not sender_email:
        return

    ses_client.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': [recipient_email]
        },
        Message={
            'Subject': {
                'Data': 'Daily Briefing Generation Failed',
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': f"Failed to generate daily briefing:\n\n{error_msg}",
                    'Charset': 'UTF-8'
                }
            }
        }
    )
