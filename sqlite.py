import sqlite3

def init_db():
    conn = sqlite3.connect("supermarket.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        sku TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        stock INTEGER
    )
    """)

    items = [
        ("SKU-1001", "Organic Gala Apples (1 lb)", "Produce", 2.49, 150),
        ("SKU-1002", "Whole Milk 1 Gallon", "Dairy", 3.89, 85),
        ("SKU-1003", "Artisanal Sourdough Bread", "Bakery", 4.50, 40),
        ("SKU-1004", "Extra Virgin Olive Oil (500ml)", "Pantry", 9.99, 62),
        ("SKU-1005", "Organic Bananas (1 Bunch)", "Produce", 1.29, 210),
        ("SKU-1006", "Greek Yogurt Plain (32 oz)", "Dairy", 5.29, 28),
        ("SKU-1007", "Free-Range Large Eggs (12 pk)", "Dairy", 4.19, 110),
        ("SKU-1008", "Organic Baby Spinach (5 oz)", "Produce", 3.49, 75),
        ("SKU-1009", "Whole Grain Wheat Bread", "Bakery", 3.25, 55),
        ("SKU-1010", "Basmati Rice (5 lbs)", "Pantry", 8.79, 320),
    ]

    cursor.executemany("INSERT OR REPLACE INTO inventory VALUES (?, ?, ?, ?, ?)", items)
    conn.commit()
    conn.close()
    print("Database 'supermarket.db' initialized successfully.")

if __name__ == "__main__":
    init_db()
