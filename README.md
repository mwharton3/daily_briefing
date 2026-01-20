# Daily Briefing Generator

An AWS Lambda function that generates personalized daily briefings using Claude Sonnet 4.5 with extended thinking and emails them automatically.

Note that you can do the same exact thing in a no-code interface with ChatGPT Tasks, however, I wanted to both learn by creating and have a bit more control. If you're looking for a simple way to achieve virtually the same goal, I'd recommend using Tasks instead.

## Features

- **AI-Powered Briefings**: Uses Claude Sonnet 4.5 with extended thinking for deep, thoughtful daily insights
- **Automated Scheduling**: Runs automatically every day at 5 AM CT via AWS EventBridge
- **Email Delivery**: Sends beautifully formatted HTML emails via AWS SES
- **Infrastructure as Code**: Complete AWS infrastructure defined using AWS CDK
- **Comprehensive Testing**: Unit tests with mocking for local development
- **Easy Deployment**: Simple shell scripts for deployment and manual triggers

## Prompt adjustment
If you'd like to use for your own use case, fork this repository, change the prompt in `lambda/prompt.md`, and then follow the below instructions.

If you want the same prompt as-is, you can still clone a copy and just use your own AWS credentials/etc.

## Architecture

```
┌─────────────────┐
│  EventBridge    │  ← Daily schedule (8 AM UTC)
│  (Cron Rule)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │
│  Function       │  ← Generates briefing
│                 │
└────────┬────────┘
         │
         ├──► Anthropic API (Claude Opus 4.5)
         │
         └──► AWS SES (Email delivery)
```

## Project Structure

```
daily_briefing/
├── lambda/                      # Lambda function code
│   ├── handler.py              # Main Lambda handler
│   ├── briefing_generator.py  # Briefing generation logic
│   └── prompt.md              # Customizable prompt template
├── infrastructure/             # AWS CDK infrastructure
│   ├── app.py                 # CDK app entry point
│   └── stack.py               # Stack definition
├── tests/                     # Test suite
│   ├── test_handler.py        # Handler tests
│   └── test_briefing_generator.py  # Generator tests
├── bin/                       # Deployment scripts
│   ├── deploy.sh             # Deploy/update infrastructure
│   └── trigger.sh            # Manual trigger for testing
├── pyproject.toml           # Project dependencies (uv)
├── cdk.json                 # CDK configuration
└── .env.example             # Environment variables template
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Python 3.12+** installed
4. **uv** package manager installed (see https://github.com/astral-sh/uv)
5. **Node.js 18+** (for AWS CDK CLI)
6. **Anthropic API Key** (get one at https://console.anthropic.com/)

## Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository (or navigate to it)
cd daily_briefing

# Install uv if not already installed
# On macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or via pip: pip install uv

# Install Python dependencies
uv pip install -e .

# Install AWS CDK CLI (if not already installed)
npm install -g aws-cdk
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Required variables:
#   ANTHROPIC_API_KEY - Your Anthropic API key
#   RECIPIENT_EMAIL - Email address to receive briefings
#   SENDER_EMAIL - Verified sender email in AWS SES
```

### 3. Verify Sender Email in AWS SES

Before deploying, you need to verify your sender email in AWS SES (see below). Note that I created a new alias using my email provider (`noreply@mydomain.com`), which I was able to authenticate and use even in SES sandbox mode. YMMV.

```bash
# Verify your sender email
aws ses verify-email-identity --email-address your-email@example.com

# Check verification status
aws ses get-identity-verification-attributes \
  --identities your-email@example.com
```

Check your email and click the verification link sent by AWS.

**Note**: By default, SES starts in sandbox mode, which only allows sending to verified addresses. To send to any email, request production access in the AWS SES console.

### 4. Configure AWS Credentials

```bash
# Authenticate your AWS account using web browser
aws login

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

## Deployment

Deploy the infrastructure to AWS:

```bash
./bin/deploy.sh
```

This script will:
1. Load environment variables from `.env`
2. Validate AWS credentials
3. Check SES email verification status
4. Install Lambda dependencies
5. Bootstrap CDK (if needed)
6. Deploy the CDK stack to AWS

The deployment creates:
- Lambda function with the briefing code
- EventBridge rule for daily scheduling (8 AM UTC)
- IAM roles and permissions
- CloudWatch log group

## Usage

### Automatic Daily Execution

Once deployed, the Lambda function runs automatically every day at 8 AM UTC. You'll receive the daily briefing via email at the configured recipient address.

To change the schedule, edit the cron expression in `infrastructure/stack.py`:

```python
schedule=events.Schedule.cron(
    minute="0",
    hour="8",  # Change this to your preferred hour (UTC)
    month="*",
    week_day="*",
    year="*"
)
```

Then redeploy with `./bin/deploy.sh`.

### Manual Trigger

To trigger a one-off execution for testing:

```bash
./bin/trigger.sh
```

This will:
1. Find your deployed Lambda function
2. Invoke it manually
3. Display the response
4. Confirm if the email was sent successfully

### Customizing the Briefing Content

The daily briefing prompt is defined in `lambda/prompt.md`, making it easy to customize without touching code.

**To customize your briefing:**

1. Edit `lambda/prompt.md` with your preferred content and style
2. Use `{date}` as a placeholder for the current date
3. Add any instructions or sections you want Claude to include
4. Redeploy with `./bin/deploy.sh`

**Example customizations:**

```markdown
# For a business-focused briefing:
Today is {date}. Create a daily briefing for a tech executive that includes:

1. Leadership insight or quote
2. Three key priorities for today
3. Market trends to be aware of
4. Team motivation tip
5. Evening reflection question
```

```markdown
# For personal growth:
Today is {date}. Create a mindful daily briefing that includes:

1. Morning meditation prompt
2. Gratitude practice (3 things)
3. Personal development focus area
4. Wellness reminder
5. Evening journaling prompt
```

```markdown
# For creative work:
Today is {date}. Create an inspiring briefing for creative work that includes:

1. Creative quote or insight
2. Today's creative challenge
3. Technique to explore
4. Inspiration sources
5. Reflection on creative process
```

**Note**: Content after the `---` separator in `prompt.md` is ignored, allowing you to keep notes and documentation in the same file.

## Testing

Run the test suite locally:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lambda --cov-report=html

# Run specific test file
pytest tests/test_handler.py

# Run with verbose output
pytest -v
```

The tests use mocking to avoid making real API calls or AWS operations, so they can run completely locally without any credentials.

## Monitoring

### View Lambda Logs

```bash
# Get the function name
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name DailyBriefingStack \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
  --output text)

# Tail the logs
aws logs tail /aws/lambda/$FUNCTION_NAME --follow
```

### Check Recent Invocations

```bash
# List recent invocations
aws lambda list-invocations \
  --function-name $FUNCTION_NAME \
  --max-items 10
```

### CloudWatch Metrics

View metrics in the AWS Console:
1. Navigate to CloudWatch → Metrics
2. Select Lambda → By Function Name
3. View invocations, errors, duration, etc.

## Costs

Estimated monthly costs (assuming daily execution):

- **Lambda**: ~$0.20/month (30 executions × 2 seconds × $0.0000166667/GB-second)
- **EventBridge**: Free (within limits)
- **CloudWatch Logs**: ~$0.50/month (for 1 GB retention)
- **SES**: $0 for first 62,000 emails/month (then $0.10/1000 emails)
- **Anthropic API**: Varies by usage (~$0.15 per briefing with extended thinking)

**Total**: ~$5-10/month depending on Claude API usage

## Troubleshooting

### Email Not Received

1. Check SES verification status: `aws ses get-identity-verification-attributes --identities your-email@example.com`
2. Check if SES is in sandbox mode (restricts recipient addresses)
3. Check spam folder
4. View Lambda logs for errors

### Lambda Function Fails

1. Check CloudWatch logs: `aws logs tail /aws/lambda/$FUNCTION_NAME`
2. Verify environment variables are set correctly
3. Verify Anthropic API key is valid
4. Check IAM permissions

### Deployment Fails

1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check CDK bootstrap: `cdk bootstrap`
3. Verify all environment variables in `.env`
4. Check Python dependencies are installed

### Tests Fail

1. Ensure test dependencies are installed: `uv pip install -e ".[dev]"`
2. Run with verbose output: `pytest -v`
3. Check that the lambda directory is in Python path

## Cleanup

To remove all AWS resources:

```bash
cd infrastructure
cdk destroy
```

This will delete:
- Lambda function
- EventBridge rule
- IAM roles
- CloudWatch log group

## Customization Ideas

- **Multiple Recipients**: Modify `send_email()` to send to a list of addresses
- **Different Models**: Change the model in `briefing_generator.py` to use different Claude versions
- **Custom Schedules**: Modify the cron expression for different frequencies
- **Personalization**: Add user-specific context or preferences to the prompt
- **Multiple Briefing Types**: Create different briefings for weekdays vs weekends
- **Attachments**: Add PDF generation for printable briefings
- **Notification Methods**: Add SMS via SNS or Slack webhooks

## Security Considerations

- API keys are stored as Lambda environment variables (consider using AWS Secrets Manager for production)
- Lambda has minimal IAM permissions (only SES send email)
- CloudWatch logs are retained for 1 week
- SES sender verification prevents unauthorized email sending
- All infrastructure is defined as code for audit and review

## License

See LICENSE file.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues or questions:
- Check the troubleshooting section above
- Review AWS Lambda and SES documentation
- Check Anthropic API documentation at https://docs.anthropic.com/

## Acknowledgments

- Built with [AWS CDK](https://aws.amazon.com/cdk/)
- Powered by [Anthropic's Claude](https://www.anthropic.com/)
- Email delivery via [Amazon SES](https://aws.amazon.com/ses/)
