#!/bin/bash

# Smart Device Analytics Platform - GitHub Push Script
# This script helps you push your project to GitHub

echo "🚀 Smart Device Analytics Platform - GitHub Push Script"
echo "========================================================"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if remote is already configured
if git remote get-url origin >/dev/null 2>&1; then
    echo "✅ Remote origin already configured:"
    git remote get-url origin
    echo ""
    echo "🔄 Pushing to existing remote..."
    git push -u origin main
    echo "✅ Successfully pushed to GitHub!"
    exit 0
fi

# Get GitHub username
echo "📝 Please provide your GitHub information:"
echo ""
read -p "Enter your GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ Error: GitHub username is required"
    exit 1
fi

# Repository name
REPO_NAME="smart-device-analytics-platform"

echo ""
echo "🔗 Setting up remote repository..."
echo "Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""

# Add remote origin
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

# Set main branch
git branch -M main

echo "📤 Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Your project has been pushed to GitHub!"
    echo "🌐 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    echo ""
    echo "📊 What's included:"
    echo "  ✅ Professional README with badges and documentation"
    echo "  ✅ Complete source code (20+ files)"
    echo "  ✅ Technical architecture documentation"
    echo "  ✅ Business impact analysis"
    echo "  ✅ Comprehensive test suite"
    echo "  ✅ Docker containerization"
    echo "  ✅ MIT License"
    echo ""
    echo "🎯 Perfect for Amazon Astro Senior Data Engineer role!"
    echo "📱 Dashboard running at: http://localhost:8502"
else
    echo ""
    echo "❌ Error: Failed to push to GitHub"
    echo "Please check:"
    echo "  1. GitHub repository exists"
    echo "  2. You have push permissions"
    echo "  3. Internet connection is working"
    echo ""
    echo "Manual commands:"
    echo "  git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi
