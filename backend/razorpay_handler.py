import os
import time
import razorpay
from dotenv import load_dotenv
from razorpay.errors import SignatureVerificationError

# Helper to dynamically reload .env and read current Razorpay credentials
def get_credentials():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
    
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    return key_id, key_secret

def is_simulation_mode() -> bool:
    """
    Returns True if Razorpay keys are completely missing or set to placeholder defaults in .env.
    Returns False if real/custom keys are configured.
    """
    key_id, key_secret = get_credentials()
    if not key_id or not key_secret or "YourKeyHere" in key_id or "YourSecretHere" in key_secret:
        return True
    return False

def create_order(amount_in_rupees: float, receipt_id: str) -> dict:
    """
    Creates a new order in Razorpay.
    
    - If keys are missing in .env: returns a simulation order payload with simulation_mode=True.
    - If keys are configured in .env: invokes client.order.create(). If Razorpay API rejects
      the key/secret (genuine authentication error), it re-raises the error to provide explicit feedback.
    """
    key_id, key_secret = get_credentials()
    amount_in_paise = int(amount_in_rupees * 100)

    if is_simulation_mode():
        print("[RAZORPAY] Test keys missing or set to placeholder. Operating in SIMULATION MODE.")
        return {
            "id": f"order_sim_{int(time.time())}",
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "status": "created",
            "simulation_mode": True
        }

    # Keys are present: execute real Razorpay client API request
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        order = client.order.create(data={
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "payment_capture": 1
        })
        order["simulation_mode"] = False
        return order
    except Exception as e:
        print(f"[RAZORPAY ERROR] Real Razorpay API order creation failed: {e}")
        # Re-raise genuine Razorpay authentication or API error without mocking
        raise e

def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verifies the authentic payment signature returned by Razorpay checkout widget.
    """
    if is_simulation_mode():
        # In simulation mode, accept simulated signatures
        return True

    key_id, key_secret = get_credentials()
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        return True
    except SignatureVerificationError:
        return False
    except Exception as e:
        print(f"[RAZORPAY ERROR] Unexpected error during signature verification: {e}")
        return False

def get_key_id() -> str:
    """
    Returns the public Razorpay Key ID needed by the frontend checkout widget.
    """
    key_id, _ = get_credentials()
    return key_id if key_id and "YourKeyHere" not in key_id else None

if __name__ == "__main__":
    print("Testing Razorpay Order Creation...")
    print("Simulation mode active?", is_simulation_mode())
    try:
        test_order = create_order(100, "test_receipt_001")
        print("Order result:", test_order)
    except Exception as err:
        print("Order creation failed (genuine key/API error):", err)

