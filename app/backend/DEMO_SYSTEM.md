# iFlow Simulation & Demo System

## Overview

The simulation system provides a complete testing environment for the iFlow automation, including:

1. **Mock iFlow Server** - Exact replica of real iFlow selectors and behavior
2. **Enhanced Automation** - Screenshot capture and detailed step logging
3. **Demo API Endpoints** - Run simulations with various modes and configurations
4. **Screenshot Storage** - Firebase Storage (production) or local filesystem (dev)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│              Calls /api/demo/run endpoint                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Demo Router                               │
│  - Validates request                                         │
│  - Configures mock server behavior                          │
│  - Calls iso_task_enhanced                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Enhanced Automation (iso_task_enhanced.py)      │
│  - Launches Playwright browser                               │
│  - Executes steps with logging                               │
│  - Captures screenshots at each step                         │
│  - Returns detailed step-by-step logs                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌──────────────────────┐       ┌──────────────────────┐
│   Mock iFlow Server  │       │  Real iFlow Server   │
│  (localhost routes)  │       │  (app.hriflow.ro)    │
└──────────────────────┘       └──────────────────────┘
```

## File Structure

```
app/backend/
├── routers/
│   └── demo.py                    # Demo API endpoints
├── services/
│   ├── iso_task.py                # Original automation (unchanged)
│   ├── iso_task_enhanced.py       # Enhanced with screenshots & logging
│   ├── screenshot_storage.py      # Firebase + local screenshot storage
│   └── mock_iflow/
│       ├── __init__.py
│       ├── routes.py              # Mock iFlow FastAPI routes
│       ├── templates.py           # HTML templates with exact selectors
│       └── state.py               # Behavior configuration
├── schemas/
│   └── demo.py                    # DemoRequest, DemoResult, SimulationStep
└── screenshots/
    └── simulations/               # Local storage for dev
        └── users/
            └── {uid}/
                └── {timestamp}/
                    ├── step_00_navigate_to_login.png
                    ├── step_01_login_form_detected.png
                    └── ...
```

## API Endpoints

### POST /api/demo/run

Run an iFlow simulation with specified parameters.

**Authentication**: Firebase user token required

**Request Body**:
```json
{
  "mode": "screenshot",           // "visual" | "screenshot" | "backend"
  "speed": "normal",              // "slow" | "normal" | "fast"
  "scenario": "check-in",         // "check-in" | "check-out"
  "location": "telemunca",        // "telemunca" | "birou" | null
  "use_mock": true,               // true = mock server, false = real iFlow
  "mock_behavior": "success"      // "success" | "login_fail" | "timeout" | "no_button"
}
```

**Modes**:
- **visual**: Opens browser window (headless=false), no screenshots
- **screenshot**: Headless browser, captures screenshots at each step
- **backend**: Production mode (headless, no screenshots)

**Speed**:
- **slow**: 2 second delays between steps (good for watching)
- **normal**: 0.5 second delays
- **fast**: No artificial delays

**Response**:
```json
{
  "success": true,
  "duration_ms": 5432,
  "step_count": 12,
  "scenario": "check-in",
  "location": "telemunca",
  "mode": "screenshot",
  "steps": [
    {
      "step_number": 0,
      "name": "navigate_to_login",
      "timestamp": "2025-11-09T10:30:00.000Z",
      "duration_ms": 234,
      "status": "success",
      "message": "Navigating to http://localhost:8000/mock-iflow/login",
      "screenshot_url": "https://storage.googleapis.com/..."
    },
    {
      "step_number": 1,
      "name": "login_form_detected",
      "timestamp": "2025-11-09T10:30:00.500Z",
      "duration_ms": 45,
      "status": "success",
      "message": "Login form found on page",
      "screenshot_url": "https://storage.googleapis.com/..."
    }
    // ... more steps
  ],
  "screenshots": [
    "https://storage.googleapis.com/...",
    "https://storage.googleapis.com/..."
  ],
  "summary": "Successfully completed check-in at telemunca in 5432ms (12 steps).",
  "error": null
}
```

### GET /api/demo/status

Get current demo system status and configuration.

**Response**:
```json
{
  "ok": true,
  "demo_modes": ["visual", "screenshot", "backend"],
  "speed_options": ["slow", "normal", "fast"],
  "scenarios": ["check-in", "check-out"],
  "locations": ["telemunca", "birou"],
  "mock_server": {
    "available": true,
    "behavior": "success",
    "stats": {
      "login_attempts": 5,
      "checkin_attempts": 3,
      "checkout_attempts": 2
    }
  },
  "screenshot_storage": {
    "enabled": true,
    "mode": "local"
  }
}
```

### POST /api/demo/reset-mock

Reset mock server state and statistics.

### POST /api/demo/configure-mock

Configure mock server behavior for testing edge cases.

**Request Body**:
```json
{
  "behavior": "login_fail"  // "success" | "login_fail" | "timeout" | "no_button" | "submit_error"
}
```

## Mock iFlow Server

### Endpoints

- `GET /mock-iflow/login` - Login page with exact selectors
- `POST /mock-iflow/login` - Process login
- `GET /mock-iflow/dashboard` - Dashboard with check-in button
- `POST /mock-iflow/submit` - Process check-in/out submission
- `GET /mock-iflow/stats` - Get mock server statistics
- `POST /mock-iflow/reset` - Reset mock state
- `POST /mock-iflow/configure` - Configure behavior

### Selectors

The mock server uses **identical selectors** to the real iFlow:

**Login Page**:
- `#td_reg_email` - Email input
- `#td_reg_password` - Password input
- `button:has-text("Intră în cont")` - Login button

**Dashboard**:
- `#app > div.td-router-view > div > div.col-md-12.td-fit-container > div.td-check-in-out > a` - Check-in button

**Modal**:
- `.td-checkin-modal .modal-body` - Modal container
- `.td-select-single-button` - Location dropdown
- `#td-ckeck-in-out-end-time-67` - Check-in time field
- `#td-ckeck-in-out-start-time-67` - Check-out time field
- `.modal-footer > button` - Submit button

### Behavior Modes

Configure different failure scenarios:

1. **success** (default): Normal operation, all steps succeed
2. **login_fail**: Login always fails with "Invalid credentials"
3. **timeout**: All operations take 60+ seconds (simulates timeout)
4. **no_button**: Check-in button is hidden on dashboard
5. **submit_error**: Form submission fails with error

### Demo Credentials

For mock server testing:
- Email: `demo@example.com`
- Password: `demo123`

Additional test account:
- Email: `test@example.com`
- Password: `test123`

## Screenshot Storage

### Configuration

Environment variables:

```bash
# Storage mode: "firebase" (production) or "local" (dev)
SCREENSHOT_STORAGE=local

# Local storage path (relative to backend directory)
LOCAL_SCREENSHOT_PATH=screenshots/simulations

# Firebase Storage bucket
FIREBASE_STORAGE_BUCKET=iflow-robot.appspot.com

# Screenshot retention days (auto-cleanup)
SCREENSHOT_RETENTION_DAYS=7
```

### Firebase Storage

**Production setup**:

Screenshots are stored in Firebase Storage with path structure:
```
users/{uid}/simulations/{timestamp}/step_{N}_{name}.png
```

Signed URLs are generated with 7-day expiration.

**Setup**:
1. Ensure Firebase Admin SDK is initialized
2. Set `SCREENSHOT_STORAGE=firebase`
3. Ensure Cloud Run service account has Storage Admin role

### Local Storage

**Development setup**:

Screenshots are stored locally at:
```
app/backend/screenshots/simulations/users/{uid}/{timestamp}/step_*.png
```

**Setup**:
1. Set `SCREENSHOT_STORAGE=local`
2. Directory is auto-created on first use
3. Paths returned are relative for frontend to construct URLs

### Auto-Cleanup

Old screenshots are automatically cleaned up after retention period.

Call cleanup manually:
```python
from services.screenshot_storage import get_screenshot_storage

storage = get_screenshot_storage()
deleted_count = storage.cleanup_old_screenshots(uid="optional_user_id")
```

Or add to cron job for scheduled cleanup.

## Usage Examples

### Visual Mode (Watch Browser)

```bash
curl -X POST https://your-backend/api/demo/run \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "visual",
    "speed": "slow",
    "scenario": "check-in",
    "location": "telemunca",
    "use_mock": true,
    "mock_behavior": "success"
  }'
```

### Screenshot Capture Mode

```bash
curl -X POST https://your-backend/api/demo/run \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "screenshot",
    "speed": "normal",
    "scenario": "check-in",
    "location": "birou",
    "use_mock": true
  }'
```

### Test Login Failure

```bash
# First configure mock to fail
curl -X POST https://your-backend/api/demo/configure-mock \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"behavior": "login_fail"}'

# Then run simulation
curl -X POST https://your-backend/api/demo/run \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "screenshot",
    "scenario": "check-in",
    "use_mock": true
  }'
```

## Development Workflow

### Local Testing

1. **Start backend server**:
   ```bash
   cd app/backend
   uvicorn main:app --reload
   ```

2. **Access mock iFlow** (in browser):
   ```
   http://localhost:8000/mock-iflow/login
   ```

3. **Run simulation** (via API):
   ```bash
   # Get Firebase token first (from frontend auth)
   curl -X POST http://localhost:8000/api/demo/run \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"mode": "visual", "speed": "slow", "scenario": "check-in", "use_mock": true}'
   ```

4. **View screenshots** (local mode):
   ```
   app/backend/screenshots/simulations/users/{uid}/{timestamp}/
   ```

### Testing Different Scenarios

```python
# Python script for comprehensive testing
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_firebase_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

test_cases = [
    {"name": "Normal check-in", "scenario": "check-in", "behavior": "success"},
    {"name": "Login failure", "scenario": "check-in", "behavior": "login_fail"},
    {"name": "Missing button", "scenario": "check-in", "behavior": "no_button"},
    {"name": "Submit error", "scenario": "check-in", "behavior": "submit_error"},
    {"name": "Check-out at birou", "scenario": "check-out", "location": "birou"},
]

for test in test_cases:
    print(f"\n=== Testing: {test['name']} ===")

    # Configure mock if needed
    if 'behavior' in test:
        requests.post(
            f"{BASE_URL}/api/demo/configure-mock",
            headers=headers,
            json={"behavior": test['behavior']}
        )

    # Run simulation
    response = requests.post(
        f"{BASE_URL}/api/demo/run",
        headers=headers,
        json={
            "mode": "screenshot",
            "speed": "fast",
            "scenario": test['scenario'],
            "location": test.get('location'),
            "use_mock": True
        }
    )

    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Duration: {result['duration_ms']}ms")
    print(f"Steps: {result['step_count']}")
    print(f"Summary: {result['summary']}")
```

## Integration with Frontend

### Example React Component

```typescript
import { useState } from 'react';
import { api } from '@/lib/api';

function SimulationDemo() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const response = await api.post('/demo/run', {
        mode: 'screenshot',
        speed: 'normal',
        scenario: 'check-in',
        location: 'telemunca',
        use_mock: true,
        mock_behavior: 'success'
      });
      setResult(response.data);
    } catch (error) {
      console.error('Simulation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={runSimulation} disabled={loading}>
        {loading ? 'Running...' : 'Run Simulation'}
      </button>

      {result && (
        <div>
          <h3>Results</h3>
          <p>Success: {result.success ? 'Yes' : 'No'}</p>
          <p>Duration: {result.duration_ms}ms</p>
          <p>Steps: {result.step_count}</p>

          <h4>Step-by-Step Log</h4>
          {result.steps.map((step) => (
            <div key={step.step_number}>
              <strong>{step.name}</strong> - {step.status}
              <p>{step.message}</p>
              {step.screenshot_url && (
                <img src={step.screenshot_url} alt={step.name} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

## Troubleshooting

### Screenshots not captured

- Check `SCREENSHOT_STORAGE` env var is set
- Verify Firebase Admin SDK is initialized
- Check Cloud Run service account has Storage Admin role
- For local mode, check directory permissions

### Mock server not accessible

- Verify backend is running: `curl http://localhost:8000/health`
- Check mock routes are registered in `core/app.py`
- Try accessing directly: `http://localhost:8000/mock-iflow/stats`

### Playwright browser not launching

- Ensure Playwright is installed: `playwright install chromium`
- Check Chrome/Chromium dependencies on Cloud Run
- Increase memory limit: `--memory 2Gi`

### Timeouts in simulation

- Increase timeout in user settings (default 30s)
- Check network connectivity to iFlow/mock server
- Use "fast" speed mode to reduce delays
- Check Cloud Run timeout setting (default 60s, may need increase)

## Future Enhancements

- [ ] WebSocket streaming for real-time step updates
- [ ] Video recording of entire simulation
- [ ] Parallel execution of multiple simulations
- [ ] Diff comparison between successful/failed runs
- [ ] Export simulation results as PDF report
- [ ] Frontend UI for demo page
- [ ] Scheduled demo runs for regression testing
- [ ] Integration with CI/CD pipeline
