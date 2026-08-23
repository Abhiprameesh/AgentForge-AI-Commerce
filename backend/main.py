from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import base64
import tempfile
import os
import asyncio
import json
import jinja2
import hmac
import hashlib

# Add ffmpeg to PATH dynamically for Windows
ffmpeg_path = r"C:\Users\Abhinand Prameesh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]

import whisper
import edge_tts

from agent import llm
from workflow import app_workflow
from services import catalog_service, cart_service, razorpay_service, audit_service

app = FastAPI(title="AgentForge Commerce API")

# Load Whisper model globally
print("Loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")
    print("Whisper model loaded!")
except Exception as e:
    print(f"Warning: Failed to load whisper model. Audio transcription might fail: {e}")
    whisper_model = None

# Active session states in memory
_session_states = {}

def get_session_state(session_id: str) -> dict:
    if session_id not in _session_states:
        cart = cart_service.get_cart(session_id)
        _session_states[session_id] = {
            "session_id": session_id,
            "user_input": "",
            "response": "",
            "selected_agent": "None",
            "conversation_history": [],
            "intent": "general_question",
            "shopper_intent": {
                "category": None,
                "budget_max": None,
                "occasion": None,
                "recipient": None,
                "preferences": []
            },
            "retrieved_products": [],
            "recommendations": [],
            "upsell": {},
            "cart": cart,
            "checkout_status": "pending_confirm",
            "payment_order": {},
            "agent_trace": []
        }
    else:
        # Keep cart in sync
        _session_states[session_id]["cart"] = cart_service.get_cart(session_id)
    return _session_states[session_id]

# INPUT MODEL
class ChatInput(BaseModel):
    message: str | None = None
    audio_data: str | None = None
    session_id: str = "default_session"
    history: list = []

# CHAT ENDPOINT
@app.post("/chat")
@app.post("/api/chat")
async def chat(chat_input: ChatInput):
    try:
        session_id = chat_input.session_id
        
        # Handle Audio Input
        if chat_input.audio_data and whisper_model:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                audio_bytes = base64.b64decode(chat_input.audio_data)
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name
            
            # Transcribe with Whisper
            result = await asyncio.to_thread(whisper_model.transcribe, temp_audio_path)
            chat_input.message = result["text"].strip()
            os.remove(temp_audio_path)
        
        if not chat_input.message:
            return {"response": "Please provide a message or audio input."}

        # Initialize or retrieve state
        state = get_session_state(session_id)
        state["user_input"] = chat_input.message
        state["conversation_history"] = chat_input.history
        state["agent_trace"] = []  # Reset trace for this turn
        
        # Run LangGraph commerce workflow
        workflow_result = await asyncio.to_thread(
            app_workflow.invoke,
            state
        )
        
        # Update session state cache
        _session_states[session_id].update(workflow_result)
        final_state = _session_states[session_id]
        
        response_text = final_state.get("response", "")

        # Generate Audio Response with Edge-TTS if audio input was used
        audio_response_b64 = None
        if chat_input.audio_data:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
                temp_mp3_path = temp_mp3.name
            
            communicate = edge_tts.Communicate(response_text, "en-US-AriaNeural")
            await communicate.save(temp_mp3_path)
            
            with open(temp_mp3_path, "rb") as f:
                audio_response_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            os.remove(temp_mp3_path)

        # Retrieve mapped product chunks for UI cards
        product_cards = final_state.get("retrieved_products", [])
        
        return {
            "response": response_text,
            "selected_agent": final_state.get("selected_agent", "Assistant"),
            "agent_trace": final_state.get("agent_trace", []),
            "shopper_intent": final_state.get("shopper_intent", {}),
            "upsell": final_state.get("upsell", {}),
            "cart": final_state.get("cart", {}),
            "checkout_status": final_state.get("checkout_status", "pending_confirm"),
            "payment_order": final_state.get("payment_order", {}),
            "product_cards": product_cards,
            "audio_response": audio_response_b64
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"response": f"Error: {str(e)}"}

# CAPABILITIES ENDPOINT (AI Buyer Mode)
@app.get("/api/agent/capabilities")
def get_capabilities():
    return {
        "merchant": "AgentForge Commerce Demo",
        "capabilities": [
            "search_products",
            "get_product",
            "check_inventory",
            "add_to_cart",
            "get_cart",
            "create_checkout"
        ],
        "api_docs": {
            "search_products": "POST /api/catalog/search {query: str, category: str, max_price: float}",
            "get_product": "GET /api/catalog/{product_id}",
            "add_to_cart": "POST /api/cart/{session_id}/items {product_id: str, quantity: int}",
            "get_cart": "GET /api/cart/{session_id}",
            "create_checkout": "POST /api/checkout/prepare {session_id: str}"
        }
    }

# CATALOG ENDPOINTS
@app.get("/api/catalog")
def get_catalog():
    return catalog_service.get_all_products()

@app.get("/api/catalog/{product_id}")
def get_catalog_product(product_id: str):
    product = catalog_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/catalog/search")
def search_catalog(payload: dict):
    query = payload.get("query", "")
    category = payload.get("category")
    max_price = payload.get("max_price")
    return catalog_service.search_products(query, category=category, max_price=max_price)

# CART ENDPOINTS
@app.get("/api/cart/{session_id}")
def get_session_cart(session_id: str):
    return cart_service.get_cart(session_id)

class CartItemPayload(BaseModel):
    product_id: str
    quantity: int = 1

@app.post("/api/cart/{session_id}/items")
def add_item_to_cart(session_id: str, payload: CartItemPayload):
    msg = cart_service.add_to_cart(session_id, payload.product_id, payload.quantity)
    if "Error" in msg:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "cart": cart_service.get_cart(session_id)}

@app.delete("/api/cart/{session_id}/items/{product_id}")
def remove_item_from_cart(session_id: str, product_id: str):
    msg = cart_service.remove_from_cart(session_id, product_id)
    if "Error" in msg:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "cart": cart_service.get_cart(session_id)}

# CHECKOUT & PAYMENT ENDPOINTS
@app.post("/api/payment/create-order")
def create_payment_order(payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    
    cart = cart_service.get_cart(session_id)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")
        
    order_res = razorpay_service.create_order(cart["final_total"], session_id, cart["items"])
    
    # Store order ID in session state
    state = get_session_state(session_id)
    state["payment_order"] = order_res
    
    audit_service.log_event(
        session_id=session_id,
        agent="Checkout Agent",
        action="create_payment_order",
        input_data=cart["final_total"],
        output_data=order_res
    )
    
    return order_res

@app.post("/api/payment/verify")
def verify_payment(payload: dict):
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")
    
    if not order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment details")
        
    is_valid = razorpay_service.verify_payment(order_id, payment_id, signature)
    
    if is_valid:
        order = razorpay_service.get_order(order_id)
        if order:
            session_id = order["session_id"]
            # Clear cart since order is paid
            cart_service.clear_cart(session_id)
            
            # Update session state checkout status
            state = get_session_state(session_id)
            state["checkout_status"] = "paid"
            state["cart"] = cart_service.get_cart(session_id)
            
            audit_service.log_event(
                session_id=session_id,
                agent="Payment Agent",
                action="payment_verified",
                input_data={"order_id": order_id, "payment_id": payment_id},
                output_data="success",
                user_confirmation=True
            )
            
        return {"success": True, "message": "Payment verified and order completed!"}
    
    return JSONResponse(status_code=400, content={"success": False, "message": "Payment signature verification failed"})

# WEBHOOK ENDPOINT
@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
        
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if webhook_secret:
        # Verify signature
        computed_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(computed_sig, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
            
    # Process event idempotently
    try:
        event_data = json.loads(raw_body.decode("utf-8"))
        event = event_data.get("event")
        
        if event == "order.paid":
            payload_order = event_data["payload"]["order"]["entity"]
            order_id = payload_order["id"]
            
            # Fetch payment ID from payments list if present
            payment_entity = event_data["payload"].get("payment", {}).get("entity", {})
            payment_id = payment_entity.get("id")
            
            # Prevent duplicate updates
            order = razorpay_service.get_order(order_id)
            if order and order["status"] != "paid":
                razorpay_service.update_order_status(order_id, "paid", payment_id)
                cart_service.clear_cart(order["session_id"])
                
                # Log webhook audit
                audit_service.log_event(
                    session_id=order["session_id"],
                    agent="Razorpay Webhook",
                    action="webhook_order_paid",
                    input_data=order_id,
                    output_data=f"Updated status to PAID. Payment ID: {payment_id}"
                )
                
    except Exception as e:
        print(f"Webhook processing error: {e}")
        
    return {"status": "ok"}

# STANDALONE CHECKOUT PAGE
@app.get("/checkout", response_class=HTMLResponse)
def get_checkout(order_id: str = Query(..., description="The Razorpay/Mock Order ID")):
    order = razorpay_service.get_order(order_id)
    if not order:
        return HTMLResponse("<h2>Order not found</h2>", status_code=404)
        
    # Read the checkout.html template file
    template_path = os.path.join(os.path.dirname(__file__), "templates", "checkout.html")
    if not os.path.exists(template_path):
        return HTMLResponse("<h2>Checkout template not found</h2>", status_code=500)
        
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    template = jinja2.Template(template_content)
    
    # Check configurations
    is_mock = order.get("is_mock", True)
    key_id = os.getenv("RAZORPAY_KEY_ID") if not is_mock else "MOCK_KEY_ID"
    
    html = template.render(
        order_id=order_id,
        session_id=order["session_id"],
        status=order["status"],
        amount_rupees=order["amount_rupees"],
        amount_paise=order["amount_paise"],
        currency="INR",
        key_id=key_id,
        is_mock=is_mock
    )
    
    return HTMLResponse(html)

# AUDIT RETRIEVAL
@app.get("/api/audit/{session_id}")
def get_audit_trail(session_id: str):
    return audit_service.get_session_logs(session_id)

# METRICS / ANALYTICS
@app.get("/api/metrics")
def get_metrics():
    """Calculate real metrics from the audit logs and order database."""
    logs = audit_service.get_all_logs()
    orders = razorpay_service.get_all_orders()
    
    conversations = set()
    searches = 0
    recs = 0
    cart_adds = 0
    checkout_attempts = 0
    upsell_shown = 0
    upsell_accepted = 0
    
    # Process audit logs
    for log in logs:
        session_id = log.get("session_id")
        conversations.add(session_id)
        
        action = log.get("action", "")
        agent = log.get("agent", "")
        
        if action == "search_catalog":
            searches += 1
        elif action == "rank_recommendations":
            recs += 1
        elif action == "cart_add":
            cart_adds += 1
        elif action == "prepare_checkout":
            checkout_attempts += 1
        elif action == "pitch_upsell":
            upsell_shown += 1
            
    # Process orders
    successful_payments = 0
    failed_payments = 0
    revenue = 0.0
    upsell_rev = 0.0
    
    for order in orders.values():
        status = order.get("status")
        amount = order.get("amount_rupees", 0.0)
        
        if status == "paid":
            successful_payments += 1
            revenue += amount
            
            # Check if order contains an upsell product that was accepted
            # We look at the logs to see if they bought a product that was recommended as an upsell
            order_items = order.get("items", [])
            for item in order_items:
                pid = item.get("product_id")
                # Check if this pid was pitched as an upsell in this session
                for log in logs:
                    if log.get("session_id") == order["session_id"] and log.get("action") == "pitch_upsell" and pid in log.get("input", ""):
                        upsell_accepted += 1
                        upsell_rev += item.get("total", 0.0)
                        break
        elif status == "failed":
            failed_payments += 1
            
    # Conversion calculations
    conv_rate = (successful_payments / len(conversations) * 100) if conversations else 0.0
    aov = (revenue / successful_payments) if successful_payments else 0.0
    upsell_rate = (upsell_accepted / upsell_shown * 100) if upsell_shown else 0.0
    
    return {
        "conversations": len(conversations),
        "searches": searches,
        "recommendations": recs,
        "cart_adds": cart_adds,
        "checkout_attempts": checkout_attempts,
        "successful_payments": successful_payments,
        "failed_payments": failed_payments,
        "conversion_rate": round(conv_rate, 1),
        "aov": round(aov, 2),
        "upsell_acceptance_rate": round(upsell_rate, 1),
        "revenue": round(revenue, 2),
        "ai_influenced_revenue": round(revenue * 0.8, 2),  # AI guided conversion estimation
        "upsell_revenue": round(upsell_rev, 2)
    }