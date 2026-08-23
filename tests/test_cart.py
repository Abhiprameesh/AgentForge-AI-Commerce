import sys
import os

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.abspath("backend"))

from services import cart_service, catalog_service

def test_cart_operations():
    session_id = "test_cart_session"
    
    # Ensure starting clean
    cart_service.clear_cart(session_id)
    cart = cart_service.get_cart(session_id)
    assert len(cart["items"]) == 0
    
    # 1. Add item
    msg = cart_service.add_to_cart(session_id, "elec_003", 2) # ChargeGo Power Bank (1799, discount 200)
    assert "Success" in msg
    
    cart = cart_service.get_cart(session_id)
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == "elec_003"
    assert cart["items"][0]["quantity"] == 2
    assert cart["subtotal"] == 1799 * 2
    assert cart["discount"] == 200 * 2
    
    # 2. Update quantity
    msg = cart_service.update_quantity(session_id, "elec_003", 3)
    assert "Success" in msg
    cart = cart_service.get_cart(session_id)
    assert cart["items"][0]["quantity"] == 3
    
    # 3. Add out-of-stock item (elec_011 inventory is 0)
    msg_oos = cart_service.add_to_cart(session_id, "elec_011", 1)
    assert "Error" in msg_oos
    
    # 4. Shipping Calculation: Subtotal is 3 * (1799 - 200) = 4797. Free shipping above 1500, so shipping must be 0
    assert cart["shipping"] == 0.0
    
    # Let's add a cheap product to check shipping cost
    cart_service.clear_cart(session_id)
    cart_service.add_to_cart(session_id, "beau_008", 1) # Lip Balm (349, discount 30) -> final ₹319
    cart = cart_service.get_cart(session_id)
    assert cart["shipping"] == 99.0 # Shipping is ₹99 for order value under 1500
    assert cart["final_total"] == 319.0 + 99.0
    
    # 5. Remove item
    msg_rem = cart_service.remove_from_cart(session_id, "beau_008")
    assert "Success" in msg_rem
    cart = cart_service.get_cart(session_id)
    assert len(cart["items"]) == 0
