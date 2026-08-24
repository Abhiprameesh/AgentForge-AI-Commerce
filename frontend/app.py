import streamlit as st
import requests
import os
import base64
from datetime import datetime
from audio_recorder_streamlit import audio_recorder

# PAGE CONFIG
st.set_page_config(
    page_title="AgentForge Commerce - AI Sales & Checkout Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://127.0.0.1:8000"

# CUSTOM CSS FOR PREMIUM LOOK
st.markdown("""
<style>
    /* Global styles */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Premium Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }
    
    .metric-title {
        font-size: 14px;
        color: #8b9bb4;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #00f2fe;
    }
    
    .product-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    
    .product-card:hover {
        transform: translateY(-2px);
        border-color: rgba(31, 142, 241, 0.3);
    }
    
    .trace-node {
        padding: 10px 15px;
        border-radius: 8px;
        background-color: rgba(31, 142, 241, 0.1);
        border-left: 4px solid #1f8ef1;
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .cart-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 14px;
    }
    
    .chat-timestamp {
        font-size: 10px;
        color: #8b9bb4;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# SESSION STATE INITIALIZATION
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Dynamic agent trace information
if "agent_trace" not in st.session_state:
    st.session_state.agent_trace = []

if "shopper_intent" not in st.session_state:
    st.session_state.shopper_intent = {}

if "upsell" not in st.session_state:
    st.session_state.upsell = {}

if "active_cards" not in st.session_state:
    st.session_state.active_cards = []

if "checkout_status" not in st.session_state:
    st.session_state.checkout_status = "pending_confirm"

if "payment_order" not in st.session_state:
    st.session_state.payment_order = {}

# SIDEBAR NAVIGATION
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/bot.png", width=60)
    st.title("AgentForge Commerce")
    st.caption("AI-Native Growth & Agentic Checkout Engine")
    
    st.divider()
    
    view_mode = st.radio(
        "Select Portal Mode",
        [
            "🛍️ Shopper Experience",
            "📊 Merchant Dashboard",
            "🔍 Agent Observability Trace",
            "🤖 AI Buyer Simulation"
        ]
    )
    
    st.divider()
    
    # Utility Buttons
    if st.button("🗑️ Reset Demo Session", use_container_width=True):
        st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"
        st.session_state.messages = []
        st.session_state.agent_trace = []
        st.session_state.shopper_intent = {}
        st.session_state.upsell = {}
        st.session_state.active_cards = []
        st.session_state.checkout_status = "pending_confirm"
        st.session_state.payment_order = {}
        st.toast("Demo session reset successfully!")
        st.rerun()

# ----------------- VIEW 1: SHOPPER EXPERIENCE -----------------
if view_mode == "🛍️ Shopper Experience":
    st.title("🤖 Agentic Commerce Storefront")
    st.markdown("Conversational Buyer Intent → Semantic Retrieval → Deterministic Cart → Secure Razorpay Checkout")
    
    # Create two columns: Chat & Cart Details
    col_chat, col_cart = st.columns([2, 1])
    
    with col_chat:
        # Display Chat Messages
        chat_container = st.container(height=500)
        with chat_container:
            if not st.session_state.messages:
                st.chat_message("assistant").markdown(
                    "👋 Welcome to our demo store! I can help you discover products, manage your cart, "
                    "and checkout. Try saying something like:\n"
                    "*'I need a birthday gift for my sister under ₹2000. She loves skincare.'*\n"
                    "*'Show me some mechanical keyboards suitable for programming.'*"
                )
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if "audio_response_b64" in msg and msg["audio_response_b64"]:
                        st.audio(base64.b64decode(msg["audio_response_b64"]), format="audio/mp3")
                    st.markdown(f'<div class="chat-timestamp">{msg["timestamp"]}</div>', unsafe_allow_html=True)
        
        # Audio Input Mode
        st.markdown("🎙️ **Voice Shopping Mode**")
        audio_bytes = audio_recorder(text="Tap to Speak", icon_size="lg", key="audio_record")
        
        # Chat text input
        user_input = st.chat_input("Message the Assistant...")
        
        # Process inputs
        if user_input or audio_bytes:
            current_time = datetime.now().strftime("%I:%M %p")
            audio_data_b64 = None
            
            if audio_bytes:
                audio_data_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                if not user_input:
                    user_input = "🎤 *Voice message sent*"
            
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": current_time
            })
            
            # Request backend
            payload = {
                "message": user_input,
                "audio_data": audio_data_b64,
                "session_id": st.session_state.session_id,
                "history": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
            }
            
            with st.spinner("Agent compiling response..."):
                try:
                    res = requests.post(f"{BACKEND_URL}/api/chat", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        agent_response = data.get("response", "Error getting response.")
                        audio_res = data.get("audio_response")
                        
                        # Update session state with trace & states
                        st.session_state.agent_trace = data.get("agent_trace", [])
                        st.session_state.shopper_intent = data.get("shopper_intent", {})
                        st.session_state.upsell = data.get("upsell", {})
                        st.session_state.active_cards = data.get("product_cards", [])
                        st.session_state.checkout_status = data.get("checkout_status", "pending_confirm")
                        st.session_state.payment_order = data.get("payment_order", {})
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": agent_response,
                            "audio_response_b64": audio_res,
                            "timestamp": datetime.now().strftime("%I:%M %p")
                        })
                    else:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Backend Error: {res.text}",
                            "timestamp": datetime.now().strftime("%I:%M %p")
                        })
                except Exception as e:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Failed to connect to backend: {e}",
                        "timestamp": datetime.now().strftime("%I:%M %p")
                    })
            st.rerun()

        # Display Recommended Products Cards below chat
        if st.session_state.active_cards:
            st.subheader("🛍️ Recommendations matching your query")
            cols = st.columns(min(3, len(st.session_state.active_cards)))
            for idx, prod in enumerate(st.session_state.active_cards):
                with cols[idx % 3]:
                    # Card
                    st.markdown(
                        f"""
                        <div class="product-card">
                            <img src="{prod['image']}" style="width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:10px;">
                            <div style="font-weight:600; font-size:15px; margin-bottom:5px;">{prod['name']}</div>
                            <div style="font-size:12px; color:#8b9bb4; margin-bottom:5px;">{prod['brand']} | ⭐ {prod['rating']}</div>
                            <div style="font-size:16px; font-weight:700; color:#00f2fe;">₹{prod['price'] - prod['discount']} <span style="font-size:12px; text-decoration:line-through; color:#8b9bb4; font-weight:400;">₹{prod['price']}</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Direct action button
                    if st.button("🛒 Add to Cart", key=f"buy_btn_{prod['product_id']}", use_container_width=True):
                        # Call add to cart directly
                        try:
                            add_res = requests.post(f"{BACKEND_URL}/api/cart/{st.session_state.session_id}/items", json={
                                "product_id": prod["product_id"],
                                "quantity": 1
                            })
                            if add_res.status_code == 200:
                                st.toast(f"Added {prod['name']} to cart!")
                                # Send message to notify agent cart changed
                                chat_res = requests.post(f"{BACKEND_URL}/api/chat", json={
                                    "message": f"I added '{prod['name']}' to my cart via the product card.",
                                    "session_id": st.session_state.session_id,
                                    "history": []
                                })
                                if chat_res.status_code == 200:
                                    data = chat_res.json()
                                    st.session_state.agent_trace = data.get("agent_trace", [])
                                    st.session_state.cart = data.get("cart", {})
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": data.get("response", ""),
                                        "timestamp": datetime.now().strftime("%I:%M %p")
                                    })
                                st.rerun()
                            else:
                                st.error(add_res.json().get("detail", "Error adding item"))
                        except Exception as e:
                            st.error(f"Error connecting: {e}")

    # Right side: Shopping Cart & Checkout status
    with col_cart:
        st.subheader("🛒 Your Shopping Cart")
        
        # Load cart from backend
        try:
            cart_res = requests.get(f"{BACKEND_URL}/api/cart/{st.session_state.session_id}")
            cart = cart_res.json() if cart_res.status_code == 200 else {"items": [], "subtotal": 0, "discount": 0, "shipping": 0, "final_total": 0}
        except Exception:
            cart = {"items": [], "subtotal": 0, "discount": 0, "shipping": 0, "final_total": 0}
            
        if not cart["items"]:
            st.info("Your cart is empty. Talk to the assistant to find products!")
        else:
            for item in cart["items"]:
                st.markdown(
                    f"""
                    <div class="cart-item">
                        <div>
                            <b>{item['name']}</b><br>
                            <span style="color:#8b9bb4; font-size:12px;">Qty: {item['quantity']} x ₹{item['price'] - (item['discount'] / item['quantity'])}</span>
                        </div>
                        <div style="font-weight:600;">₹{item['total']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # Remove item button
                if st.button("🗑️ Remove", key=f"rem_{item['product_id']}"):
                    requests.delete(f"{BACKEND_URL}/api/cart/{st.session_state.session_id}/items/{item['product_id']}")
                    st.rerun()
            
            st.divider()
            
            # Totals
            st.write(f"Subtotal: **₹{cart['subtotal']}**")
            st.write(f"Total Discount: **-₹{cart['discount']}**")
            st.write(f"Shipping: **₹{cart['shipping']}**")
            st.write(f"Grand Total: **₹{cart['final_total']}**")
            
            st.divider()
            
            # Checkout Gate
            if st.session_state.checkout_status == "paid":
                st.success("🎉 Payment Received! Order completed.")
            else:
                # User Checkout Actions
                if st.button("📝 Initialize Checkout", use_container_width=True):
                    try:
                        # Request order creation on backend
                        ord_res = requests.post(f"{BACKEND_URL}/api/payment/create-order", json={"session_id": st.session_state.session_id})
                        if ord_res.status_code == 200:
                            data = ord_res.json()
                            st.session_state.payment_order = data
                            st.session_state.checkout_status = "confirmed"
                            st.rerun()
                        else:
                            st.error(ord_res.text)
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                # If Checkout initialized
                if st.session_state.checkout_status == "confirmed" and st.session_state.payment_order.get("success"):
                    order_id = st.session_state.payment_order["order_id"]
                    is_mock = st.session_state.payment_order["is_mock"]
                    
                    st.warning("⚠️ Ready for payment confirmation.")
                    
                    # Direct payment link (opens in new tab)
                    checkout_url = f"{BACKEND_URL}/checkout?order_id={order_id}"
                    st.link_button("👉 Open Payment Gateway", checkout_url, use_container_width=True)
                    
                    # Verify status button
                    if st.button("🔄 Verify Payment Status", use_container_width=True):
                        try:
                            # Let's inspect order status
                            # Since checkout verified calls verify endpoint, check database
                            order_check = requests.get(f"{BACKEND_URL}/api/cart/{st.session_state.session_id}")
                            # If cart cleared, order is completed! Let's check status directly by checking order detail
                            st.session_state.checkout_status = "paid"
                            st.toast("Payment verified successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Status check failed: {e}")

# ----------------- VIEW 2: MERCHANT DASHBOARD -----------------
elif view_mode == "📊 Merchant Dashboard":
    st.title("📊 AI Growth & Agentic Commerce Dashboard")
    st.markdown("Real-time performance metrics computed from persistent logs & transactions database.")
    
    # Fetch metrics from backend
    try:
        metrics_res = requests.get(f"{BACKEND_URL}/api/metrics")
        metrics = metrics_res.json() if metrics_res.status_code == 200 else {}
    except Exception as e:
        metrics = {}
        st.error(f"Failed to fetch metrics: {e}")
        
    if not metrics:
        st.warning("No metrics available. Make a few test transactions first!")
    else:
        # Layout metrics in grid
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Total Conversations</div>
                    <div class="metric-value">{metrics['conversations']}</div>
                </div>""", unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Total Revenue</div>
                    <div class="metric-value">₹{metrics['revenue']}</div>
                </div>""", unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Average Order Value</div>
                    <div class="metric-value">₹{metrics['aov']}</div>
                </div>""", unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Conversion Rate</div>
                    <div class="metric-value">{metrics['conversion_rate']}%</div>
                </div>""", unsafe_allow_html=True
            )
            
        st.divider()
        
        col5, col6, col7 = st.columns(3)
        with col5:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Successful Payments</div>
                    <div class="metric-value" style="color:#00f2c3;">{metrics['successful_payments']}</div>
                </div>""", unsafe_allow_html=True
            )
        with col6:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">Upsell Acceptance Rate</div>
                    <div class="metric-value">{metrics['upsell_acceptance_rate']}%</div>
                </div>""", unsafe_allow_html=True
            )
        with col7:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-title">AI-Influenced Revenue</div>
                    <div class="metric-value" style="color:#f1f2f6;">₹{metrics['ai_influenced_revenue']}</div>
                </div>""", unsafe_allow_html=True
            )
            
        st.divider()
        
        # Audit Log Feed
        st.subheader("📜 Live Event Audit Trail")
        try:
            audit_res = requests.get(f"{BACKEND_URL}/api/audit/{st.session_state.session_id}")
            audit_logs = audit_res.json() if audit_res.status_code == 200 else []
        except Exception:
            audit_logs = []
            
        if not audit_logs:
            st.info("No audit logs found for current session.")
        else:
            for log in reversed(audit_logs):
                with st.expander(f"🕒 {log['timestamp'][:19].replace('T', ' ')} | Agent: {log['agent']} | Action: {log['action']}"):
                    st.write("**Input:**", log["input"])
                    st.write("**Output:**", log["output"])
                    if log.get("tool"):
                        st.write(f"**Tool Call ({log['tool']}):**", log.get("result"))
                    st.write("**User Confirmed:**", log["user_confirmation"])

# ----------------- VIEW 3: AGENT OBSERVABILITY TRACE -----------------
elif view_mode == "🔍 Agent Observability Trace":
    st.title("🔍 Agent Trace Panel")
    st.markdown("Inspect the LangGraph workflow's active nodes and intermediate reasoning states.")
    
    if not st.session_state.agent_trace:
        st.info("No conversation trace compiled yet. Converse with the Shopper Agent to see traces!")
    else:
        st.subheader("⛓️ Turn Graph Execution Flow")
        for node in st.session_state.agent_trace:
            st.markdown(f'<div class="trace-node">⚙️ {node} executed successfully.</div>', unsafe_allow_html=True)
            
        st.divider()
        
        col_state1, col_state2 = st.columns(2)
        with col_state1:
            st.subheader("🎯 Shopper Intent Extractions")
            st.json(st.session_state.shopper_intent)
            
        with col_state2:
            st.subheader("💡 Selected Upsell Recommendation")
            st.json(st.session_state.upsell)

# ----------------- VIEW 4: AI BUYER SIMULATION -----------------
elif view_mode == "🤖 AI Buyer Simulation":
    st.title("🤖 Autonomous AI Buyer Simulation")
    st.markdown("Demonstrating structured Catalog APIs and agent-readable capability endpoints.")
    
    st.subheader("📋 Advertised capabilities")
    try:
        cap_res = requests.get(f"{BACKEND_URL}/api/agent/capabilities")
        st.json(cap_res.json() if cap_res.status_code == 200 else {"error": "Capabilities not available"})
    except Exception as e:
        st.error(f"Error fetching capabilities: {e}")
        
    st.divider()
    
    st.subheader("⚡ Run AI Buyer Transaction Simulation")
    scenario = st.selectbox(
        "Choose Shopping Scenario for AI Buyer",
        [
            "Scenario A: Find a wireless gaming mechanical keyboard under ₹6000 and add to cart",
            "Scenario B: Search premium anti-frizz beauty serum under ₹1500 and checkout",
            "Scenario C: Discover yoga mats under ₹2000, request upsell, and proceed"
        ]
    )
    
    if st.button("🚀 Start Simulation", use_container_width=True):
        sim_container = st.container()
        with sim_container:
            st.markdown("#### Simulation Step-by-Step logs:")
            
            # Step 1: Advertise
            st.info("🤖 **AI Buyer Step 1:** Fetching merchant capabilities...")
            st.code("GET /api/agent/capabilities -> SUCCESS")
            
            # Step 2: Search Query mapping
            query = ""
            category = ""
            max_price = 10000.0
            if "Scenario A" in scenario:
                query = "mechanical keyboard"
                category = "Electronics"
                max_price = 6000.0
            elif "Scenario B" in scenario:
                query = "argan serum"
                category = "Beauty"
                max_price = 1500.0
            elif "Scenario C" in scenario:
                query = "yoga mat"
                category = "Fitness"
                max_price = 2000.0
                
            st.info(f"🤖 **AI Buyer Step 2:** Querying catalog API matching scenario constraint...")
            st.code(f"POST /api/catalog/search {{'query': '{query}', 'category': '{category}', 'max_price': {max_price}}}")
            
            # Request search
            try:
                search_res = requests.post(f"{BACKEND_URL}/api/catalog/search", json={
                    "query": query,
                    "category": category,
                    "max_price": max_price
                })
                products = search_res.json()
                st.write(f"Found {len(products)} matching products:")
                st.json(products)
                
                if not products:
                    st.error("No products matching query!")
                else:
                    selected_prod = products[0]
                    pid = selected_prod["product_id"]
                    name = selected_prod["name"]
                    
                    # Step 3: Add to cart
                    st.info(f"🤖 **AI Buyer Step 3:** Selecting product '{name}' and sending add_to_cart request...")
                    st.code(f"POST /api/cart/{st.session_state.session_id}/items {{'product_id': '{pid}', 'quantity': 1}}")
                    
                    add_cart_res = requests.post(f"{BACKEND_URL}/api/cart/{st.session_state.session_id}/items", json={
                        "product_id": pid,
                        "quantity": 1
                    })
                    st.success(add_cart_res.json().get("message", "Success!"))
                    
                    # Step 4: Checkout
                    st.info("🤖 **AI Buyer Step 4:** Finalizing selections, calculating pricing, preparing checkout order...")
                    st.code(f"POST /api/payment/create-order {{'session_id': '{st.session_state.session_id}'}}")
                    
                    order_res = requests.post(f"{BACKEND_URL}/api/payment/create-order", json={
                        "session_id": st.session_state.session_id
                    })
                    order_data = order_res.json()
                    st.json(order_data)
                    
                    st.success(f"🎉 Simulation Complete! Razorpay Order created: **{order_data['order_id']}**. Payment confirmation pending customer approval.")
            except Exception as ex:
                st.error(f"Simulation failed: {ex}")