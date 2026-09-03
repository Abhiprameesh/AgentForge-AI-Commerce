import json
import re
from agent import llm
from services.catalog_service import get_product

def clean_json_response(content: str) -> str:
    """Strip code blocks, markdown wrapper, or whitespace around a JSON response."""
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def parse_json_safely(content: str, default: dict) -> dict:
    """Clean and parse JSON with safety fallback."""
    cleaned = clean_json_response(content)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON Parsing Error: {e} | Content: {content}")
        # Try a quick regex fallback if possible
        try:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
        return default

def router_agent(user_input: str, conversation_history: list = None) -> dict:
    """
    Commerce Router Agent.
    Identifies intent from user request and returns a structured classification.
    """
    history_str = ""
    if conversation_history:
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])

    prompt = f"""
    You are the Core Commerce Router for AgentForge Commerce.
    Analyze the user's input (and recent history) and identify the customer's current intent.

    Available Intents:
    1. "product_search": User is looking for products, searching, asking for types of items.
    2. "product_comparison": User wants to compare two or more specific products.
    3. "recommendation": User wants a recommendation based on criteria (e.g. gift ideas, specific recipient).
    4. "cart_add": User wants to add an item to their shopping cart.
    5. "cart_remove": User wants to remove an item from their cart.
    6. "cart_update": User wants to update the quantity of an item in their cart.
    7. "checkout": User wants to proceed to checkout, pay, buy, or finalize the order.
    8. "payment_status": User is checking if their payment was successful.
    9. "order_status": User is checking order details or order history.
    10. "general_question": General greeting, queries about shop policy, shipping times, or capability questions.
    11. "unsupported_request": Irrelevant queries (e.g., coding help, math, resumes, job interviews, writing code).

    Return ONLY a valid JSON object matching this schema:
    {{
        "intent": "intent_string_here",
        "reason": "Short explanation of why this intent was selected"
    }}

    Recent History:
    {history_str}

    User Input:
    "{user_input}"
    """
    
    response = llm.invoke(prompt)
    default_resp = {"intent": "general_question", "reason": "Failed to parse router output."}
    return parse_json_safely(response.content, default_resp)

def intent_agent(user_input: str, previous_intent: dict = None) -> dict:
    """
    Shopper Intent Agent.
    Extracts structured constraints (category, budget, recipient, occasion, preferences) from natural language.
    """
    prev_str = json.dumps(previous_intent) if previous_intent else "{}"
    
    prompt = f"""
    You are the Shopper Intent Agent for AgentForge Commerce.
    Your job is to extract structured shopping requirements from the user's query and merge them with any existing requirements.

    Extract the following fields:
    - "category": The product category mentioned (e.g. skincare, electronics, fashion, beauty, home, fitness).
    - "budget_max": The maximum budget if specified. Return a number in INR (e.g. 2000). If not specified, return null.
    - "occasion": The occasion if mentioned (e.g. birthday, wedding, anniversary, workout, travel).
    - "recipient": The recipient if mentioned (e.g. sister, self, friend, father, boyfriend).
    - "preferences": A list of specific preferences or attributes mentioned (e.g. premium, wireless, mechanical, organic, gel, waterproof).

    Return ONLY a valid JSON object matching this schema. Merge the new criteria with the previous criteria. If a field isn't mentioned and is empty in previous criteria, return null.
    {{
        "category": "string or null",
        "budget_max": number or null,
        "occasion": "string or null",
        "recipient": "string or null",
        "preferences": ["string"]
    }}

    Previous Criteria:
    {prev_str}

    User Query:
    "{user_input}"
    """
    
    response = llm.invoke(prompt)
    default_resp = {"category": None, "budget_max": None, "occasion": None, "recipient": None, "preferences": []}
    return parse_json_safely(response.content, default_resp)

def recommendation_agent(user_query: str, shopper_intent: dict, retrieved_products: list) -> dict:
    """
    Recommendation Agent.
    Produces ranked recommendations based on intent and retrieved products.
    """
    if not retrieved_products:
        return {
            "explanation": "I couldn't find any products in our catalog matching those criteria. Let's try searching for another category or adjusting your budget.",
            "recommendations": []
        }

    # Format retrieved products for prompt
    products_context = []
    for p in retrieved_products:
        products_context.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "description": p["description"],
            "price": p["price"],
            "discount": p["discount"],
            "brand": p["brand"],
            "rating": p["rating"],
            "popularity": p["popularity"],
            "inventory": p["inventory"]
        })

    products_str = json.dumps(products_context, indent=2)
    intent_str = json.dumps(shopper_intent, indent=2)

    prompt = f"""
    You are the Recommendation Agent for AgentForge Commerce.
    Your goal is to rank the retrieved products based on the customer query and intent, explaining why they match the buyer's needs.

    RULES:
    1. Do NOT invent products, prices, discounts, or inventory. Only use the products listed below.
    2. Suggest only products that are in stock (inventory > 0). If out of stock, do not recommend.
    3. Rank them from best match (Rank 1) to least. Limit to max 3 recommendations.
    4. Provide a clear, personalized reason for why each product matches.

    Return ONLY a valid JSON object matching this schema:
    {{
        "explanation": "A friendly conversational summary explaining the options and how they fit the requirements.",
        "recommendations": [
            {{
                "product_id": "product_id_here",
                "reason": "Explain why this matches their intent specifically (e.g. Under the budget of 2000, perfect premium gift for sister).",
                "confidence": 0.0 to 1.0,
                "rank": 1
            }}
        ]
    }}

    Customer Query:
    "{user_query}"

    Extracted Intent:
    {intent_str}

    Retrieved Products:
    {products_str}
    """

    response = llm.invoke(prompt)
    default_resp = {
        "explanation": "I found these items in our catalog for you.",
        "recommendations": []
    }
    return parse_json_safely(response.content, default_resp)

def upsell_agent(cart_items: list, recommended_items: list, conversation_history: list = None) -> dict:
    """
    Upsell Agent.
    Selects a complementary, in-stock product from the catalog that goes well with the active products.
    """
    # 1. Identify active product IDs (from cart or recent recommendations)
    active_ids = [item["product_id"] for item in cart_items]
    if not active_ids:
        active_ids = [item["product_id"] for item in recommended_items]
        
    if not active_ids:
        return {"suggest_upsell": False, "product_id": None, "reason": None}

    # 2. Extract potential complementary products deterministically from catalog
    potential_upsell_candidates = []
    for pid in active_ids:
        prod = get_product(pid)
        if prod and prod.get("complementary_products"):
            for comp_id in prod["complementary_products"]:
                comp_prod = get_product(comp_id)
                # Ensure complementary product exists, is in stock, and not already in active list
                if comp_prod and comp_prod["inventory"] > 0 and comp_id not in active_ids:
                    if comp_prod not in potential_upsell_candidates:
                        potential_upsell_candidates.append(comp_prod)

    if not potential_upsell_candidates:
        return {"suggest_upsell": False, "product_id": None, "reason": None}

    # 3. Use LLM to contextually select the best candidate (if any) and write a pitch
    candidates_context = [{
        "product_id": c["product_id"],
        "name": c["name"],
        "price": c["price"],
        "description": c["description"],
        "discount": c["discount"]
    } for c in potential_upsell_candidates]

    history_str = ""
    if conversation_history:
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-4:]])

    prompt = f"""
    You are the Upsell Agent for AgentForge Commerce.
    Your goal is to suggest a single complementary product from the candidate list that goes well with the customer's shopping list.

    RULES:
    1. Suggest an upsell ONLY if it fits naturally into the conversation. Do not be pushy or repetitive.
    2. Choose at most ONE product.
    3. Pitch it conversationally. Highlight compatibility.

    Return ONLY a valid JSON object matching this schema:
    {{
        "suggest_upsell": true or false,
        "product_id": "product_id_here or null",
        "reason": "A highly contextual pitch explaining why this is a great addition (e.g. 'Since you got the KeyCraft mechanical keyboard, would you like to add the KeyCraft Memory Foam Palm Rest for ₹799? It helps prevent wrist fatigue during long coding sessions.')"
    }}

    Currently Selected Products:
    {json.dumps(active_ids)}

    Recent Conversation History:
    {history_str}

    Upsell Candidates:
    {json.dumps(candidates_context, indent=2)}
    """

    response = llm.invoke(prompt)
    default_resp = {"suggest_upsell": False, "product_id": None, "reason": None}
    return parse_json_safely(response.content, default_resp)


def router_intent_agent(user_input: str, conversation_history: list = None, previous_shopper_intent: dict = None) -> dict:
    """
    Combined Commerce Router and Shopper Intent Agent.
    Classifies intent AND extracts/merges shopper constraints in one single LLM call.
    """
    history_str = ""
    if conversation_history:
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])
        
    prev_intent_str = json.dumps(previous_shopper_intent) if previous_shopper_intent else "{}"
    
    prompt = f"""
    You are the Core Commerce Router and Intent Extractor for AgentForge Commerce.
    Analyze the user's input (and recent history) to:
    1. Identify the customer's current intent.
    2. Extract structured shopping requirements (if applicable) and merge them with any previous criteria.

    Available Intents:
    1. "product_search": User is looking for products, searching, asking for types of items.
    2. "product_comparison": User wants to compare two or more specific products.
    3. "recommendation": User wants a recommendation based on criteria (e.g. gift ideas, specific recipient).
    4. "cart_add": User wants to add an item to their shopping cart.
    5. "cart_remove": User wants to remove an item from their cart.
    6. "cart_update": User wants to update the quantity of an item in their cart.
    7. "checkout": User wants to proceed to checkout, pay, buy, or finalize the order.
    8. "payment_status": User is checking if their payment was successful.
    9. "order_status": User is checking order details or order history.
    10. "general_question": General greeting, queries about shop policy, shipping times, or capability questions.
    11. "unsupported_request": Irrelevant queries (e.g., coding help, math, resumes, job interviews, writing code).

    Shopper Intent Extraction Fields (only extract if the intent is shopping-related: product_search, product_comparison, recommendation):
    - "category": The product category mentioned (e.g. skincare, electronics, fashion, beauty, home, fitness).
    - "budget_max": The maximum budget if specified. Return a number in INR (e.g. 2000). If not specified, return null.
    - "occasion": The occasion if mentioned (e.g. birthday, wedding, anniversary, workout, travel).
    - "recipient": The recipient if mentioned (e.g. sister, self, friend, father, boyfriend).
    - "preferences": A list of specific preferences or attributes mentioned (e.g. premium, wireless, mechanical, organic, gel, waterproof).

    Return ONLY a valid JSON object matching this schema. If the intent is not shopping-related, set all shopper_intent fields to null (or empty list for preferences). Merge any new shopping criteria with the previous criteria.
    {{
        "intent": "intent_string_here",
        "reason": "Short explanation of why this intent was selected",
        "shopper_intent": {{
            "category": "string or null",
            "budget_max": number or null,
            "occasion": "string or null",
            "recipient": "string or null",
            "preferences": ["string"]
        }}
    }}

    Previous Shopping Criteria:
    {prev_intent_str}

    Recent History:
    {history_str}

    User Input:
    "{user_input}"
    """
    response = llm.invoke(prompt)
    default_resp = {
        "intent": "general_question",
        "reason": "Failed to parse router output.",
        "shopper_intent": {"category": None, "budget_max": None, "occasion": None, "recipient": None, "preferences": []}
    }
    return parse_json_safely(response.content, default_resp)


def recommendation_upsell_agent(user_query: str, shopper_intent: dict, retrieved_products: list, potential_upsell_candidates: list = None, conversation_history: list = None) -> dict:
    """
    Combined Recommendation and Upsell Agent.
    Produces ranked recommendations based on intent/retrieved products, AND pitches a complementary product in the same LLM call.
    """
    if not retrieved_products:
        return {
            "explanation": "I couldn't find any products in our catalog matching those criteria. Let's try searching for another category or adjusting your budget.",
            "recommendations": [],
            "suggest_upsell": False,
            "upsell_product_id": None,
            "upsell_reason": None
        }

    # Format retrieved products for prompt
    products_context = []
    for p in retrieved_products:
        products_context.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "description": p["description"],
            "price": p["price"],
            "discount": p["discount"],
            "brand": p["brand"],
            "rating": p["rating"],
            "popularity": p["popularity"],
            "inventory": p["inventory"]
        })

    products_str = json.dumps(products_context, indent=2)
    intent_str = json.dumps(shopper_intent, indent=2)

    # Format upsell candidates
    candidates_context = []
    if potential_upsell_candidates:
        candidates_context = [{
            "product_id": c["product_id"],
            "name": c["name"],
            "price": c["price"],
            "description": c["description"],
            "discount": c["discount"]
        } for c in potential_upsell_candidates]

    history_str = ""
    if conversation_history:
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-4:]])

    prompt = f"""
    You are the Recommendation and Upsell Agent for AgentForge Commerce.
    Your goals are:
    1. Rank the retrieved products based on the customer query and intent, explaining why they match the buyer's needs.
    2. Suggest a single complementary product from the candidate list that goes well with the customer's shopping list / recommendations.

    RULES FOR RECOMMENDATIONS:
    1. Do NOT invent products, prices, discounts, or inventory. Only use the products listed below.
    2. Suggest only products that are in stock (inventory > 0). If out of stock, do not recommend.
    3. Rank them from best match (Rank 1) to least. Limit to max 3 recommendations.
    4. Provide a clear, personalized reason for why each product matches.

    RULES FOR UPSELL:
    1. Suggest an upsell ONLY if it fits naturally into the conversation. Do not be pushy or repetitive.
    2. Choose at most ONE product from the Upsell Candidates list.
    3. Pitch it conversationally. Highlight compatibility.

    Return ONLY a valid JSON object matching this schema:
    {{
        "explanation": "A friendly conversational summary explaining the options and how they fit the requirements.",
        "recommendations": [
            {{
                "product_id": "product_id_here",
                "reason": "Explain why this matches their intent specifically (e.g. Under the budget of 2000, perfect premium gift for sister).",
                "confidence": 0.0 to 1.0,
                "rank": 1
            }}
        ],
        "suggest_upsell": true or false,
        "upsell_product_id": "product_id_here or null",
        "upsell_reason": "A highly contextual pitch explaining why this is a great addition or null if suggest_upsell is false"
    }}

    Customer Query:
    "{user_query}"

    Extracted Intent:
    {intent_str}

    Retrieved Products:
    {products_str}

    Upsell Candidates:
    {json.dumps(candidates_context, indent=2)}

    Recent Conversation History:
    {history_str}
    """

    response = llm.invoke(prompt)
    default_resp = {
        "explanation": "I found these items in our catalog for you.",
        "recommendations": [],
        "suggest_upsell": False,
        "upsell_product_id": None,
        "upsell_reason": None
    }
    return parse_json_safely(response.content, default_resp)

