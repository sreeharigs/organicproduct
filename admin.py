import psycopg2
import hashlib
from tabulate import tabulate
from datetime import datetime

PG_HOST = "localhost"
PG_DATABASE = "organicshopdb"
PG_USER = "postgres"
PG_PASSWORD = "12345"


def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        # Prints a clear error message if connection fails
        print(f"\n[ERROR] Database connection failed. Please check credentials and server status.")
        print(f"Details: {e}")
        return None

def hash_password(password):
    """Hashes a password using SHA256 (used for secure comparison during login)."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- Authentication & User Management ---

def login_admin():
    """Handles the admin authentication process."""
    print("\n--- Admin Login ---")
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    hashed_pw = hash_password(password)

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()

    # Query uses the 'admin_users' table as defined in your schema
    cursor.execute("SELECT id FROM admin_users WHERE username=%s AND password=%s", (username, hashed_pw))
    result = cursor.fetchone()
    conn.close()

    if result:
        print("Login successful!")
        return True
    else:
        print("Invalid credentials.")
        return False

def add_admin_user():
    """9. Add Admin User: Registers a new admin user."""
    print("\n--- Add New Admin User ---")
    username = input("Enter new admin username: ").strip()
    password = input("Enter new admin password: ").strip()
    
    if not username or not password:
        print("Username and password cannot be empty.")
        return

    hashed_pw = hash_password(password)
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO admin_users (username, password) VALUES (%s, %s)", (username, hashed_pw))
        conn.commit()
        print(f"Admin user '{username}' added successfully.")
    except psycopg2.IntegrityError:
        print(f"Error: Admin user '{username}' already exists.")
        conn.rollback()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

def remove_seller():
    """10. Remove Seller: Deletes a seller, cascading to their products, orders, and feedback."""
    # Assuming view_sellers exists or imported (it does in this file, but removed for brevity in snippet)
    # view_sellers() # This call needs to exist in the actual file. Assuming it's there.
    seller_id = input("\n[DANGER] Enter Seller ID to REMOVE (or 0 to cancel): ").strip()
    if seller_id == '0': return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT username FROM sellers WHERE id=%s", (seller_id,))
        seller_name = cursor.fetchone()

        if seller_name:
            confirm = input(f"Are you sure you want to delete seller '{seller_name[0]}' (ID: {seller_id}) and ALL their data? (Y/N): ").strip().upper()
            if confirm == 'Y':
                # The ON DELETE CASCADE constraint in SQL handles deletion of dependent records
                cursor.execute("DELETE FROM sellers WHERE id=%s", (seller_id,))
                conn.commit()
                print(f"\nSeller ID {seller_id} ('{seller_name[0]}') and all associated records deleted successfully.")
            else:
                print("Removal cancelled.")
        else:
            print(f"Seller ID {seller_id} not found.")

    except psycopg2.Error as e:
        print(f"Database error during removal: {e}")
        conn.rollback()
    finally:
        conn.close()

def remove_buyer():
    """11. Remove Buyer: Deletes a buyer, cascading to their orders and feedback."""
    # Assuming view_buyers exists or imported (it does in this file, but removed for brevity in snippet)
    # view_buyers() # This call needs to exist in the actual file. Assuming it's there.
    buyer_id = input("\n[DANGER] Enter Buyer ID to REMOVE (or 0 to cancel): ").strip()
    if buyer_id == '0': return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT username FROM buyers WHERE id=%s", (buyer_id,))
        buyer_name = cursor.fetchone()

        if buyer_name:
            confirm = input(f"Are you sure you want to delete buyer '{buyer_name[0]}' (ID: {buyer_id}) and ALL their orders/feedback? (Y/N): ").strip().upper()
            if confirm == 'Y':
                # The ON DELETE CASCADE constraint in SQL handles deletion of dependent records
                cursor.execute("DELETE FROM buyers WHERE id=%s", (buyer_id,))
                conn.commit()
                print(f"\nBuyer ID {buyer_id} ('{buyer_name[0]}') and all associated records deleted successfully.")
            else:
                print("Removal cancelled.")
        else:
            print(f"Buyer ID {buyer_id} not found.")

    except psycopg2.Error as e:
        print(f"Database error during removal: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- Dashboard & Reports ---

# ... (dashboard_overview, monthly_sales_report, view_buyers, view_sellers, view_products, view_orders, add_jaivik_id, approve_reject_products definitions would continue here) ...

def dashboard_overview():
    """1. Dashboard Overview: Provides a quick summary of key metrics."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    print("\n--- 1. Dashboard Overview ---")
    
    # Fetching counts for key tables
    cursor.execute("SELECT COUNT(*) FROM sellers")
    total_sellers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM buyers")
    total_buyers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'Pending'")
    pending_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    # Calculate Total Revenue from non-cancelled orders
    cursor.execute("""
        SELECT COALESCE(SUM(o.quantity * p.price), 0)
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.status != 'Cancelled'
    """)
    total_revenue = cursor.fetchone()[0]

    stats = [
        ["Total Sellers", total_sellers],
        ["Total Buyers", total_buyers],
        ["Total Products Listed", total_products],
        ["Products Pending Review", pending_products],
        ["Total Orders Placed", total_orders],
        ["Estimated Total Revenue", f"₹ {total_revenue:,.2f}"],
    ]
    
    print(tabulate(stats, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    conn.close()


def monthly_sales_report():
    """8. Monthly Sales Report: Generates a summary of sales grouped by month/year."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    print("\n--- 8. Monthly Sales Report ---")

    cursor.execute("""
        SELECT 
            TO_CHAR(o.order_date, 'YYYY-MM') AS sale_month,
            COUNT(o.id) AS orders_count,
            COALESCE(SUM(o.quantity * p.price), 0) AS monthly_revenue
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.status != 'Cancelled'
        GROUP BY 1
        ORDER BY 1 DESC
    """)
    sales_data = cursor.fetchall()
    conn.close()

    if not sales_data:
        print("No sales data available to generate a report.")
        return

    report_rows = []
    for month, count, revenue in sales_data:
        report_rows.append([month, count, f"₹ {revenue:,.2f}"])

    headers = ["Month", "Order Count", "Total Revenue"]
    print(tabulate(report_rows, headers=headers, tablefmt="grid"))

# --- Data Viewing ---

def view_buyers():
    """2. View Buyers: Views all registered buyers."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, email, mobile FROM buyers ORDER BY id")
    buyers = cursor.fetchall()
    conn.close()

    if buyers:
        headers = ["ID", "Username", "Email", "Mobile"]
        print("\n--- 2. All Registered Buyers ---")
        print(tabulate(buyers, headers=headers, tablefmt="grid"))
    else:
        print("No buyers registered yet.")

def view_sellers():
    """3. View Sellers: Views all registered sellers."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, jaivik_cert, TO_CHAR(registered_at, 'YYYY-MM-DD HH24:MI')
        FROM sellers
        ORDER BY id
    """)
    sellers = cursor.fetchall()
    conn.close()

    if sellers:
        headers = ["ID", "Username", "Jaivik Cert", "Registered At"]
        print("\n--- 3. All Registered Sellers ---")
        print(tabulate(sellers, headers=headers, tablefmt="grid"))
    else:
        print("No sellers registered yet.")


def view_products():
    """4. View Products: Views all products regardless of status."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.name, p.category, p.status, p.price, p.quantity, s.username
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        ORDER BY p.id
    """)
    products = cursor.fetchall()
    conn.close()

    if products:
        headers = ["ID", "Name", "Category", "Status", "Price", "Qty", "Seller"]
        print("\n--- 4. All Products Listed ---")
        print(tabulate(products, headers=headers, tablefmt="grid"))
    else:
        print("No products listed yet.")


def view_orders():
    """5. View Orders: Views all orders placed."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id, p.name AS product_name, b.username AS buyer, 
               o.quantity, o.status, TO_CHAR(o.order_date, 'YYYY-MM-DD') AS order_date
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN buyers b ON o.buyer_id = b.id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    conn.close()

    if orders:
        headers = ["ID", "Product Name", "Buyer", "Qty", "Status", "Date"]
        print("\n--- 5. All Orders Placed ---")
        print(tabulate(orders, headers=headers, tablefmt="grid"))
    else:
        print("No orders placed yet.")

# --- Product & Certificate Management ---

def add_jaivik_id():
    """6. Add Jaivik ID: Allows admin to add a new approved Jaivik certificate."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    print("\n--- 6. Add Approved Jaivik ID ---")
    new_cert = input("Enter new Jaivik Bharat Certificate Number to approve: ").strip()

    if not new_cert:
        print("Certificate number cannot be empty.")
        conn.close()
        return

    try:
        # Inserts into the approved_jaivik table
        cursor.execute("INSERT INTO approved_jaivik (cert_number) VALUES (%s)", (new_cert,))
        conn.commit()
        print(f"\nCertificate '{new_cert}' has been approved and added.")
    except psycopg2.IntegrityError:
        print(f"\nCertificate '{new_cert}' already exists in the approved list.")
        conn.rollback()
    except psycopg2.Error as e:
        print(f"Error adding certificate: {e}")
        conn.rollback()
    finally:
        conn.close()


def approve_reject_products():
    """7. Approve/Reject Products: Allows admin to view and approve/reject products that are 'Pending'."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    print("\n--- 7. Approve/Reject Products ---")

    # Select only products pending approval
    cursor.execute("""
        SELECT p.id, p.name, p.category, p.price, p.quantity, p.unit, s.username, p.jaivik_id
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.status='Pending'
        ORDER BY p.id
    """)
    pending_products = cursor.fetchall()

    if not pending_products:
        print("No products currently pending review.")
        conn.close()
        return

    headers = ["ID", "Name", "Category", "Price", "Qty", "Unit", "Seller", "Jaivik ID"]
    print(tabulate(pending_products, headers=headers, tablefmt="grid"))

    try:
        product_id = input("\nEnter Product ID to review (or 0 to cancel): ").strip()
        if product_id == '0':
            conn.close()
            return
        product_id = int(product_id)
    except ValueError:
        print("Invalid ID. Please enter a number.")
        conn.close()
        return

    # Validate that the product ID is both pending and exists
    cursor.execute("SELECT 1 FROM products WHERE id=%s AND status='Pending'", (product_id,))
    if not cursor.fetchone():
        print(f"Product ID {product_id} is not pending or does not exist.")
        conn.close()
        return

    action = input("Approve (A) or Reject (R)? ").strip().upper()
    
    if action == 'A':
        new_status = 'Approved'
    elif action == 'R':
        new_status = 'Rejected'
    else:
        print("Invalid action. Review cancelled.")
        conn.close()
        return

    try:
        cursor.execute("UPDATE products SET status=%s WHERE id=%s", (new_status, product_id))
        conn.commit()
        print(f"\nProduct ID {product_id} successfully marked as {new_status}.")
    except psycopg2.Error as e:
        print(f"Database error during update: {e}")
        conn.rollback()
    finally:
        conn.close()


# --- Main Application Loop ---

def admin_main():
    """
    Main function for the Admin panel, displaying the 12-point menu.
    
    Returns:
        bool: True if the function returns (either due to logout or login failure), 
              signaling that control should return to the calling module (main menu).
    """
    if not login_admin():
        # Login failed, return control to main menu
        return True

    # Login successful, enter dashboard loop
    while True:
        print("\n====================================")
        print("       ADMIN MANAGEMENT PORTAL      ")
        print("====================================")
        print("--- Dashboard & Reports ---")
        print(" 1. Dashboard Overview")
        print(" 2. Monthly Sales Report")
        print("\n--- Data Viewing ---")
        print(" 3. View Products (All)")
        print(" 4. View Orders (All)")
        print(" 5. View Sellers")
        print(" 6. View Buyers")
        print("\n--- Product & Certificate Mgmt. ---")
        print(" 7. Approve/Reject Products")
        print(" 8. Add Jaivik ID")
        print("\n--- User Management ---")
        print(" 9. Add New Admin User")
        print("10. Remove Seller")
        print("11. Remove Buyer")
        print("12. Logout")
        print("------------------------------------")
        
        dash_choice = input("Choose an option (1-12): ").strip()

        if dash_choice == "1":
            dashboard_overview()
        elif dash_choice == "2":
            monthly_sales_report()
        elif dash_choice == "3":
            view_products()
        elif dash_choice == "4":
            view_orders()
        elif dash_choice == "5":
            view_sellers()
        elif dash_choice == "6":
            view_buyers()
        elif dash_choice == "7":
            approve_reject_products()
        elif dash_choice == "8":
            add_jaivik_id()
        elif dash_choice == "9":
            add_admin_user()
        elif dash_choice == "10":
            remove_seller()
        elif dash_choice == "11":
            remove_buyer()
        elif dash_choice == "12":
            print("Logging out. Returning to Main Menu.")
            return True  # <-- Clean logout, returns control to main.py
        else:
            print("Invalid choice. Please enter a number between 1 and 12.")
            
    return True # Catch-all return

if __name__ == "__main__":
    # Ensure all required libraries are installed:
    # pip install psycopg2-binary tabulate
    admin_main()