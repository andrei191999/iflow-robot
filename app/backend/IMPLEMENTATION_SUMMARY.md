# iFlow Simulation Backend - Implementation Summary

## Overview

Successfully implemented a complete simulation and demo system for the iFlow Robot automation platform. This system allows users to test the automation workflow in a controlled environment before running against the real iFlow HR platform.

## What Was Built

### 1. Screenshot Storage Service (`services/screenshot_storage.py`)

**Purpose**: Manage screenshot storage across Firebase Storage (production) and local filesystem (development).

**Features**:
- Dual-mode operation (Firebase/local) via environment variable
- Automatic signed URL generation for Firebase Storage
- Relative path generation for local development
- Auto-cleanup of screenshots older than retention period (7 days default)
- Per-user, per-simulation organized directory structure

**Key Methods**:
- `save_screenshot()` - Save PNG screenshot with metadata
- `get_simulation_screenshots()` - List all screenshots for a simulation
- `cleanup_old_screenshots()` - Remove old files based on retention policy

**Configuration**:
```env
SCREENSHOT_STORAGE=local              # or "firebase"
LOCAL_SCREENSHOT_PATH=screenshots/simulations
FIREBASE_STORAGE_BUCKET=iflow-robot.appspot.com
SCREENSHOT_RETENTION_DAYS=7
```

### 2. Demo Schemas (`schemas/demo.py`)

**Purpose**: Pydantic models for demo API request/response validation.

**Models**:
- `DemoRequest` - Input parameters for simulation runs
  - mode: visual, screenshot, backend
  - speed: slow, normal, fast
  - scenario: check-in, check-out
  - location: telemunca, birou
  - use_mock: boolean
  - mock_behavior: success, login_fail, timeout, no_button

- `SimulationStep` - Individual step in execution flow
  - step_number, name, timestamp, duration_ms
  - status (success/warning/error)
  - message, screenshot_url

- `DemoResult` - Complete simulation outcome
  - success, duration_ms, step_count
  - steps array, screenshots array
  - summary, error

### 3. Mock iFlow Server (`services/mock_iflow/`)

**Purpose**: Local replica of app.hriflow.ro with identical selectors and behavior.

**Components**:

#### `state.py` - Behavior Configuration
- `MockState` dataclass tracks behavior mode, delays, sessions, statistics
- `set_mock_behavior()` - Configure failure scenarios
- `reset_mock_state()` - Reset to defaults
- Behavior modes: success, login_fail, timeout, no_button, submit_error

#### `templates.py` - HTML Templates
- `get_login_page()` - Login form with exact selectors (`#td_reg_email`, `#td_reg_password`)
- `get_dashboard_page()` - Dashboard with check-in button and modal
- `get_success_page()` - Success confirmation page
- All templates use **identical CSS selectors** as real iFlow

#### `routes.py` - FastAPI Endpoints
- `GET /mock-iflow/login` - Display login page
- `POST /mock-iflow/login` - Process login with session cookie
- `GET /mock-iflow/dashboard` - Dashboard (requires session)
- `POST /mock-iflow/submit` - Process check-in/out form
- `GET /mock-iflow/stats` - Server statistics
- `POST /mock-iflow/reset` - Reset state
- `POST /mock-iflow/configure` - Change behavior mode

**Demo Credentials**:
- demo@example.com / demo123
- test@example.com / test123

### 4. Enhanced Automation (`services/iso_task_enhanced.py`)

**Purpose**: Extended version of `iso_task.py` with screenshot capture and detailed logging.

**Key Additions**:

#### `SimulationLogger` Class
- Captures step-by-step execution details
- Takes screenshots at each major step (optional)
- Applies speed-based delays (slow: 2s, normal: 0.5s, fast: 0s)
- Tracks total duration and step count
- Returns structured step logs with timestamps

#### `run_iso_check_enhanced()` Function
- Drop-in replacement for `run_iso_check()` with additional parameters
- `capture_screenshots` - Enable screenshot capture
- `speed` - Control execution speed
- `use_mock_url` - Override with mock server URL
- `screenshot_storage` - ScreenshotStorage instance
- `uid` / `timestamp` - For screenshot organization
- Returns: `(status, message, steps, duration_ms)`

**Integration**: Original `iso_task.py` remains unchanged for production use. Enhanced version used only for demo/testing.

### 5. Demo Router (`routers/demo.py`)

**Purpose**: API endpoints for running and managing simulations.

**Endpoints**:

#### `POST /api/demo/run` ⭐ Main Endpoint
- **Authentication**: Firebase user token required
- **Request**: DemoRequest model
- **Response**: DemoResult model with full step logs and screenshots

**Process**:
1. Validates user authentication
2. Configures mock server behavior if requested
3. Determines headless mode based on execution mode
4. Initializes screenshot storage if needed
5. Calls `run_iso_check_enhanced()` with configuration
6. Returns detailed results with step-by-step logs

**Example Request**:
```json
{
  "mode": "screenshot",
  "speed": "normal",
  "scenario": "check-in",
  "location": "telemunca",
  "use_mock": true,
  "mock_behavior": "success"
}
```

**Example Response**:
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
      "screenshot_url": "users/uid123/simulations/2025-11-09/step_00_navigate.png"
    }
  ],
  "screenshots": ["url1", "url2", ...],
  "summary": "Successfully completed check-in at telemunca in 5432ms (12 steps)."
}
```

#### `GET /api/demo/status`
- Returns available options and mock server statistics
- Shows current configuration and capabilities

#### `POST /api/demo/reset-mock`
- Resets mock server state and statistics
- Useful between test runs

#### `POST /api/demo/configure-mock`
- Changes mock server behavior mode
- Test different failure scenarios

### 6. Integration with Main App

**Modified Files**:
- `core/app.py` - Registered demo router and mock iFlow router
- `requirements.txt` - Added `python-multipart` dependency

**New Routes**:
```
/api/demo/run              # Run simulation
/api/demo/status           # Get status
/api/demo/reset-mock       # Reset mock
/api/demo/configure-mock   # Configure mock

/mock-iflow/login         # Mock login page
/mock-iflow/dashboard     # Mock dashboard
/mock-iflow/submit        # Mock form submission
/mock-iflow/stats         # Mock statistics
```

## File Structure

```
app/backend/
├── core/
│   └── app.py                         [MODIFIED] - Registered routers
├── routers/
│   └── demo.py                        [NEW] - Demo API endpoints
├── schemas/
│   └── demo.py                        [NEW] - Request/response models
├── services/
│   ├── iso_task.py                    [UNCHANGED] - Original automation
│   ├── iso_task_enhanced.py           [NEW] - Enhanced with screenshots
│   ├── screenshot_storage.py          [NEW] - Storage management
│   └── mock_iflow/                    [NEW]
│       ├── __init__.py
│       ├── routes.py                  - Mock iFlow endpoints
│       ├── templates.py               - HTML templates
│       └── state.py                   - Behavior configuration
├── screenshots/                       [NEW]
│   └── simulations/                   - Local screenshot storage
├── requirements.txt                   [MODIFIED] - Added python-multipart
├── test_demo_system.py                [NEW] - Test suite
├── DEMO_SYSTEM.md                     [NEW] - User documentation
└── IMPLEMENTATION_SUMMARY.md          [NEW] - This file
```

## Testing

**Test Suite**: `test_demo_system.py`

**Tests**:
1. ✅ Import verification (all modules load correctly)
2. ✅ Schema validation (Pydantic models work)
3. ✅ Mock state management (behavior configuration)
4. ✅ Template generation (HTML with correct selectors)
5. ✅ Screenshot storage (save/list/cleanup)
6. ✅ Simulation logger (step tracking)

**Run Tests**:
```bash
cd app/backend
python test_demo_system.py
```

**Result**: All 6/6 tests passing ✅

## Key Features

### 1. Exact Selector Matching
Mock iFlow uses **identical CSS selectors** as real iFlow:
- `#td_reg_email` - Email input
- `#td_reg_password` - Password input
- `button:has-text("Intră în cont")` - Login button
- `.td-checkin-modal .modal-body` - Modal
- `.td-select-single-button` - Location dropdown
- `#td-ckeck-in-out-end-time-67` - Check-in time
- `#td-ckeck-in-out-start-time-67` - Check-out time

This ensures automation code works identically in mock and production.

### 2. Configurable Failure Modes
Test edge cases and error handling:
- **success**: Normal operation
- **login_fail**: Invalid credentials scenario
- **timeout**: Slow response simulation
- **no_button**: Missing UI element
- **submit_error**: Form submission failure

### 3. Visual Debugging
Three execution modes:
- **visual**: Watch browser (headless=false)
- **screenshot**: Capture every step
- **backend**: Production mode (fast, no screenshots)

### 4. Speed Control
Adjust execution speed for observation:
- **slow**: 2 second delays (good for watching)
- **normal**: 0.5 second delays
- **fast**: No delays (production speed)

### 5. Detailed Logging
Every simulation returns:
- Step-by-step execution log
- Timestamps and durations
- Success/warning/error status per step
- Screenshot URLs (if captured)
- Total duration and step count

### 6. Production-Ready Storage
- **Development**: Local filesystem with auto-created directories
- **Production**: Firebase Storage with signed URLs
- **Auto-cleanup**: Old screenshots deleted after retention period
- **Organized**: Per-user, per-simulation directory structure

## Usage Examples

### Visual Mode (Watch Browser)
```bash
curl -X POST http://localhost:8000/api/demo/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "visual",
    "speed": "slow",
    "scenario": "check-in",
    "location": "telemunca",
    "use_mock": true
  }'
```

### Screenshot Capture
```bash
curl -X POST http://localhost:8000/api/demo/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "screenshot",
    "speed": "normal",
    "scenario": "check-in",
    "use_mock": true
  }'
```

### Test Failure Scenario
```bash
# Configure mock to fail
curl -X POST http://localhost:8000/api/demo/configure-mock \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"behavior": "login_fail"}'

# Run simulation
curl -X POST http://localhost:8000/api/demo/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "screenshot",
    "scenario": "check-in",
    "use_mock": true
  }'
```

## Environment Configuration

### Development (Local)
```env
# Backend (.env.local)
SCREENSHOT_STORAGE=local
LOCAL_SCREENSHOT_PATH=screenshots/simulations
BASE_URL=http://localhost:8000
ENABLE_DEBUG_LOGIN=1
DEV_SKIP_OIDC=1
```

### Production (Cloud Run)
```env
# Set via Cloud Run environment variables
SCREENSHOT_STORAGE=firebase
FIREBASE_STORAGE_BUCKET=iflow-robot.appspot.com
SCREENSHOT_RETENTION_DAYS=7
BASE_URL=https://iso-backend-xxx.run.app
ENABLE_DEBUG_LOGIN=0
DEV_SKIP_OIDC=0
```

## Security Considerations

1. **Authentication Required**: All demo endpoints require valid Firebase user tokens
2. **User Isolation**: Screenshots stored per-user (uid-based paths)
3. **Temporary Storage**: Auto-cleanup prevents unlimited storage growth
4. **Mock Only**: Real iFlow testing requires proper credentials (not implemented in demo for security)
5. **Debug Mode**: Mock server shows credentials in UI (development only)

## Performance

- **Fast Mode**: ~3-5 seconds for complete check-in flow (mock server)
- **Normal Mode**: ~5-10 seconds with delays
- **Screenshot Capture**: Adds ~100-200ms per screenshot
- **Memory**: Playwright requires ~2GB RAM (Cloud Run setting)

## Dependencies Added

```
python-multipart  # For FastAPI Form handling
```

All other dependencies were already in `requirements.txt`.

## Next Steps / Future Enhancements

### Frontend Integration
- React component for demo page
- Step-by-step visualization with thumbnails
- Real-time progress updates
- Screenshot gallery view

### Advanced Features
- WebSocket streaming for live step updates
- Video recording of entire simulation
- Parallel execution of multiple scenarios
- Diff comparison (successful vs failed runs)
- PDF report generation
- Scheduled regression testing

### Production Readiness
- Add real iFlow testing with user's actual credentials
- Implement credential encryption in Firestore
- Add rate limiting on demo endpoints
- Monitor and alert on simulation failures
- CI/CD integration for automated testing

## Troubleshooting

### Screenshots Not Saved
- Check `SCREENSHOT_STORAGE` environment variable
- Verify Firebase Admin SDK initialized
- Check service account permissions (Storage Admin role)
- For local mode, check directory write permissions

### Mock Server Not Working
- Verify routes registered in `core/app.py`
- Check `python-multipart` installed
- Test: `curl http://localhost:8000/mock-iflow/stats`

### Tests Failing
- Ensure virtual environment activated
- Install dependencies: `pip install -r requirements.txt`
- Check Python version (3.10+)
- Windows: Unicode encoding issue (script handles this)

## Documentation

- **DEMO_SYSTEM.md** - Comprehensive user documentation
- **IMPLEMENTATION_SUMMARY.md** - This file (technical overview)
- **test_demo_system.py** - Automated test suite with examples
- **Code comments** - All files well-documented with docstrings

## Summary

✅ Complete simulation backend system implemented
✅ Mock iFlow server with exact selector matching
✅ Screenshot capture with dual storage modes
✅ Detailed step-by-step logging
✅ Multiple execution modes and speeds
✅ Configurable failure scenarios for testing
✅ Production-ready authentication and security
✅ Comprehensive test suite (6/6 passing)
✅ Full documentation and examples
✅ Zero breaking changes to existing code

The system is ready for integration with the frontend and deployment to Cloud Run.
