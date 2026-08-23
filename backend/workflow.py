from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
import json

from agents.commerce_agents import (
    router_agent,
    intent_agent,
    recommendation_agent,
    upsell_agent
)
from services import catalog_service, cart_service, razorpay_service, audit_service

# Define the state schema
class AgentState(TypedDict):
    session_id: str
    user_input: str
    response: str
    selected_agent: str
    conversation_history: list  # list of dicts: {"role": str, "content": str}
    
    # Commerce state
    intent: str
    shopper_intent: dict
    retrieved_products: list
    recommendations: dict
    upsell: dict
    cart: dict
    checkout_status: str  # pending_confirm, confirmed, paid
    payment_order: dict
    agent_trace: list

# NODES

def router_node(state: AgentState):
    """Classifies user intent."""
    user_input = state["user_input"]
    history = state.get("conversation_history", [])
    
    # Classify intent
    result = router_agent(user_input, history)
    intent = result.get("intent", "general_question")
    
    trace = state.get("agent_trace", [])
    trace = trace + ["Router Agent"]
    
    # Log audit event
    audit_service.log_event(
        session_id=state["session_id"],
        agent="Router Agent",
        action="classify_intent",
        input_data=user_input,
        output_data=result
    )
    
    return {
        "intent": intent,
        "selected_agent": intent,
        "agent_trace": trace
    }

def intent_node(state: AgentState):
    """Extracts shopper constraints."""
    user_input = state["user_input"]
    prev_intent = state.get("shopper_intent", {})
    
    # Extract intent
    shopper_intent = intent_agent(user_input, prev_intent)
    
    trace = state.get("agent_trace", []) + ["Shopper Intent Agent"]
    
    audit_service.log_event(
        session_id=state["session_id"],
        agent="Shopper Intent Agent",
        action="extract_shopper_intent",
        input_data={"user_input": user_input, "prev_intent": prev_intent},
        output_data=shopper_intent
    )
    
    return {
        "shopper_intent": shopper_intent,
        "agent_trace": trace
    }

def retrieval_node(state: AgentState):
    """Retrieves products from the merchant catalog."""
    user_input = state["user_input"]
    intent = state.get("shopper_intent", {})
    
    category = intent.get("category")
    budget_max = intent.get("budget_max")
    
    # Retrieve products with filters
    retrieved = catalog_service.search_products(
        query=user_input,
        limit=4,
        category=category,
        max_price=budget_max
    )
    
    trace = state.get("agent_trace", []) + ["Catalog Retrieval Agent"]
    
    audit_service.log_event(
        session_id=state["session_id"],
        agent="Catalog Retrieval Agent",
        action="search_catalog",
        input_data={"query": user_input, "filters": {"category": category, "budget_max": budget_max}},
        output_data=[p["product_id"] for p in retrieved],
        tool="catalog_search",
        result=f"Found {len(retrieved)} products"
    )
    
    return {
        "retrieved_products": retrieved,
        "agent_trace": trace
    }

def recommendation_node(state: AgentState):
    """Ranks and explains product recommendations."""
    user_input = state["user_input"]
    intent = state.get("shopper_intent", {})
    retrieved = state.get("retrieved_products", [])
    
    rec_result = recommendation_agent(user_input, intent, retrieved)
    explanation = rec_result.get("explanation", "")
    recs = rec_result.get("recommendations", [])
    
    trace = state.get("agent_trace", []) + ["Recommendation Agent"]
    
    audit_service.log_event(
        session_id=state["session_id"],
        agent="Recommendation Agent",
        action="rank_recommendations",
        input_data={"intent": intent, "retrieved_count": len(retrieved)},
        output_data=rec_result
    )
    
    return {
        "recommendations": recs,
        "response": explanation,
        "agent_trace": trace
    }

def upsell_node(state: AgentState):
    """Contextually pitches complementary products."""
    session_id = state["session_id"]
    cart_data = cart_service.get_cart(session_id)
    recs = state.get("recommendations", [])
    
    # Invoke upsell agent
    result = upsell_agent(cart_data.get("items", []), recs, state.get("conversation_history", []))
    
    trace = state.get("agent_trace", []) + ["Upsell Agent"]
    response = state.get("response", "")
    
    upsell_data = {}
    if result.get("suggest_upsell") and result.get("product_id"):
        pid = result["product_id"]
        pitch = result["reason"]
        
        # Verify compatibility and inventory one last time
        prod = catalog_service.get_product(pid)
        if prod and prod["inventory"] > 0:
            upsell_data = {
                "product_id": pid,
                "name": prod["name"],
                "price": prod["price"],
                "pitch": pitch
            }
            # Append pitch to final response
            response = f"{response}\n\n💡 *Special Offer:* {pitch}"
            
            audit_service.log_event(
                session_id=session_id,
                agent="Upsell Agent",
                action="pitch_upsell",
                input_data=pid,
                output_data=pitch
            )
            
    return {
        "upsell": upsell_data,
        "response": response,
        "agent_trace": trace
    }

def cart_node(state: AgentState):
    """Deterministic Cart Updates (add, remove, update)."""
    session_id = state["session_id"]
    user_input = state["user_input"]
    intent = state.get("intent", "cart_add")
    
    # We parse the LLM intent parameters or run a quick classification to extract product and qty
    # Let's use a fast prompt to extract action details
    prompt = f"""
    Analyze the user cart request: "{user_input}"
    Extracted Intent: {intent}
    
    Identify:
    1. "product_name": A string of the product name or ID they want to add/remove/update.
    2. "quantity": An integer quantity (default to 1 if not specified).
    
    Available Catalog Products:
    {json.dumps([{"product_id": p["product_id"], "name": p["name"]} for p in catalog_service.get_all_products()])}
    
    Return ONLY a valid JSON object:
    {{
        "product_id": "matched_product_id_here_or_null",
        "quantity": 1
    }}
    """
    from agent import llm
    from agents.commerce_agents import parse_json_safely
    
    extraction = parse_json_safely(llm.invoke(prompt).content, {"product_id": None, "quantity": 1})
    pid = extraction.get("product_id")
    qty = extraction.get("quantity", 1)
    
    cart_msg = ""
    if not pid:
        cart_msg = "I couldn't identify which product you want to modify in your cart. Could you specify the product name?"
    else:
        if intent == "cart_add":
            cart_msg = cart_service.add_to_cart(session_id, pid, qty)
        elif intent == "cart_remove":
            cart_msg = cart_service.remove_from_cart(session_id, pid)
        elif intent == "cart_update":
            cart_msg = cart_service.update_quantity(session_id, pid, qty)
            
    # Calculate cart status for display
    cart_data = cart_service.get_cart(session_id)
    
    trace = state.get("agent_trace", []) + ["Cart Agent"]
    
    # Construct response summarizing the action and cart
    items_desc = []
    for item in cart_data["items"]:
        items_desc.append(f"- {item['name']} (x{item['quantity']}) - ₹{item['total']}")
        
    cart_summary = "\n".join(items_desc) if items_desc else "Your cart is empty."
    response = f"{cart_msg}\n\n🛒 **Current Cart:**\n{cart_summary}\n\n**Subtotal:** ₹{cart_data['subtotal']}\n**Discount:** -₹{cart_data['discount']}\n**Shipping:** ₹{cart_data['shipping']}\n**Total:** ₹{cart_data['final_total']}"
    
    audit_service.log_event(
        session_id=session_id,
        agent="Cart Agent",
        action=intent,
        input_data={"product_id": pid, "quantity": qty},
        output_data=response
    )
    
    return {
        "cart": cart_data,
        "response": response,
        "agent_trace": trace
    }

def checkout_node(state: AgentState):
    """Prepares checkout details and handles confirmation gate."""
    session_id = state["session_id"]
    cart_data = cart_service.get_cart(session_id)
    
    trace = state.get("agent_trace", []) + ["Checkout Agent"]
    
    if not cart_data["items"]:
        return {
            "response": "Your cart is empty! Add some items before checking out.",
            "checkout_status": "pending_confirm",
            "agent_trace": trace
        }
        
    items_desc = "\n".join([f"- {item['name']} (x{item['quantity']}) - ₹{item['total']}" for item in cart_data["items"]])
    
    response = (
        f"📝 **Checkout Summary:**\n\n"
        f"{items_desc}\n\n"
        f"--- \n"
        f"**Subtotal:** ₹{cart_data['subtotal']}\n"
        f"**Discount:** -₹{cart_data['discount']}\n"
        f"**Tax (GST 18% Incl.):** ₹{cart_data['tax']}\n"
        f"**Shipping:** ₹{cart_data['shipping']}\n"
        f"**Grand Total:** ₹{cart_data['final_total']}\n\n"
        f"⚠️ **Would you like to proceed to payment?** Please confirm by typing 'yes' or clicking the checkout button."
    )
    
    audit_service.log_event(
        session_id=session_id,
        agent="Checkout Agent",
        action="prepare_checkout",
        input_data=cart_data,
        output_data=response
    )
    
    return {
        "cart": cart_data,
        "response": response,
        "checkout_status": "pending_confirm",
        "agent_trace": trace
    }

def status_node(state: AgentState):
    """Handles order or payment status query."""
    session_id = state["session_id"]
    user_input = state["user_input"]
    intent = state.get("intent", "order_status")
    
    orders = razorpay_service.get_all_orders()
    session_orders = [o for o in orders.values() if o.get("session_id") == session_id]
    
    trace = state.get("agent_trace", []) + ["Payment Agent"]
    
    if not session_orders:
        response = "I couldn't find any orders placed in this session yet."
    else:
        # Sort by creation / ID
        latest_order = session_orders[-1]
        oid = latest_order["order_id"]
        status = latest_order["status"]
        amount = latest_order["amount_rupees"]
        pay_id = latest_order.get("payment_id", "N/A")
        
        response = (
            f"📦 **Order Status:**\n\n"
            f"- **Order ID:** `{oid}`\n"
            f"- **Amount:** ₹{amount}\n"
            f"- **Status:** `{status.upper()}`\n"
            f"- **Payment ID:** `{pay_id}`\n\n"
            f"If payment is completed, you can check details on the merchant dashboard!"
        )
        
    audit_service.log_event(
        session_id=session_id,
        agent="Payment Agent",
        action=intent,
        input_data=user_input,
        output_data=response
    )
    
    return {
        "response": response,
        "agent_trace": trace
    }

def general_node(state: AgentState):
    """Handles greeting, general questions, capabilities, or unsupported queries."""
    user_input = state["user_input"]
    intent = state.get("intent", "general_question")
    
    trace = state.get("agent_trace", []) + ["Assistant"]
    
    if intent == "unsupported_request":
        from agent import llm
        prompt = f"""
        You are the Shopping Assistant for AgentForge Commerce.
        The user has asked something completely unrelated to shopping, product discovery, or merchant services.
        Politely explain that you can only help with product searches, recommendations, shopping cart management, and checkouts.
        
        User Input: "{user_input}"
        """
        response = llm.invoke(prompt).content
    else:
        # General question or greeting
        from agent import llm
        prompt = f"""
        You are the Shopping Assistant for AgentForge Commerce.
        Provide a helpful greeting or answer the general query about the store.
        We sell Electronics, Fashion, Beauty, Home decor, and Fitness products.
        Briefly explain that they can search for products (e.g. "gift for sister under ₹2000") or ask about their cart.
        
        User Input: "{user_input}"
        """
        response = llm.invoke(prompt).content
        
    audit_service.log_event(
        session_id=state["session_id"],
        agent="Assistant",
        action=intent,
        input_data=user_input,
        output_data=response
    )
    
    return {
        "response": response,
        "agent_trace": trace
    }

# CONDITIONAL ROUTING

def route_agent(state: AgentState):
    """Routes execution based on intent."""
    intent = state.get("intent", "general_question")
    
    if intent in ["product_search", "product_comparison", "recommendation"]:
        return "shopping_path"
    elif intent in ["cart_add", "cart_remove", "cart_update"]:
        return "cart_path"
    elif intent == "checkout":
        return "checkout"
    elif intent in ["payment_status", "order_status"]:
        return "status"
    else:
        return "general"

# BUILD GRAPH
graph = StateGraph(AgentState)

# Add Nodes
graph.add_node("router", router_node)
graph.add_node("intent", intent_node)
graph.add_node("retrieved", retrieval_node)
graph.add_node("recommendation", recommendation_node)
graph.add_node("upsell", upsell_node)
graph.add_node("cart", cart_node)
graph.add_node("checkout", checkout_node)
graph.add_node("status", status_node)
graph.add_node("general", general_node)

# Flow Setup
graph.set_entry_point("router")

# Router conditional edges
graph.add_conditional_edges(
    "router",
    route_agent,
    {
        "shopping_path": "intent",
        "cart_path": "cart",
        "checkout": "checkout",
        "status": "status",
        "general": "general"
    }
)

# Connect shopping path
graph.add_edge("intent", "retrieved")
graph.add_edge("retrieved", "recommendation")
graph.add_edge("recommendation", "upsell")
graph.add_edge("upsell", END)

# Connect cart path
graph.add_edge("cart", "upsell")

# Connect final steps to END
graph.add_edge("checkout", END)
graph.add_edge("status", END)
graph.add_edge("general", END)

app_workflow = graph.compile()