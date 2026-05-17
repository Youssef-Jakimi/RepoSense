# PowerShell deployment script for Vercel

Write-Host "🚀 Preparing RepoSense for Vercel deployment..." -ForegroundColor Cyan

# Check if vercel CLI is installed
$vercelInstalled = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelInstalled) {
    Write-Host "❌ Vercel CLI not found. Install it with: npm i -g vercel" -ForegroundColor Red
    exit 1
}

# Backup original requirements if not already done
if (-not (Test-Path "requirements-local.txt")) {
    Write-Host "📦 Backing up original requirements.txt..." -ForegroundColor Yellow
    Copy-Item requirements.txt requirements-local.txt
}

# Use Vercel-optimized requirements
Write-Host "📝 Using lightweight requirements for Vercel..." -ForegroundColor Yellow
Copy-Item requirements-vercel.txt requirements.txt

# Check environment variables
Write-Host "🔍 Checking environment variables..." -ForegroundColor Yellow
if (-not $env:GITHUB_TOKEN -and -not $env:WATSONX_API_KEY) {
    Write-Host "⚠️  Warning: Environment variables not set locally." -ForegroundColor Yellow
    Write-Host "   Make sure to configure them in Vercel dashboard:" -ForegroundColor Yellow
    Write-Host "   - GITHUB_TOKEN" -ForegroundColor Yellow
    Write-Host "   - WATSONX_API_KEY" -ForegroundColor Yellow
    Write-Host "   - WATSONX_PROJECT_ID" -ForegroundColor Yellow
}

# Deploy
Write-Host "🚀 Deploying to Vercel..." -ForegroundColor Cyan
vercel --prod

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "📖 See VERCEL_DEPLOYMENT.md for more information" -ForegroundColor Cyan

# Made with Bob
