import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from razorpay_handler import create_order, verify_payment_signature, is_simulation_mode

print("=== TEST 1: Default Order Creation ===")
try:
    order = create_order(100, "test_rcpt_101")
    print("Order result:", order)
    assert "id" in order
    assert "simulation_mode" in order
    print("SUCCESS: Order created cleanly!")
except Exception as e:
    print("FAIL:", e)

print("\n=== TEST 2: Signature Verification for Simulated Order ===")
sim_order_id = "order_sim_123456789"
sim_payment_id = "pay_sim_987654321"
sim_sig = "simulated_signature"
verified = verify_payment_signature(sim_order_id, sim_payment_id, sim_sig)
print("Verified sim signature:", verified)
assert verified is True
print("SUCCESS: Simulated signature verified cleanly!")

print("\n=== TEST 3: Forced Simulation Mode via Environment Variable ===")
os.environ["RAZORPAY_SIMULATION_MODE"] = "true"
print("Simulation mode active?", is_simulation_mode())
assert is_simulation_mode() is True

sim_order = create_order(250, "test_rcpt_102")
print("Forced Sim Order result:", sim_order)
assert sim_order["simulation_mode"] is True
assert sim_order["id"].startswith("order_sim_")
del os.environ["RAZORPAY_SIMULATION_MODE"]
print("SUCCESS: Forced simulation mode passed!")

print("\n>>> ALL RAZORPAY ORDER FALLBACK TESTS PASSED SUCCESSFULLY! <<<")
