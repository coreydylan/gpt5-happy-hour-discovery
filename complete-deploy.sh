#!/bin/bash

# GPT-5 Happy Hour Discovery - Complete CLI Deployment
# This script automates GitHub repo creation and Vercel deployment

set -e  # Exit on any error

echo "🚀 GPT-5 Happy Hour Discovery - Complete CLI Deployment"
echo "========================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if required CLIs are installed
check_dependencies() {
    echo -e "${BLUE}📦 Checking dependencies...${NC}"
    
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}❌ GitHub CLI not found${NC}"
        echo "Installing GitHub CLI..."
        brew install gh
    else
        echo -e "${GREEN}✅ GitHub CLI installed${NC}"
    fi
    
    if ! command -v vercel &> /dev/null; then
        echo -e "${RED}❌ Vercel CLI not found${NC}"
        echo "Installing Vercel CLI..."
        npm install -g vercel
    else
        echo -e "${GREEN}✅ Vercel CLI installed${NC}"
    fi
}

# Authenticate with GitHub
auth_github() {
    echo -e "${BLUE}🔐 Authenticating with GitHub...${NC}"
    
    if gh auth status &> /dev/null; then
        echo -e "${GREEN}✅ Already authenticated with GitHub${NC}"
    else
        echo -e "${YELLOW}Please authenticate with GitHub CLI...${NC}"
        gh auth login --web --scopes repo,workflow
        
        if gh auth status &> /dev/null; then
            echo -e "${GREEN}✅ GitHub authentication successful${NC}"
        else
            echo -e "${RED}❌ GitHub authentication failed${NC}"
            exit 1
        fi
    fi
}

# Create GitHub repository
create_github_repo() {
    echo -e "${BLUE}📁 Creating GitHub repository...${NC}"
    
    REPO_NAME="gpt5-happy-hour-discovery"
    
    # Check if repo already exists
    if gh repo view "$REPO_NAME" &> /dev/null; then
        echo -e "${YELLOW}⚠️  Repository already exists${NC}"
        read -p "Do you want to use the existing repository? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Exiting..."
            exit 1
        fi
    else
        # Create new repository
        gh repo create "$REPO_NAME" \
            --public \
            --description "GPT-5 powered happy hour discovery system for La Jolla restaurants" \
            --confirm
        
        echo -e "${GREEN}✅ GitHub repository created: https://github.com/$(gh api user --jq .login)/$REPO_NAME${NC}"
    fi
    
    # Add remote and push
    if git remote | grep -q origin; then
        git remote remove origin
    fi
    
    git remote add origin "https://github.com/$(gh api user --jq .login)/$REPO_NAME.git"
    git push -u origin main
    
    echo -e "${GREEN}✅ Code pushed to GitHub${NC}"
}

# Authenticate with Vercel
auth_vercel() {
    echo -e "${BLUE}🔐 Authenticating with Vercel...${NC}"
    
    # Check if already logged in
    if vercel whoami &> /dev/null; then
        echo -e "${GREEN}✅ Already authenticated with Vercel${NC}"
        echo "Current user: $(vercel whoami)"
    else
        echo -e "${YELLOW}Please authenticate with Vercel...${NC}"
        vercel login
        
        if vercel whoami &> /dev/null; then
            echo -e "${GREEN}✅ Vercel authentication successful${NC}"
            echo "Logged in as: $(vercel whoami)"
        else
            echo -e "${RED}❌ Vercel authentication failed${NC}"
            exit 1
        fi
    fi
}

# Deploy backend to Vercel
deploy_backend() {
    echo -e "${BLUE}🚀 Deploying backend to Vercel...${NC}"
    
    # Set environment variables
    echo -e "${YELLOW}Setting up environment variables...${NC}"
    
    # Deploy with environment variables
    vercel --prod \
        --name "gpt5-happy-hour-api" \
        --env OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE" \
        --confirm \
        --force
    
    # Get backend URL
    BACKEND_URL=$(vercel ls --scope="$(vercel whoami)" | grep "gpt5-happy-hour-api" | head -1 | awk '{print $2}')
    if [[ $BACKEND_URL != https://* ]]; then
        BACKEND_URL="https://$BACKEND_URL"
    fi
    
    echo -e "${GREEN}✅ Backend deployed at: $BACKEND_URL${NC}"
    echo "Backend URL: $BACKEND_URL" > backend-url.txt
}

# Deploy frontend to Vercel
deploy_frontend() {
    echo -e "${BLUE}🚀 Deploying frontend to Vercel...${NC}"
    
    # Read backend URL
    if [[ -f backend-url.txt ]]; then
        BACKEND_URL=$(cat backend-url.txt | cut -d' ' -f3)
    else
        echo -e "${RED}❌ Backend URL not found${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Backend URL: $BACKEND_URL${NC}"
    
    # Change to frontend directory
    cd happy-hour-frontend
    
    # Deploy frontend with environment variables
    vercel --prod \
        --name "gpt5-happy-hour-frontend" \
        --env REACT_APP_API_URL="$BACKEND_URL" \
        --confirm \
        --force
    
    # Get frontend URL
    FRONTEND_URL=$(vercel ls --scope="$(vercel whoami)" | grep "gpt5-happy-hour-frontend" | head -1 | awk '{print $2}')
    if [[ $FRONTEND_URL != https://* ]]; then
        FRONTEND_URL="https://$FRONTEND_URL"
    fi
    
    echo -e "${GREEN}✅ Frontend deployed at: $FRONTEND_URL${NC}"
    
    cd ..
}

# Main execution
main() {
    echo -e "${GREEN}Starting complete deployment process...${NC}"
    
    check_dependencies
    auth_github
    create_github_repo
    auth_vercel
    deploy_backend
    deploy_frontend
    
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
    echo "=================================="
    
    if [[ -f backend-url.txt ]]; then
        BACKEND_URL=$(cat backend-url.txt | cut -d' ' -f3)
        echo -e "${BLUE}Backend API:${NC} $BACKEND_URL"
        echo -e "${BLUE}API Docs:${NC} $BACKEND_URL/docs"
    fi
    
    FRONTEND_URL=$(vercel ls --scope="$(vercel whoami)" | grep "gpt5-happy-hour-frontend" | head -1 | awk '{print $2}')
    if [[ $FRONTEND_URL != https://* ]]; then
        FRONTEND_URL="https://$FRONTEND_URL"
    fi
    echo -e "${BLUE}Frontend App:${NC} $FRONTEND_URL"
    
    echo ""
    echo -e "${YELLOW}🧪 To test your system:${NC}"
    echo "1. Open: $FRONTEND_URL"
    echo "2. Search for 'DUKES' or 'BARBARELLA'"
    echo "3. Click 'Analyze Happy Hour'"
    echo "4. Watch GPT-5 perform analysis!"
    
    echo ""
    echo -e "${GREEN}✨ Features now live:${NC}"
    echo "• GPT-5 Responses API with reasoning tokens"
    echo "• Beautiful React interface"
    echo "• Real-time restaurant search"
    echo "• AI-powered happy hour analysis"
    echo "• Mobile responsive design"
    echo "• Global CDN with HTTPS"
    
    # Clean up
    rm -f backend-url.txt
}

# Run main function
main "$@"