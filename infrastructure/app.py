#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stack import DailyBriefingStack


app = cdk.App()

DailyBriefingStack(
    app,
    "DailyBriefingStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
    ),
    description="Daily briefing generator using Claude API and AWS Lambda"
)

app.synth()
