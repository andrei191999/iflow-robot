# Quick Start - iFlow Simulation System

## Installation

```bash
# Navigate to backend
cd app/backend

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

## Local Development

### 1. Start Backend Server

```bash
cd app/backend
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`

### 2. Test Mock iFlow Server

Open browser to: `http://localhost:8000/mock-iflow/login`

**Demo credentials**:
- Email: `demo@example.com`
- Password: `demo123`

### 3. Run Test Suite

```bash
python test_demo_system.py
```

Expected output: `🎉 All tests passed!` (6/6)

## API Usage

### Get Demo Status

```bash
curl http://localhost:8000/api/demo/status \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

### Run Visual Simulation (Watch Browser)

```bash
curl -X POST http://localhost:8000/api/demo/run \
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

### Run with Screenshot Capture

```bash
curl -X POST http://localhost:8000/api/demo/run \
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

### Test Failure Scenarios

```bash
# Configure mock to fail login
curl -X POST http://localhost:8000/api/demo/configure-mock \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"behavior": "login_fail"}'

# Run simulation
curl -X POST http://localhost:8000/api/demo/run \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "screenshot",
    "scenario": "check-in",
    "use_mock": true
  }'
```

## Configuration

Create `app/backend/.env.local`:

```env
# Screenshot storage
SCREENSHOT_STORAGE=local
LOCAL_SCREENSHOT_PATH=screenshots/simulations

# Mock server
BASE_URL=http://localhost:8000

# Development mode
ENABLE_DEBUG_LOGIN=1
DEV_SKIP_OIDC=1

# Firebase
FIREBASE_PROJECT_ID=iflow-robot
GOOGLE_CLOUD_PROJECT=iflow-robot
```

## Available Options

### Execution Modes
- **visual** - Opens browser window (headless=false)
- **screenshot** - Captures screenshots at each step (headless)
- **backend** - Production mode (fast, no screenshots)

### Speed Settings
- **slow** - 2 second delays between steps
- **normal** - 0.5 second delays
- **fast** - No artificial delays

### Scenarios
- **check-in** - Simulate check-in
- **check-out** - Simulate check-out

### Locations
- **telemunca** - Remote work
- **birou** - Office

### Mock Behaviors
- **success** - Normal operation
- **login_fail** - Invalid credentials
- **timeout** - Slow responses (60s)
- **no_button** - Missing check-in button
- **submit_error** - Form submission fails

## Viewing Screenshots

Screenshots are saved locally at:
```
app/backend/screenshots/simulations/users/{uid}/{timestamp}/
```

Example:
```
screenshots/simulations/users/user123/2025-11-09T10-30-00/
├── step_00_navigate_to_login.png
├── step_01_login_form_detected.png
├── step_02_fill_credentials.png
└── ...
```

## Troubleshooting

### Backend won't start
```bash
# Check dependencies
pip install -r requirements.txt

# Check Playwright
playwright install chromium
```

### Tests fail
```bash
# Ensure virtual environment active
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Mock server not accessible
```bash
# Check server is running
curl http://localhost:8000/health

# Should return: {"ok": true, "project": "iflow-robot"}
```

### Screenshots not captured
```bash
# Check environment variable
echo $SCREENSHOT_STORAGE  # Should be "local"

# Check directory exists
ls screenshots/simulations/
```

## Integration with Frontend

### Example React Hook

```typescript
import { useState } from 'react';
import { api } from '@/lib/api';

function useSimulation() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const runSimulation = async (params) => {
    setLoading(true);
    try {
      const response = await api.post('/demo/run', params);
      setResult(response.data);
      return response.data;
    } catch (error) {
      console.error('Simulation failed:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return { runSimulation, loading, result };
}

// Usage
function DemoPage() {
  const { runSimulation, loading, result } = useSimulation();

  const handleRun = () => {
    runSimulation({
      mode: 'screenshot',
      speed: 'normal',
      scenario: 'check-in',
      location: 'telemunca',
      use_mock: true,
      mock_behavior: 'success'
    });
  };

  return (
    <div>
      <button onClick={handleRun} disabled={loading}>
        {loading ? 'Running...' : 'Run Simulation'}
      </button>

      {result && (
        <div>
          <h3>Success: {result.success ? 'Yes' : 'No'}</h3>
          <p>Duration: {result.duration_ms}ms</p>
          <p>Steps: {result.step_count}</p>

          {result.steps.map(step => (
            <div key={step.step_number}>
              <strong>{step.name}</strong>: {step.message}
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

## Python Script Example

```python
import requests

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "your_firebase_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Run simulation
response = requests.post(
    f"{BASE_URL}/api/demo/run",
    headers=headers,
    json={
        "mode": "screenshot",
        "speed": "normal",
        "scenario": "check-in",
        "location": "telemunca",
        "use_mock": True,
        "mock_behavior": "success"
    }
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Duration: {result['duration_ms']}ms")
print(f"Steps: {result['step_count']}")

# Display steps
for step in result['steps']:
    print(f"{step['step_number']}: {step['name']} - {step['status']}")
    print(f"  {step['message']}")
    if step['screenshot_url']:
        print(f"  Screenshot: {step['screenshot_url']}")
```

## Documentation

- **DEMO_SYSTEM.md** - Complete documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical overview
- **QUICK_START.md** - This file

## Support

For issues or questions:
1. Check test suite: `python test_demo_system.py`
2. Review logs in console
3. Check `DEMO_SYSTEM.md` for detailed troubleshooting
