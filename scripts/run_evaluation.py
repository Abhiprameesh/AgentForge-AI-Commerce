import sys
import os
import json
from datetime import datetime

# Reconfigure stdout to support UTF-8 characters (like rupee symbols) on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.abspath("backend"))

from workflow import app_workflow
from services import catalog_service, cart_service, razorpay_service

scenarios = [
    # 1. Recommendations & Search (15 scenarios)
    {
        "query": "I need a birthday gift for my sister under ₹2000. She likes skincare and I want something premium.",
        "expected_intent": "recommendation",
        "category": "Beauty",
        "budget_max": 2000
    },
    {
        "query": "Find running shoes under ₹3000.",
        "expected_intent": "product_search",
        "category": "Fashion",
        "budget_max": 3000
    },
    {
        "query": "I want to buy a high-end mechanical keyboard for programming. Show me options.",
        "expected_intent": "product_search",
        "category": "Electronics",
        "budget_max": None
    },
    {
        "query": "Recommend a yoga mat under ₹2500.",
        "expected_intent": "recommendation",
        "category": "Fitness",
        "budget_max": 2500
    },
    {
        "query": "I am looking for premium argan hair serum under ₹2000.",
        "expected_intent": "product_search",
        "category": "Beauty",
        "budget_max": 2000
    },
    {
        "query": "What essential oil diffusers do you have under ₹3000?",
        "expected_intent": "product_search",
        "category": "Home",
        "budget_max": 3000
    },
    {
        "query": "Recommend some t-shirts or hoodies under ₹1500.",
        "expected_intent": "recommendation",
        "category": "Fashion",
        "budget_max": 1500
    },
    {
        "query": "Show me smartwatches or fitness trackers.",
        "expected_intent": "product_search",
        "category": "Electronics",
        "budget_max": None
    },
    {
        "query": "Recommend some weights or dumbbells for a home gym.",
        "expected_intent": "recommendation",
        "category": "Fitness",
        "budget_max": None
    },
    {
        "query": "I need decorative velvet pillow covers under ₹1000.",
        "expected_intent": "product_search",
        "category": "Home",
        "budget_max": 1000
    },
    {
        "query": "Suggest a good face wash under ₹800.",
        "expected_intent": "recommendation",
        "category": "Beauty",
        "budget_max": 800
    },
    {
        "query": "Show me canvas duffle bags for travel.",
        "expected_intent": "product_search",
        "category": "Fashion",
        "budget_max": None
    },
    {
        "query": "I need a fast charging power bank under ₹2000.",
        "expected_intent": "product_search",
        "category": "Electronics",
        "budget_max": 2000
    },
    {
        "query": "Recommend manual french press coffee makers.",
        "expected_intent": "recommendation",
        "category": "Home",
        "budget_max": None
    },
    {
        "query": "I am looking for a heart rate strap under ₹3000.",
        "expected_intent": "product_search",
        "category": "Fitness",
        "budget_max": 3000
    },

    # 2. Cart Actions (10 scenarios)
    {
        "query": "Add SonicWave Pro Noise-Cancelling Headphones to my cart.",
        "expected_intent": "cart_add",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Please put keycraft keyboard in my shopping cart.",
        "expected_intent": "cart_add",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Remove fash_001 from my cart.",
        "expected_intent": "cart_remove",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Change quantity of KeyCraft mechanical keyboard to 3.",
        "expected_intent": "cart_update",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Add ChargeGo Ultra power bank to cart.",
        "expected_intent": "cart_add",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Remove the power bank from my cart.",
        "expected_intent": "cart_remove",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Increase VeloFit tracker quantity to 2 in cart.",
        "expected_intent": "cart_update",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Put French Pink Clay Face Mask in my cart.",
        "expected_intent": "cart_add",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Delete clay mask from cart.",
        "expected_intent": "cart_remove",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Set running shoes quantity to 1 in cart.",
        "expected_intent": "cart_update",
        "category": None,
        "budget_max": None
    },

    # 3. Checkout, Payments & Status (5 scenarios)
    {
        "query": "I want to proceed to checkout and pay for my items.",
        "expected_intent": "checkout",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Let's checkout now.",
        "expected_intent": "checkout",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Has my payment been received? Check status.",
        "expected_intent": "payment_status",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Show me the status of my latest order.",
        "expected_intent": "order_status",
        "category": None,
        "budget_max": None
    },
    {
        "query": "Can you help me solve this algebra equation: 3x + 5 = 20?",
        "expected_intent": "unsupported_request",
        "category": None,
        "budget_max": None
    }
]

def run_evaluation():
    print(f"==================================================")
    print(f"Starting AgentForge Commerce Evaluation Engine")
    print(f"Evaluating {len(scenarios)} scenarios...")
    print(f"==================================================")

    results = []
    
    intent_correct = 0
    constraint_adhered = 0
    no_hallucinations = 0
    out_of_stock_rejected = 0
    total_evals = 0

    session_id = f"eval_{int(datetime.now().timestamp())}"

    # Verify out of stock flag works: Nomad USB Hub (elec_011) has inventory 0.
    # Let's ensure if we search or request it, it is handled.
    for idx, s in enumerate(scenarios):
        query = s["query"]
        expected_intent = s["expected_intent"]
        
        print(f"\n[{idx+1}/30] Query: '{query}'")
        
        state = {
            "session_id": session_id,
            "user_input": query,
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
            "cart": {"items": [], "subtotal": 0, "discount": 0, "shipping": 0, "final_total": 0},
            "checkout_status": "pending_confirm",
            "payment_order": {},
            "agent_trace": []
        }
        
        try:
            workflow_res = app_workflow.invoke(state)
            detected_intent = workflow_res.get("intent")
            recs = workflow_res.get("recommendations", [])
            
            # Check 1: Intent router accuracy
            is_intent_ok = detected_intent == expected_intent
            if is_intent_ok:
                intent_correct += 1
                
            # Check 2: Grounding and constraint check (for searches and recs)
            is_constraint_ok = True
            is_grounded = True
            
            if expected_intent in ["product_search", "recommendation"] and recs:
                for r in recs:
                    pid = r["product_id"]
                    prod = catalog_service.get_product(pid)
                    if not prod:
                        is_grounded = False  # Recommended a non-existent ID!
                        print(f"  ❌ Hallucinated product: {pid}")
                        continue
                    
                    # Category constraint
                    if s["category"] and prod["category"].lower() != s["category"].lower():
                        # Let's check tags as well, sometimes categorizations overlap
                        is_constraint_ok = False
                        print(f"  ❌ Category mismatch: Product {pid} is in {prod['category']} but expected {s['category']}")
                        
                    # Price constraint
                    actual_price = prod["price"] - prod["discount"]
                    if s["budget_max"] and actual_price > s["budget_max"]:
                        is_constraint_ok = False
                        print(f"  ❌ Budget exceeded: Product {pid} price is {actual_price} but max budget is {s['budget_max']}")
                        
            if is_grounded:
                no_hallucinations += 1
            if is_constraint_ok:
                constraint_adhered += 1
                
            print(f"  Result: Intent Router: {'✅ MATCH' if is_intent_ok else '❌ MISMATCH'} (Got '{detected_intent}', Expected '{expected_intent}')")
            if recs:
                print(f"  Recommendations Count: {len(recs)} | Grounded: {is_grounded} | Constraints Met: {is_constraint_ok}")
            
            results.append({
                "query": query,
                "expected_intent": expected_intent,
                "detected_intent": detected_intent,
                "recs_count": len(recs),
                "intent_correct": is_intent_ok,
                "grounded": is_grounded,
                "constraint_adherence": is_constraint_ok
            })
            
        except Exception as e:
            print(f"  ❌ Error executing workflow: {e}")
            results.append({
                "query": query,
                "error": str(e)
            })

    # Summary
    print(f"\n==================================================")
    print(f"Evaluation Complete! Summary Results:")
    print(f"==================================================")
    print(f"Total Scenarios Evaluated: {len(scenarios)}")
    print(f"Router Intent Accuracy: {intent_correct}/{len(scenarios)} ({round(intent_correct/len(scenarios)*100, 1)}%)")
    print(f"Recommendation Constraints Met: {constraint_adhered}/{len(scenarios)} ({round(constraint_adhered/len(scenarios)*100, 1)}%)")
    print(f"Hallucination Rate: {len(scenarios) - no_hallucinations} / {len(scenarios)} ({round((len(scenarios) - no_hallucinations)/len(scenarios)*100, 1)}%)")
    print(f"==================================================")

    # Save to file
    os.makedirs("evaluation", exist_ok=True)
    report_path = os.path.join("evaluation", "results.json")
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_evaluated": len(scenarios),
            "router_accuracy_pct": round(intent_correct/len(scenarios)*100, 1),
            "constraint_adherence_pct": round(constraint_adhered/len(scenarios)*100, 1),
            "hallucination_count": len(scenarios) - no_hallucinations,
            "detailed_results": results
        }, f, indent=4)
        
    print(f"Evaluation report saved to {report_path}")

if __name__ == "__main__":
    run_evaluation()
