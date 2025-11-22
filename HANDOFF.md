# 🤖 iFlow Robot - Current Status & Handoff

**Last Updated:** 2025-11-22 14:20
**Branch:** `develop`
**Status:** ⚠️ Partially Working - CORS Fixed, Backend 500 Error

---

## ✅ What's Working

### Infrastructure & CI/CD
- **GitHub Actions Workflows:**
  - ✅ `deploy-dev.yml` - Deploys to development environment
  - ✅ `deploy-prod.yml` - Deploys to production environment
  - ✅ `backend-tests.yml` - Runs pytest (10 tests passing locally)
  - ✅ `security-scan.yml` - Bandit configured to ignore low-severity issues
  - ✅ Upgraded `actions/upload-artifact` from v3 to v4

### Cloud Services
- **Backend Deployments:**
  - Dev: `https://iso-backend-dev-ioq56tobdq-ew.a.run.app`
  - Prod: `https://iso-backend-ioq56tobdq-ew.a.run.app`

- **Frontend Deployments:**
  - Dev: `https://iflow-robot--dev-1x36p6u8.web.app`
  - Prod: `https://iflow-robot.web.app`

- **Firebase Authentication:**
  - ✅ Test users created:
    - `demo-user@iflow-robot.dev` / `demo-password-123`
    - `dev-user@iflow-robot.dev` / `dev-test-password-123`

- **Google Cloud Secret Manager:**
  - ✅ Secrets created for both test users
  - Secrets: `iflow-cred-dev-test-user-001`, `iflow-cred-dev-demo-user-001`

### Service Account
- **Name:** `github-actions@iflow-robot.iam.gserviceaccount.com`
- **Key File:** `firebase-sa-key.json` (gitignored, regenerated 4x due to corruption)
- **Roles Granted:**
  - `roles/firebaseauth.admin`
  - `roles/datastore.user`
  - `roles/secretmanager.admin`
  - `roles/artifactregistry.admin`
  - `roles/cloudbuild.builds.builder`
  - `roles/storage.admin`
  - `roles/iam.serviceAccountUser`
  - `roles/firebasehosting.admin`

### Code Fixes Applied
- ✅ **CORS Configuration:** Updated `app/backend/core/app.py` to use `allow_origin_regex` accepting all Firebase Hosting URLs (production + dev channels)
- ✅ **Environment Variables:** Workflows now create `.env.development` and `.env.production` dynamically (not committed to git)
- ✅ **Frontend Config:** Added Firebase config (API key, project ID, etc.) to build process
- ✅ **UI Updates:** Added "Try Demo" and "Sign Up" buttons to sign-in page

---

## ⚠️ Current Issues

### 1. **Backend 500 Error (NEW)**
- **Symptom:** `/api/simulation/run-public` returns 500 Internal Server Error
- **Impact:** Frontend shows CORS error (because 500 response has no CORS headers)
- **Next Step:** Check Cloud Run logs with:
  ```bash
  gcloud run services logs read iso-backend-dev --region=europe-west1 --limit=50 --project=iflow-robot
  ```

### 2. **Firebase API Keys in Workflow Files**
- **Current State:** Keys are hardcoded in `deploy-dev.yml` and `deploy-prod.yml`
- **Security Note:** Firebase web API keys are meant to be public, BUT should be restricted by domain in Firebase Console
- **Recommendation:** Move to GitHub Secrets for consistency:
  ```yaml
  VITE_FIREBASE_API_KEY: ${{ secrets.FIREBASE_WEB_API_KEY }}
  ```

---

## 📋 Configuration Reference

### Backend Environment Variables (Set in Cloud Run)
```bash
ENVIRONMENT=development  # or production
GOOGLE_CLOUD_PROJECT=iflow-robot
FIREBASE_PROJECT_ID=iflow-robot
SECRET_MANAGER_PROJECT=iflow-robot
```

### Frontend Environment Variables (Generated in CI)
```bash
# Backend
VITE_API_BASE_URL=https://iso-backend-dev-ioq56tobdq-ew.a.run.app
VITE_ENVIRONMENT=development

# Firebase
VITE_FIREBASE_API_KEY=AIzaSyBdXhCOMR0Yzyn6qtrCRzk_D12psPN7c44
VITE_FIREBASE_AUTH_DOMAIN=iflow-robot.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=iflow-robot
VITE_FIREBASE_MESSAGING_SENDER_ID=416751442341
VITE_FIREBASE_APP_ID=1:416751442341:web:3c5ad9c7f654bee019704c
```

### GitHub Secrets Required
- `GCP_SERVICE_ACCOUNT` - Full JSON of service account key (updated 2025-11-22)
- `FIREBASE_SERVICE_ACCOUNT` - Same as above (both use same key for now)
- `SNYK_TOKEN` - For security scanning (optional)

---

## 🔨 Recent Fixes (Last 24 Hours)

1. **Service Account Key Regeneration**
   - Old key was corrupted (`Invalid JWT Signature`)
   - Generated new key: `f5b8c155cdb86fd3730206e260d506c089793185`
   - Updated both GitHub secrets

2. **CORS Configuration**
   - Changed from static `allow_origins` list to `allow_origin_regex`
   - Regex pattern: `r"https://(iflow-robot(--[\w-]+)?\.(web|firebaseapp)\.app|localhost:\d+|127\.0\.0\.1:\d+)"`
   - Allows all Firebase preview URLs + localhost

3. **Environment Variable Fix**
   - Frontend code uses `VITE_API_BASE_URL` but workflow was setting `VITE_API_URL`
   - Fixed variable name mismatch in both workflows

4. **Firebase Config Addition**
   - Frontend needs Firebase SDK config to initialize auth
   - Added all required Firebase env vars to build process

5. **Feature Branch Workflow**
   - Created `feature/cors-and-ui-fixes` branch
   - Merged to `develop` with `--no-ff` for clean history

---

## 🚀 Next Steps (Priority Order)

### Immediate (Fix Current Issues)
1. **Debug Backend 500 Error:**
   - Check logs: `gcloud run services logs read iso-backend-dev --region=europe-west1 --limit=50`
   - Look for Python exceptions in `/api/simulation/run-public` endpoint
   - File: `app/backend/routers/demo.py`

2. **Move Firebase Config to Secrets:**
   - Create GitHub secrets for all Firebase env vars
   - Update workflows to use `${{ secrets.FIREBASE_WEB_API_KEY }}` etc.
   - Restrict API key by domain in Firebase Console

### Short Term (Polish)
3. **Test End-to-End Flow:**
   - Login with test users
   - Create a schedule
   - Run simulation
   - Test demo mode without login

4. **Fix Firestore Permissions:**
   - Service account gets 403 when writing to Firestore
   - May need `roles/datastore.owner` instead of `roles/datastore.user`
   - Run `setup_env.py` again after permission update

### Medium Term (Production Readiness)
5. **Branch Protection:**
   - Protect `master` and `develop` branches
   - Require PR reviews
   - Require CI checks to pass

6. **Cost Optimization:**
   - Review Secret Manager cache settings (currently 5 minutes)
   - Set up Cloud Run min/max instances
   - Review Firebase usage

7. **Monitoring:**
   - Set up Cloud Monitoring alerts
   - Configure error reporting
   - Add health check endpoints

---

## 📁 Important Files

### Workflows
- `.github/workflows/deploy-dev.yml` - Dev deployment
- `.github/workflows/deploy-prod.yml` - Prod deployment
- `.github/workflows/backend-tests.yml` - Backend tests
- `.github/workflows/security-scan.yml` - Security scanning

### Backend Core
- `app/backend/core/app.py` - FastAPI app + CORS config
- `app/backend/core/test_users.py` - Test user definitions
- `app/backend/services/user_passwords.py` - Secret Manager integration
- `app/backend/routers/demo.py` - Public demo endpoint (⚠️ currently 500ing)

### Frontend
- `web/src/lib/api.ts` - API client (line 12: `VITE_API_BASE_URL`)
- `web/src/lib/firebase.ts` - Firebase initialization
- `web/src/pages/SignIn.tsx` - Login page with Demo/Sign Up buttons

### Setup Scripts
- `app/backend/scripts/setup_env.py` - Creates test users + secrets
- `app/backend/scripts/migrate_credentials.py` - Migrates from Firestore to Secret Manager

---

## 🔍 Troubleshooting Commands

```bash
# Check backend logs
gcloud run services logs read iso-backend-dev --region=europe-west1 --limit=50 --project=iflow-robot

# List Cloud Run services
gcloud run services list --project=iflow-robot

# Check latest GitHub Actions run
gh run list --limit 5

# Re-run failed workflow
gh run watch

# Test backend locally
cd app/backend
python -m uvicorn main:app --reload --port 8000

# Test frontend locally
cd web
npm run dev

# Create test users & secrets (requires GOOGLE_APPLICATION_CREDENTIALS)
python app/backend/scripts/setup_env.py
```

---

## 💡 Quick Reference

- **Project ID:** `iflow-robot`
- **Region:** `europe-west1`
- **Firebase Project:** `iflow-robot`
- **Service Account:** `github-actions@iflow-robot.iam.gserviceaccount.com`
- **Test User UIDs:** `dev-test-user-001`, `dev-demo-user-001`

---

## ⚠️ Known Quirks

1. **Service Account Key:** Has been regenerated 4 times due to corruption. Always copy using `Get-Content firebase-sa-key.json -Raw | Set-Clipboard` to avoid formatting issues.

2. **Cache Issues:** Firebase Hosting CDN caches aggressively. Always hard refresh (Ctrl+Shift+R) or use incognito mode when testing frontend changes.

3. **Empty DOM in Browser Agent:** The automated browser sometimes gets empty DOM. This is a known limitation, not a site issue.

4. **Git Ignored Files:** `.env.*` files are gitignored (correct). CI creates them dynamically from hardcoded values (should move to secrets).

---

**Good luck! 🚀**
*If you have questions about any of this, search for the relevant file/function in the codebase.*
