#!/bin/bash

# Git Credentials Configuration Script
# This script configures Git with your username and access token

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo -e "${BLUE}🔧 Git Credentials Configuration${NC}"
echo "=================================="

# Git Configuration
GIT_USERNAME="arafatkhairul"
GIT_TOKEN="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"
GIT_EMAIL="office.khairul@gmail.com"

print_status "Configuring Git credentials..."

# Configure Git username
if git config --global user.name "$GIT_USERNAME"; then
    print_success "Git username configured: $GIT_USERNAME"
else
    print_error "Failed to configure Git username"
    exit 1
fi

# Configure Git email
if git config --global user.email "$GIT_EMAIL"; then
    print_success "Git email configured: $GIT_EMAIL"
else
    print_error "Failed to configure Git email"
    exit 1
fi

# Configure Git credential helper
if git config --global credential.helper store; then
    print_success "Git credential helper configured"
else
    print_error "Failed to configure Git credential helper"
    exit 1
fi

# Create credentials file
CREDENTIALS_FILE="$HOME/.git-credentials"
CREDENTIALS_URL="https://${GIT_USERNAME}:${GIT_TOKEN}@github.com"

if echo "$CREDENTIALS_URL" > "$CREDENTIALS_FILE"; then
    print_success "Git credentials file created"
    chmod 600 "$CREDENTIALS_FILE"
    print_success "Credentials file permissions set to 600"
else
    print_error "Failed to create Git credentials file"
    exit 1
fi

# Configure Git to use HTTPS instead of SSH for GitHub
if git config --global url."https://github.com/".insteadOf "git@github.com:"; then
    print_success "Git HTTPS configuration set"
else
    print_error "Failed to configure Git HTTPS"
    exit 1
fi

# Test Git configuration
print_status "Testing Git configuration..."

if git config --global --get user.name | grep -q "$GIT_USERNAME"; then
    print_success "Git username test passed"
else
    print_error "Git username test failed"
fi

if git config --global --get user.email | grep -q "$GIT_EMAIL"; then
    print_success "Git email test passed"
else
    print_error "Git email test failed"
fi

# Test GitHub access
print_status "Testing GitHub access..."

if curl -s -H "Authorization: token $GIT_TOKEN" https://api.github.com/user | grep -q "$GIT_USERNAME"; then
    print_success "GitHub access test passed"
else
    print_warning "GitHub access test failed - token may be invalid"
fi

echo ""
print_success "🎉 Git credentials configured successfully!"
echo ""
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "Username: $GIT_USERNAME"
echo "Email: $GIT_EMAIL"
echo "Token: ${GIT_TOKEN:0:10}... (hidden)"
echo "Credentials file: $CREDENTIALS_FILE"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Test with: git clone https://github.com/arafatkhairul/shci-app.git"
echo "2. Or test with: git pull origin main"
echo "3. Credentials will be automatically used for GitHub operations"
echo ""
echo -e "${BLUE}🔒 Security Note:${NC}"
echo "- Credentials file is protected with 600 permissions"
echo "- Token is stored securely in credentials file"
echo "- HTTPS is used instead of SSH for better compatibility"
