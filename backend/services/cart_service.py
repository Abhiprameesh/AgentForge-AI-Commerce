import json
import os
from services.catalog_service import get_product

CARTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "carts.json"))

def _load_carts() -> dict:
    if not os.path.exists(CARTS_PATH):
        os.makedirs(os.path.dirname(CARTS_PATH), exist_ok=True)
        return {}
    try:
        with open(CARTS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_carts(carts: dict):
    os.makedirs(os.path.dirname(CARTS_PATH), exist_ok=True)
    with open(CARTS_PATH, "w") as f:
        json.dump(carts, f, indent=4)

def add_to_cart(session_id: str, product_id: str, quantity: int = 1) -> str:
    """Add a product to the cart. Verify inventory. Return status message."""
    product = get_product(product_id)
    if not product:
        return f"Error: Product {product_id} does not exist."
    
    if product["inventory"] <= 0:
        return f"Error: '{product['name']}' is out of stock."
    
    carts = _load_carts()
    if session_id not in carts:
        carts[session_id] = {}
        
    current_qty = carts[session_id].get(product_id, 0)
    new_qty = current_qty + quantity
    
    if new_qty > product["inventory"]:
        return f"Error: Cannot add {quantity} more of '{product['name']}'. Only {product['inventory']} available."
        
    carts[session_id][product_id] = new_qty
    _save_carts(carts)
    return f"Success: Added '{product['name']}' to cart."

def remove_from_cart(session_id: str, product_id: str) -> str:
    """Remove a product from the cart."""
    carts = _load_carts()
    if session_id in carts and product_id in carts[session_id]:
        product = get_product(product_id)
        name = product["name"] if product else product_id
        del carts[session_id][product_id]
        _save_carts(carts)
        return f"Success: Removed '{name}' from cart."
    return "Error: Product not in cart."

def update_quantity(session_id: str, product_id: str, quantity: int) -> str:
    """Update product quantity in cart. Check inventory."""
    if quantity <= 0:
        return remove_from_cart(session_id, product_id)
        
    product = get_product(product_id)
    if not product:
        return f"Error: Product {product_id} does not exist."
        
    if quantity > product["inventory"]:
        return f"Error: Cannot set quantity to {quantity}. Only {product['inventory']} available."
        
    carts = _load_carts()
    if session_id not in carts:
        carts[session_id] = {}
        
    carts[session_id][product_id] = quantity
    _save_carts(carts)
    return f"Success: Updated '{product['name']}' quantity to {quantity}."

def get_cart(session_id: str) -> dict:
    """
    Retrieve cart details and calculate totals.
    Price, discount, taxes, and shipping are computed deterministically.
    """
    carts = _load_carts()
    session_cart = carts.get(session_id, {})
    
    items = []
    subtotal = 0.0
    total_discount = 0.0
    
    for pid, qty in list(session_cart.items()):
        product = get_product(pid)
        if not product:
            # Clean up invalid product from cart
            del session_cart[pid]
            continue
            
        item_subtotal = float(product["price"] * qty)
        item_discount = float(product["discount"] * qty)
        item_total = item_subtotal - item_discount
        
        subtotal += item_subtotal
        total_discount += item_discount
        
        items.append({
            "product_id": pid,
            "name": product["name"],
            "price": float(product["price"]),
            "quantity": qty,
            "subtotal": item_subtotal,
            "discount": item_discount,
            "total": item_total,
            "image": product["image"]
        })
        
    if not items:
        return {
            "items": [],
            "subtotal": 0.0,
            "discount": 0.0,
            "tax": 0.0,
            "shipping": 0.0,
            "final_total": 0.0
        }
        
    # Standard Tax Calculation (e.g., 18% GST included in price or added? Standard is 18% tax of taxable value)
    # Let's say prices are inclusive of tax for simplicity, but we break it down
    taxable_value = subtotal - total_discount
    tax_rate = 0.18
    tax = round(taxable_value * (tax_rate / (1 + tax_rate)), 2) # tax portion of inclusive price
    
    # Shipping fee calculation (Free shipping above ₹1500, otherwise ₹99)
    shipping = 0.0 if taxable_value >= 1500.0 else 99.0
    final_total = taxable_value + shipping
    
    return {
        "items": items,
        "subtotal": round(subtotal, 2),
        "discount": round(total_discount, 2),
        "tax": round(tax, 2),
        "shipping": round(shipping, 2),
        "final_total": round(final_total, 2)
    }

def clear_cart(session_id: str):
    """Clear the cart for the session."""
    carts = _load_carts()
    if session_id in carts:
        carts[session_id] = {}
        _save_carts(carts)
    return "Success: Cart cleared."
