# Vercel Deployment Guide

This guide explains how to deploy RepoSense to Vercel.

## Problem: Bundle Size Limit

The original `requirements.txt` includes `sentence-transformers`, which bundles PyTorch and large ML models (~5GB). Vercel Lambda functions have a 500MB limit, causing deployment failures.

## Solution: Lightweight Embedder

We've created two versions of the embedder:

1. **Local Development** (`ingestion/embedder.py`): Uses `sentence-transformers` with local models
2. **Vercel Deployment** (`ingestion/embedder_lite.py`): Uses IBM watsonx.ai API for embeddings

The system automatically selects the right version based on the environment.

## Deployment Steps

### 1. Prerequisites

- Vercel account
- GitHub repository connected to Vercel
- IBM watsonx.ai API credentials

### 2. Configure Environment Variables

In your Vercel project settings, add these environment variables:

```
GITHUB_TOKEN=your_github_token
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
```

**Important**: Use Vercel's environment variable secrets feature for sensitive data.

### 3. Update Requirements File

Before deploying, rename the requirements file:

```bash
# Backup original
cp requirements.txt requirements-local.txt

# Use Vercel-optimized requirements
cp requirements-vercel.txt requirements.txt
```

Or modify `vercel.json` to use `requirements-vercel.txt` directly.

### 4. Deploy to Vercel

#### Option A: Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Option B: Via GitHub Integration

1. Push your code to GitHub
2. Import the repository in Vercel dashboard
3. Configure environment variables
4. Deploy

### 5. Verify Deployment

Test the deployed API:

```bash
# Health check
curl https://your-app.vercel.app/api/health

# Test ingestion (replace with your repo)
curl -X POST https://your-app.vercel.app/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

## File Structure for Deployment

```
RepoSense/
├── vercel.json                 # Vercel configuration
├── requirements-vercel.txt     # Lightweight dependencies
├── .vercelignore              # Files to exclude from deployment
├── api/                       # FastAPI backend
├── ingestion/
│   ├── embedder.py           # Local development (with sentence-transformers)
│   ├── embedder_lite.py      # Vercel deployment (API-based)
│   └── embedder_auto.py      # Auto-selector
└── ui/web/                    # Frontend static files
```

## Configuration Files

### vercel.json

Configures Vercel build and routing:
- Maps `/api/*` to FastAPI backend
- Serves static frontend from `/ui/web/`
- Sets Lambda size limit to 50MB

### requirements-vercel.txt

Lightweight dependencies without `sentence-transformers`:
- Removes: `sentence-transformers` (~5GB)
- Keeps: All other dependencies for API, ingestion, and LLM integration

### .vercelignore

Excludes unnecessary files from deployment:
- Development files (`bob_sessions/`, `demo/`, `docs/`)
- Test scripts (`scripts/`)
- Local environment files (`.env`, `venv/`)

## Differences: Local vs Vercel

| Feature | Local Development | Vercel Deployment |
|---------|------------------|-------------------|
| Embeddings | sentence-transformers (local) | watsonx.ai API |
| Model | all-MiniLM-L6-v2 | ibm/slate-125m-english-rtrvr |
| Bundle Size | ~5GB | ~50MB |
| Cold Start | Fast (model cached) | Slower (API calls) |
| Cost | Free (local compute) | API usage costs |

## Troubleshooting

### Bundle Size Error

If you still see "Bundle size exceeds limit":
1. Verify `requirements-vercel.txt` is being used
2. Check `.vercelignore` excludes large directories
3. Ensure `sentence-transformers` is not in dependencies

### API Timeout

Vercel has a 10-second timeout for Hobby plan, 60 seconds for Pro:
- Large repositories may timeout during ingestion
- Consider splitting into smaller chunks
- Use background jobs for long operations

### Environment Variables Not Working

1. Check variable names match exactly (case-sensitive)
2. Redeploy after adding/changing variables
3. Use Vercel CLI to verify: `vercel env ls`

### Embedding API Errors

If watsonx.ai API fails:
1. Verify API key and project ID are correct
2. Check API quota/limits
3. Review logs: `vercel logs`

## Cost Considerations

### Vercel
- **Hobby Plan**: Free (limited bandwidth/builds)
- **Pro Plan**: $20/month (higher limits)

### IBM watsonx.ai
- Embedding API calls are metered
- Monitor usage in IBM Cloud dashboard
- Consider caching embeddings to reduce API calls

## Rollback to Local Development

To switch back to local development:

```bash
# Restore original requirements
cp requirements-local.txt requirements.txt

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn api.main:app --reload
```

## Production Recommendations

1. **Use Pro Plan**: For production workloads, use Vercel Pro for better limits
2. **Monitor Costs**: Track watsonx.ai API usage
3. **Cache Embeddings**: Store embeddings to avoid re-computing
4. **Rate Limiting**: Implement rate limiting to control costs
5. **Error Handling**: Add retry logic for API failures
6. **Logging**: Use Vercel's logging for debugging

## Support

For issues:
- Vercel: https://vercel.com/docs
- IBM watsonx.ai: https://cloud.ibm.com/docs/watsonxdata
- RepoSense: Check GitHub issues

## Next Steps

After successful deployment:
1. Test all endpoints thoroughly
2. Monitor performance and costs
3. Set up custom domain (optional)
4. Configure CI/CD for automatic deployments
5. Add monitoring/alerting