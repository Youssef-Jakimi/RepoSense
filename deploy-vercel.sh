#!/bin/bash
# Deployment script for Vercel

echo "🚀 Preparing RepoSense for Vercel deployment..."

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Install it with: npm i -g vercel"
    exit 1
fi

# Backup original requirements if not already done
if [ ! -f "requirements-local.txt" ]; then
    echo "📦 Backing up original requirements.txt..."
    cp requirements.txt requirements-local.txt
fi

# Use Vercel-optimized requirements
echo "📝 Using lightweight requirements for Vercel..."
cp requirements-vercel.txt requirements.txt

# Check environment variables
echo "🔍 Checking environment variables..."
if [ -z "$GITHUB_TOKEN" ] && [ -z "$WATSONX_API_KEY" ]; then
    echo "⚠️  Warning: Environment variables not set locally."
    echo "   Make sure to configure them in Vercel dashboard:"
    echo "   - GITHUB_TOKEN"
    echo "   - WATSONX_API_KEY"
    echo "   - WATSONX_PROJECT_ID"
fi

# Deploy
echo "🚀 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo "📖 See VERCEL_DEPLOYMENT.md for more information"

# Made with Bob
