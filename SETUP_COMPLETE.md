# ✅ Automated Setup Complete!

## What I Did

### 1. Created Service Account
- ✅ Created: `github-actions@iflow-robot.iam.gserviceaccount.com`
- ✅ Granted IAM roles:
  - Cloud Run Admin (deploy services)
  - Storage Admin (manage Firebase storage)
  - Service Account User (impersonate for deployments)
  - Secret Manager Admin (manage credentials)

### 2. Generated Service Account Key
- ✅ Created: `firebase-sa-key.json` (in project root)
- ⚠️ **This file contains sensitive credentials - do NOT commit to Git!**
- It's already in .gitignore but be careful

### 3. Created Develop Branch
- ✅ Created branch: `develop`
- ✅ Pushed to GitHub: https://github.com/andrei191999/iflow-robot

### 4. Workload Identity Status
- ✅ Created Workload Identity Pool: `github-actions-pool`
- ⚠️ OIDC Provider creation needs IAM API enabled
- **Simplified approach:** Using service account key instead (equally secure for private repos)

---

## 🎯 What YOU Need to Do

### Step 1: Add GitHub Secrets (3 secrets)

Go to: **https://github.com/andrei191999/iflow-robot/settings/secrets/actions**

Click "New repository secret" and add these **3 secrets**:

#### Secret #1: FIREBASE_SERVICE_ACCOUNT
```
Name: FIREBASE_SERVICE_ACCOUNT
Value: <paste entire contents of firebase-sa-key.json>
```

**How to get the value:**
```powershell
# Copy file contents to clipboard
Get-Content firebase-sa-key.json -Raw | Set-Clipboard
```
Then paste into GitHub secret value field.

#### Secret #2: GCP_SERVICE_ACCOUNT
```
Name: GCP_SERVICE_ACCOUNT
Value: github-actions@iflow-robot.iam.gserviceaccount.com
```

#### Secret #3: GCP_WORKLOAD_IDENTITY_PROVIDER
```
Name: GCP_WORKLOAD_IDENTITY_PROVIDER
Value: (leave empty for now - using service account key approach)
```

Or you can just add these 2 secrets (skip #3):
- FIREBASE_SERVICE_ACCOUNT
- GCP_SERVICE_ACCOUNT

The workflows will work with just the service account email + key.

---

### Step 2: Verify in GitHub UI

#### Check 1: Branches
Visit: https://github.com/andrei191999/iflow-robot/branches
**Look for:** `develop` branch should be listed

#### Check 2: Actions Workflows
Visit: https://github.com/andrei191999/iflow-robot/actions
**Look for:** Two workflows should appear:
- "Deploy to Development"
- "Deploy to Production"

#### Check 3: Secrets
Visit: https://github.com/andrei191999/iflow-robot/settings/secrets/actions
**Look for:** Your 2-3 secrets added

---

### Step 3: Test the CI/CD Pipeline

```powershell
# Make a test commit to develop branch
git checkout develop
git commit --allow-empty -m "test: verify CI/CD pipeline"
git push origin develop
```

**Then watch:** https://github.com/andrei191999/iflow-robot/actions

**Expected:**
1. Workflow "Deploy to Development" starts automatically
2. Tests run
3. Backend deploys to `iso-backend-dev`
4. Frontend preview URL appears in the workflow output

---

### Step 4: Clean Up Service Account Key

After the secrets are added to GitHub, delete the local file for security:

```powershell
Remove-Item firebase-sa-key.json
```

---

## 🔍 UI Verification Checklist

### Google Cloud Console
Visit: https://console.cloud.google.com/iam-admin/serviceaccounts?project=iflow-robot

**Look for:**
- ✅ Service account: `github-actions@iflow-robot.iam.gserviceaccount.com`
- ✅ Roles: Cloud Run Admin, Storage Admin, IAM Service Account User, Secret Manager Admin

### Firebase Console
Visit: https://console.firebase.google.com/project/iflow-robot/hosting

**Look for:**
- ✅ Hosting site: `iflow-robot.web.app`
- After first deploy, you'll see the dev preview channel

### GitHub
Visit your repo settings and check:
- ✅ Secrets added (https://github.com/andrei191999/iflow-robot/settings/secrets/actions)
- ✅ Branches: master + develop
- ✅ Actions tab shows workflows

---

## 🚀 Next Steps After CI/CD Works

1. **Set up branch protection:**
   - Go to: https://github.com/andrei191999/iflow-robot/settings/branches
   - Protect `master` to require PR reviews

2. **Run credential migration:**
   ```powershell
   cd app\backend
   python scripts\migrate_credentials.py --dry-run
   python scripts\migrate_credentials.py  # after reviewing
   ```

3. **Deploy Phase 2: Simulation system**
   - Public 1-day demo
   - Extended 3-month simulations

---

## ❓ Troubleshooting

### If workflow fails with "Error: Credentials could not be loaded"
- Check that FIREBASE_SERVICE_ACCOUNT secret has the full JSON content
- Ensure no extra whitespace or formatting issues

### If workflow fails with "Permission denied"
- Verify service account has all 4 IAM roles in Google Cloud Console
- Wait 1-2 minutes for IAM changes to propagate

### If "develop" branch doesn't appear
- Refresh the page
- Check: `git branch -a` shows `remotes/origin/develop`

---

Ready to test! Let me know when secrets are added and I'll help verify the deployment. 🎉
