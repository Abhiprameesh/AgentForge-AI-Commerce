import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath("backend"))

# Import test functions
from test_catalog import test_catalog_load, test_get_product, test_search_and_metadata_filtering, test_out_of_stock_flag
from test_cart import test_cart_operations
from test_payments import test_signature_verification_mock, test_signature_verification_real, test_webhook_idempotency
from test_agents import test_router_agent, test_intent_agent, test_langgraph_routing

def run_all_tests():
    print("==================================================")
    print("AgentForge Commerce Test Suite Runner")
    print("==================================================")
    
    test_cases = [
        ("test_catalog_load", test_catalog_load),
        ("test_get_product", test_get_product),
        ("test_search_and_metadata_filtering", test_search_and_metadata_filtering),
        ("test_out_of_stock_flag", test_out_of_stock_flag),
        ("test_cart_operations", test_cart_operations),
        ("test_signature_verification_mock", test_signature_verification_mock),
        ("test_signature_verification_real", test_signature_verification_real),
        ("test_webhook_idempotency", test_webhook_idempotency),
        ("test_router_agent", test_router_agent),
        ("test_intent_agent", test_intent_agent),
        ("test_langgraph_routing", test_langgraph_routing),
    ]
    
    passed = 0
    failed = 0
    
    for name, func in test_cases:
        try:
            print(f"Running {name:.<45} ", end="")
            func()
            print("... [PASSED]")
            passed += 1
        except Exception as e:
            print("... [FAILED]")
            print(f"  Error details: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            
    print("==================================================")
    print(f"Test Execution Summary: {passed} passed, {failed} failed")
    print("==================================================")
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()
