# Smart Payment Advisor ⚡

Smart Payment Advisor is an AI-powered payment intelligence and dynamic routing engine designed to minimize checkout friction, eliminate transaction drop-offs, and reduce merchant fees. By analyzing rolling 2-hour transaction windows with exponential recency weighting and statistical anomaly detection, the platform dynamically re-ranks payment options in real time, steering customers away from failing bank gateways before they experience checkout failures.

## 🏗️ Architecture Overview

```
                        +---------------------------------------+
                        |           React + Vite Frontend       |
                        | (Tailwind CSS, WebSockets, Realtime)  |
                        +-------------------+-------------------+
                                            |
                                            | HTTP REST API & WS
                                            v
                        +-------------------+-------------------+
                        |            FastAPI Backend            |
                        | (Routing Engine, Anomaly Detector,    |
                        |   Rate Limiter, Error Resilience)     |
                        +---------+-------------------+---------+
                                  |                   |
                        SQLite DB |                   | Razorpay SDK
                                  v                   v
                        +---------+-------+   +-------+---------+
                        | payments.db     |   | Razorpay PG /   |
                        | Transactions Log|   | Simulation Mode |
                        +-----------------+   +-----------------+
```

## ⚡ Key Features

- **Dynamic AI Recommendation Engine**: Ranks payment options based on real-time success probability, transaction cost in INR, and confidence intervals (p ± SE).
- **Database-Level Windowed Aggregations**: Uses direct SQLite aggregate queries for fast rolling window computations.
- **Exponential Recency Weighting**: Time-decay weighting (w = e^(−0.0277 × age)) where 5-minute-old data has 2x the influence of 30-minute-old data.
- **Statistical Anomaly Detection**: Detects genuine downtime spikes when a method drops >30% below its own historical baseline.
- **Live Outage & Downtime Simulator**: Inject artificial bank outage spikes and observe immediate AI re-ranking without page refresh.
- **Multi-Merchant Support**: Configurable payment capabilities for ABC College Fee Portal, E-Commerce Store, and Electricity Bill Portal.
- **Real-Time Analytics Dashboard**: Tracks overall success rate, top failing payment methods, and estimated merchant fee savings in INR.
- **Full Razorpay Integration**: Native checkout widget integration with fallback simulation mode when API credentials are absent.

## 🛠️ Tech Stack Summary

- **Backend**: Python 3.13, FastAPI, SQLite3, Pydantic v2, Uvicorn, WebSockets
- **Frontend**: React 19, Vite, Tailwind CSS v4
- **Payment Gateway**: Razorpay Payment Gateway Python SDK

## 🚀 Setup & Run Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI dev server (default port 8000)
python -m uvicorn main:app --reload --port 8000
```

> If port 8000 is already in use, pass any free port instead (e.g. `--port 8080`) — just make sure the frontend's API base URL is updated to match.

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run Vite dev server
npm run dev
```

Open `http://localhost:5173` in your browser.

> If port 5173 is already in use, Vite will automatically pick the next free port (e.g. `5174`) and print the correct URL in the terminal — always use the URL shown in your terminal output, not a hardcoded one.

### 3. Environment Variables

Create a `.env` file inside `backend/` with your Razorpay API credentials:

```
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

If these are not set, the backend automatically falls back to **simulation mode** — all payment flows work end-to-end using generated data, no live Razorpay account required for local testing.

## 🤖 How the Demo Works

On startup, the backend automatically launches two background workers — no manual triggering needed to see the system live:

- **Transaction Simulator**: Continuously generates realistic multi-factor transactions (varying bank, method, amount, time-of-day) and periodically injects artificial bank/method outages so you can watch the AI re-rank payment options in real time.
- **ML Retrain Worker**: Runs every 5 minutes, checking whether enough new transaction data has accumulated to justify retraining the model (see [Known Issues](#-known-issues--warnings) below for the retrain guard logic).

This means you can open the dashboard right after starting the backend and immediately see live activity, without needing real Razorpay transactions.

## 🛡️ Security Hygiene & Resilience

- **Strict Input Validation**: Pydantic models validate amounts (₹1 to ₹1,000,000) and safe alphanumeric receipt IDs.
- **CORS Protection**: Restricted strictly to local development origins.
- **In-Memory Rate Limiting**: Max 10 requests/minute per IP on simulation and order creation endpoints (returns HTTP 429).
- **Graceful Error Resilience**: Structured HTTP error responses (400, 404, 503, 500) and React Error Boundary fallback UI.

## ⚠️ Known Issues & Warnings

- **scikit-learn version pinning**: The persisted model (`.pkl`) was trained on `scikit-learn==1.7.1`. Installing a newer scikit-learn (e.g. 1.9.x) will unpickle the model with an `InconsistentVersionWarning` and may break the ML guard's metadata check (`No module named '_loss'`). To avoid this, make sure `requirements.txt` pins:
  ```
  scikit-learn==1.7.1
  ```
  If you intentionally upgrade scikit-learn, force a full retrain via `/api/retrain-model` instead of relying on the persisted model.
- **Auto-retrain guard**: The ML retrain worker only retrains automatically once new data is at least 20% larger than the data the current model was trained on. Until that threshold is hit, you'll see `[ML GUARD] Skipping auto-retrain` in the logs — this is expected behavior, not an error. Use `POST /api/retrain-model` to force a retrain manually at any time.

## About

Real-time payment intelligence system — pre-payment method recommendation + post-failure diagnosis & recovery, built on Razorpay.

### Resources

- Readme
- Activity
- Stars: 0
- Watchers: 0
- Forks: 0
- Releases: No releases published

### Contributors

1 ([@SomyaSarswat](https://github.com/SomyaSarswat))

### Languages

- Python: 65.3%
- JavaScript: 33.2%
- CSS: 1.3%
- HTML: 0.2%
