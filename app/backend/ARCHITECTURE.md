# iFlow Simulation System - Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Demo Page    │  │ Schedule Mgmt│  │ Settings     │          │
│  │ UI Component │  │ Dashboard    │  │ Page         │          │
│  └──────┬───────┘  └──────────────┘  └──────────────┘          │
│         │                                                        │
│         │ POST /api/demo/run                                    │
│         │ (DemoRequest JSON)                                    │
└─────────┼────────────────────────────────────────────────────────┘
          │
          │ Firebase ID Token (Authentication)
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Cloud Run)                   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Security Middleware                            │ │
│  │  - Verify Firebase ID Token                                │ │
│  │  - Extract user UID                                         │ │
│  └────────────────────┬───────────────────────────────────────┘ │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                Demo Router                                  │ │
│  │  /routers/demo.py                                           │ │
│  │                                                             │ │
│  │  POST /api/demo/run                                         │ │
│  │  - Validate DemoRequest                                     │ │
│  │  - Configure mock server behavior                           │ │
│  │  - Initialize screenshot storage                            │ │
│  │  - Call iso_task_enhanced                                   │ │
│  │  - Return DemoResult                                        │ │
│  └────────────────────┬───────────────────────────────────────┘ │
│                       │                                          │
│                       ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         Enhanced Automation Engine                          │ │
│  │  /services/iso_task_enhanced.py                             │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ SimulationLogger                                      │  │ │
│  │  │ - Track steps with timestamps                         │  │ │
│  │  │ - Capture screenshots at each step                    │  │ │
│  │  │ - Apply speed-based delays                            │  │ │
│  │  │ - Build detailed execution log                        │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ run_iso_check_enhanced()                              │  │ │
│  │  │ 1. Launch Playwright browser                          │  │ │
│  │  │ 2. Navigate to login page → Screenshot                │  │ │
│  │  │ 3. Fill credentials → Screenshot                      │  │ │
│  │  │ 4. Submit login → Screenshot                          │  │ │
│  │  │ 5. Open check-in modal → Screenshot                   │  │ │
│  │  │ 6. Select location → Screenshot                       │  │ │
│  │  │ 7. Submit form → Screenshot                           │  │ │
│  │  │ 8. Verify success → Screenshot                        │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────┘ │
│                       │                                          │
│         ┌─────────────┴─────────────┐                           │
│         │                           │                           │
│         ▼                           ▼                           │
│  ┌─────────────┐            ┌─────────────┐                    │
│  │ Mock iFlow  │            │ Real iFlow  │                    │
│  │ Server      │            │ Server      │                    │
│  └─────────────┘            └─────────────┘                    │
└──────────────────┬────────────────────────────────────────────┘
                   │
                   │ Save Screenshots
                   ▼
         ┌────────────────────┐
         │ Screenshot Storage │
         ├────────────────────┤
         │  Firebase Storage  │  (Production)
         │        OR          │
         │  Local Filesystem  │  (Development)
         └────────────────────┘
```

## Component Details

### 1. Frontend Layer

```
┌──────────────────────────────────────┐
│         Demo UI Component            │
├──────────────────────────────────────┤
│                                      │
│  [Configuration Form]                │
│   ┌────────────────────────────┐    │
│   │ Mode: [screenshot ▼]       │    │
│   │ Speed: [normal ▼]          │    │
│   │ Scenario: [check-in ▼]     │    │
│   │ Location: [telemunca ▼]    │    │
│   │ Use Mock: [✓]              │    │
│   │ Behavior: [success ▼]      │    │
│   └────────────────────────────┘    │
│                                      │
│  [Run Simulation Button]             │
│                                      │
│  [Results Display]                   │
│   ┌────────────────────────────┐    │
│   │ Success: Yes               │    │
│   │ Duration: 5432ms           │    │
│   │ Steps: 12                  │    │
│   │                            │    │
│   │ Step-by-Step Log:          │    │
│   │  0: navigate_to_login      │    │
│   │     [screenshot thumbnail] │    │
│   │  1: login_form_detected    │    │
│   │     [screenshot thumbnail] │    │
│   │  ...                       │    │
│   └────────────────────────────┘    │
└──────────────────────────────────────┘
```

### 2. Mock iFlow Server Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Mock iFlow Server                       │
│                /services/mock_iflow/                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Step 1: Login Page                                     │
│  ┌────────────────────────────────────────────┐         │
│  │  GET /mock-iflow/login                     │         │
│  │  ┌──────────────────────────────────────┐  │         │
│  │  │  Email: [____________]               │  │         │
│  │  │           #td_reg_email              │  │         │
│  │  │                                      │  │         │
│  │  │  Password: [____________]            │  │         │
│  │  │            #td_reg_password          │  │         │
│  │  │                                      │  │         │
│  │  │  [Intră în cont]                     │  │         │
│  │  │   (button:has-text)                  │  │         │
│  │  └──────────────────────────────────────┘  │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     │ POST /mock-iflow/login             │
│                     │ (username, password)               │
│                     ▼                                    │
│  ┌────────────────────────────────────────────┐         │
│  │  state.is_valid_login()                    │         │
│  │  - Check credentials                       │         │
│  │  - Create session cookie                   │         │
│  │  - Redirect to dashboard                   │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     ▼                                    │
│  Step 2: Dashboard                                      │
│  ┌────────────────────────────────────────────┐         │
│  │  GET /mock-iflow/dashboard                 │         │
│  │  ┌──────────────────────────────────────┐  │         │
│  │  │  Welcome!                            │  │         │
│  │  │                                      │  │         │
│  │  │  [Înregistrează Pontaj]              │  │         │
│  │  │   (check-in button)                  │  │         │
│  │  │   Opens modal on click               │  │         │
│  │  └──────────────────────────────────────┘  │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     │ Click button (opens modal)         │
│                     ▼                                    │
│  Step 3: Modal                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  Modal (visible)                           │         │
│  │  ┌──────────────────────────────────────┐  │         │
│  │  │  Location: [Telemunca ▼]             │  │         │
│  │  │            (.td-select-single-button)│  │         │
│  │  │                                      │  │         │
│  │  │  Check-in Time: [09:00]              │  │         │
│  │  │  #td-ckeck-in-out-end-time-67        │  │         │
│  │  │                                      │  │         │
│  │  │  Check-out Time: [18:00]             │  │         │
│  │  │  #td-ckeck-in-out-start-time-67      │  │         │
│  │  │                                      │  │         │
│  │  │  [Trimite]                           │  │         │
│  │  │   (submit button)                    │  │         │
│  │  └──────────────────────────────────────┘  │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     │ POST /mock-iflow/submit            │
│                     ▼                                    │
│  ┌────────────────────────────────────────────┐         │
│  │  Success Page                              │         │
│  │  ┌──────────────────────────────────────┐  │         │
│  │  │  ✓ Pontaj înregistrat cu succes!     │  │         │
│  │  └──────────────────────────────────────┘  │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### 3. Screenshot Storage Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Screenshot Storage Service                   │
│           /services/screenshot_storage.py                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Environment Variable: SCREENSHOT_STORAGE                 │
│         │                                                 │
│         ├─── "firebase" ──────────────────────┐          │
│         │                                      │          │
│         │                                      ▼          │
│         │                   ┌──────────────────────────┐ │
│         │                   │  Firebase Storage        │ │
│         │                   │                          │ │
│         │                   │  Path Structure:         │ │
│         │                   │  users/                  │ │
│         │                   │    {uid}/                │ │
│         │                   │      simulations/        │ │
│         │                   │        {timestamp}/      │ │
│         │                   │          step_00.png     │ │
│         │                   │          step_01.png     │ │
│         │                   │          ...             │ │
│         │                   │                          │ │
│         │                   │  Returns: Signed URLs    │ │
│         │                   │  (7-day expiration)      │ │
│         │                   └──────────────────────────┘ │
│         │                                                │
│         │                                                │
│         └─── "local" ──────────────────────┐            │
│                                             │            │
│                                             ▼            │
│                            ┌──────────────────────────┐  │
│                            │  Local Filesystem        │  │
│                            │                          │  │
│                            │  Path: screenshots/      │  │
│                            │    simulations/          │  │
│                            │      users/              │  │
│                            │        {uid}/            │  │
│                            │          {timestamp}/    │  │
│                            │            step_00.png   │  │
│                            │            step_01.png   │  │
│                            │            ...           │  │
│                            │                          │  │
│                            │  Returns: Relative paths │  │
│                            └──────────────────────────┘  │
│                                                           │
│  Methods:                                                 │
│  - save_screenshot(uid, timestamp, step_num, data)        │
│  - get_simulation_screenshots(uid, timestamp)             │
│  - cleanup_old_screenshots(uid?)                          │
│                                                           │
│  Auto-Cleanup: Deletes screenshots > 7 days old          │
└──────────────────────────────────────────────────────────┘
```

### 4. Execution Flow with Steps

```
┌─────────────────────────────────────────────────────────────┐
│           run_iso_check_enhanced() Execution Flow           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input Parameters:                                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ event_type: "checkIn"                                 │ │
│  │ location: "telemunca"                                 │ │
│  │ capture_screenshots: true                             │ │
│  │ speed: "normal" (500ms delays)                        │ │
│  │ use_mock_url: "http://localhost:8000/mock-iflow"     │ │
│  │ uid: "user123"                                        │ │
│  │ timestamp: "2025-11-09T10-30-00"                      │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ SimulationLogger Initialization                       │ │
│  │ - Initialize step counter                             │ │
│  │ - Set speed delays (500ms)                            │ │
│  │ - Start timer                                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 0: validate_config                               │ │
│  │ Duration: 5ms                                          │ │
│  │ Status: success                                        │ │
│  │ Message: "Configuration validated"                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 1: browser_launched                              │ │
│  │ Duration: 234ms                                        │ │
│  │ Status: success                                        │ │
│  │ Screenshot: step_01_browser_launched.png              │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼ [Delay 500ms]                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 2: navigate_to_login                             │ │
│  │ Duration: 345ms                                        │ │
│  │ Status: success                                        │ │
│  │ Screenshot: step_02_navigate_to_login.png             │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼ [Delay 500ms]                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 3: login_form_detected                           │ │
│  │ Duration: 45ms                                         │ │
│  │ Status: success                                        │ │
│  │ Screenshot: step_03_login_form_detected.png           │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼ [Delay 500ms]                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 4: fill_credentials                              │ │
│  │ Duration: 123ms                                        │ │
│  │ Status: success                                        │ │
│  │ Screenshot: step_04_fill_credentials.png              │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                        [... more steps ...]                 │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Step 11: verify_success                               │ │
│  │ Duration: 67ms                                         │ │
│  │ Status: success                                        │ │
│  │ Screenshot: step_11_verify_success.png                │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  Output:                                                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ status: "success"                                     │ │
│  │ message: "Check-in successful at location=telemunca"  │ │
│  │ steps: [12 SimulationStep objects]                    │ │
│  │ duration_ms: 5432                                     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 5. Data Flow

```
                        REQUEST
                           │
    ┌──────────────────────┴──────────────────────┐
    │                                              │
    │   POST /api/demo/run                         │
    │   {                                          │
    │     "mode": "screenshot",                    │
    │     "speed": "normal",                       │
    │     "scenario": "check-in",                  │
    │     "location": "telemunca",                 │
    │     "use_mock": true                         │
    │   }                                          │
    │                                              │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │      Validate DemoRequest Schema           │
    │      Extract user UID from token           │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │      Configure Mock Server                 │
    │      set_mock_behavior("success")          │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │      Initialize Screenshot Storage         │
    │      storage = get_screenshot_storage()    │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │   Call run_iso_check_enhanced()            │
    │   - Launch browser                         │
    │   - Execute automation                     │
    │   - Capture screenshots                    │
    │   - Build step logs                        │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │   Each step:                               │
    │   1. Execute action (navigate, click)      │
    │   2. Capture screenshot → storage.save()   │
    │   3. Log to SimulationLogger               │
    │   4. Apply delay based on speed            │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌────────────────────────────────────────────┐
    │   Build DemoResult                         │
    │   {                                        │
    │     success: true,                         │
    │     duration_ms: 5432,                     │
    │     steps: [...],                          │
    │     screenshots: [...]                     │
    │   }                                        │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
                       RESPONSE
```

## Security Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Security Layers                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Layer 1: Firebase Authentication                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Frontend: User signs in with Firebase Auth        │  │
│  │ Token: ID token generated                         │  │
│  │ Header: Authorization: Bearer {id_token}          │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│                         ▼                                 │
│  Layer 2: Token Verification                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Middleware: require_firebase_user()                │  │
│  │ - Verify token signature                           │  │
│  │ - Check expiration                                 │  │
│  │ - Extract UID and email                            │  │
│  │ - Reject if invalid                                │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│                         ▼                                 │
│  Layer 3: User Isolation                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Storage: Screenshots saved to users/{uid}/...      │  │
│  │ Firestore: Rules enforce uid-based access          │  │
│  │ API: User can only access their own data           │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│                         ▼                                 │
│  Layer 4: Rate Limiting (Future)                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Limit simulations per user per hour                │  │
│  │ Prevent abuse of screenshot storage                 │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Production Setup                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Frontend                                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Firebase Hosting                                  │  │
│  │  - Serves React SPA                                │  │
│  │  - CDN distribution                                │  │
│  │  - HTTPS by default                                │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│                         │ API Calls                       │
│                         ▼                                 │
│  Backend                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Cloud Run                                         │  │
│  │  - FastAPI application                             │  │
│  │  - Auto-scaling (0 to N instances)                 │  │
│  │  - 2Gi memory (for Playwright)                     │  │
│  │  - 60s timeout (adjustable)                        │  │
│  │                                                    │  │
│  │  Environment:                                      │  │
│  │  - SCREENSHOT_STORAGE=firebase                     │  │
│  │  - ENABLE_DEBUG_LOGIN=0                            │  │
│  │  - DEV_SKIP_OIDC=0                                 │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│                         │ Storage                         │
│                         ▼                                 │
│  Storage                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Firebase Storage                                  │  │
│  │  - Screenshot PNG files                            │  │
│  │  - Signed URLs (7-day expiry)                      │  │
│  │  - Auto-cleanup lifecycle rules                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  Database                                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Cloud Firestore                                   │  │
│  │  - User settings (credentials)                     │  │
│  │  - Schedules                                       │  │
│  │  - Execution history (runs)                        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Technology Stack

```
┌──────────────────────────────────────────────────────────┐
│                   Technology Stack                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Frontend:                                                │
│  - React 18                                               │
│  - TypeScript                                             │
│  - Vite (build tool)                                      │
│  - Tailwind CSS                                           │
│                                                           │
│  Backend:                                                 │
│  - Python 3.10+                                           │
│  - FastAPI (async web framework)                          │
│  - Pydantic (data validation)                             │
│  - Playwright (browser automation)                        │
│  - Firebase Admin SDK                                     │
│                                                           │
│  Storage:                                                 │
│  - Firebase Storage (cloud)                               │
│  - Local filesystem (dev)                                 │
│                                                           │
│  Database:                                                │
│  - Cloud Firestore (NoSQL)                                │
│                                                           │
│  Authentication:                                          │
│  - Firebase Authentication                                │
│                                                           │
│  Deployment:                                              │
│  - Cloud Run (backend)                                    │
│  - Firebase Hosting (frontend)                            │
│                                                           │
│  Testing:                                                 │
│  - pytest                                                 │
│  - Custom test suite                                      │
└──────────────────────────────────────────────────────────┘
```
