# Smart Payment Advisor ⚡

**Smart Payment Advisor** is an AI-powered payment intelligence and dynamic routing engine designed to minimize checkout friction, eliminate transaction drop-offs, and reduce merchant fees. By analyzing rolling 2-hour transaction windows with exponential recency weighting and statistical anomaly detection, the platform dynamically re-ranks payment options in real time, steering customers away from failing bank gateways before they experience checkout failures.

---

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

---

## ⚡ Key Features

- **Dynamic AI Recommendation Engine**: Ranks payment options based on real-time success probability, transaction cost in INR, and confidence intervals ($p \pm \text{SE}$).
- **Database-Level Windowed Aggregations**: Uses direct SQLite aggregate queries for fast rolling window computations.
- **Exponential Recency Weighting**: Time-decay weighting ($w = e^{-0.0277 \times \text{age}}$) where 5-minute-old data has 2x the influence of 30-minute-old data.
- **Statistical Anomaly Detection**: Detects genuine downtime spikes when a method drops $>30\%$ below its own historical baseline.
- **Live Outage & Downtime Simulator**: Inject artificial bank outage spikes and observe immediate AI re-ranking without page refresh.
- **Multi-Merchant Support**: Configurable payment capabilities for ABC College Fee Portal, E-Commerce Store, and Electricity Bill Portal.
- **Real-Time Analytics Dashboard**: Tracks overall success rate, top failing payment methods, and estimated merchant fee savings in INR.
- **Full Razorpay Integration**: Native checkout widget integration with fallback simulation mode when API credentials are absent.

---

## 🛠️ Tech Stack Summary

- **Backend**: Python 3.13, FastAPI, SQLite3, Pydantic v2, Uvicorn, WebSockets
- **Frontend**: React 19, Vite, Tailwind CSS v4
- **Payment Gateway**: Razorpay Payment Gateway Python SDK

---

## 🚀 Setup & Run Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+ and `npm`

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

# Run FastAPI dev server (Port 8080 or 8000)
python -m uvicorn main:app --reload --port 8080
```

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

---

## 🛡️ Security Hygiene & Resilience

- **Strict Input Validation**: Pydantic models validate amounts ($1$ to $1,000,000$ INR) and safe alphanumeric receipt IDs.
- **CORS Protection**: Restricted strictly to local development origins.
- **In-Memory Rate Limiting**: Max 10 requests/minute per IP on simulation and order creation endpoints (returns HTTP 429).
- **Graceful Error Resilience**: Structured HTTP error responses (400, 404, 503, 500) and React Error Boundary fallback UI.
