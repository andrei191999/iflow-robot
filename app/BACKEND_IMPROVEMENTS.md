# Backend Improvements Summary

## Overview
The backend has been significantly enhanced with per-user credential storage, comprehensive logging, and improved error handling. These changes enable multi-user support where each colleague can securely store their own iFlow credentials.

---

## Key Improvements

### 1. Per-User Credential Storage ✅

**Problem:** Previously, all users shared the same iFlow credentials from environment variables.

**Solution:** Implemented secure per-user settings storage in Firestore.

**Files Created:**
- [`schemas/settings.py`](./backend/schemas/settings.py) - Pydantic models for user settings
- [`routers/settings.py`](./backend/routers/settings.py) - Settings API endpoints

**New API Endpoints:**

#### `GET /api/settings`
Get user's settings (password never returned in response)
```json
{
  "uid": "user123",
  "iflowUrl": "https://app.hriflow.ro/#/dashboard",
  "iflowUsername": "user@company.com",
  "iflowHeadless": true,
  "iflowTimeout": 30000
}
```

#### `PUT /api/settings`
Update user settings (only provided fields are updated)
```json
{
  "iflowUsername": "user@company.com",
  "iflowPassword": "secret123",
  "iflowUrl": "https://app.hriflow.ro/#/dashboard",
  "iflowHeadless": true,
  "iflowTimeout": 30000
}
```

#### `DELETE /api/settings/credentials`
Delete stored credentials (user will need to re-enter them)

#### `POST /api/settings/test-credentials`
Test if stored credentials work by attempting login
```json
{
  "success": true,
  "message": "Login successful"
}
```

**Security:**
- Passwords are stored in Firestore per-user
- Passwords are NEVER returned in API responses
- Firestore security rules ensure users can only access their own settings
- Each user's credentials are isolated from others

---

### 2. Comprehensive Logging 📋

**Problem:** Limited visibility into what's happening during execution.

**Solution:** Added extensive logging throughout the backend.

**Changes:**
- [`services/iso_task.py`](./backend/services/iso_task.py) - Full execution logging with screenshots
- [`routers/cron.py`](./backend/routers/cron.py) - Detailed cron execution logging

**Logging Features:**
- INFO level logs for all major operations
- DEBUG level logs for detailed debugging
- ERROR level logs with full stack traces
- Screenshots saved at key points (login_before.png, login_after.png, checkin_before.png, etc.)
- Sensitive data (passwords) are redacted from logs

**Example Log Output:**
```
2025-01-07 10:30:00 - services.iso_task - INFO - === Starting iFlow automation: checkIn at location=telemunca ===
2025-01-07 10:30:00 - services.iso_task - INFO - Using user-specific settings from Firestore
2025-01-07 10:30:00 - services.iso_task - INFO - Configuration: url=https://app.hriflow.ro/#/dashboard, username=user@company.com, headless=True, timeout=30000ms
2025-01-07 10:30:01 - services.iso_task - INFO - Launching browser (headless=True)
2025-01-07 10:30:02 - services.iso_task - INFO - Navigating to https://app.hriflow.ro/#/dashboard
2025-01-07 10:30:03 - services.iso_task - INFO - Login form detected, proceeding with authentication
2025-01-07 10:30:03 - services.iso_task - INFO - Filling in username: user@company.com
2025-01-07 10:30:04 - services.iso_task - INFO - Login successful
2025-01-07 10:30:05 - services.iso_task - INFO - Starting check-in procedure at location=telemunca
2025-01-07 10:30:06 - services.iso_task - INFO - Check-in completed at location=telemunca
2025-01-07 10:30:06 - services.iso_task - INFO - === iFlow automation completed: success - Check-in completed at location=telemunca ===
```

---

### 3. Enhanced ISO Task Implementation 🤖

**Improvements to [`services/iso_task.py`](./backend/services/iso_task.py):**

1. **Per-User Settings Support**
   - New parameter `user_settings` in `run_iso_check()`
   - Falls back to environment variables if no user settings provided
   - Supports multi-user deployment

2. **Better Error Handling**
   - Try-catch blocks around all operations
   - Graceful degradation (e.g., location selection failure doesn't fail entire operation)
   - Detailed error messages with stack traces

3. **Screenshots for Debugging**
   - Saves screenshots at critical points
   - Helps diagnose issues with selectors or page structure

4. **Improved Selectors**
   - Added Romanian language selectors ("Autentificare", "Intrare", "Iesire")
   - More comprehensive selector lists
   - Better handling of different page structures

5. **New Test Function**
   - `test_credentials()` - Allows testing credentials without executing check-in/out
   - Used by `/api/settings/test-credentials` endpoint

---

### 4. Cron Job Updates 🕐

**Changes to [`routers/cron.py`](./backend/routers/cron.py):**

1. **Per-User Settings Fetching**
   - Fetches settings for each user from Firestore
   - Passes user settings to `run_iso_check()`
   - Falls back to environment variables if user has no settings

2. **Enhanced Logging**
   - Logs start/end of cron tick
   - Logs each schedule being processed
   - Logs results of each execution

**Flow:**
```
1. Cron tick triggered
2. Query for due schedules
3. For each schedule:
   a. Fetch user's settings from Firestore
   b. Execute check-in/out with user's credentials
   c. Record result in runs collection
   d. Update next_event
4. Return count of processed schedules
```

---

### 5. Firestore Security Rules 🔒

**Updated [`firestore.rules`](../../firestore.rules):**

Added settings collection rules:
```javascript
match /settings/{uid} {
  allow read, write: if request.auth != null && request.auth.uid == uid;
}
```

**Security guarantees:**
- Users can only read/write their own settings
- Credentials are isolated per user
- Backend can access any settings via Admin SDK

---

## Multi-User Deployment Guide

### Setup for Your Colleagues

1. **Deploy the updated backend** to Cloud Run

2. **Each user should:**
   - Sign up / Sign in to the web app
   - Go to Settings page
   - Enter their iFlow credentials
   - Click "Test Credentials" to verify
   - Save settings

3. **Create schedules**
   - Each user creates their own schedules
   - Schedules use that user's saved credentials

4. **Automatic execution**
   - Cloud Scheduler triggers `/cron/tick` every minute
   - For each due schedule, the system:
     - Fetches that user's credentials
     - Executes check-in/out with those credentials
     - Records the result

### Environment Variables (Optional Fallback)

If a user has NOT saved credentials, the system falls back to these:
- `IFLOW_URL` - Default iFlow URL
- `IFLOW_USERNAME` - Default username
- `IFLOW_PASSWORD` - Default password
- `IFLOW_HEADLESS` - Run browser in headless mode (true/false)
- `IFLOW_TIMEOUT` - Operation timeout in milliseconds

**Recommendation:** Remove or leave empty so users are forced to enter their own credentials.

---

## Testing the Changes

### Run Backend Tests
```bash
cd app/backend
python -m pytest tests/ -v
```

All 11 tests should pass ✅

### Test Credentials Endpoint

1. Start the backend:
```bash
cd app/backend
uvicorn main:app --reload
```

2. Sign in and get a token

3. Set credentials:
```bash
curl -X PUT http://localhost:8000/api/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "iflowUsername": "your@email.com",
    "iflowPassword": "yourpassword"
  }'
```

4. Test credentials:
```bash
curl -X POST http://localhost:8000/api/settings/test-credentials \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Should return:
```json
{
  "success": true,
  "message": "Login successful"
}
```

---

## Debugging Tips

### Enable Debug Logging

Set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

Or in code:
```python
logging.basicConfig(level=logging.DEBUG)
```

### View Screenshots

Screenshots are saved in the working directory:
- `login_before.png` - Before clicking login
- `login_after.png` - After login
- `checkin_before.png` - Before check-in
- `checkin_after.png` - After check-in
- `checkout_before.png` - Before check-out
- `checkout_after.png` - After check-out

### Run in Non-Headless Mode

Set `iflowHeadless: false` in user settings to see the browser window.

### Check Logs

On Cloud Run:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=iso-backend" --limit 50
```

Local:
- Logs appear in terminal when running `uvicorn`

---

## Security Considerations

### ✅ What's Secure

1. **Firestore Security Rules** - Users can only access their own data
2. **Password Never Returned** - API never returns passwords in responses
3. **Firebase Authentication** - All endpoints require valid auth token
4. **Per-User Isolation** - Each user's credentials are completely separate

### ⚠️ Additional Security (Optional)

For even better security, consider:

1. **Encrypt passwords in Firestore**
   ```python
   from cryptography.fernet import Fernet
   # Encrypt before storing
   # Decrypt before using
   ```

2. **Use Secret Manager** instead of Firestore
   ```python
   from google.cloud import secretmanager
   # Store credentials in Secret Manager with per-user paths
   ```

3. **Rotate credentials regularly**
   - Add "last updated" timestamp
   - Prompt users to update every 90 days

---

## File Changes Summary

### New Files
- `backend/schemas/settings.py` - Settings data models
- `backend/routers/settings.py` - Settings API endpoints
- `BACKEND_IMPROVEMENTS.md` - This document

### Modified Files
- `backend/services/iso_task.py` - Enhanced logging, per-user settings, screenshots
- `backend/routers/cron.py` - Per-user settings fetching, enhanced logging
- `backend/core/app.py` - Registered settings router
- `backend/requirements.txt` - Added playwright
- `firestore.rules` - Added settings collection rules
- `backend/.env.local` - Added iFlow configuration section

### Test Results
- All 11 existing tests pass ✅
- Coverage: 76% overall

---

## Next Steps

1. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy iso-backend \
     --source app/backend \
     --region europe-west1
   ```

2. **Update Firestore rules**
   ```bash
   firebase deploy --only firestore:rules
   ```

3. **Test with real credentials**
   - Use your own iFlow credentials
   - Run in non-headless mode first
   - Verify selectors work for your iFlow instance

4. **Invite colleagues**
   - Share the web app URL
   - Each person creates account and enters their credentials
   - Test with a few users first

5. **Monitor logs**
   - Check Cloud Run logs regularly
   - Look for errors or failed logins
   - Adjust selectors if needed

---

## API Documentation

Full API docs available at: `http://localhost:8000/docs` (FastAPI Swagger UI)

Or in production: `https://your-backend-url/docs`

---

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Look at screenshots to diagnose selector issues
3. Test credentials using `/api/settings/test-credentials`
4. Run in non-headless mode to see what's happening
5. Verify your iFlow URL is correct

Common issues:
- **Invalid selectors** - iFlow page structure changed, update SELECTORS in iso_task.py
- **Login fails** - Wrong credentials or URL
- **Timeout** - Increase `iflowTimeout` in settings
- **Import error** - Run `pip install playwright && python -m playwright install chromium`
