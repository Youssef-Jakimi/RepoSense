# Quick Deployment Guide

## The Problem
Your Vercel deployment failed with:
```
Bundle size (5032.11 MB) exceeds limit. 
Total bundle size exceeds Lambda ephemeral storage limit (500 MB).
```

## The Solution
We've optimized the app for Vercel by:
1. ✅ Removing `sentence-transformers` (5GB package)
2. ✅ Using IBM watsonx.ai API for embeddings instead
3. ✅ Created lightweight requirements file
4. ✅ Added Vercel configuration files

## Deploy Now (3 Steps)

### Step 1: Set Environment Variables in Vercel

Go to your Vercel project settings and add:
```
GITHUB_TOKEN=your_github_personal_access_token
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
```

### Step 2: Push Changes to GitHub

```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### Step 3: Deploy

Vercel will automatically deploy when you push to GitHub, or manually trigger:
```bash
# Install Vercel CLI (if not installed)
npm i -g vercel

# Deploy
vercel --prod
```

## What Changed?

### New Files Created:
- `vercel.json` - Vercel configuration
- `requirements-vercel.txt` - Lightweight dependencies (no sentence-transformers)
- `.vercelignore` - Excludes unnecessary files
- `ingestion/embedder_lite.py` - API-based embedder for Vercel
- `ingestion/embedder_auto.py` - Auto-selects embedder based on environment
- `VERCEL_DEPLOYMENT.md` - Detailed deployment guide

### Modified Files:
- `requirements.txt` - Now uses lightweight version
- `requirements-local.txt` - Backup of original (for local development)
- `api/routes/ingest.py` - Uses auto-selecting embedder

## Verify Deployment

After deployment, test your API:

```bash
# Replace YOUR_APP_URL with your Vercel URL
curl https://YOUR_APP_URL.vercel.app/api/health
```

Expected response:
```json
{"status": "ok"}
```

## Important Notes

### Bundle Size Reduced
- **Before**: 5032 MB (sentence-transformers + PyTorch)
- **After**: ~50 MB (API-based embeddings)

### How It Works
- **Local Development**: Uses `sentence-transformers` with local models
- **Vercel Deployment**: Uses IBM watsonx.ai API for embeddings
- **Auto-Detection**: System automatically picks the right version

### Cost Implications
- Vercel: Free tier available (Hobby plan)
- IBM watsonx.ai: Pay-per-use for embedding API calls
- Monitor usage in IBM Cloud dashboard

## Troubleshooting

### Still Getting Bundle Size Error?
1. Verify `requirements.txt` doesn't include `sentence-transformers`
2. Check `.vercelignore` is excluding large directories
3. Clear Vercel build cache and redeploy

### Environment Variables Not Working?
1. Double-check variable names (case-sensitive)
2. Redeploy after adding variables
3. Check Vercel logs: `vercel logs`

### API Errors?
1. Verify watsonx.ai credentials are correct
2. Check API quota hasn't been exceeded
3. Review error logs in Vercel dashboard

## Need More Help?

- **Detailed Guide**: See `VERCEL_DEPLOYMENT.md`
- **Architecture**: See `ARCHITECTURE.md`
- **Testing**: See `TESTING_GUIDE.md`

## Rollback to Local Development

To use the full version locally:

```bash
# Restore original requirements
cp requirements-local.txt requirements.txt

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn api.main:app --reload
```

The app will automatically use local embeddings when not on Vercel.

## Success Checklist

- [ ] Environment variables configured in Vercel
- [ ] Code pushed to GitHub
- [ ] Deployment successful (no bundle size error)
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] Can ingest a test repository
- [ ] Can query the ingested repository

## Next Steps

1. Test all API endpoints
2. Configure custom domain (optional)
3. Set up monitoring
4. Review costs and usage
5. Add rate limiting if needed

---

**Ready to deploy?** Run `./deploy-vercel.ps1` (Windows) or `./deploy-vercel.sh` (Linux/Mac)