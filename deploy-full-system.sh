#!/bin/bash

# GPT-5 Happy Hour Discovery - Complete Deployment Script
# Deploys both backend (AWS Lambda) and frontend (Vercel/AWS)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install AWS SAM CLI if not present
install_sam_cli() {
    if command_exists sam; then
        log_info "AWS SAM CLI already installed: $(sam --version)"
        return 0
    fi
    
    log_info "Installing AWS SAM CLI..."
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew tap aws/tap
            brew install aws-sam-cli
        else
            log_error "Homebrew not found. Please install Homebrew first or install SAM CLI manually."
            log_info "Visit: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
        unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
        sudo ./sam-installation/install
        rm -rf sam-installation aws-sam-cli-linux-x86_64.zip
    else
        log_error "Unsupported OS. Please install AWS SAM CLI manually."
        exit 1
    fi
    
    log_success "AWS SAM CLI installed successfully"
}

# Setup environment variables
setup_environment() {
    log_info "Setting up environment variables..."
    
    # Check for .env file
    if [[ ! -f .env ]]; then
        if [[ -f .env.example ]]; then
            log_warning ".env file not found. Creating from .env.example"
            cp .env.example .env
            log_warning "Please edit .env file with your actual values before continuing"
            log_info "Required variables:"
            grep -E "^[A-Z]" .env.example || true
            read -p "Press Enter after configuring .env file..."
        else
            log_error ".env file not found and no .env.example template available"
            exit 1
        fi
    fi
    
    # Load environment variables
    set -a
    source .env
    set +a
    
    log_success "Environment variables loaded"
}

# Validate required environment variables
validate_env_vars() {
    log_info "Validating required environment variables..."
    
    REQUIRED_VARS=(
        "SUPABASE_URL"
        "SUPABASE_SERVICE_KEY" 
        "OPENAI_API_KEY"
    )
    
    MISSING_VARS=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    log_success "All required environment variables are set"
}

# Create simplified SAM template for orchestrator only
create_simple_sam_template() {
    log_info "Creating simplified SAM template for orchestrator..."
    
    cat > simple-template.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: 'GPT-5 Happy Hour Discovery - Orchestrator Function'

Parameters:
  Environment:
    Type: String
    Default: dev
  SupabaseUrl:
    Type: String
  SupabaseServiceKey:
    Type: String
    NoEcho: true
  OpenAIApiKey:
    Type: String
    NoEcho: true

Globals:
  Function:
    Runtime: python3.11
    Timeout: 300
    MemorySize: 1024

Resources:
  # Main orchestrator function
  OrchestratorFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub 'gpt5-happy-hour-orchestrator-${Environment}'
      Handler: lambda_orchestrator.lambda_handler
      CodeUri: ./
      Description: 'GPT-5 Happy Hour Discovery Orchestrator'
      Environment:
        Variables:
          SUPABASE_URL: !Ref SupabaseUrl
          SUPABASE_SERVICE_KEY: !Ref SupabaseServiceKey
          OPENAI_API_KEY: !Ref OpenAIApiKey
          ENVIRONMENT: !Ref Environment
      FunctionUrlConfig:
        AuthType: NONE
        Cors:
          AllowCredentials: true
          AllowHeaders:
            - "content-type"
            - "authorization"
          AllowMethods:
            - "GET"
            - "POST"
            - "OPTIONS"
          AllowOrigins:
            - "*"
      Events:
        ApiEvent:
          Type: HttpApi
          Properties:
            Path: /{proxy+}
            Method: ANY

Outputs:
  FunctionUrl:
    Description: 'Lambda Function URL'
    Value: !GetAtt OrchestratorFunctionUrl.FunctionUrl
  ApiUrl:
    Description: 'API Gateway URL'
    Value: !Sub 'https://${ServerlessHttpApi}.execute-api.${AWS::Region}.amazonaws.com'
EOF

    log_success "Simple SAM template created"
}

# Deploy backend using SAM
deploy_backend() {
    log_info "Deploying backend Lambda function..."
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt -t ./
    
    # Create simple template since complex one has missing directories
    create_simple_sam_template
    
    # Build and deploy
    log_info "Building SAM application..."
    sam build -t simple-template.yaml --use-container || {
        log_warning "Container build failed, trying without container..."
        sam build -t simple-template.yaml
    }
    
    log_info "Deploying to AWS..."
    sam deploy \
        --template-file simple-template.yaml \
        --stack-name gpt5-happy-hour-dev \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides \
            Environment=dev \
            SupabaseUrl="${SUPABASE_URL}" \
            SupabaseServiceKey="${SUPABASE_SERVICE_KEY}" \
            OpenAIApiKey="${OPENAI_API_KEY}" \
        --resolve-s3 \
        --no-confirm-changeset
    
    # Get the deployed URL
    BACKEND_URL=$(sam list stack-outputs --stack-name gpt5-happy-hour-dev --output table | grep "FunctionUrl" | awk '{print $4}' || echo "")
    
    if [[ -z "$BACKEND_URL" ]]; then
        BACKEND_URL=$(sam list stack-outputs --stack-name gpt5-happy-hour-dev --output table | grep "ApiUrl" | awk '{print $4}' || echo "")
    fi
    
    if [[ -n "$BACKEND_URL" ]]; then
        log_success "Backend deployed successfully!"
        log_info "Backend URL: $BACKEND_URL"
        echo "REACT_APP_API_URL=$BACKEND_URL" > .env.frontend
    else
        log_error "Could not retrieve backend URL from deployment"
        exit 1
    fi
}

# Deploy frontend
deploy_frontend() {
    log_info "Deploying frontend..."
    
    # Decide which frontend to deploy based on what's available
    if [[ -d "frontend" && -f "frontend/package.json" ]]; then
        FRONTEND_DIR="frontend"
        FRONTEND_TYPE="nextjs"
    elif [[ -d "happy-hour-frontend" && -f "happy-hour-frontend/package.json" ]]; then
        FRONTEND_DIR="happy-hour-frontend"  
        FRONTEND_TYPE="create-react-app"
    else
        log_error "No frontend directory found"
        return 1
    fi
    
    log_info "Deploying $FRONTEND_TYPE frontend from $FRONTEND_DIR"
    
    cd "$FRONTEND_DIR"
    
    # Copy environment variables
    if [[ -f "../.env.frontend" ]]; then
        cp ../.env.frontend .env.local
    fi
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci
    
    # Build application
    log_info "Building frontend application..."
    npm run build
    
    # Deploy to Vercel if available, otherwise provide instructions
    if command_exists vercel; then
        log_info "Deploying to Vercel..."
        
        # Set environment variables in Vercel
        if [[ -f ".env.local" ]]; then
            while IFS='=' read -r key value; do
                if [[ $key && $value && $key != \#* ]]; then
                    vercel env add "$key" production <<< "$value" || true
                fi
            done < .env.local
        fi
        
        # Deploy
        vercel --prod --yes
        
        FRONTEND_URL=$(vercel list | grep "gpt5-happy-hour\|happy-hour" | head -1 | awk '{print $2}' || echo "")
        if [[ -n "$FRONTEND_URL" ]]; then
            log_success "Frontend deployed to Vercel!"
            log_info "Frontend URL: https://$FRONTEND_URL"
        fi
    else
        log_warning "Vercel CLI not found. Build completed, ready for manual deployment."
        log_info "Build output available in: $(pwd)/build or $(pwd)/.next"
        log_info "You can deploy manually to:"
        log_info "  - Vercel: https://vercel.com"
        log_info "  - Netlify: https://netlify.com"
        log_info "  - AWS S3 + CloudFront"
        log_info "  - Any static hosting service"
    fi
    
    cd ..
}

# Test deployed endpoints
test_deployment() {
    log_info "Testing deployed endpoints..."
    
    if [[ -n "$BACKEND_URL" ]]; then
        log_info "Testing backend health check..."
        
        HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL%/}/" || echo "000")
        
        if [[ "$HEALTH_RESPONSE" == "200" ]]; then
            log_success "Backend health check passed!"
        else
            log_warning "Backend health check returned status: $HEALTH_RESPONSE"
        fi
        
        # Test analyze endpoint
        log_info "Testing analyze endpoint..."
        ANALYZE_RESPONSE=$(curl -s -X POST "${BACKEND_URL%/}/api/analyze" \
            -H "Content-Type: application/json" \
            -d '{"name":"Test Restaurant","address":"123 Test St, Test City, CA"}' \
            -w "%{http_code}" -o /tmp/analyze_response.json || echo "000")
        
        if [[ "$ANALYZE_RESPONSE" == "200" ]]; then
            log_success "Analyze endpoint working!"
            if [[ -f /tmp/analyze_response.json ]]; then
                JOB_ID=$(cat /tmp/analyze_response.json | python3 -c "import json,sys; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null || echo "")
                if [[ -n "$JOB_ID" ]]; then
                    log_info "Created test job: $JOB_ID"
                fi
            fi
        else
            log_warning "Analyze endpoint returned status: $ANALYZE_RESPONSE"
        fi
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f simple-template.yaml .env.frontend
    # Remove installed Python packages from root
    find . -maxdepth 1 -name "*.dist-info" -exec rm -rf {} \; 2>/dev/null || true
    find . -maxdepth 1 -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
}

# Main deployment function
main() {
    log_info "🚀 Starting GPT-5 Happy Hour Discovery deployment..."
    
    # Setup
    install_sam_cli
    setup_environment
    validate_env_vars
    
    # Deploy backend
    deploy_backend
    
    # Deploy frontend
    deploy_frontend
    
    # Test deployment
    test_deployment
    
    # Cleanup
    cleanup
    
    log_success "🎉 Deployment completed successfully!"
    
    echo ""
    log_info "📋 Deployment Summary:"
    echo "────────────────────────────────────────"
    if [[ -n "$BACKEND_URL" ]]; then
        echo "🔧 Backend API: $BACKEND_URL"
    fi
    if [[ -n "$FRONTEND_URL" ]]; then
        echo "🌐 Frontend: https://$FRONTEND_URL"
    fi
    echo "📊 AWS Console: https://console.aws.amazon.com/lambda"
    echo "📈 Monitoring: CloudWatch Logs"
    echo ""
    log_info "🔍 Next steps:"
    echo "  1. Test the deployed application"
    echo "  2. Monitor CloudWatch logs for any issues"
    echo "  3. Configure DNS/custom domain if needed"
    echo "  4. Set up monitoring and alerts"
}

# Run main function with error handling
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    trap cleanup EXIT
    main "$@"
fi