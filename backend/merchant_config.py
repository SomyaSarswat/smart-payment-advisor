"""
Merchant configuration registry mapping merchant IDs to supported payment options.
Serves as the single source of truth for merchant payment capabilities across the application.
"""

MERCHANT_CONFIGS = {
    "college_fee_portal": [
        ("Credit Card", "SBI"),
        ("Credit Card", "HDFC"),
        ("Debit Card", "SBI"),
        ("Net Banking", "HDFC"),
        ("Net Banking", "SBI"),
        ("UPI", None),
        ("Wallet", None)
    ],
    "ecommerce_store": [
        ("Credit Card", "HDFC"),
        ("Credit Card", "ICICI"),
        ("UPI", None),
        ("Net Banking", "Axis"),
        ("Wallet", None)
    ],
    "electricity_bill": [
        ("Net Banking", "SBI"),
        ("Net Banking", "HDFC"),
        ("UPI", None),
        ("Debit Card", "SBI")
    ]
}

# Sensible default list for unknown/new merchant IDs
DEFAULT_MERCHANT_CONFIG = [
    ("Credit Card", "SBI"),
    ("Credit Card", "HDFC"),
    ("Debit Card", "SBI"),
    ("Net Banking", "HDFC"),
    ("Net Banking", "SBI"),
    ("UPI", None),
    ("Wallet", None)
]

def get_merchant_config(merchant_id: str) -> list:
    """
    Returns available (method, bank) tuples for a given merchant_id.
    Falls back gracefully to DEFAULT_MERCHANT_CONFIG if merchant_id is not recognized.
    """
    return MERCHANT_CONFIGS.get(merchant_id, DEFAULT_MERCHANT_CONFIG)
