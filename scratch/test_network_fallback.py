import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import razorpay_handler

print("=== TEST NETWORK FALLBACK: Mocking razorpay client exception ===")

original_create = razorpay_handler.razorpay.Client

class MockFailingClient:
    def __init__(self, auth=None):
        pass
    @property
    def order(self):
        class MockOrder:
            def create(self, data):
                raise Exception("HTTPSConnectionPool(host='api.razorpay.com', port=443): Max retries exceeded (Caused by NameResolutionError('Failed to resolve api.razorpay.com'))")
        return MockOrder()

razorpay_handler.razorpay.Client = MockFailingClient

try:
    fallback_order = razorpay_handler.create_order(500, "rcpt_mock_fail")
    print("Fallback Order Payload:", fallback_order)
    assert fallback_order["simulation_mode"] is True
    assert "order_sim_" in fallback_order["id"]
    assert "api.razorpay.com" in fallback_order["simulation_reason"]
    print("\n>>> NETWORK FAILURE FALLBACK TEST PASSED! Order created seamlessly without crash! <<<")
finally:
    razorpay_handler.razorpay.Client = original_create
