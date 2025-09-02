#!/bin/bash

# GPT-5 Happy Hour Discovery System - AWS Deployment Script
# Optimized for fast MVP+ deployment with proper error handling

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="happy-hour-discovery"
REGION="us-east-1"  # Change as needed
PYTHON_VERSION="3.11"

# Default environment
ENVIRONMENT="${1:-dev}"
VALID_ENVS=("dev" "staging" "prod")

# Helper functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Validate environment
validate_environment() {
    if [[ ! " ${VALID_ENVS[@]} " =~ " ${ENVIRONMENT} " ]]; then
        error "Invalid environment: ${ENVIRONMENT}. Use: ${VALID_ENVS[*]}"
    fi
    success "Environment validated: ${ENVIRONMENT}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI not found. Install: https://aws.amazon.com/cli/"
    fi
    
    # Check SAM CLI
    if ! command -v sam &> /dev/null; then
        error "SAM CLI not found. Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    fi
    
    # Check Python
    if ! command -v python3.11 &> /dev/null; then
        warning "Python 3.11 not found. Using default python3..."
        if ! command -v python3 &> /dev/null; then
            error "Python 3 not found. Install Python 3.11+"
        fi
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Run: aws configure"
    fi
    
    success "Prerequisites check passed"
}

# Validate required environment variables
check_environment_variables() {
    log "Checking environment variables..."
    
    local required_vars=(
        "SUPABASE_URL"
        "SUPABASE_KEY"
        "OPENAI_API_KEY"
    )
    
    # Optional but recommended
    local optional_vars=(
        "ANTHROPIC_API_KEY"
        "GOOGLE_PLACES_API_KEY"
        "YELP_API_KEY" 
        "TWILIO_ACCOUNT_SID"
        "TWILIO_AUTH_TOKEN"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables: ${missing_vars[*]}
        
Set them with:
export SUPABASE_URL='your-supabase-url'
export SUPABASE_KEY='your-supabase-service-key'
export OPENAI_API_KEY='your-openai-key'

Optional (for full functionality):
export ANTHROPIC_API_KEY='your-anthropic-key'
export GOOGLE_PLACES_API_KEY='your-google-key'
export YELP_API_KEY='your-yelp-key'
export TWILIO_ACCOUNT_SID='your-twilio-sid'
export TWILIO_AUTH_TOKEN='your-twilio-token'"
    fi
    
    for var in "${optional_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            warning "Optional variable not set: $var (some features may be limited)"
        fi
    done
    
    success "Environment variables validated"
}

# Build Lambda layers
build_layers() {
    log "Building Lambda layers..."
    
    # Create layers directory
    mkdir -p ../layers/python_deps/python/lib/python3.11/site-packages
    mkdir -p ../layers/playwright
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip3 install -r requirements.txt -t ../layers/python_deps/python/lib/python3.11/site-packages/
    
    # Note: Playwright layer would need custom build process
    # For MVP, we'll handle browser automation differently or use a pre-built layer
    
    success "Lambda layers built"
}

# Build agent functions
build_agents() {
    log "Building agent functions..."
    
    local agents=("orchestrator" "site_agent" "google_agent" "yelp_agent" "voice_verify" "consensus")
    
    for agent in "${agents[@]}"; do
        local agent_dir="../agents/${agent}"
        
        if [[ ! -d "$agent_dir" ]]; then
            warning "Agent directory not found: $agent_dir (skipping)"
            continue
        fi
        
        log "Building $agent..."
        
        # Create __init__.py if it doesn't exist
        touch "$agent_dir/__init__.py"
        
        # Validate handler.py exists
        if [[ ! -f "$agent_dir/handler.py" ]]; then
            warning "Handler not found for $agent (creating placeholder)"
            cat > "$agent_dir/handler.py" << EOF
"""
${agent} Lambda handler
TODO: Implement agent logic
"""

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': {
            'message': 'Agent ${agent} placeholder - implement me!',
            'agent': '${agent}',
            'event': event
        }
    }
EOF
        fi
    done
    
    success "Agent functions prepared"
}

# Deploy with SAM
deploy_stack() {
    log "Deploying stack: ${STACK_NAME}-${ENVIRONMENT}..."
    
    # Build the application
    log "Building SAM application..."
    sam build --use-container --cached
    
    # Deploy with parameters
    log "Deploying to AWS..."
    sam deploy \
        --stack-name "${STACK_NAME}-${ENVIRONMENT}" \
        --s3-bucket "${STACK_NAME}-deployments-${REGION}" \
        --capabilities CAPABILITY_IAM \
        --region "${REGION}" \
        --parameter-overrides \
            Environment="${ENVIRONMENT}" \
            SupabaseUrl="${SUPABASE_URL}" \
            SupabaseKey="${SUPABASE_KEY}" \
            OpenAIApiKey="${OPENAI_API_KEY}" \
            AnthropicApiKey="${ANTHROPIC_API_KEY:-''}" \
            GooglePlacesApiKey="${GOOGLE_PLACES_API_KEY:-''}" \
            YelpApiKey="${YELP_API_KEY:-''}" \
            TwilioAccountSid="${TWILIO_ACCOUNT_SID:-''}" \
            TwilioAuthToken="${TWILIO_AUTH_TOKEN:-''}" \
        --confirm-changeset \
        --fail-on-empty-changeset false
    
    success "Stack deployed successfully"
}

# Create deployment bucket if it doesn't exist
create_deployment_bucket() {
    local bucket_name="${STACK_NAME}-deployments-${REGION}"
    
    if ! aws s3api head-bucket --bucket "$bucket_name" 2>/dev/null; then
        log "Creating deployment bucket: $bucket_name"
        
        if [[ "$REGION" == "us-east-1" ]]; then
            aws s3api create-bucket --bucket "$bucket_name" --region "$REGION"
        else
            aws s3api create-bucket \
                --bucket "$bucket_name" \
                --region "$REGION" \
                --create-bucket-configuration LocationConstraint="$REGION"
        fi
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$bucket_name" \
            --versioning-configuration Status=Enabled
        
        success "Deployment bucket created: $bucket_name"
    else
        success "Deployment bucket exists: $bucket_name"
    fi
}

# Get stack outputs
get_outputs() {
    log "Retrieving stack outputs..."
    
    local stack_name="${STACK_NAME}-${ENVIRONMENT}"
    
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    success "Stack outputs displayed above"
}

# Main deployment process
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║       GPT-5 Happy Hour Discovery System Deployment       ║"
    echo "║                        MVP+ Version                       ║"  
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    log "Starting deployment for environment: ${ENVIRONMENT}"
    
    validate_environment
    check_prerequisites
    check_environment_variables
    create_deployment_bucket
    build_layers
    build_agents
    deploy_stack
    get_outputs
    
    echo ""
    success "🚀 Deployment completed successfully!"
    success "Environment: ${ENVIRONMENT}"
    success "Region: ${REGION}"
    success "Stack: ${STACK_NAME}-${ENVIRONMENT}"
    
    echo ""
    log "Next steps:"
    echo "  1. Test the API endpoints"
    echo "  2. Run the agent functions individually"
    echo "  3. Deploy the frontend to Vercel"
    echo "  4. Set up monitoring and alerts"
    
    echo ""
    log "Useful commands:"
    echo "  sam logs -n OrchestratorFunction --stack-name ${STACK_NAME}-${ENVIRONMENT}"
    echo "  aws cloudformation describe-stacks --stack-name ${STACK_NAME}-${ENVIRONMENT}"
    echo "  sam delete --stack-name ${STACK_NAME}-${ENVIRONMENT}  # To delete"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "delete")
        log "Deleting stack: ${STACK_NAME}-${2:-dev}..."
        sam delete --stack-name "${STACK_NAME}-${2:-dev}" --region "${REGION}"
        success "Stack deleted"
        ;;
    "outputs")
        get_outputs
        ;;
    "logs")
        FUNCTION_NAME="${2:-OrchestratorFunction}"
        log "Tailing logs for: $FUNCTION_NAME"
        sam logs -n "$FUNCTION_NAME" --stack-name "${STACK_NAME}-${ENVIRONMENT}" --tail
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command] [environment]"
        echo ""
        echo "Commands:"
        echo "  deploy [dev|staging|prod]  - Deploy the stack (default)"
        echo "  delete [dev|staging|prod]  - Delete the stack"  
        echo "  outputs                    - Show stack outputs"
        echo "  logs [function-name]       - Tail function logs"
        echo "  help                       - Show this help"
        echo ""
        echo "Environment variables required:"
        echo "  SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY"
        echo ""
        echo "Optional:"
        echo "  ANTHROPIC_API_KEY, GOOGLE_PLACES_API_KEY, YELP_API_KEY"
        echo "  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN"
        ;;
    *)
        error "Unknown command: $1. Use '$0 help' for usage information."
        ;;
esac