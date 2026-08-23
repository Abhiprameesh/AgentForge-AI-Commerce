import sys
import os

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.abspath("backend"))

from agents import commerce_agents
from workflow import route_agent

def test_router_agent():
    """Verify intent classifications from user text inputs."""
    res1 = commerce_agents.router_agent("I want a birthday gift for my sister")
    # Should resolve to recommendation or search
    assert res1["intent"] in ["recommendation", "product_search"]
    
    res2 = commerce_agents.router_agent("add running shoes to my cart")
    assert res2["intent"] == "cart_add"
    
    res3 = commerce_agents.router_agent("Please proceed to checkout")
    assert res3["intent"] == "checkout"

def test_intent_agent():
    """Verify that occasion, recipient, and budgets are correctly parsed."""
    res = commerce_agents.intent_agent("skincare product under 1500 for my sister's birthday")
    assert res["category"].lower() == "skincare" or "skin" in res["category"].lower()
    assert res["budget_max"] == 1500
    assert "sister" in res["recipient"].lower()
    assert "birthday" in res["occasion"].lower()

def test_langgraph_routing():
    """Verify conditional edges route state to correct execution paths."""
    state_shopping = {"intent": "product_search"}
    assert route_agent(state_shopping) == "shopping_path"
    
    state_cart = {"intent": "cart_add"}
    assert route_agent(state_cart) == "cart_path"
    
    state_checkout = {"intent": "checkout"}
    assert route_agent(state_checkout) == "checkout"
    
    state_status = {"intent": "payment_status"}
    assert route_agent(state_status) == "status"
    
    state_general = {"intent": "general_question"}
    assert route_agent(state_general) == "general"
