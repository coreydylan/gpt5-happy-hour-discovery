#!/bin/bash

# GPT-5 Happy Hour Discovery - AWS Lambda Deployment
set -e

echo "🚀 Deploying GPT-5 Happy Hour Discovery to AWS Lambda"
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Create deployment directory
echo -e "${BLUE}📦 Creating deployment package...${NC}"
rm -rf lambda_deploy
mkdir -p lambda_deploy

# Install dependencies
python3 -m pip install -r lambda_requirements.txt -t lambda_deploy/

# Copy function code
cp lambda_function.py lambda_deploy/

# Create deployment zip
cd lambda_deploy
zip -r ../gpt5-happy-hour-lambda.zip .
cd ..

echo -e "${GREEN}✅ Deployment package created${NC}"

# Create/update Lambda function
FUNCTION_NAME="gpt5-happy-hour-discovery"
REGION="us-east-1"

echo -e "${BLUE}🚀 Deploying to AWS Lambda...${NC}"

# Try to update existing function first
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo -e "${YELLOW}Updating existing function...${NC}"
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://gpt5-happy-hour-lambda.zip \
        --region $REGION
else
    echo -e "${YELLOW}Creating new function...${NC}"
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://gpt5-happy-hour-lambda.zip \
        --timeout 30 \
        --region $REGION
fi

# Set environment variable for OpenAI API key
echo -e "${YELLOW}Setting environment variables...${NC}"
# You'll need to set your actual API key here
OPENAI_KEY="YOUR_OPENAI_API_KEY_HERE"
echo "Using placeholder API key - you'll need to update this in AWS console"

aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "Variables={OPENAI_API_KEY=$OPENAI_KEY}" \
    --region $REGION

# Create API Gateway
echo -e "${BLUE}🌐 Setting up API Gateway...${NC}"

API_NAME="gpt5-happy-hour-api"

# Check if API Gateway exists
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='$API_NAME'].id" --output text)

if [ "$API_ID" = "" ]; then
    echo -e "${YELLOW}Creating new API Gateway...${NC}"
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "GPT-5 Happy Hour Discovery API" \
        --region $REGION \
        --query 'id' --output text)
fi

echo -e "${GREEN}✅ API Gateway ID: $API_ID${NC}"

# Get the root resource ID
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[?path==`/`].id' --output text)

# Create API resources and methods (simplified for demo)
echo -e "${YELLOW}Configuring API Gateway resources...${NC}"

# This is a simplified setup - full API Gateway configuration would be more complex
# For now, we'll use the function URL feature which is simpler

# Enable function URL
echo -e "${BLUE}🔗 Creating Function URL...${NC}"
FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name $FUNCTION_NAME \
    --cors 'AllowCredentials=false,AllowHeaders=*,AllowMethods=*,AllowOrigins=*' \
    --auth-type NONE \
    --region $REGION \
    --query 'FunctionUrl' --output text 2>/dev/null || \
    aws lambda get-function-url-config \
    --function-name $FUNCTION_NAME \
    --region $REGION \
    --query 'FunctionUrl' --output text)

# Clean up
rm -rf lambda_deploy
rm gpt5-happy-hour-lambda.zip

echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
echo "==============================="
echo -e "${BLUE}Function URL:${NC} $FUNCTION_URL"
echo -e "${BLUE}Region:${NC} $REGION"
echo ""
echo -e "${YELLOW}🧪 Test your endpoints:${NC}"
echo "1. Health: curl $FUNCTION_URL"
echo "2. Search: curl '${FUNCTION_URL}api/restaurants/search?query=DUKES'"
echo "3. Analyze: curl -X POST $FUNCTION_URL/api/analyze -H 'Content-Type: application/json' -d '{\"restaurant_name\":\"DUKES\"}'"
echo ""
echo -e "${GREEN}✨ Your GPT-5 system is now running on AWS Lambda!${NC}"