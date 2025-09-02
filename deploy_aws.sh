#!/bin/bash

# GPT-5 Happy Hour Discovery System - AWS Lambda Deployment Script
# Deploys the orchestrator and all agents to AWS Lambda

set -e

echo "🚀 Deploying GPT-5 Happy Hour Discovery System to AWS Lambda"

# Configuration
REGION="us-east-1"
FUNCTION_PREFIX="happy-hour"
RUNTIME="python3.9"

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Not logged in to AWS. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI configured"

# Create deployment package for orchestrator
echo "📦 Creating orchestrator deployment package..."
mkdir -p lambda_deploy/orchestrator
cp lambda_orchestrator.py lambda_deploy/orchestrator/lambda_function.py
cp -r shared lambda_deploy/orchestrator/
cd lambda_deploy/orchestrator

# Install dependencies
pip3 install -t . supabase boto3 --quiet
cd ../..

# Create ZIP file
cd lambda_deploy/orchestrator
zip -r ../orchestrator.zip . -q
cd ../..

echo "✅ Orchestrator package created"

# Deploy or update orchestrator function
FUNCTION_NAME="${FUNCTION_PREFIX}-orchestrator"
echo "🔧 Deploying orchestrator function: $FUNCTION_NAME"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_deploy/orchestrator.zip \
        --region $REGION > /dev/null
else
    echo "   Creating new function..."
    # First create the role
    ROLE_ARN=$(aws iam create-role \
        --role-name ${FUNCTION_NAME}-role \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --query 'Role.Arn' \
        --output text 2>/dev/null || aws iam get-role --role-name ${FUNCTION_NAME}-role --query 'Role.Arn' --output text)
    
    # Attach policies
    aws iam attach-role-policy \
        --role-name ${FUNCTION_NAME}-role \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
    
    aws iam attach-role-policy \
        --role-name ${FUNCTION_NAME}-role \
        --policy-arn arn:aws:iam::aws:policy/AWSLambdaExecute 2>/dev/null || true
    
    # Wait for role to propagate
    sleep 10
    
    # Create function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://lambda_deploy/orchestrator.zip \
        --timeout 60 \
        --memory-size 512 \
        --region $REGION > /dev/null
fi

# Set environment variables
echo "   Setting environment variables..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "Variables={
        SUPABASE_URL='${SUPABASE_URL}',
        SUPABASE_SERVICE_KEY='${SUPABASE_SERVICE_KEY}',
        OPENAI_API_KEY='${OPENAI_API_KEY}',
        GOOGLE_PLACES_API_KEY='${GOOGLE_PLACES_API_KEY}'
    }" \
    --region $REGION > /dev/null

echo "✅ Orchestrator deployed"

# Create Lambda Function URL
echo "🌐 Creating Function URL for orchestrator..."
FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name $FUNCTION_NAME \
    --auth-type NONE \
    --cors '{
        "AllowOrigins": ["*"],
        "AllowMethods": ["GET", "POST", "OPTIONS"],
        "AllowHeaders": ["Content-Type"]
    }' \
    --region $REGION \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || \
    aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --query 'FunctionUrl' \
        --output text)

echo "✅ Function URL created: $FUNCTION_URL"

# Deploy agents
echo "📦 Deploying agents..."

for agent in site_agent google_agent yelp_agent voice_verify; do
    echo "   Deploying $agent..."
    
    # Create package
    mkdir -p lambda_deploy/$agent
    cp agents/${agent}/handler.py lambda_deploy/$agent/lambda_function.py 2>/dev/null || echo "     ⚠️  Agent not found, skipping"
    
    if [ -f lambda_deploy/$agent/lambda_function.py ]; then
        cp -r shared lambda_deploy/$agent/
        cd lambda_deploy/$agent
        pip3 install -t . openai supabase --quiet
        zip -r ../${agent}.zip . -q
        cd ../..
        
        # Deploy function
        AGENT_FUNCTION="${FUNCTION_PREFIX}-${agent//_/-}"
        
        if aws lambda get-function --function-name $AGENT_FUNCTION --region $REGION &> /dev/null; then
            aws lambda update-function-code \
                --function-name $AGENT_FUNCTION \
                --zip-file fileb://lambda_deploy/${agent}.zip \
                --region $REGION > /dev/null
        else
            # Create with same role as orchestrator
            aws lambda create-function \
                --function-name $AGENT_FUNCTION \
                --runtime $RUNTIME \
                --role $ROLE_ARN \
                --handler lambda_function.lambda_handler \
                --zip-file fileb://lambda_deploy/${agent}.zip \
                --timeout 30 \
                --memory-size 256 \
                --region $REGION > /dev/null
        fi
        
        # Set environment variables
        aws lambda update-function-configuration \
            --function-name $AGENT_FUNCTION \
            --environment "Variables={
                SUPABASE_URL='${SUPABASE_URL}',
                SUPABASE_SERVICE_KEY='${SUPABASE_SERVICE_KEY}',
                OPENAI_API_KEY='${OPENAI_API_KEY}',
                GOOGLE_PLACES_API_KEY='${GOOGLE_PLACES_API_KEY}'
            }" \
            --region $REGION > /dev/null
        
        echo "     ✅ $agent deployed"
    fi
done

# Clean up
rm -rf lambda_deploy

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📍 API Endpoint: $FUNCTION_URL"
echo ""
echo "Test with:"
echo "curl -X POST $FUNCTION_URL/api/analyze \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"name\": \"DUKES RESTAURANT\", \"address\": \"1216 PROSPECT ST, LA JOLLA, CA 92037\"}'"
echo ""
echo "Update your frontend to use this API endpoint."