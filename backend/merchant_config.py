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

DEFAULT_MERCHANT_CONFIG = [
    ("Credit Card", "SBI"),
    ("Credit Card", "HDFC"),
    ("Debit Card", "SBI"),
    ("Net Banking", "HDFC"),
    ("Net Banking", "SBI"),
    ("UPI", None),
    ("Wallet", None)
]

MERCHANT_NAME_MAP = {
    "college_fee_portal": "college_fee_portal",
    "abc college fee portal": "college_fee_portal",
    "college fee portal": "college_fee_portal",
    "ecommerce_store": "ecommerce_store",
    "e-commerce store": "ecommerce_store",
    "ecommerce store": "ecommerce_store",
    "electricity_bill": "electricity_bill",
    "electricity bill portal": "electricity_bill",
    "electricity bill": "electricity_bill",
    "electricity_bill_portal": "electricity_bill",
}

VALID_METHODS = {"Credit Card", "Debit Card", "Net Banking", "UPI", "Wallet"}
VALID_BANKS = {"SBI", "HDFC", "ICICI", "Axis", "Kotak", None}

def validate_payment_method_bank(method: str, bank: str = None) -> None:
    """
    Validates payment method and bank against known allowed options.
    Raises ValueError if invalid or malformed.
    """
    if not method or not isinstance(method, str) or method.strip() not in VALID_METHODS:
        raise ValueError(f"Invalid payment method: '{method}'. Allowed: {sorted(list(VALID_METHODS))}")
    if bank is not None and (not isinstance(bank, str) or bank.strip() not in VALID_BANKS):
        raise ValueError(f"Invalid bank: '{bank}'. Allowed: {sorted([b for b in VALID_BANKS if b])}")
    if method.strip() in ["UPI", "Wallet"] and bank is not None:
        raise ValueError(f"Payment method '{method}' does not accept a bank parameter.")

def validate_and_normalize_merchant_id(merchant_id: str) -> str:
    """
    Validates and normalizes incoming merchant_id (case-insensitive).
    Returns normalized internal merchant_id (e.g. 'electricity_bill').
    Raises ValueError("Unknown merchant: <id>") if merchant_id is not in allow-list.
    """
    if not merchant_id or not isinstance(merchant_id, str):
        raise ValueError("Unknown merchant: Merchant ID is required")
    
    cleaned = merchant_id.strip().lower()
    
    if cleaned in MERCHANT_NAME_MAP:
        return MERCHANT_NAME_MAP[cleaned]
    
    snake_case = cleaned.replace(" ", "_")
    if snake_case in MERCHANT_CONFIGS:
        return snake_case

    raise ValueError(f"Unknown merchant: '{merchant_id}' is not in the merchant allow-list")

def get_merchant_config(merchant_id: str) -> list:
    """
    Returns available (method, bank) tuples for a given merchant_id.
    Falls back gracefully to DEFAULT_MERCHANT_CONFIG if merchant_id is not recognized.
    """
    try:
        norm_id = validate_and_normalize_merchant_id(merchant_id)
        return MERCHANT_CONFIGS.get(norm_id, DEFAULT_MERCHANT_CONFIG)
    except ValueError:
        return DEFAULT_MERCHANT_CONFIG
