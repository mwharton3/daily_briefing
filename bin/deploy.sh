#!/bin/bash

# Deploy or update Daily Briefing AWS infrastructure
# This script deploys the CDK stack to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Daily Briefing Deployment Script${NC}"
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file with the required variables."
    echo "See .env.example for reference."
    exit 1
fi

# Load environment variables
echo -e "${YELLOW}Loading environment variables...${NC}"
export $(cat .env | grep -v '^#' | xargs)

# Verify required environment variables
required_vars=("ANTHROPIC_API_KEY" "RECIPIENT_EMAIL" "SENDER_EMAIL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set${NC}"
        echo "Please set $var in your .env file"
        exit 1
    fi
done

echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo -e "${RED}Error: AWS CDK CLI is not installed${NC}"
    echo "Please install it with: npm install -g aws-cdk"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials are not configured${NC}"
    echo "Please configure AWS CLI with: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS credentials verified${NC}"

# Check if SES email is verified
echo -e "${YELLOW}Checking SES email verification...${NC}"
SENDER_VERIFIED=$(aws ses get-identity-verification-attributes --identities "$SENDER_EMAIL" --query "VerificationAttributes.\"$SENDER_EMAIL\".VerificationStatus" --output text 2>/dev/null || echo "NotFound")

if [ "$SENDER_VERIFIED" != "Success" ]; then
    echo -e "${YELLOW}Warning: Sender email ($SENDER_EMAIL) is not verified in SES${NC}"
    echo "Please verify your email address in AWS SES before sending emails."
    echo "You can verify it with: aws ses verify-email-identity --email-address $SENDER_EMAIL"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install Python dependencies for Lambda
echo -e "${YELLOW}Installing Lambda dependencies...${NC}"
# Install only runtime dependencies (not dev dependencies) to lambda directory
# Use pip with --platform to get Linux x86_64 binaries compatible with Lambda
pip install anthropic boto3 markdown --target lambda/ --upgrade \
    --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all:

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Bootstrap CDK (only needed once per account/region)
echo -e "${YELLOW}Bootstrapping CDK (if needed)...${NC}"
cdk bootstrap 2>&1 | grep -v "already bootstrapped" || true

# Synthesize CDK stack
echo -e "${YELLOW}Synthesizing CDK stack...${NC}"
cdk synth

echo -e "${GREEN}✓ CDK stack synthesized${NC}"

# Deploy CDK stack
echo -e "${YELLOW}Deploying CDK stack...${NC}"
cdk deploy --require-approval never

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Verify your sender email in AWS SES (if not already done)"
echo "2. Test the function with: ./bin/trigger.sh"
echo "3. The function will run automatically every day at 5 AM CT"
