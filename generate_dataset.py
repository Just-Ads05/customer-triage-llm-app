import json
import random

# Seed for reproducibility
random.seed(42)

first_names = [
    "Alice", "Bob", "Charlie", "David", "Eva", "Frank", "Grace", "Hannah", "Ian", "Jack",
    "Karen", "Leo", "Mia", "Nathan", "Olivia", "Peter", "Quinn", "Rachel", "Sam", "Tina",
    "Umar", "Victoria", "Will", "Xavier", "Yara", "Zack", "Aaron", "Bella", "Chris", "Diana"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

# Generate 500 unique customer names
customer_names = list(set([f"{fn} {ln}" for fn in first_names for ln in last_names]))[:500]

products = [
    "Pro Wireless Earbuds",
    "UltraHD 4K Monitor 27-inch",
    "Mechanical RGB Keyboard",
    "Ergonomic Mesh Office Chair",
    "Smart Fitness Watch V2",
    "Noise-Canceling Headphones",
    "USB-C Multi-Port Hub 8-in-1",
    "Portable SSD 1TB",
    "Wireless Precision Mouse",
    "Smart Home Speaker Hub"
]

fault_categories = [
    "Hardware Defect",
    "Software & Firmware Bug",
    "Battery & Power Issue",
    "Physical & Shipping Damage",
    "Connectivity Issue",
    "Billing & Overcharge",
    "Missing Accessories"
]

priorities = ["Low", "Medium", "High", "Critical"]

descriptions = {
    "Hardware Defect": [
        "Device powers off unexpectedly after 10-15 minutes of continuous use.",
        "Internal speaker emits static buzzing noise when volume exceeds 50%.",
        "Left channel button is stuck and fails to register clicks consistently.",
        "Display panel flickering with vertical blue lines across the center."
    ],
    "Software & Firmware Bug": [
        "Companion mobile app crashes every time firmware update v2.1 is initiated.",
        "Device loses saved custom key mappings upon restarting.",
        "Bluetooth pairing disconnects randomly every 20 minutes.",
        "System freezes during high-load processing and requires a hard reboot."
    ],
    "Battery & Power Issue": [
        "Battery drains from 100% to 0% in under two hours without heavy usage.",
        "Device refuses to charge past 80% when connected to standard wall adapter.",
        "Charging case overheating significantly while plugged in overnight.",
        "Unit displays fake battery level percentages and shuts off without warning."
    ],
    "Physical & Shipping Damage": [
        "Package arrived crushed with visible cracks on outer casing.",
        "Unboxed product has scratches on screen right out of sealed packaging.",
        "Hinge mechanism loose and wobbling directly out of the delivery box.",
        "Power cable sheath stripped exposing internal copper wiring."
    ],
    "Connectivity Issue": [
        "Wi-Fi connection drops whenever 5GHz network frequency switches.",
        "USB dongle fails to recognize on Windows 11 without driver manual force.",
        "Audio latency exceeds 400ms causing severe sync lag in video playback.",
        "Device range fails beyond 3 feet from primary host laptop."
    ],
    "Billing & Overcharge": [
        "Billed twice on credit card statement for single order item.",
        "Promotional discount code applied at checkout was removed on final receipt.",
        "Charged unexpected express shipping fee despite standard option selected.",
        "Subscription auto-renewed after cancellation confirmation was sent."
    ],
    "Missing Accessories": [
        "Box contained unit but lacked USB-C charging cable and manual.",
        "Missing extra silicone ear tips specified in product packaging list.",
        "Power supply brick missing from shipment bundle.",
        "Mounting bracket accessories missing from shipment container."
    ]
}

refund_types = ["Full Refund", "Partial Refund", "Store Credit", "None"]

tickets = []

for i in range(1, 501):
    category = random.choice(fault_categories)
    refund_req = random.choice([True, False, False])  # ~33% refund request rate
    refund_type = random.choice(["Full Refund", "Partial Refund", "Store Credit"]) if refund_req else "None"
    
    ticket = {
        "ticket_id": f"TICK-{1000 + i}",
        "customer_name": customer_names[i - 1],
        "order_id": f"ORD-{random.randint(10000, 99999)}",
        "product_name": random.choice(products),
        "fault_category": category,
        "priority": random.choice(priorities),
        "refund_requested": refund_req,
        "refund_type": refund_type,
        "description": random.choice(descriptions[category])
    }
    tickets.append(ticket)

# Save to tickets.json
with open("tickets.json", "w", encoding="utf-8") as f:
    json.dump(tickets, f, indent=2)

print(f"✅ Successfully generated 'tickets.json' with {len(tickets)} records!")