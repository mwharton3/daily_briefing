from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct
import os


class DailyBriefingStack(Stack):
    """CDK Stack for Daily Briefing Lambda function."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get configuration from environment variables
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        recipient_email = os.environ.get("RECIPIENT_EMAIL")
        sender_email = os.environ.get("SENDER_EMAIL")

        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        if not recipient_email:
            raise ValueError("RECIPIENT_EMAIL environment variable is required")
        if not sender_email:
            raise ValueError("SENDER_EMAIL environment variable is required")

        # Create Lambda function
        briefing_lambda = lambda_.Function(
            self,
            "DailyBriefingFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                "ANTHROPIC_API_KEY": anthropic_api_key,
                "RECIPIENT_EMAIL": recipient_email,
                "SENDER_EMAIL": sender_email,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Generates and emails daily briefings using Claude API",
        )

        # Grant SES permissions to Lambda
        briefing_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"],
            )
        )

        # Create EventBridge rule to trigger daily at 5 AM Central time (11 AM UTC)
        # Note: During daylight saving time (CDT), this will be 6 AM local time
        rule = events.Rule(
            self,
            "DailyBriefingSchedule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="11",  # 11 AM UTC = 5 AM CST (6 AM CDT)
                month="*",
                week_day="*",
                year="*"
            ),
            description="Triggers daily briefing generation every day at 5 AM Central time",
        )

        # Add Lambda as target
        rule.add_target(targets.LambdaFunction(briefing_lambda))

        # Output the Lambda function name for easy invocation
        CfnOutput(
            self,
            "LambdaFunctionName",
            value=briefing_lambda.function_name,
            description="Name of the daily briefing Lambda function",
        )

        CfnOutput(
            self,
            "LambdaFunctionArn",
            value=briefing_lambda.function_arn,
            description="ARN of the daily briefing Lambda function",
        )
