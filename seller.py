import psycopg2 
import hashlib
import smtplib
import random
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tabulate import tabulate

PG_HOST = "localhost"
PG_DATABASE = "organicshopdb"
PG_USER = "postgres"
PG_PASSWORD = "12345"

EMAIL_SENDER = "shoporganicproduct@gmail.com"
EMAIL_PASSWORD = "rxfb rucb gzcj kdwd"

CATEGORY_OPTIONS = ["Food", "Personal Care", "Other"]

CATEGORY_MAX_DAYS = {
    "Food": 365,          
    "Personal Care": 365 * 3,  
    "Other": 365 * 10      
}
FOOD_LONG_LIFE_DAYS = 365 * 5


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
        print(f"Database connection error: {e}")
        return None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()



def generate_otp():
    return str(random.randint(100000, 999999))


def send_email(receiver_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def input_email(prompt="Enter email: "):
    while True:
        email = input(prompt).strip()
        if validate_email(email):
            return email
        print("Invalid email format.")


def input_mobile(prompt="Enter mobile number: "):
    while True:
        mobile = input(prompt).strip()
        if mobile.isdigit() and len(mobile) == 10:
            return mobile
        print("Invalid mobile number. Must be exactly 10 digits.")


def input_password(prompt="Enter password (min 6 chars): "):
    while True:
        pw = input(prompt).strip()
        if len(pw) >= 6:
            return pw
        print("Password too short. Minimum 6 characters required.")


def get_valid_number(prompt, number_type=float, min_value=0):
    while True:
        value = input(prompt)
        try:
            num = int(value) if number_type == int else float(value)
            if num < min_value:
                print(f"Value must be at least {min_value}.")
                continue
            return num
        except ValueError:
            print("Invalid input! Please enter a valid number.")


def select_category():
    print("\nSelect category:")
    for i, c in enumerate(CATEGORY_OPTIONS, 1):
        print(f"{i}. {c}")
    choice = input("Enter choice number: ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(CATEGORY_OPTIONS):
        print("Invalid choice. Defaulting to 'Other'.")
        return "Other"
    return CATEGORY_OPTIONS[int(choice) - 1]


def ensure_product_columns():
    """Adds the long_life column to products table if it doesn't exist (PostgreSQL DDL)."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='products' AND column_name='long_life'
    """)
    
    if not cursor.fetchone():
        try:
            print("Adding 'long_life' column to products table...")
            cursor.execute("ALTER TABLE products ADD COLUMN long_life INTEGER DEFAULT 0")
            conn.commit()
        except psycopg2.Error as e:
            print(f"Warning: Could not add long_life column (it might already exist). Error: {e}")
            conn.rollback()
    
    conn.close()


def register_seller():
    ensure_product_columns()
    print("\n--- Seller Registration ---")
    username = input("Enter username: ").strip()
    password = input_password()
    hashed_pw = hash_password(password)
    jaivik_cert = input("Enter Jaivik Bharat Certificate Number: ").strip()

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM approved_jaivik WHERE cert_number=%s", (jaivik_cert,))
    if not cursor.fetchone():
        print("Certificate not approved. Contact admin.")
        conn.close()
        return

    cursor.execute("SELECT 1 FROM sellers WHERE jaivik_cert=%s", (jaivik_cert,))
    if cursor.fetchone():
        print("This Jaivik certificate is already registered to another seller.")
        conn.close()
        return

    try:
        cursor.execute(
            "INSERT INTO sellers (username, password, jaivik_cert) VALUES (%s, %s, %s)",
            (username, hashed_pw, jaivik_cert)
        )
        conn.commit()
        print("Registration successful!")
    except psycopg2.IntegrityError:
        print("Username or Jaivik Certificate already exists. Try again.")
        conn.rollback()
    finally:
        conn.close()


def login_seller():
    print("\n--- Seller Login ---")
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    hashed_pw = hash_password(password)

    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()

    cursor.execute("SELECT id, jaivik_cert FROM sellers WHERE username=%s AND password=%s", (username, hashed_pw))
    result = cursor.fetchone()
    conn.close()

    if result:
        print("Login successful!")
        return result  
    else:
        print("Invalid credentials.")
        return None


def add_product(seller_id, jaivik_cert):
    ensure_product_columns()
    print("\n--- Add Product ---")
    name = input("Enter product name: ").strip()
    category = select_category()
    price = get_valid_number("Enter price: ", float, 0)
    unit = input("Enter unit (kg/l/pcs) or press Enter for 'pcs': ").strip() or "pcs"
    quantity = get_valid_number("Enter quantity: ", float, 0)

    discount = get_valid_number("Enter discount % (0 if none): ", float, 0)


    manufacture_date = datetime.now().date()

    if manufacture_date.year < 2020:
        print("Manufacture date must be >= 2020-01-01.")
        return

    long_life_flag = 0
    if category == "Food":
        ll = input("Is this a long-life food product? (e.g., honey) (y/n): ").strip().lower()
        if ll == "y":
            long_life_flag = 1

    print("Provide expiry date (YYYY-MM-DD). It must be after manufacture date.")
    expiry_input = input("Expiry date (YYYY-MM-DD): ").strip()
    try:
        expiry_date = datetime.strptime(expiry_input, "%Y-%m-%d").date()
    except Exception:
        print("Invalid expiry date format.")
        return

    if expiry_date <= manufacture_date:
        print("Expiry date must be after manufacture date.")
        return

    allowed_days = CATEGORY_MAX_DAYS.get(category, CATEGORY_MAX_DAYS["Other"])
    if category == "Food" and long_life_flag:
        allowed_days = FOOD_LONG_LIFE_DAYS

    max_allowed_date = manufacture_date + timedelta(days=allowed_days)
    if expiry_date > max_allowed_date:
        print(f"Expiry date exceeds allowed maximum for category '{category}'.")
        if category == "Food" and long_life_flag:
            print(f"Allowed for long-life food is up to {FOOD_LONG_LIFE_DAYS // 365} years.")
        else:
            print(f"Allowed max for {category} is {allowed_days // 365} years from manufacture.")
        print("You may set a shorter expiry, or mark long-life (if Food) and request admin approval.")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO products (seller_id, name, category, price, quantity, unit, jaivik_id, discount, manufacture_date, expiry_date, status, long_life)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', %s)
        """, (
            seller_id, name, category, price, quantity, unit, jaivik_cert, discount,
            manufacture_date.isoformat(), expiry_date.isoformat(), long_life_flag
        ))

        conn.commit()
        print("Product added successfully! Status: Pending approval by admin.")
    except psycopg2.Error as e:
        print(f"Error adding product: {e}")
        conn.rollback()
    finally:
        conn.close()


def view_my_products(seller_id):
    print("\n--- My Products ---")
    ensure_product_columns()
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, category, price, quantity, unit, available, status, jaivik_id, 
               manufacture_date, expiry_date, long_life
        FROM products
        WHERE seller_id=%s
        ORDER BY id
    """, (seller_id,))

    products = cursor.fetchall()
    conn.close()

    if not products:
        print("You haven't added any products yet.")
        return

    headers = ["ID", "Name", "Category", "Price", "Qty", "Unit", "Available", "Status", "Jaivik ID", "Mfg Date", "Expiry Date", "LongLife"]
    print(tabulate(products, headers=headers, tablefmt="grid"))


def edit_product(seller_id):
    ensure_product_columns()
    view_my_products(seller_id)
    try:
        product_id = int(input("Enter product ID to edit: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, category, price, quantity, unit, discount, manufacture_date, expiry_date, status, long_life 
        FROM products 
        WHERE id=%s AND seller_id=%s
    """, (product_id, seller_id))
    product = cursor.fetchone()

    if not product:
        print("Product not found.")
        conn.close()
        return

    (prod_id, old_name, old_category, old_price, old_quantity, old_unit, old_discount, 
     old_mfg_date, old_exp_date, current_status, old_long_life) = product

    print("Leave input blank to keep current value.")

    if current_status == 'Approved':
        print("Product is approved: name and category cannot be changed.")
        new_name = old_name
        new_category = old_category
    else:
        new_name = input(f"Name [{old_name}]: ").strip() or old_name
        print(f"Current category: {old_category}")
        change_cat = input("Change category? (y/n): ").strip().lower()
        if change_cat == 'y':
            new_category = select_category()
        else:
            new_category = old_category

    new_price_input = input(f"Price [{old_price}]: ").strip()
    new_price = float(new_price_input) if new_price_input else old_price

    new_quantity_input = input(f"Quantity [{old_quantity}]: ").strip()
    new_quantity = float(new_quantity_input) if new_quantity_input else old_quantity

    new_unit = input(f"Unit [{old_unit}]: ").strip() or old_unit

    new_discount_input = input(f"Discount% [{old_discount}]: ").strip()
    new_discount = float(new_discount_input) if new_discount_input else old_discount

    manufacture_date = old_mfg_date
    
    expiry_input = input(f"Expiry Date [{old_exp_date}] (YYYY-MM-DD): ").strip()
    if expiry_input:
        try:
            new_expiry = datetime.strptime(expiry_input, "%Y-%m-%d").date()
        except Exception:
            print("Invalid expiry date format.")
            conn.close()
            return
        if new_expiry <= manufacture_date:
            print("Expiry must be after manufacture date.")
            conn.close()
            return
    else:
        new_expiry = old_exp_date

    new_long_life = old_long_life
    if new_category == "Food":
        ll = input(f"Long-life flag (current {old_long_life})? (y/n to change): ").strip().lower()
        if ll == 'y':
            new_long_life = 1 if old_long_life == 0 else 0

    allowed_days = CATEGORY_MAX_DAYS.get(new_category, CATEGORY_MAX_DAYS["Other"])
    if new_category == "Food" and new_long_life:
        allowed_days = FOOD_LONG_LIFE_DAYS
    max_allowed_date = manufacture_date + timedelta(days=allowed_days)
    if new_expiry > max_allowed_date:
        print("New expiry exceeds allowed maximum for this category.")
        conn.close()
        return

    try:
        cursor.execute("""
            UPDATE products
            SET name=%s, category=%s, price=%s, quantity=%s, unit=%s, discount=%s, expiry_date=%s, status='Pending', long_life=%s
            WHERE id=%s AND seller_id=%s
        """, (new_name, new_category, new_price, new_quantity, new_unit, new_discount, new_expiry.isoformat(), new_long_life, prod_id, seller_id))

        conn.commit()
        print("Product updated. Status set to Pending for admin approval.")
    except psycopg2.Error as e:
        print(f"Error updating product: {e}")
        conn.rollback()
    finally:
        conn.close()


def delete_product(seller_id):
    view_my_products(seller_id)
    try:
        product_id = int(input("Enter product ID to delete: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM products WHERE id=%s AND seller_id=%s", (product_id, seller_id))
    if not cursor.fetchone():
        print("Product not found.")
        conn.close()
        return

    confirm = input("Are you sure you want to delete this product? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Deletion cancelled.")
        conn.close()
        return

    try:
        cursor.execute("DELETE FROM products WHERE id=%s AND seller_id=%s", (product_id, seller_id))
        conn.commit()
        print("Product deleted successfully.")
    except psycopg2.Error as e:
        print(f"Error deleting product: {e}")
        conn.rollback()
    finally:
        conn.close()


def toggle_availability(seller_id):
    view_my_products(seller_id)
    try:
        product_id = int(input("Enter product ID: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("SELECT available FROM products WHERE id=%s AND seller_id=%s", (product_id, seller_id))
    result = cursor.fetchone()

    if not result:
        print("Product not found.")
        conn.close()
        return

    current_status = result[0]
    new_status = not current_status

    try:
        cursor.execute("UPDATE products SET available=%s WHERE id=%s AND seller_id=%s", (new_status, product_id, seller_id))
        conn.commit()
        print(f"Product availability set to {'Available' if new_status else 'Not Available'}.")
    except psycopg2.Error as e:
        print(f"Error toggling availability: {e}")
        conn.rollback()
    finally:
        conn.close()


def view_orders(seller_id):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id, b.username, p.name, o.quantity, p.unit, o.address, o.status, o.order_date
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN buyers b ON o.buyer_id = b.id
        WHERE p.seller_id=%s
        ORDER BY o.order_date DESC
    """, (seller_id,))
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        print("No orders found.")
        return

    headers = ["Order ID", "Buyer", "Product", "Qty", "Unit", "Address", "Status", "Order Date"]
    print(tabulate(orders, headers=headers, tablefmt="grid"))


def mark_order_delivered(seller_id):
    view_orders(seller_id)
    try:
        order_id = int(input("Enter Order ID to mark as Delivered: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.id=%s AND p.seller_id=%s
    """, (order_id, seller_id))
    if not cursor.fetchone():
        print("Order not found or does not belong to you.")
        conn.close()
        return

    try:
        cursor.execute("UPDATE orders SET status='Delivered' WHERE id=%s", (order_id,))
        conn.commit()
        print("Order marked as Delivered.")
    except psycopg2.Error as e:
        print(f"Error marking order delivered: {e}")
        conn.rollback()
    finally:
        conn.close()


def view_product_reviews(seller_id):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, AVG(f.rating) as avg_rating, COUNT(f.id) as review_count
        FROM products p
        LEFT JOIN feedback f ON p.id = f.product_id
        WHERE p.seller_id=%s
        GROUP BY p.id, p.name
    """, (seller_id,))

    products = cursor.fetchall()
    if not products:
        print("No products found.")
        conn.close()
        return

    display_products = [(p[0], p[1], round(p[2] or 0, 2), p[3]) for p in products]
    
    headers = ["ID", "Product Name", "Avg Rating", "Review Count"]
    print(tabulate(display_products, headers=headers, tablefmt="grid"))

    prod_id = input("Enter product ID to view detailed reviews (or 0 to go back): ").strip()
    if prod_id == "0":
        conn.close()
        return

    cursor.execute("""
        SELECT f.rating, f.comment, f.date, b.username
        FROM feedback f
        JOIN products p ON f.product_id = p.id
        JOIN buyers b ON f.buyer_id = b.id
        WHERE p.id=%s AND p.seller_id=%s
        ORDER BY f.date DESC
    """, (prod_id, seller_id))
    reviews = cursor.fetchall()
    
    if reviews:
        headers = ["Rating", "Comment", "Date", "Buyer"]
        print(f"\nReviews for Product ID {prod_id}:")
        print(tabulate(reviews, headers=headers, tablefmt="grid"))
    else:
        print("No reviews for this product.")
    conn.close()


def view_analytics(seller_id):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.name, p.unit, SUM(o.quantity) as total_units, 
               SUM(o.quantity * p.price) as total_revenue
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE p.seller_id=%s AND o.status='Delivered'
        GROUP BY p.id, p.name, p.unit
        ORDER BY total_units DESC
        LIMIT 10
    """, (seller_id,))
    top_products = cursor.fetchall()

    if top_products:
        display_top_products = [(p[0], p[1], p[2], p[3], round(p[4] or 0, 2)) for p in top_products]
        headers = ["Product ID", "Name", "Unit", "Units Sold", "Revenue"]
        print("\nTop Selling Products:")
        print(tabulate(display_top_products, headers=headers, tablefmt="grid"))
    else:
        print("No sales data yet for your products.")

    cursor.execute("""
        SELECT TO_CHAR(o.order_date, 'YYYY-MM') as month, COUNT(*) as total_orders,
               SUM(o.quantity * p.price) as revenue
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE p.seller_id=%s AND o.status='Delivered'
        GROUP BY month
        ORDER BY month DESC
    """, (seller_id,))
    monthly = cursor.fetchall()
    if monthly:
        display_monthly = [(m[0], m[1], round(m[2] or 0, 2)) for m in monthly]
        headers = ["Month", "Orders", "Revenue"]
        print("\nMonthly Sales:")
        print(tabulate(display_monthly, headers=headers, tablefmt="grid"))
    conn.close()


def seller_main():
    ensure_product_columns()
    while True:
        print("\n--- Seller Menu ---")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            register_seller()
        elif choice == "2":
            login_result = login_seller()
            if login_result:
                seller_id, jaivik_cert = login_result
                while True:
                    print("\n--- Seller Dashboard ---")
                    print("1. View My Products")
                    print("2. Add Product")
                    print("3. Edit Product")
                    print("4. Delete Product")
                    print("5. Toggle Availability")
                    print("6. View Orders")
                    print("7. Mark Order Delivered")
                    print("8. View Product Reviews")
                    print("9. View Analytics")
                    print("10. Logout")
                    dash_choice = input("Choose an option: ").strip()

                    if dash_choice == "1":
                        view_my_products(seller_id)
                    elif dash_choice == "2":
                        add_product(seller_id, jaivik_cert)
                    elif dash_choice == "3":
                        edit_product(seller_id)
                    elif dash_choice == "4":
                        delete_product(seller_id)
                    elif dash_choice == "5":
                        toggle_availability(seller_id)
                    elif dash_choice == "6":
                        view_orders(seller_id)
                    elif dash_choice == "7":
                        mark_order_delivered(seller_id)
                    elif dash_choice == "8":
                        view_product_reviews(seller_id)
                    elif dash_choice == "9":
                        view_analytics(seller_id)
                    elif dash_choice == "10":
                        break
                    else:
                        print("Invalid choice.")
        elif choice == "3":
            break
        else:
            print("Invalid input.")