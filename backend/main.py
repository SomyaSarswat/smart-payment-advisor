import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

from database import init_db, get_all_transactions_count, insert_transaction, inject_failure_spike, get_merchant_analytics
from data_simulator import generate_one_fake_transaction
from recommendation_engine import get_recommendations
from razorpay_handler import create_order, verify_payment_signature, get_key_id
from merchant_config import get_merchant_config

# Background task worker to continuously generate fresh live transactions
async def background_transaction_worker():
    """
    Runs continuously alongside FastAPI server.
    Generates fresh realistic transactions every 8 seconds to ensure
    the 2-hour live sliding window dynamically fluctuates in real time.
    """
    print("[BACKGROUND WORKER] Continuous live transaction simulator started.")
    while True:
        try:
            generate_one_fake_transaction()
        except Exception as e:
            print(f"[BACKGROUND WORKER ERROR] {e}")
        await asyncio.sleep(8)

# Lifespan context manager to handle startup and shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on server startup
    init_db()
    # Start continuous background transaction simulator task
    worker_task = asyncio.create_task(background_transaction_worker())
    yield
    # Clean up worker task on server shutdown
    worker_task.cancel()

# Create FastAPI application instance
app = FastAPI(
    title="Smart Payment Advisor API",
    description="AI-powered Payment Intelligence API for Razorpay Buildathon",
    lifespan=lifespan
)

# Configure CORS Middleware to allow requests from React frontend (Vite dev server)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for payment recommendation request body
class RecommendationRequest(BaseModel):
    merchant_id: str
    amount: float
    device: str
    # Optional list of [method, bank] pairs. If omitted, fetched automatically via merchant_config
    available_methods_banks: Optional[List[List[Optional[str]]]] = None

# Pydantic model for order creation request body
class CreateOrderRequest(BaseModel):
    amount: float
    receipt_id: str

# Pydantic model for payment signature verification request body
class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    merchant_id: str
    method: str
    bank: Optional[str] = None
    amount: float
    device: Optional[str] = "Desktop"
    hour: Optional[int] = None

# Pydantic model for failure simulation request body
class SimulateFailureRequest(BaseModel):
    merchant_id: str
    method: str
    bank: Optional[str] = None
    failure_count: Optional[int] = 10

@app.get("/")
def read_root():
    """
    Health check endpoint to verify backend service is active.
    """
    return {"status": "Smart Payment Advisor API is running"}

@app.get("/api/merchant-config/{merchant_id}")
def merchant_config_endpoint(merchant_id: str):
    """
    Returns available payment methods and bank options for a specific merchant.
    """
    try:
        options = get_merchant_config(merchant_id)
        return {
            "merchant_id": merchant_id,
            "available_methods_banks": options
        }
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
        # If available_methods_banks is omitted or None, load from merchant_config
        if request.available_methods_banks is None:
            tuple_options = get_merchant_config(request.merchant_id)
        else:
            # Convert incoming list of lists into a list of (method, bank) tuples
            tuple_options = [(item[0], item[1]) for item in request.available_methods_banks]

        # Call recommendation engine
        recommendations = get_recommendations(
            merchant_id=request.merchant_id,
            amount=request.amount,
            device=request.device,
            available_methods_banks=tuple_options
        )

        return {"recommendations": recommendations}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

@app.get("/api/stats")
def stats_endpoint():
    """
    Returns global system transaction metrics.
    """
    try:
        total_count = get_all_transactions_count()
        return {"total_transactions": total_count}
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
        analytics = get_merchant_analytics(merchant_id)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating analytics: {str(e)}"
        )

@app.post("/api/simulate-failure")
def simulate_failure_endpoint(request: SimulateFailureRequest):
    """
    Injects artificial failure records to simulate real-time network or bank downtime spikes.
    """
    try:
        result = inject_failure_spike(
            merchant_id=request.merchant_id,
            method=request.method,
            bank=request.bank,
            failure_count=request.failure_count or 10
        )
        return {
            "status": "success",
            "message": f"Successfully injected {result['injected_count']} failure records for {request.method}" + (f" ({request.bank})" if request.bank else ""),
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error simulating failure spike: {str(e)}"
        )

@app.post("/api/create-order")
def create_order_endpoint(request: CreateOrderRequest):
    """
    Creates a Razorpay payment order for the specified amount in INR.
    """
    try:
        order = create_order(amount_in_rupees=request.amount, receipt_id=request.receipt_id)
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": "INR",
            "key_id": get_key_id(),
            "simulation_mode": order.get("simulation_mode", False)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Razorpay Order Error: {str(e)}"
        )

@app.post("/api/verify-payment")
def verify_payment_endpoint(request: VerifyPaymentRequest):
    """
    Verifies Razorpay payment signature and records the transaction in the database.
    """
    try:
        is_verified = verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )

        if is_verified:
            # Record successful transaction in SQLite database
            insert_transaction(
                merchant_id=request.merchant_id,
                method=request.method,
                bank=request.bank,
                amount=request.amount,
                device=request.device,
                hour=request.hour,
                status="success",
                error_code=None
            )
            return {
                "verified": True,
                "message": "Payment verified and recorded"
            }
        else:
            # Record failed transaction in SQLite database
            insert_transaction(
                merchant_id=request.merchant_id,
                method=request.method,
                bank=request.bank,
                amount=request.amount,
                device=request.device,
                hour=request.hour,
                status="failed",
                error_code="signature_verification_failed"
            )
            return {
                "verified": False,
                "message": "Payment verification failed"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying payment: {str(e)}"
        )

# Run with: uvicorn main:app --reload --port 8000


