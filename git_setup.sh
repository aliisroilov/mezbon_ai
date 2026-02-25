#!/bin/bash
################################################################################
# Git Setup Script for Mezbon AI
# Initializes git repository with proper .gitignore
################################################################################

set -e

echo ""
echo "=================================="
echo "🔧 MEZBON AI - GIT SETUP"
echo "=================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Check if .gitignore exists
if [ ! -f ".gitignore" ]; then
    echo "❌ Error: .gitignore not found!"
    echo "   Please create .gitignore first"
    exit 1
fi

echo "✅ .gitignore found"

# Check if .env.example exists
if [ ! -f "backend/.env.example" ]; then
    echo "⚠️  Warning: backend/.env.example not found"
else
    echo "✅ backend/.env.example found"
fi

# Initialize git if not already initialized
if [ ! -d ".git" ]; then
    echo ""
    echo "📝 Initializing git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Create .env from example if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "📝 Creating backend/.env from example..."
    cp backend/.env.example backend/.env
    echo "✅ backend/.env created"
    echo "⚠️  IMPORTANT: Edit backend/.env and add your actual credentials!"
else
    echo "✅ backend/.env already exists"
fi

# Verify .env is ignored
echo ""
echo "🔍 Verifying .gitignore is working..."

# Test if .env would be ignored
if git check-ignore backend/.env > /dev/null 2>&1; then
    echo "✅ backend/.env is properly ignored"
else
    echo "❌ ERROR: backend/.env is NOT ignored!"
    echo "   This is a security risk!"
    exit 1
fi

# Check for common sensitive files
echo ""
echo "🔍 Checking for sensitive files..."

SENSITIVE_FILES=(
    "backend/.env"
    "backend/google-credentials.json"
    "backend/.db_password"
    "*.key"
    "*.pem"
)

FOUND_SENSITIVE=0
for pattern in "${SENSITIVE_FILES[@]}"; do
    if git ls-files | grep -q "$pattern" 2>/dev/null; then
        echo "❌ WARNING: Found $pattern in git!"
        FOUND_SENSITIVE=1
    fi
done

if [ $FOUND_SENSITIVE -eq 0 ]; then
    echo "✅ No sensitive files found in git"
fi

# Show what will be committed
echo ""
echo "📊 Files ready to commit:"
git status --short

# Count files
TOTAL_FILES=$(git status --short | wc -l)
echo ""
echo "Total files: $TOTAL_FILES"

# Check for node_modules
if git status --short | grep -q "node_modules"; then
    echo "❌ ERROR: node_modules found in git!"
    echo "   This should be ignored"
    exit 1
fi

# Check for __pycache__
if git status --short | grep -q "__pycache__"; then
    echo "❌ ERROR: __pycache__ found in git!"
    echo "   This should be ignored"
    exit 1
fi

# Check for venv
if git status --short | grep -q "venv/\|.venv/"; then
    echo "❌ ERROR: venv found in git!"
    echo "   This should be ignored"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ GIT SETUP VERIFICATION COMPLETE"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Review files with: git status"
echo "2. Add all files: git add ."
echo "3. Make initial commit: git commit -m 'Initial commit'"
echo "4. Add remote: git remote add origin YOUR_REPO_URL"
echo "5. Push: git push -u origin main"
echo ""
echo "⚠️  BEFORE PUSHING:"
echo "   - Double-check no .env files are included"
echo "   - Verify no API keys or passwords are in code"
echo "   - Review GIT_SETUP.md for detailed instructions"
echo ""
echo "=================================="
