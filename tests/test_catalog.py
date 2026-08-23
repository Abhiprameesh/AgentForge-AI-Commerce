import sys
import os

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.abspath("backend"))

from services import catalog_service

def test_catalog_load():
    """Verify that products are loaded from JSON on startup."""
    products = catalog_service.get_all_products()
    assert len(products) >= 50
    assert any(p["product_id"] == "elec_001" for p in products)

def test_get_product():
    """Verify detail retrieval for a specific product."""
    product = catalog_service.get_product("elec_001")
    assert product is not None
    assert product["name"] == "SonicWave Pro Noise-Cancelling Headphones"
    assert product["price"] == 14999
    
    # Check invalid product ID returns None (hallucination rejection)
    assert catalog_service.get_product("invalid_product_xyz") is None

def test_search_and_metadata_filtering():
    """Verify category and price constraints are met during search."""
    # Test Beauty under 2000
    results = catalog_service.search_products("serum", category="Beauty", max_price=2000)
    for p in results:
        assert p["category"] == "Beauty"
        assert (p["price"] - p["discount"]) <= 2000
        
    # Test Electronics category restriction
    results_elec = catalog_service.search_products("keyboard", category="Electronics")
    for p in results_elec:
        assert p["category"] == "Electronics"

def test_out_of_stock_flag():
    """Verify out-of-stock items (Nomad USB Hub - elec_011) are cataloged correctly."""
    out_of_stock_item = catalog_service.get_product("elec_011")
    assert out_of_stock_item is not None
    assert out_of_stock_item["inventory"] == 0
