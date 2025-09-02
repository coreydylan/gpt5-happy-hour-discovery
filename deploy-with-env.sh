#!/bin/bash

# GPT-5 Happy Hour Discovery - Complete Deployment with Environment Variables
set -e

echo "🚀 GPT-5 Happy Hour Discovery - Complete CLI Deployment"
echo "========================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get OpenAI API Key from environment or prompt
get_api_key() {
    if [[ -n "$OPENAI_API_KEY" ]]; then
        echo -e "${GREEN}✅ OpenAI API Key found in environment${NC}"
        API_KEY="$OPENAI_API_KEY"
    else
        echo -e "${YELLOW}🔑 OpenAI API Key not found in environment${NC}"
        echo "Please enter your OpenAI API Key:"
        read -s API_KEY
        export OPENAI_API_KEY="$API_KEY"
        echo -e "${GREEN}✅ API Key set${NC}"
    fi
}

# Deploy backend to Vercel
deploy_backend() {
    echo -e "${BLUE}🚀 Deploying backend to Vercel...${NC}"
    
    # Deploy with environment variables
    vercel --prod \
        --name "gpt5-happy-hour-api" \
        --env OPENAI_API_KEY="$API_KEY" \
        --yes
    
    # Get backend URL
    BACKEND_URL=$(vercel inspect gpt5-happy-hour-api --timeout 10000 --token $(vercel whoami) 2>/dev/null | grep -o 'https://[^"]*\.vercel\.app' | head -1)
    
    if [[ -z "$BACKEND_URL" ]]; then
        # Fallback method
        BACKEND_URL="https://gpt5-happy-hour-api.vercel.app"
    fi
    
    echo -e "${GREEN}✅ Backend deployed at: $BACKEND_URL${NC}"
    echo "$BACKEND_URL" > backend-url.txt
}

# Deploy frontend to Vercel
deploy_frontend() {
    echo -e "${BLUE}🚀 Deploying frontend to Vercel...${NC}"
    
    # Read backend URL
    if [[ -f backend-url.txt ]]; then
        BACKEND_URL=$(cat backend-url.txt)
    else
        BACKEND_URL="https://gpt5-happy-hour-api.vercel.app"
    fi
    
    echo -e "${YELLOW}Using Backend URL: $BACKEND_URL${NC}"
    
    # Change to frontend directory
    cd happy-hour-frontend
    
    # Deploy frontend with environment variables
    vercel --prod \
        --name "gpt5-happy-hour-frontend" \
        --env REACT_APP_API_URL="$BACKEND_URL" \
        --yes
    
    # Get frontend URL
    FRONTEND_URL="https://gpt5-happy-hour-frontend.vercel.app"
    
    echo -e "${GREEN}✅ Frontend deployed at: $FRONTEND_URL${NC}"
    
    cd ..
    
    # Store URLs
    echo "BACKEND_URL=$BACKEND_URL" > deployment-urls.txt
    echo "FRONTEND_URL=$FRONTEND_URL" >> deployment-urls.txt
}

# Check Vercel authentication
check_vercel_auth() {
    echo -e "${BLUE}🔐 Checking Vercel authentication...${NC}"
    
    if vercel whoami &> /dev/null; then
        echo -e "${GREEN}✅ Authenticated with Vercel as: $(vercel whoami)${NC}"
    else
        echo -e "${YELLOW}Please authenticate with Vercel...${NC}"
        vercel login
        
        if vercel whoami &> /dev/null; then
            echo -e "${GREEN}✅ Vercel authentication successful${NC}"
        else
            echo -e "${RED}❌ Vercel authentication failed${NC}"
            exit 1
        fi
    fi
}

# Main execution
main() {
    echo -e "${GREEN}Starting deployment process...${NC}"
    
    get_api_key
    check_vercel_auth
    deploy_backend
    deploy_frontend
    
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
    echo "=================================="
    
    if [[ -f deployment-urls.txt ]]; then
        source deployment-urls.txt
        echo -e "${BLUE}Backend API:${NC} $BACKEND_URL"
        echo -e "${BLUE}API Docs:${NC} $BACKEND_URL/docs"
        echo -e "${BLUE}Frontend App:${NC} $FRONTEND_URL"
    fi
    
    echo ""
    echo -e "${YELLOW}🧪 To test your system:${NC}"
    echo "1. Open: $FRONTEND_URL"
    echo "2. Search for 'DUKES' or 'BARBARELLA'"
    echo "3. Click 'Analyze Happy Hour'"
    echo "4. Watch GPT-5 perform analysis!"
    
    echo ""
    echo -e "${GREEN}✨ Your GPT-5 Happy Hour Discovery System is now live!${NC}"
    
    # Clean up
    rm -f backend-url.txt deployment-urls.txt
}

# Run main function
main "$@"