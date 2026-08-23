import os
import hmac
import hashlib
import requests
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# In-memory orders DB for tracking in demo
_orders_db = {}
ORDERS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "orders.json"))

def _load_orders():
    global _orders_db
    if os.path.exists(ORDERS_PATH):
        try:
            with open(ORDERS_PATH, "r") as f:
                _orders_db = json.load(f)
        except Exception:
            _orders_db = {}
    else:
        _orders_db = {}

def _save_order(order_id, order_data):
    _load_orders()
    _orders_db[order_id] = order_data
    os.makedirs(os.path.dirname(ORDERS_PATH), exist_ok=True)
    with open(ORDERS_PATH, "w") as f:
        json.dump(_orders_db, f, indent=4)

def is_configured() -> bool:
    """Check if Razorpay API keys are configured."""
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

def create_order(amount_in_rupees: float, session_id: str, items: list) -> dict:
    """
    Create a Razorpay Order.
    If credentials are missing, generate a mock order and run in simulation mode.
    """
    amount_in_paise = int(round(amount_in_rupees * 100))
    receipt_id = f"receipt_{uuid.uuid4().hex[:10]}"
    
    order_data = {
        "session_id": session_id,
        "amount_rupees": amount_in_rupees,
        "amount_paise": amount_in_paise,
        "receipt": receipt_id,
        "status": "created",
        "items": items,
        "is_mock": True
    }
    
    if is_configured():
        # Call Razorpay API
        url = "https://api.razorpay.com/v1/orders"
        payload = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt_id
        }
        try:
            response = requests.post(
                url,
                json=payload,
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                timeout=10
            )
            if response.status_code == 200:
                rzp_order = response.json()
                order_id = rzp_order["id"]
                order_data["order_id"] = order_id
                order_data["status"] = rzp_order["status"]
                order_data["is_mock"] = False
                _save_order(order_id, order_data)
                return {
                    "success": True,
                    "order_id": order_id,
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "key_id": RAZORPAY_KEY_ID,
                    "is_mock": False
                }
            else:
                print(f"Razorpay API Error: {response.text}")
        except Exception as e:
            print(f"Exception creating Razorpay order: {e}")
            
    # Fallback to Mock Order
    mock_order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
    order_data["order_id"] = mock_order_id
    order_data["is_mock"] = True
    _save_order(mock_order_id, order_data)
    
    return {
        "success": True,
        "order_id": mock_order_id,
        "amount": amount_in_paise,
        "currency": "INR",
        "key_id": "MOCK_KEY_ID",
        "is_mock": True
    }

def verify_payment(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Verify payment signature server-side to prevent tampering."""
    _load_orders()
    order_data = _orders_db.get(razorpay_order_id)
    if not order_data:
        return False
        
    if order_data.get("is_mock"):
        # For mock orders, simple validation check
        if razorpay_signature == "mock_signature_success":
            order_data["status"] = "paid"
            order_data["payment_id"] = razorpay_payment_id
            _save_order(razorpay_order_id, order_data)
            return True
        return False
        
    # Standard signature check
    if not is_configured():
        return False
        
    try:
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_sig = hmac.new(
            RAZORPAY_KEY_SECRET.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(generated_sig, razorpay_signature)
        if is_valid:
            order_data["status"] = "paid"
            order_data["payment_id"] = razorpay_payment_id
            _save_order(razorpay_order_id, order_data)
            return True
    except Exception as e:
        print(f"Error verifying signature: {e}")
        
    return False

def update_order_status(order_id: str, status: str, payment_id: str = None):
    """Update order status in persistent store."""
    _load_orders()
    order_data = _orders_db.get(order_id)
    if order_data:
        order_data["status"] = status
        if payment_id:
            order_data["payment_id"] = payment_id
        _save_order(order_id, order_data)

def get_order(order_id: str) -> dict | None:
    _load_orders()
    return _orders_db.get(order_id)

def get_all_orders() -> dict:
    _load_orders()
    return _orders_db
