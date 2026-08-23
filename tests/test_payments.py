import sys
import os
import hmac
import hashlib

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.abspath("backend"))

from services import razorpay_service, cart_service

def test_signature_verification_mock():
    """Verify mock payment signatures verify successfully in sandbox mode."""
    order_res = razorpay_service.create_order(100.0, "test_pay_session", [])
    order_id = order_res["order_id"]
    
    # Correct mock signature
    assert razorpay_service.verify_payment(order_id, "pay_mock_123", "mock_signature_success") is True
    
    # Incorrect mock signature
    assert razorpay_service.verify_payment(order_id, "pay_mock_123", "incorrect_sig") is False

def test_signature_verification_real():
    """Verify HMAC signature calculation for real Razorpay responses."""
    # Temporarily set key credentials
    razorpay_service.RAZORPAY_KEY_ID = "test_key_id"
    razorpay_service.RAZORPAY_KEY_SECRET = "test_secret"
    
    order_id = "order_real_123"
    payment_id = "pay_real_456"
    
    # Calculate expected signature
    msg = f"{order_id}|{payment_id}"
    sig = hmac.new(
        b"test_secret",
        msg.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # Create matching order in DB
    razorpay_service._save_order(order_id, {
        "session_id": "test_session",
        "is_mock": False,
        "status": "created"
    })
    
    # Verify signature
    assert razorpay_service.verify_payment(order_id, payment_id, sig) is True
    assert razorpay_service.verify_payment(order_id, payment_id, "wrong_sig") is False

def test_webhook_idempotency():
    """Verify webhook payments are processed idempotently."""
    order_id = "order_web_123"
    session_id = "web_session"
    
    # Add item to cart
    cart_service.add_to_cart(session_id, "elec_003", 1)
    
    # Create order
    razorpay_service._save_order(order_id, {
        "session_id": session_id,
        "is_mock": True,
        "status": "created"
    })
    
    # First update status to paid
    razorpay_service.update_order_status(order_id, "paid", "pay_web_abc")
    cart_service.clear_cart(session_id)
    
    order = razorpay_service.get_order(order_id)
    assert order["status"] == "paid"
    assert len(cart_service.get_cart(session_id)["items"]) == 0
    
    # Duplicate update should not raise exception or break state
    razorpay_service.update_order_status(order_id, "paid", "pay_web_abc")
    order = razorpay_service.get_order(order_id)
    assert order["status"] == "paid"
