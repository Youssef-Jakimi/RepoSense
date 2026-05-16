# RepoSense Testing & Submission Guide
**IBM Bob Hackathon 2026**

---

## 📋 Pre-Submission Checklist

This guide will walk you through testing your RepoSense project and preparing it for submission to the IBM Bob Hackathon.

---

## 🔧 Step 1: Get IBM watsonx.ai Credentials

Your project uses **IBM watsonx.ai** (via the Granite model) for the Q&A engine. You need these credentials:

### 1.1 Request IBM Cloud Account (if not done)
1. Go to: https://www.ibm.com/account/reg/us-en/signup?formid=urx-54370
2. Use the **same email** you used to register for the hackathon
3. Create an IBMid or log in if you already have one
4. Complete the account request form
5. Wait for the email invite (check spam/junk folders)

### 1.2 Access Your IBM Cloud Account
1. Open the email from IBM Cloud team
2. Click **"Join Now"** button
3. Accept the account notice and click **"Join Account"**
4. Complete authentication
5. You'll be taken to the IBM Cloud dashboard
6. **Important:** Make sure you're in the "xxxxxxx - watsonx" account (check top-right dropdown)

### 1.3 Get watsonx.ai Credentials
1. From IBM Cloud dashboard, navigate to **watsonx.ai**
2. Click **"Open Prompt Lab"** on the dashboard
3. Look for **"Developer Access"** section (usually in settings or profile)
4. Create an **API Key**:
   - Click "Create API Key"
   - Give it a name (e.g., "RepoSense-Hackathon")
   - Copy the API key immediately (you won't see it again!)
   - Save it to your `.env` file as `WATSONX_API_KEY`
5. Get your **Project ID**:
   - In watsonx.ai, look for "Project" or "Developer Access"
   - Copy the Project ID
   - Save it to your `.env` file as `WATSONX_PROJECT_ID`

### 1.4 Update Your .env File

Open your `.env` file and fill in these values:

```env
# GitHub Token (optional for public repos, but recommended)
GITHUB_TOKEN=your_github_personal_access_token_here

# IBM watsonx.ai credentials
WATSONX_API_KEY=your_api_key_from_step_1.3
WATSONX_PROJECT_ID=your_project_id_from_step_1.3
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct

# IBM Bob (already configured)
IBM_BOB_API_KEY=bob_prod_bob-user_dmQ7RpWYRzmLBYne7Ryak3hqJFzw44pLMwNy32v1cCVji6CVHnqi8jtSBRny6pdVrD6v6NksxbtZ6NtMjpeTzSb_234C1yykGzrHh4G5fJQknDK1CUcXSFnFh6SNVaTubbjL
IBM_BOB_BASE_URL=https://api.dataplatform.cloud.ibm.com

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
```

**⚠️ CRITICAL:** Before final submission, you MUST remove all credentials from your code!

---

## 🧪 Step 2: Run Tests

### 2.1 Verify Dependencies
```bash
# Check if all packages are installed
pip list | grep -E "fastapi|streamlit|langchain|sentence-transformers|PyGithub"

# If any are missing, reinstall
pip install -r requirements.txt
```

### 2.2 Test IBM Bob Connectivity
```bash
python scripts/check_bob.py
```
**Expected:** Should show API key details and connection attempts. Look for successful responses (not all 405 errors).

### 2.3 Test Ingestion Pipeline
```bash
python scripts/smoke_ingest.py
```
**Expected output:**
- ✅ Loads a GitHub repo
- ✅ Chunks files into semantic pieces
- ✅ Embeds chunks into ChromaDB
- ✅ Retrieves relevant chunks for a test query
- ✅ "Smoke test PASSED"

**If it fails:** Check your `GITHUB_TOKEN` and internet connection.

### 2.4 Test Risk Review Pipeline
```bash
python scripts/smoke_review.py --save
```
**Expected output:**
- ✅ Loads repo and analyzes files
- ✅ Detects untested functions
- ✅ Identifies breaking points
- ✅ Scans for security issues
- ✅ Generates risk score (0-100)
- ✅ Saves report to `demo/sample_report.md`
- ✅ "Smoke test PASSED"

---

## 🚀 Step 3: Full System Test

### 3.1 Start the Backend
Open **Terminal 1**:
```bash
uvicorn api.main:app --reload
```
**Expected:** Server starts on `http://localhost:8000`

Test the health endpoint:
```bash
curl http://localhost:8000/health
```
Should return: `{"status":"ok"}`

### 3.2 Start the UI
Open **Terminal 2**:
```bash
streamlit run ui/app.py
```
**Expected:** Browser opens to `http://localhost:8501`

### 3.3 Test with a Sample Repository

1. **Choose a test repo** (start small):
   - `https://github.com/octocat/Hello-World` (tiny, fast)
   - `https://github.com/psf/requests-html` (medium, good for testing)

2. **Ingest the repo:**
   - Paste URL in sidebar
   - Click **"Ingest"**
   - Wait 15-60 seconds (watch the status indicator)
   - ✅ Risk Score should appear (e.g., "72/100")

3. **Test Q&A (Ask tab):**
   Try these questions:
   - "What does this repository do?"
   - "Where is the main entry point?"
   - "What are the key dependencies?"
   - "Are there any security issues?"
   - "Which functions are untested?"

   **Expected:** 
   - Answers should be relevant and grounded in the code
   - Sources should be shown with file paths and line numbers

4. **Check Risk Review (Risk Review tab):**
   - ✅ Untested functions table
   - ✅ Breaking points table
   - ✅ Security findings table
   - ✅ Recommendations list
   - ✅ Download Markdown report button works

---

## 🐛 Step 4: Error Handling Tests

Test edge cases to ensure robustness:

### 4.1 Invalid Repository URL
- Enter: `https://github.com/nonexistent/repo-404`
- **Expected:** Clear error message, no crash

### 4.2 Private Repository (without token)
- Enter a private repo URL without providing a token
- **Expected:** Error message about authentication

### 4.3 Empty Repository
- Enter: `https://github.com/octocat/Hello-World` (has minimal files)
- **Expected:** Should still work, just with fewer findings

### 4.4 Network Interruption
- Start ingestion, then disconnect internet briefly
- **Expected:** Graceful error handling, status shows "error"

---

## 📦 Step 5: Prepare for Submission

### 5.1 Export Bob IDE Session Reports

**⚠️ REQUIRED FOR JUDGING**

1. Open **Bob IDE** (VS Code extension)
2. Click **"Views and More Actions"** → **"History"**
3. Confirm you're in the correct project workspace
4. Select **all tasks** related to your RepoSense project
5. Export each task session as JSON/HTML
6. Create folder in your project:
   ```bash
   mkdir bob_sessions
   ```
7. Save all exported reports to `bob_sessions/` folder

### 5.2 Remove ALL Credentials

**⚠️ CRITICAL - Account will be suspended if credentials are exposed!**

Before pushing to GitHub:

1. **Check `.env` file:**
   ```bash
   # Make sure .env is in .gitignore
   cat .gitignore | grep .env
   ```

2. **Search for hardcoded credentials:**
   ```bash
   # Search for API keys in code
   grep -r "WATSONX_API_KEY" --include="*.py" .
   grep -r "IBM_BOB_API_KEY" --include="*.py" .
   grep -r "GITHUB_TOKEN" --include="*.py" .
   ```

3. **Verify .env.example has no real values:**
   ```bash
   cat .env.example
   ```
   Should only have placeholder text, no actual keys!

4. **Check git status:**
   ```bash
   git status
   ```
   Make sure `.env` is NOT staged for commit!

### 5.3 Final Code Review

Run through this checklist:

- [ ] All smoke tests pass
- [ ] Full UI workflow works end-to-end
- [ ] README.md is up to date
- [ ] ARCHITECTURE.md accurately describes the system
- [ ] `bob_sessions/` folder contains exported reports
- [ ] `.env` file is in `.gitignore`
- [ ] No credentials in any `.py` files
- [ ] `.env.example` has only placeholders
- [ ] `requirements.txt` is complete
- [ ] Demo materials ready (screenshots/video)

### 5.4 Create Demo Materials

1. **Screenshots:**
   - Risk Score display
   - Q&A conversation example
   - Risk Review report
   - Save to `demo/` folder

2. **Demo Video (optional but recommended):**
   - 2-3 minutes showing:
     - Ingesting a repo
     - Asking questions
     - Reviewing risk report
   - Upload to YouTube/Loom and add link to README

### 5.5 Update Documentation

Make sure these files are polished:

1. **README.md:**
   - Clear project description
   - Setup instructions
   - Demo link (if you made a video)
   - Hackathon context

2. **ARCHITECTURE.md:**
   - System diagram
   - Component descriptions
   - Data flow

3. **demo/DEMO_SCRIPT.md:**
   - Step-by-step demo walkthrough
   - Example questions to ask
   - Expected outputs

---

## 🎯 Step 6: Final Submission

### 6.1 Submission Requirements

According to the hackathon guide, you must submit:

1. ✅ **GitHub repository** with:
   - Complete source code
   - `bob_sessions/` folder with exported reports
   - README with setup instructions
   - Demo materials (screenshots/video)
   - NO credentials in code

2. ✅ **Project description** on lablab.ai:
   - What problem it solves
   - How IBM Bob is used
   - Key features
   - Tech stack

3. ✅ **Demo video/presentation** (recommended):
   - 2-5 minutes
   - Show the tool in action
   - Explain the value proposition

### 6.2 Judging Criteria Alignment

Make sure your submission addresses:

| Criteria | How RepoSense Addresses It |
|----------|----------------------------|
| **Application of Technology** | IBM Bob powers both Q&A and risk analysis |
| **Business Value** | Solves real developer pain: onboarding & code risk |
| **Originality** | Unique combination of Q&A + automated risk review |
| **Presentation** | Clean UI, structured reports, live demo |

### 6.3 Pre-Submission Checklist

Final check before submitting:

- [ ] All tests pass (smoke tests + full system)
- [ ] Bob IDE session reports exported to `bob_sessions/`
- [ ] All credentials removed from code
- [ ] `.env` is in `.gitignore` and not committed
- [ ] README is clear and complete
- [ ] Demo materials are ready
- [ ] GitHub repo is public and accessible
- [ ] Project submitted on lablab.ai platform

---

## 🆘 Troubleshooting

### Issue: "IBM Bob not connected" in Q&A
**Solution:** Check your `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` in `.env`

### Issue: Ingestion fails with rate limit error
**Solution:** Add a `GITHUB_TOKEN` to your `.env` file

### Issue: ChromaDB errors
**Solution:** Delete `./chroma_db/` folder and re-run ingestion

### Issue: "Module not found" errors
**Solution:** Reinstall dependencies: `pip install -r requirements.txt`

### Issue: Streamlit won't start
**Solution:** Check if port 8501 is already in use: `lsof -i :8501` (Mac/Linux) or `netstat -ano | findstr :8501` (Windows)

### Issue: Backend won't start
**Solution:** Check if port 8000 is already in use, or try: `uvicorn api.main:app --port 8001`

---

## 📞 Support

- **Hackathon Discord:** Check the IBM Bob Hackathon Discord for support
- **IBM Bob Docs:** Refer to the hackathon guide PDF
- **lablab.ai:** Contact hackathon organizers through the platform

---

## 🎉 Good Luck!

You've built an impressive tool that combines deep codebase intelligence with automated risk analysis. Make sure to:

1. ✅ Test thoroughly
2. ✅ Export Bob sessions
3. ✅ Remove all credentials
4. ✅ Create compelling demo materials
5. ✅ Submit on time!

**Deadline:** May 17, 2026

---

*Built for the IBM Bob Hackathon 2026 by Youssef Jakimi*