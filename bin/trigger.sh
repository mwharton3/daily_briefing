#!/bin/bash

# Trigger a one-off execution of the Daily Briefing Lambda function
# This script invokes the Lambda function manually for testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Daily Briefing Manual Trigger${NC}"
echo "======================================"

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials are not configured${NC}"
    echo "Please configure AWS CLI with: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS credentials verified${NC}"

# Get the Lambda function name from CDK outputs
echo -e "${YELLOW}Finding Lambda function...${NC}"

FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name DailyBriefingStack \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$FUNCTION_NAME" ]; then
    echo -e "${RED}Error: Could not find Lambda function${NC}"
    echo "Make sure the stack is deployed with: ./bin/deploy.sh"
    exit 1
fi

echo -e "${GREEN}✓ Found function: $FUNCTION_NAME${NC}"

# Invoke the Lambda function
echo -e "${YELLOW}Invoking Lambda function...${NC}"
echo ""

aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload '{}' \
    --cli-binary-format raw-in-base64-out \
    --cli-read-timeout 900 \
    /tmp/lambda-response.json

echo ""
echo -e "${YELLOW}Lambda Response:${NC}"
cat /tmp/lambda-response.json | python3 -m json.tool
echo ""

# Check if invocation was successful
STATUS_CODE=$(cat /tmp/lambda-response.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('statusCode', 0))")

if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Daily briefing generated and sent successfully!${NC}"
    echo "Check your email at the configured recipient address."
else
    echo -e "${RED}✗ Daily briefing generation failed${NC}"
    echo "Check the Lambda logs for more details:"
    echo "aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
fi

# Clean up
rm -f /tmp/lambda-response.json
