import json
import random
from datetime import datetime, timedelta

random.seed(42)

first_names = ["Alice", "Bob", "Charlie", "David", "Eva", "Frank", "Grace", "Hannah", "Ian", "Jack"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
customer_names = [f"{fn} {ln}" for fn in first_names for ln in last_names]

products = [
    "Pro Wireless Earbuds", "UltraHD 4K Monitor 27-inch", "Mechanical RGB Keyboard",
    "Ergonomic Mesh Office Chair", "Smart Fitness Watch V2", "Noise-Canceling Headphones"
]

fault_categories = [
    "Hardware Defect", "Software & Firmware Bug", "Battery & Power Issue",
    "Physical & Shipping Damage", "Connectivity Issue", "Billing & Overcharge"
]

priorities = ["Low", "Medium", "High", "Critical"]

descriptions = {
    "Hardware Defect": ["Device powers off unexpectedly.", "Display panel flickering with blue lines."],
    "Software & Firmware Bug": ["App crashes on update.", "Bluetooth pairing disconnects randomly."],
    "Battery & Power Issue": ["Battery drains in under 2 hours.", "Device refuses to charge past 80%."],
    "Physical & Shipping Damage": ["Package arrived crushed.", "Scratches on screen out of box."],
    "Connectivity Issue": ["Wi-Fi connection drops continuously.", "Latency exceeds 400ms."],
    "Billing & Overcharge": ["Billed twice on credit card statement.", "Discount code not applied."]
}

tickets = []
now = datetime.now()

for i in range(1, 501):
    category = random.choice(fault_categories)
    refund_req = random.choice([True, False, False])
    
    # Generate timestamp within last 90 days
    random_days = random.randint(0, 90)
    random_hours = random.randint(0, 23)
    created_date = (now - timedelta(days=random_days, hours=random_hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    ticket = {
        "ticket_id": f"TICK-{1000 + i}",
        "customer_name": random.choice(customer_names),
        "order_id": f"ORD-{random.randint(10000, 99999)}",
        "product_name": random.choice(products),
        "fault_category": category,
        "priority": random.choice(priorities),
        "refund_requested": refund_req,
        "refund_type": random.choice(["Full Refund", "Partial Refund", "Store Credit"]) if refund_req else "None",
        "description": random.choice(descriptions[category]),
        "created_at": created_date
    }
    tickets.append(ticket)

with open("tickets.json", "w", encoding="utf-8") as f:
    json.dump(tickets, f, indent=2)

print("✅ Successfully updated 'tickets.json' with timestamps and 500 records!")