# iFlow Robot

An automated time-tracking system that performs check-ins and check-outs on the iFlow HR platform using browser automation.

## Overview

iFlow Robot allows users to automate their daily check-in and check-out routines on the iFlow HR platform (app.hriflow.ro). Users create schedules through a web interface, and a Cloud Scheduler cron job executes the automation at scheduled times using headless browser automation.

### Key Features

- **Automated Check-In/Out**: Browser automation using Playwright to interact with iFlow
- **Flexible Scheduling**: Weekly patterns with customizable times per day
- **Smart Scheduling**:
  - Randomization (jitter) to make check-ins appear more natural
  - Public holiday detection (supports multiple countries)
  - Personal holiday management
  - Date/time exceptions (include/exclude specific dates or time windows)
- **Per-User Settings**: Each user stores their own iFlow credentials securely
- **Execution History**: Complete audit trail of all automation runs
- **Multi-User Support**: Each user has isolated schedules and settings

## Architecture

- **Backend**: FastAPI (Python) + Playwright for browser automation
- **Frontend**: React + TypeScript + Vite
- **Database**: Google Cloud Firestore
- **Authentication**: Firebase Authentication (email/password)
- **Deployment**:
  - Backend: Google Cloud Run
  - Frontend: Firebase Hosting
  - Scheduler: Google Cloud Scheduler

## Project Structure

```
iflow-robot/
├── app/
│   ├── backend/          # FastAPI backend
│   │   ├── core/         # App initialization, DB, security
│   │   ├── routers/      # API endpoints
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Business logic
│   │   └── tests/        # Unit and API tests
│   └── pyproject.toml    # Python project config
├── web/                  # React frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── contexts/     # React contexts (Auth)
│   │   ├── lib/          # API client, Firebase config
│   │   ├── pages/        # Route components
│   │   └── types/        # TypeScript types
│   └── package.json
├── firebase.json         # Firebase config
├── firestore.rules       # Firestore security rules
└── firestore.indexes.json # Firestore indexes
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Cloud account with Firestore enabled
- Firebase project configured

### Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd app/backend
pip install -r requirements.txt
playwright install chromium

# Configure environment
cp .env.example .env.local
# Edit .env.local with your credentials

# Start development server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd web

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your backend URL

# Start development server
npm run dev
```

### Running Tests

```bash
# Backend tests
cd app/backend
python -m pytest

# With coverage
python -m pytest --cov=. --cov-report=html
```

## Deployment

### Backend (Cloud Run)

```bash
cd app/backend
gcloud run deploy iso-backend \
  --source . \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 60s
```

### Frontend (Firebase Hosting)

```bash
cd web
npm run build
cd ..
firebase deploy --only hosting
```

### Firestore

```bash
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes
```

### Cloud Scheduler

Create a cron job to hit `/cron/tick` every minute with OIDC authentication.

## Key Technologies

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Playwright**: Browser automation library
- **Google Cloud Firestore**: NoSQL document database
- **Firebase Admin SDK**: Server-side Firebase integration
- **python-dateutil**: Date/time handling
- **croniter**: Cron expression parsing
- **holidays**: Public holiday calculation

### Frontend
- **React 19**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Tailwind CSS 4**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **React Router**: Client-side routing
- **Firebase SDK**: Client-side Firebase integration
- **date-fns**: Date utility library
- **Zod**: TypeScript-first schema validation

## Security Notes

- **Credentials**: iFlow credentials are stored in Firestore (not encrypted - consider adding encryption)
- **Authentication**: Firebase Authentication with ID token verification
- **Authorization**: Firestore security rules enforce per-user data isolation
- **OIDC**: Cloud Scheduler uses OIDC tokens for authenticated requests to backend
- **Environment Variables**: Never commit `.env.local` files or service account keys

## Contributing

This is a personal automation project. If you'd like to use it:

1. Fork the repository
2. Set up your own Firebase and Google Cloud projects
3. Configure your own credentials
4. Customize for your iFlow instance

## License

This project is for personal use. Not licensed for redistribution.

## Disclaimer

This tool automates interactions with the iFlow platform. Use at your own risk. Ensure compliance with your organization's policies regarding automated time tracking.
