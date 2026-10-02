import sqlite3
import pypdf
import os
from datetime import datetime

# ----------------------------------------------------
# MCP TOOL 1: Inventory SQLite Database Tool
# ----------------------------------------------------
def query_inventory(item_name: str) -> str:
    """Search for product stock and price in the local SQLite database."""
    conn = sqlite3.connect("supermarket.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sku, name, category, price, stock FROM inventory WHERE name LIKE ?", (f"%{item_name}%",))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return f"No product matching '{item_name}' found in inventory."
    
    results = []
    for r in rows:
        results.append(f"SKU: {r[0]} | Item: {r[1]} | Category: {r[2]} | Price: ${r[3]:.2f} | Stock: {r[4]}")
    return "\n".join(results)

# ----------------------------------------------------
# MCP TOOL 2: Document File System / Policy Tool
# ----------------------------------------------------
def search_return_policy(item_name: str, purchase_date_str: str) -> str:
    """
    Evaluates return eligibility based on item category, purchase date, and policy constraints.
    Current date context: September 27, 2026.
    """
    pdf_path = "supermarket_return_policy.pdf"
    policy_text = ""
    
    if os.path.exists(pdf_path):
        try:
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                policy_text += page.extract_text() + "\n"
        except Exception as e:
            policy_text = f"Error reading PDF policy document: {str(e)}"
    else:
        policy_text = (
            "Standard Store Return Policy:\n"
            "- Perishable items (Dairy, Meat, Produce, Milk, Yogurt) must be returned within 7 days.\n"
            "- Non-perishable packaged items can be returned within 30 days.\n"
            "- A valid receipt is strictly required for all return processing."
        )

    current_date = datetime(2026, 9, 27)
    try:
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
        days_since_purchase = (current_date - purchase_date).days
    except ValueError:
        return f"Error: Invalid date format '{purchase_date_str}'. Please use YYYY-MM-DD."

    perishable_keywords = ["milk", "dairy", "cheese", "meat", "produce", "fruit", "yogurt", "spinach", "apples", "bananas", "bread"]
    is_perishable = any(keyword in item_name.lower() for keyword in perishable_keywords)
    allowed_days = 7 if is_perishable else 30

    if days_since_purchase < 0:
        return f"Policy Verification Result: REJECTED. Purchase date ({purchase_date_str}) is in the future."

    if days_since_purchase <= allowed_days:
        return (
            f"Policy Verification Result:\n"
            f"- Item: {item_name} ({'Perishable' if is_perishable else 'Non-perishable'})\n"
            f"- Purchase Date: {purchase_date_str} ({days_since_purchase} days ago)\n"
            f"- Allowed Window: {allowed_days} days\n"
            f"- Return Status: ELIGIBLE FOR RETURN\n"
            f"- Action: Customer may proceed to customer service with receipt."
        )
    else:
        return (
            f"Policy Verification Result:\n"
            f"- Item: {item_name} ({'Perishable' if is_perishable else 'Non-perishable'})\n"
            f"- Purchase Date: {purchase_date_str} ({days_since_purchase} days ago)\n"
            f"- Allowed Window: {allowed_days} days\n"
            f"- Return Status: NOT ELIGIBLE FOR RETURN\n"
            f"- Reason: Window expired by {days_since_purchase - allowed_days} day(s).\n\n"
            f"Policy Reference:\n{policy_text[:300]}"
        )

# ----------------------------------------------------
# MCP TOOL 3: Operating Schedule Tool
# ----------------------------------------------------
def get_store_hours(day_or_holiday: str) -> str:
    """Retrieve opening hours or holiday closure information."""
    return (
        "Supermarket Store Hours:\n"
        "- Monday - Saturday: 7:00 AM - 10:00 PM\n"
        "- Sunday: 8:00 AM - 8:00 PM\n"
        "- Holidays (Thanksgiving, Christmas): Closed\n"
        "- Special Notice: Produce restocks occur daily at 6:00 AM."
    )
