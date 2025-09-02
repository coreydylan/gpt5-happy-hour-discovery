#!/bin/bash

# Master Deployment Script for Happy Hour Discovery System
# GPT-5 Powered Multi-Source Verification

set -e

echo "🚀 Happy Hour Discovery System - Master Deployment"
echo "=================================================="
echo "GPT-5 Powered | Voice Verification | Multi-Source Consensus"
echo ""

# Check for required environment variables
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists aws; then
    echo "❌ AWS CLI not found. Please install: brew install awscli"
    exit 1
fi

if ! command_exists vercel; then
    echo "❌ Vercel CLI not found. Please install: npm i -g vercel"
    exit 1
fi

if ! command_exists docker; then
    echo "❌ Docker not found. Please install Docker Desktop"
    exit 1
fi

echo "✅ All prerequisites met"
echo ""

# Step 1: Deploy Database Schema
echo "📊 Step 1: Setting up Supabase database..."
echo "Please ensure you've created a Supabase project and have the credentials in .env"
echo "Run the schema in Supabase SQL editor: database/supabase-schema.sql"
read -p "Press enter when database is ready..."
echo ""

# Step 2: Deploy Lambda Functions
echo "⚡ Step 2: Deploying AWS Lambda functions..."
cd aws

if [ "$1" == "production" ]; then
    ./deploy.sh
    echo "✅ Lambda functions deployed to AWS"
else
    echo "Skipping Lambda deployment (run with 'production' flag to deploy)"
fi

cd ..
echo ""

# Step 3: Deploy Orchestrator
echo "🧠 Step 3: Deploying FastAPI Orchestrator..."
cd orchestrator

if [ "$1" == "production" ]; then
    # Deploy to AWS ECS or EC2
    ./deploy.sh aws
    ORCHESTRATOR_URL=$(aws ecs describe-services --cluster happy-hour --services orchestrator --query 'services[0].loadBalancers[0].dnsName' --output text)
    echo "✅ Orchestrator deployed to: https://$ORCHESTRATOR_URL"
else
    # Run locally for development
    echo "Starting orchestrator locally..."
    ./deploy.sh local &
    ORCHESTRATOR_PID=$!
    ORCHESTRATOR_URL="http://localhost:8000"
    echo "✅ Orchestrator running at: $ORCHESTRATOR_URL"
fi

cd ..
echo ""

# Step 4: Deploy Frontend
echo "🎨 Step 4: Deploying Next.js Frontend..."
cd frontend

# Install dependencies
npm install

if [ "$1" == "production" ]; then
    # Set environment variables for Vercel
    vercel env add NEXT_PUBLIC_API_URL production < <(echo "$ORCHESTRATOR_URL")
    vercel env add NEXT_PUBLIC_SUPABASE_URL production < <(echo "$SUPABASE_URL")
    vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production < <(echo "$SUPABASE_ANON_KEY")
    
    # Deploy to Vercel
    vercel --prod
    FRONTEND_URL=$(vercel ls --json | jq -r '.[] | select(.name=="happy-hour-frontend") | .url')
    echo "✅ Frontend deployed to: https://$FRONTEND_URL"
else
    # Run locally for development
    echo "Starting frontend locally..."
    npm run dev &
    FRONTEND_PID=$!
    FRONTEND_URL="http://localhost:3000"
    echo "✅ Frontend running at: $FRONTEND_URL"
fi

cd ..
echo ""

# Step 5: Run Tests
echo "🧪 Step 5: Running integration tests..."

if [ "$1" != "production" ]; then
    # Wait for services to start
    sleep 5
    
    # Test orchestrator health
    curl -s "$ORCHESTRATOR_URL/" > /dev/null && echo "✅ Orchestrator health check passed" || echo "❌ Orchestrator not responding"
    
    # Test a sample restaurant lookup
    echo "Testing Duke's La Jolla..."
    curl -X POST "$ORCHESTRATOR_URL/api/analyze" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Duke'\''s La Jolla",
            "address": "1216 Prospect St, La Jolla, CA 92037",
            "phone": "(858) 454-5325",
            "website": "https://dukeslajolla.com",
            "skip_voice_verify": true
        }' | jq '.'
fi

echo ""
echo "🎉 Deployment Complete!"
echo "================================"
echo ""
echo "📍 Service URLs:"
echo "   Frontend: $FRONTEND_URL"
echo "   API: $ORCHESTRATOR_URL"
echo "   API Docs: $ORCHESTRATOR_URL/docs"
echo ""
echo "📊 Monitoring:"
echo "   - Supabase Dashboard: https://app.supabase.com"
echo "   - AWS CloudWatch: https://console.aws.amazon.com/cloudwatch"
echo "   - Vercel Dashboard: https://vercel.com/dashboard"
echo ""
echo "💰 Cost Optimization Tips:"
echo "   - Voice verification adds $0.10-0.20 per restaurant"
echo "   - Skip voice for restaurants with >80% confidence"
echo "   - GPT-5-nano is 96% cheaper than GPT-5 for simple tasks"
echo ""
echo "🚦 Next Steps:"
echo "   1. Test with 10 real restaurants"
echo "   2. Monitor costs and accuracy"
echo "   3. Adjust confidence thresholds"
echo "   4. Scale up gradually"
echo ""

# Cleanup function for local development
if [ "$1" != "production" ]; then
    echo "Press Ctrl+C to stop local services..."
    
    cleanup() {
        echo "Stopping services..."
        kill $ORCHESTRATOR_PID 2>/dev/null || true
        kill $FRONTEND_PID 2>/dev/null || true
        echo "Services stopped"
        exit 0
    }
    
    trap cleanup INT
    wait
fi