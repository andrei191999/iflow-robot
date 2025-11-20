# CI/CD Setup Guide

## Prerequisites

Configure these GitHub secrets for CI/CD: **GCP_WORKLOAD_IDENTITY_PROVIDER**, **GCP_SERVICE_ACCOUNT**, **FIREBASE_SERVICE_ACCOUNT**

## Quick Setup Commands

```powershell
# Set variables
$PROJECT_ID = "iflow-robot"
$SERVICE_ACCOUNT = "github-actions@iflow-robot.iam.gserviceaccount.com"
$REPO = "andrei191999/iflow-robot"

# 1. Create service account
gcloud iam service-accounts create github-actions --project=$PROJECT_ID

# 2. Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/storage.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/iam.serviceAccountUser"

# 3. Generate Firebase key
gcloud iam service-accounts keys create firebase-key.json --iam-account=$SERVICE_ACCOUNT
Get-Content firebase-key.json | Set-Clipboard
Remove-Item firebase-key.json

# Add to GitHub Secrets:
# - GCP_SERVICE_ACCOUNT: github-actions@iflow-robot.iam.gserviceaccount.com
# - FIREBASE_SERVICE_ACCOUNT: (clipboard content)
```

## Workflow Overview

**Development (`develop` branch):**
- Auto-deploy to `iso-backend-dev` + Firebase preview
- No approval required

**Production (`master` branch):**
- Required: Manual approval
- Deploys to production URLs
- Creates GitHub release

## Testing

```powershell
# Test dev deployment
git checkout develop
git commit --allow-empty -m "test: CI/CD"
git push origin develop

# Watch: https://github.com/andrei191999/iflow-robot/actions
```

See full guide at: `.github/workflows/` directory
