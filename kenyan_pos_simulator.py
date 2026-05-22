import copy
import json
import random
import time
from datetime import datetime

from kafka import KafkaProducer
import pymongo
import psycopg2
from psycopg2.extras import execute_values

# ---------------------------------------------------------------------------
# Product catalogue — 20 sectors representing a major Kenyan supermarket
# ---------------------------------------------------------------------------

KENYAN_STORE_SECTORS = {
    "Maize & Wheat Flour": [
        {"id": "MW-01", "name": "Jogoo Maize Meal 2kg",            "price": 140.00},
        {"id": "MW-02", "name": "Pembe Maize Meal 2kg",            "price": 145.00},
        {"id": "MW-03", "name": "Axe Wheat Flour 2kg",             "price": 175.00},
        {"id": "MW-04", "name": "Hostess Premium Maize Meal 2kg",  "price": 230.00},
    ],
    "Dairy & Milk": [
        {"id": "DY-01", "name": "KCC Fresh Milk 500ml",            "price":  55.00},
        {"id": "DY-02", "name": "Brookside Long Life Milk 500ml",  "price":  65.00},
        {"id": "DY-03", "name": "Bio Molo Milk 1L",                "price": 160.00},
        {"id": "DY-04", "name": "Ilara Lala 500ml",                "price":  70.00},
    ],
    "Sugar & Sweeteners": [
        {"id": "SG-01", "name": "Kabras Sugar 1kg",     "price": 160.00},
        {"id": "SG-02", "name": "Kabras Sugar 2kg",     "price": 310.00},
        {"id": "SG-03", "name": "Nutrameal Honey 500g", "price": 450.00},
    ],
    "Cooking Oils & Fats": [
        {"id": "CO-01", "name": "Fresh Fri Cooking Oil 1L", "price": 320.00},
        {"id": "CO-02", "name": "Salit Vegetable Oil 2L",   "price": 580.00},
        {"id": "CO-03", "name": "Kimbo Premium Fat 1kg",    "price": 390.00},
    ],
    "Bakery & Pastries": [
        {"id": "BK-01", "name": "Superloaf White Bread 400g",         "price":  65.00},
        {"id": "BK-02", "name": "Festive Wholemeal Bread 400g",       "price":  70.00},
        {"id": "BK-03", "name": "Freshly Baked Mandazi (4pc)",        "price":  50.00},
        {"id": "BK-04", "name": "Supermarket Large Queen Cakes (6pc)", "price": 180.00},
    ],
    "Cosmetics & Beauty": [
        {"id": "CS-01", "name": "Nice & Lovely Body Lotion 400ml",        "price": 280.00},
        {"id": "CS-02", "name": "Nivea Perfect & Radiant Men Cream 75ml", "price": 350.00},
        {"id": "CS-03", "name": "Amara Body Butter 250ml",                "price": 220.00},
    ],
    "Hair Care": [
        {"id": "HC-01", "name": "Miadi Leave-In Conditioner", "price": 420.00},
        {"id": "HC-02", "name": "Darlin Braids (Three-pack)",  "price": 360.00},
        {"id": "HC-03", "name": "Mennen Speed Stick",          "price": 480.00},
    ],
    "Baby Products": [
        {"id": "BB-01", "name": "Pampers Baby Dry Size 4 (44pc)", "price": 1250.00},
        {"id": "BB-02", "name": "Huggies Wipes 56pc",             "price":  290.00},
        {"id": "BB-03", "name": "Cerelac Maize 400g",             "price":  410.00},
    ],
    "Butchery & Meat": [
        {"id": "BT-01", "name": "Beef Steak 1kg",                     "price": 780.00},
        {"id": "BT-02", "name": "Broiler Chicken Whole 1.2kg",        "price": 650.00},
        {"id": "BT-03", "name": "Farmer's Choice Beef Sausages 500g", "price": 460.00},
    ],
    "Fresh Produce & Groceries": [
        {"id": "FP-01", "name": "Local Tomatoes 1kg",         "price": 120.00},
        {"id": "FP-02", "name": "Red Onions 1kg",             "price": 150.00},
        {"id": "FP-03", "name": "Sukuma Wiki Bunch",          "price":  30.00},
        {"id": "FP-04", "name": "Export Quality Bananas 1kg", "price": 110.00},
    ],
    "Beverages & Soft Drinks": [
        {"id": "BV-01", "name": "Coca-Cola Soda 1.25L",        "price": 110.00},
        {"id": "BV-02", "name": "Minute Maid Pulpy Orange 1L", "price": 140.00},
        {"id": "BV-03", "name": "Keringet Mineral Water 1L",   "price":  75.00},
    ],
    "Tea & Coffee": [
        {"id": "TC-01", "name": "Ketepa Pride Tea Bags 100pc",      "price": 210.00},
        {"id": "TC-02", "name": "Kericho Gold Pure Kenya Tea 250g", "price": 290.00},
        {"id": "TC-03", "name": "Nescafe Classic 100g",             "price": 540.00},
    ],
    "Snacks & Confectionery": [
        {"id": "SN-01", "name": "Tropical Mints Bag",              "price": 120.00},
        {"id": "SN-02", "name": "Urban Bites Potato Crisps Large", "price": 160.00},
        {"id": "SN-03", "name": "Cadbury Dairy Milk 100g",         "price": 240.00},
    ],
    "Home Care & Laundry": [
        {"id": "HL-01", "name": "Toss Sensitive Detergent 1kg", "price": 390.00},
        {"id": "HL-02", "name": "Menengai Cream Bar Soap 800g", "price": 170.00},
        {"id": "HL-03", "name": "Downy Fabric Softener 500ml",  "price": 450.00},
    ],
    "Toiletries & Oral Care": [
        {"id": "TO-01", "name": "Colgate Herbal Toothpaste 120g", "price": 190.00},
        {"id": "TO-02", "name": "Geisha Bathing Soap 200g",       "price": 115.00},
        {"id": "TO-03", "name": "Hanifit Tissue White 4pk",       "price": 180.00},
    ],
    "Grains, Pulses & Rice": [
        {"id": "GP-01", "name": "Daawat Long Grain Basmati Rice 2kg", "price": 440.00},
        {"id": "GP-02", "name": "Pearl Pishori Rice 2kg",             "price": 520.00},
        {"id": "GP-03", "name": "Local Wairimu Beans 1kg",            "price": 190.00},
        {"id": "GP-04", "name": "Green Grams (Ndengu) 1kg",           "price": 180.00},
    ],
    "Spices & Condiments": [
        {"id": "SP-01", "name": "Royco Mchuzi Mix Beef 200g", "price": 140.00},
        {"id": "SP-02", "name": "Kenbro Salt 1kg",            "price":  45.00},
        {"id": "SP-03", "name": "Tropical Heat Black Pepper", "price": 180.00},
    ],
    "Cereals & Spreads": [
        {"id": "CR-01", "name": "Weetabix 450g",             "price": 420.00},
        {"id": "CR-02", "name": "Peptang Peanut Butter 800g","price": 490.00},
        {"id": "CR-03", "name": "Plumbe Jam 500g",           "price": 230.00},
    ],
    "Crockery & Housewares": [
        {"id": "HW-01", "name": "Plastic Basin Large (Blue)", "price": 250.00},
        {"id": "HW-02", "name": "Luminarc Glass Mug",         "price": 180.00},
        {"id": "HW-03", "name": "Meko Gas Ring Burner",       "price": 850.00},
    ],
    "Electronics & Appliances": [
        {"id": "EL-01", "name": "Ramtons Dry Iron Box",      "price": 1850.00},
        {"id": "EL-02", "name": "Sayona Subwoofer System",   "price": 6500.00},
        {"id": "EL-03", "name": "Mika Electric Kettle 1.7L", "price": 2200.00},
    ],
}

PAYMENT_METHODS = ["M-Pesa", "Cash", "Visa Card", "Mastercard", "Pesalink"]
PAYMENT_WEIGHTS = [0.55, 0.30, 0.10, 0.03, 0.02]
HIGH_VOLUME_SECTORS = {"Maize & Wheat Flour", "Dairy & Milk", "Fresh Produce & Groceries"}

# ---------------------------------------------------------------------------
# Infrastructure initialisation
# ---------------------------------------------------------------------------

def init_postgres():
    """
    Creates the products reference table and upserts the full catalogue.
    Returns (conn, cursor). Raises on failure so the problem is visible.
    NOTE: port=5433 matches the docker-compose host mapping.
    """
    conn = psycopg2.connect(
        host="localhost",
        port=5433,              # FIX: was missing — docker-compose maps 5433:5432
        database="supermarket_metadata",
        user="kenyan_retail_admin",
        password="NaivasPassword2026",
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id   VARCHAR(50)    PRIMARY KEY,
            product_name VARCHAR(255),
            sector_name  VARCHAR(100),
            unit_price   NUMERIC(10, 2)
        );
    """)
    conn.commit()  # FIX: original never committed the DDL

    product_rows = [
        (item["id"], item["name"], sector, item["price"])
        for sector, items in KENYAN_STORE_SECTORS.items()
        for item in items
    ]
    execute_values(
        cursor,
        """
        INSERT INTO products (product_id, product_name, sector_name, unit_price)
        VALUES %s
        ON CONFLICT (product_id) DO UPDATE SET
            product_name = EXCLUDED.product_name,
            sector_name  = EXCLUDED.sector_name,
            unit_price   = EXCLUDED.unit_price;
        """,
        product_rows,
    )
    conn.commit()
    print("[✓] PostgreSQL: product catalogue synced.")
    return conn, cursor


def init_kafka():
    """Returns a KafkaProducer or None if the broker is unavailable."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print("[✓] Kafka: connected to streaming cluster.")
        return producer
    except Exception as exc:
        print(f"[!] Kafka unavailable — local-debug mode active: {exc}")
        return None


def init_mongo():
    """Returns (client, collection) or (None, None) if unavailable."""
    try:
        client = pymongo.MongoClient(
            "mongodb://mongo_retail_admin:QuickmartPassword2026@localhost:27017/?authSource=admin",
            serverSelectionTimeoutMS=2000,
        )
        client.server_info()
        collection = client["supermarket_audit_logs"]["raw_receipts"]
        print("[✓] MongoDB: connected to audit log store.")
        return client, collection
    except Exception as exc:
        print(f"[!] MongoDB unavailable — audit logging disabled: {exc}")
        return None, None


# ---------------------------------------------------------------------------
# Transaction generator
# ---------------------------------------------------------------------------

def generate_kenyan_transaction(txn_id: int) -> dict:
    """Simulates a live checkout receipt from a Kenyan supermarket till."""
    num_unique_items = random.randint(1, 7)
    chosen_sectors = random.sample(
        list(KENYAN_STORE_SECTORS.keys()),
        min(num_unique_items, len(KENYAN_STORE_SECTORS)),
    )

    items_bought = []
    total_amount = 0.0

    for sector in chosen_sectors:
        product = random.choice(KENYAN_STORE_SECTORS[sector])
        quantity = (
            random.randint(1, 4) if sector in HIGH_VOLUME_SECTORS
            else random.randint(1, 2)
        )
        item_total = round(product["price"] * quantity, 2)
        total_amount += item_total
        items_bought.append({
            "product_id": product["id"],
            "name":       product["name"],
            "sector":     sector,
            "quantity":   quantity,
            "price":      product["price"],
            "subtotal":   item_total,
        })

    return {
        "transaction_id": f"KE-POS-{txn_id:07d}",
        "till_number":    f"TILL-{random.randint(1, 12):02d}",
        "timestamp":      datetime.utcnow().isoformat() + "Z",
        "currency":       "KES",
        "items":          items_bought,
        "payment_method": random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0],
        "total_amount":   round(total_amount, 2),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pg_conn, pg_cursor = init_postgres()
    producer        = init_kafka()
    mongo_client, mongo_collection = init_mongo()

    transaction_counter = 450_001
    topic_name = "supermarket-transactions"

    print("\nLaunching Real-Time Multi-Target Pipeline Streamer...")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            txn = generate_kenyan_transaction(transaction_counter)

            # Target 1: Kafka streaming layer
            if producer:
                producer.send(topic_name, value=txn)
                producer.flush()
                print(f" [Kafka]  → {txn['transaction_id']} | KES {txn['total_amount']:,.2f}")
            else:
                print(f" [Debug]  → {json.dumps(txn, indent=2)}\n{'-'*60}")

            # Target 2: MongoDB immutable audit log
            if mongo_collection is not None:
                # FIX: deepcopy — shallow dict() leaves nested `items` list shared
                mongo_collection.insert_one(copy.deepcopy(txn))

            transaction_counter += 1
            time.sleep(random.uniform(0.3, 1.8))

    except KeyboardInterrupt:
        print("\n[!] Shutting down — flushing connections...")

    finally:
        # FIX: shutdown in `finally` so it always runs, even on unexpected errors
        if producer:
            producer.close()
            print("[✓] Kafka producer closed.")
        if mongo_client:
            mongo_client.close()
            print("[✓] MongoDB connection closed.")
        if pg_conn:
            pg_cursor.close()
            pg_conn.close()
            print("[✓] PostgreSQL connection closed.")
        print("[✓] POS Simulator stopped.")