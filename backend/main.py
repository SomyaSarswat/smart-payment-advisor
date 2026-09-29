# Smart Payment Advisor - FastAPI Server with Real-Time WebSocket Push
import asyncio
import time
import re
from collections import defaultdict
from typing import List, Optional
from contextlib import asynccontextmanager


from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from database import (
    init_db, get_all_transactions_count, insert_transaction, 
    inject_failure_spike, get_merchant_analytics, DatabaseUnavailableError
)
from data_simulator import generate_one_fake_transaction, get_current_generation_interval
from recommendation_engine import get_recommendations
from razorpay_handler import create_order, verify_payment_signature, get_key_id
from merchant_config import (
    get_merchant_config, validate_and_normalize_merchant_id, 
    validate_payment_method_bank
)
from ml_model import train_and_save_model, get_model_metadata

# In-Memory Rate Limiter Store (Max 10 requests per minute per IP for sensitive endpoints)
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60
rate_limit_store = defaultdict(list)

def check_rate_limit(client_ip: str, endpoint_key: str):
    """
    In-memory IP rate limiter preventing route abuse during live demonstrations.
    Raises HTTP 429 if request threshold (10 reqs/min) is exceeded.
    """
    now = time.time()
    key = f"{client_ip}:{endpoint_key}"
    timestamps = rate_limit_store[key]
    
    # Filter out timestamps older than the lookback window
    valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]
    rate_limit_store[key] = valid_timestamps
    
    if len(valid_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Rate limit exceeded (max 10 requests per minute). Please try again shortly."
        )
    
    rate_limit_store[key].append(now)

# WebSocket Connection Manager for real-time live transaction feed push updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Background task worker to continuously generate fresh live transactions
async def background_transaction_worker():
    """
    Runs continuously alongside FastAPI server.
    Generates fresh realistic transactions at dynamic intervals (correlated with hourly rush patterns)
    to ensure the live sliding window dynamically fluctuates in real time.
    """
    print("[BACKGROUND WORKER] Continuous live multi-factor transaction simulator started.")
    while True:
        try:
            tx_data = generate_one_fake_transaction()
            if tx_data:
                await manager.broadcast({"type": "NEW_TRANSACTION", "data": tx_data})
        except Exception as e:
            print(f"[BACKGROUND WORKER ERROR] Failed iteration: {e}")
        sleep_interval = get_current_generation_interval()
        await asyncio.sleep(sleep_interval)

# Background task worker to retrain ML model every 5 minutes
async def periodic_ml_retraining_worker():
    """
    Retrains the supervised ML model every 5 minutes using cumulative database transactions,
    ensuring recommendations stay synchronized with newly accumulated patterns.
    """
    print("[ML RETRAIN WORKER] Periodic 5-minute ML retraining worker started.")
    while True:
        await asyncio.sleep(300)  # Retrain every 5 minutes (300s)
        try:
            print("[ML RETRAIN WORKER] Initiating scheduled ML model retrain...")
            meta = train_and_save_model()
            print(f"[ML RETRAIN WORKER SUCCESS] Retrained model on {meta['training_sample_count']} rows. Accuracy: {meta['test_accuracy']}%, ROC-AUC: {meta['test_auc']}")
            await manager.broadcast({"type": "MODEL_RETRAINED", "data": meta})
        except Exception as e:
            print(f"[ML RETRAIN WORKER ERROR] Failed periodic retrain: {e}")

# Lifespan context manager to handle startup and shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        # Train ML model on startup if needed
        train_and_save_model()
    except Exception as e:
        print(f"[STARTUP WARNING] Database/ML initialization failed: {e}")
    worker_task = asyncio.create_task(background_transaction_worker())
    ml_task = asyncio.create_task(periodic_ml_retraining_worker())
    yield
    worker_task.cancel()
    ml_task.cancel()

# Create FastAPI application instance
app = FastAPI(
    title="Smart Payment Advisor API",
    description="AI-powered Payment Intelligence API for Razorpay Buildathon",
    lifespan=lifespan
)

# PHASE 2: Restrict CORS Middleware to explicit local frontend development origins
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# PHASE 1: Basic Request Logging Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {request.method} {request.url.path} -> {response.status_code} ({process_time:.1f}ms)")
    return response

# PHASE 1 & 2: Global Exception Handlers
@app.exception_handler(DatabaseUnavailableError)
async def db_unavailable_exception_handler(request: Request, exc: DatabaseUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable: Database is locked or unreachable."}
    )

@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    detail_str = str(exc)
    status_code = 404 if "Unknown merchant" in detail_str else 400
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail_str}
    )

# Pydantic models with strict validation constraints
class RecommendationRequest(BaseModel):
    merchant_id: str
    amount: float = Field(..., gt=0, le=1000000, description="Amount must be positive between 1 and 1,000,000 INR")
    device: Optional[str] = "Desktop"
    available_methods_banks: Optional[List[List[Optional[str]]]] = None

class CreateOrderRequest(BaseModel):
    amount: float = Field(..., gt=0, le=1000000, description="Amount must be positive between 1 and 1,000,000 INR")
    receipt_id: str = Field(..., description="Alphanumeric safe receipt string")

    @field_validator("receipt_id")
    @classmethod
    def validate_receipt_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("receipt_id must be a safe alphanumeric string containing only letters, numbers, underscores, or hyphens.")
        return v

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    merchant_id: str
    method: str
    bank: Optional[str] = None
    amount: float = Field(..., gt=0, le=1000000)
    device: Optional[str] = "Desktop"
    hour: Optional[int] = None

class SimulateFailureRequest(BaseModel):
    merchant_id: str
    method: str
    bank: Optional[str] = None
    failure_count: Optional[int] = Field(10, gt=0, le=100)

class DebugForceIncidentRequest(BaseModel):
    bank: str = Field("SBI", description="Bank name")
    method: str = Field("Credit Card", description="Payment method")
    duration_seconds: Optional[int] = Field(180, gt=0, le=3600)
    drop_depth: Optional[float] = Field(0.30, ge=0.05, le=0.90)

# WebSocket endpoint for real-time push updates
@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "Smart Payment Advisor API is running"}

@app.get("/api/merchant-config/{merchant_id}")
def merchant_config_endpoint(merchant_id: str):
    """
    Returns available payment methods and bank options for a specific merchant.
    """
    try:
        norm_id = validate_and_normalize_merchant_id(merchant_id)
        options = get_merchant_config(norm_id)
        return {
            "merchant_id": norm_id,
            "available_methods_banks": options
        }
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        status_code = 404 if "Unknown merchant" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching merchant config: {str(e)}"
        )

@app.post("/api/get-recommendations")
def recommendations_endpoint(request: RecommendationRequest):
    """
    Ranks available payment options by live success rate and fee metrics.
    """
    try:
        norm_merchant_id = validate_and_normalize_merchant_id(request.merchant_id)
        device = request.device or "Desktop"

        if request.available_methods_banks is None:
            tuple_options = get_merchant_config(norm_merchant_id)
        else:
            tuple_options = [(item[0], item[1]) for item in request.available_methods_banks]
            for m, b in tuple_options:
                validate_payment_method_bank(m, b)

        recommendations = get_recommendations(
            merchant_id=norm_merchant_id,
            amount=request.amount,
            device=device,
            available_methods_banks=tuple_options
        )

        return {"recommendations": recommendations}

    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        status_code = 404 if "Unknown merchant" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

@app.get("/api/model-info")
def model_info_endpoint():
    """
    Returns supervised ML model training metadata (trained_at, training_sample_count, test_accuracy, test_auc).
    """
    try:
        meta = get_model_metadata()
        return meta
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching model metadata: {str(e)}"
        )

@app.post("/api/retrain-model")
def retrain_model_endpoint(raw_req: Request):
    """
    Triggers an immediate manual retrain of the supervised ML model on all transactions in payments.db.
    Applies IP rate limiting (max 10 calls/min).
    """
    client_ip = raw_req.client.host if raw_req.client else "127.0.0.1"
    check_rate_limit(client_ip, "retrain-model")

    try:
        meta = train_and_save_model(force_retrain=True)
        try:
            asyncio.create_task(manager.broadcast({"type": "MODEL_RETRAINED", "data": meta}))
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Successfully retrained ML model on {meta['training_sample_count']} transaction records.",
            "details": meta
        }
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retraining ML model: {str(e)}"
        )

@app.get("/api/stats")
def stats_endpoint():
    """
    Returns global system transaction metrics.
    """
    try:
        total_count = get_all_transactions_count()
        return {"total_transactions": total_count}
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )

@app.get("/api/analytics/{merchant_id}")
def analytics_endpoint(merchant_id: str):
    """
    Returns detailed analytics metrics and recent transactions for a merchant.
    """
    try:
        if merchant_id and merchant_id.lower() != "all":
            norm_merchant_id = validate_and_normalize_merchant_id(merchant_id)
        else:
            norm_merchant_id = "all"
        analytics = get_merchant_analytics(norm_merchant_id)
        return analytics
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        status_code = 404 if "Unknown merchant" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating analytics: {str(e)}"
        )

@app.post("/api/simulate-failure")
def simulate_failure_endpoint(request: SimulateFailureRequest, raw_req: Request):
    """
    Injects artificial failure records to simulate real-time network or bank downtime spikes.
    Applies IP rate limiting (max 10 calls/min).
    """
    client_ip = raw_req.client.host if raw_req.client else "127.0.0.1"
    check_rate_limit(client_ip, "simulate-failure")

    try:
        norm_merchant_id = validate_and_normalize_merchant_id(request.merchant_id)
        validate_payment_method_bank(request.method, request.bank)

        result = inject_failure_spike(
            merchant_id=norm_merchant_id,
            method=request.method,
            bank=request.bank,
            failure_count=request.failure_count or 10
        )
        try:
            asyncio.create_task(manager.broadcast({"type": "FAILURE_SIMULATED", "data": result}))
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Successfully injected {result['injected_count']} failure records for {request.method}" + (f" ({request.bank})" if request.bank else ""),
            "details": result
        }
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        status_code = 404 if "Unknown merchant" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error simulating failure spike: {str(e)}"
        )

@app.post("/api/debug/force-incident")
def debug_force_incident_endpoint(request: DebugForceIncidentRequest):
    """
    Test/debug endpoint to explicitly force an autonomous incident state for predictable demo verification.
    Separated from production logic.
    """
    from data_simulator import trigger_incident
    trigger_incident(
        bank=request.bank,
        method=request.method,
        duration_seconds=request.duration_seconds or 180,
        drop_depth=request.drop_depth or 0.30
    )
    return {
        "status": "success",
        "message": f"Forced incident triggered for {request.bank} {request.method} ({request.duration_seconds}s, drop depth {request.drop_depth*100:.0f}%)"
    }

@app.post("/api/create-order")
def create_order_endpoint(request: CreateOrderRequest, raw_req: Request):
    """
    Creates a Razorpay payment order for specified amount in INR.
    Applies IP rate limiting (max 10 calls/min).
    """
    client_ip = raw_req.client.host if raw_req.client else "127.0.0.1"
    check_rate_limit(client_ip, "create-order")

    try:
        order = create_order(amount_in_rupees=request.amount, receipt_id=request.receipt_id)
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": "INR",
            "key_id": get_key_id(),
            "simulation_mode": order.get("simulation_mode", False),
            "simulation_reason": order.get("simulation_reason")
        }
    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Razorpay Order Error: {str(e)}"
        )

@app.post("/api/verify-payment")
def verify_payment_endpoint(request: VerifyPaymentRequest):
    """
    Verifies Razorpay payment signature and records transaction in SQLite database.
    """
    try:
        norm_merchant_id = validate_and_normalize_merchant_id(request.merchant_id)
        validate_payment_method_bank(request.method, request.bank)

        is_verified = verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )

        status_str = "success" if is_verified else "failed"
        err_code = None if is_verified else "signature_verification_failed"

        inserted_id = insert_transaction(
            merchant_id=norm_merchant_id,
            method=request.method,
            bank=request.bank,
            amount=request.amount,
            device=request.device or "Desktop",
            hour=request.hour or time.localtime().tm_hour,
            status=status_str,
            error_code=err_code
        )

        tx_dict = {
            "id": inserted_id,
            "merchant_id": norm_merchant_id,
            "method": request.method,
            "bank": request.bank,
            "amount": request.amount,
            "device": request.device,
            "hour": request.hour,
            "status": status_str,
            "error_code": err_code
        }
        try:
            asyncio.create_task(manager.broadcast({"type": "NEW_TRANSACTION", "data": tx_dict}))
        except Exception:
            pass

        return {
            "verified": is_verified,
            "message": "Payment verified and recorded" if is_verified else "Payment verification failed",
            "transaction_id": inserted_id
        }

    except DatabaseUnavailableError as de:
        raise HTTPException(status_code=503, detail=str(de))
    except ValueError as ve:
        status_code = 404 if "Unknown merchant" in str(ve) else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying payment: {str(e)}"
        )
