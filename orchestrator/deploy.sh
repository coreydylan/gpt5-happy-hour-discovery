#!/bin/bash

# Deploy Orchestrator to AWS EC2/ECS or local Docker
# This script packages and deploys the FastAPI orchestrator

set -e

echo "🚀 Deploying Happy Hour Orchestrator (GPT-5 Powered)"

# Build Docker image
echo "📦 Building Docker image..."
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
COPY ../shared /app/shared

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

docker build -t happy-hour-orchestrator .

# Option 1: Run locally
if [ "$1" == "local" ]; then
    echo "🏠 Running locally..."
    docker run -d \
        --name happy-hour-orchestrator \
        -p 8000:8000 \
        --env-file ../.env \
        happy-hour-orchestrator
    
    echo "✅ Orchestrator running at http://localhost:8000"
    echo "📊 API docs at http://localhost:8000/docs"
fi

# Option 2: Push to ECR and deploy to ECS
if [ "$1" == "aws" ]; then
    echo "☁️ Deploying to AWS..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${AWS_REGION:-us-east-1}
    
    # Create ECR repository if not exists
    aws ecr describe-repositories --repository-names happy-hour-orchestrator 2>/dev/null || \
        aws ecr create-repository --repository-name happy-hour-orchestrator
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Tag and push image
    docker tag happy-hour-orchestrator:latest \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/happy-hour-orchestrator:latest
    
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/happy-hour-orchestrator:latest
    
    echo "✅ Image pushed to ECR"
    echo "📝 Update your ECS task definition with the new image"
fi

# Option 3: Deploy to Vercel (using Vercel's Python support)
if [ "$1" == "vercel" ]; then
    echo "▲ Deploying to Vercel..."
    
    # Create vercel.json
    cat > vercel.json << EOF
{
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
EOF
    
    # Deploy
    vercel --prod
    
    echo "✅ Deployed to Vercel"
fi

echo "🎉 Deployment complete!"