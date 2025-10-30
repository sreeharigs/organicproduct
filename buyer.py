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

# Utility Functions
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
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp():
    return str(random.randint(100000, 999999))

def generate_reset_token():
    return hashlib.sha256(str(random.randint(100000, 999999)).encode()).hexdigest()


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

def send_otp_email(receiver_email, otp):
    subject = "Organic Shop - OTP Verification"
    body = f"Your OTP for registration is: {otp}\nDo not share it with anyone."
    return send_email(receiver_email, subject, body)

def send_reset_email(receiver_email, reset_token):
    subject = "Organic Shop - Password Reset"
    body = f"Your password reset token is: {reset_token}\nThis token will expire in 1 hour."
    return send_email(receiver_email, subject, body)


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

def input_int(prompt, min_val=None, max_val=None):
    while True:
        val = input(prompt).strip()
        if not val.isdigit():
            print("Please enter a valid number.")
            continue
        val = int(val)
        if min_val is not None and val < min_val:
            print(f"Value must be at least {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"Value must not exceed {max_val}.")
            continue
        return val

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_valid_date(prompt):
    while True:
        date = input(prompt)
        if validate_date(date):
            return date
        else:
            print("Invalid date format! Use YYYY-MM-DD.")

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

def input_pincode(prompt="Enter pincode: "):
    while True:
        pincode = input(prompt).strip()
        if pincode.isdigit() and len(pincode) == 6:
            return pincode
        print("Invalid pincode. Must be exactly 6 digits.")

def input_address():
    print("\n--- Enter Address Details ---")
    house = input("House/Flat No: ").strip()
    while not house:
        print("House/Flat No cannot be empty.")
        house = input("House/Flat No: ").strip()
    
    street = input("Street/Locality: ").strip()
    while not street:
        print("Street/Locality cannot be empty.")
        street = input("Street/Locality: ").strip()
    
    city = input("City: ").strip()
    while not city or any(char.isdigit() for char in city):
        if not city:
            print("City cannot be empty.")
        else:
            print("City should not contain numbers.")
        city = input("City: ").strip()
    
    state = input("State: ").strip()
    while not state or any(char.isdigit() for char in state):
        if not state:
            print("State cannot be empty.")
        else:
            print("State should not contain numbers.")
        state = input("State: ").strip()
    
    pincode = input_pincode()
    
    return f"{house}, {street}, {city}, {state} - {pincode}", pincode


# Buyer Functions
def register_buyer():
    print("\n--- Buyer Registration ---")
    username = input("Enter username: ").strip()
    email = input_email()
    mobile = input_mobile()
    password = input_password()
    hashed_pw = hash_password(password)
    
    otp = generate_otp()
    if not send_otp_email(email, otp):
        print("OTP sending failed. Try again.")
        return
    
    entered_otp = input("Enter the OTP sent to your email: ").strip()
    if entered_otp != otp:
        print("Invalid OTP. Registration failed.")
        return
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO buyers (username, email, mobile, password) VALUES (%s, %s, %s, %s)",
            (username, email, mobile, hashed_pw)
        )
        conn.commit()
        print("Buyer registered successfully!")
    except psycopg2.IntegrityError:
        print("Username or email already exists. Try again.")
        conn.rollback() # Rollback in case of error
    finally:
        conn.close()

def login_buyer():
    email = input_email()
    password = input("Enter password: ").strip()
    hashed_pw = hash_password(password)
    
    conn = get_db_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, mobile, address, pincode 
        FROM buyers 
        WHERE email=%s AND password=%s
    """, (email, hashed_pw))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        print(f"Login successful! Welcome {result[1]}")
        return result
    else:
        print("Invalid login.")
        return None

def reset_buyer_password():
    email = input_email()
    
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM buyers WHERE email=%s", (email,))
    buyer = cursor.fetchone()
    
    if not buyer:
        print("No account found with this email.")
        conn.close()
        return
    
    reset_token = generate_reset_token()
    expiry = datetime.now() + timedelta(hours=1)
    
    cursor.execute(
        "UPDATE buyers SET reset_token=%s, reset_token_expiry=%s WHERE email=%s",
        (reset_token, expiry, email)
    )
    conn.commit()
    conn.close()
    
    if send_reset_email(email, reset_token):
        print("Password reset token sent to your email.")
    else:
        print("Failed to send reset email. Try again.")

def complete_password_reset(user_type="buyer"):
    email = input_email()
    token = input("Enter reset token: ").strip()
    new_password = input_password("Enter new password: ")
    hashed_pw = hash_password(new_password)
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    if user_type == "buyer":
        cursor.execute("""
            SELECT id FROM buyers 
            WHERE email=%s AND reset_token=%s AND reset_token_expiry > %s
        """, (email, token, datetime.now()))
    else: 
        cursor.execute("""
            SELECT id FROM sellers 
            WHERE username=%s AND reset_token=%s AND reset_token_expiry > %s
        """, (email, token, datetime.now()))
    
    user = cursor.fetchone()
    
    if not user:
        print("Invalid or expired reset token.")
        conn.close()
        return
    
    if user_type == "buyer":
        cursor.execute(
            "UPDATE buyers SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE email=%s",
            (hashed_pw, email)
        )
    else:
    
        cursor.execute(
            "UPDATE sellers SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE username=%s",
            (hashed_pw, email)
        )
    
    conn.commit()
    conn.close()
    print("Password reset successfully!")

def browse_products():
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.id, p.name, p.price, p.category, s.username, p.jaivik_id, p.quantity, p.unit
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.available=TRUE AND p.status='Approved' -- PostgreSQL uses TRUE/FALSE for boolean
        ORDER BY p.id
    """)
    
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        print("No approved products available.")
        return
    
    headers = ["ID", "Name", "Price", "Category", "Seller", "Jaivik ID", "Stock", "Unit"]
    print("\n=== Available Products ===")
    print(tabulate(products, headers=headers, tablefmt="grid"))

def browse_by_category():
    category = input("Enter category: ").strip()
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.id, p.name, p.price, s.username, p.jaivik_id, p.quantity, p.unit
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.category=%s AND p.available=TRUE AND p.status='Approved'
        ORDER BY p.name
    """, (category,))
    
    products = cursor.fetchall()
    conn.close()
    
    if products:
        headers = ["ID", "Name", "Price", "Seller", "Jaivik ID", "Stock", "Unit"]
        print(f"\n=== Products in '{category}' Category ===")
        print(tabulate(products, headers=headers, tablefmt="grid"))
    else:
        print("No products found in this category.")

def search_products():
    keyword = input("Enter product name or category: ").strip()
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    search_term = '%' + keyword + '%'
    cursor.execute("""
        SELECT p.id, p.name, p.price, p.category, s.username, p.jaivik_id, p.quantity, p.unit
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE (p.name ILIKE %s OR p.category ILIKE %s) AND p.available=TRUE AND p.status='Approved' -- ILIKE is case-insensitive in PostgreSQL
        ORDER BY p.name
    """, (search_term, search_term))
    
    results = cursor.fetchall()
    conn.close()
    
    if results:
        headers = ["ID", "Name", "Price", "Category", "Seller", "Jaivik ID", "Stock", "Unit"]
        print(f"\n=== Search Results for '{keyword}' ===")
        print(tabulate(results, headers=headers, tablefmt="grid"))
    else:
        print("No products found.")

def buy_product(buyer, product_id=None):
    if not product_id:
        browse_products()
        product_id = input_int("Enter product ID to buy: ", min_val=1)
    
    buyer_id, username, mobile, saved_address, saved_pincode = buyer
    print(f"\nBuyer Details:")
    print(f"Name: {username}")
    print(f"Mobile: {mobile}")
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT quantity, name, unit, price FROM products WHERE id=%s AND available=TRUE AND status='Approved'", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            print("Product not found or not available.")
            return
        
        # --- FIX APPLIED HERE ---
        # PostgreSQL returns NUMERIC/DECIMAL as decimal.Decimal object. 
        # Convert these to float before performing arithmetic with user input (qty).
        available_qty_decimal, product_name, unit, price_decimal = product
        available_qty = float(available_qty_decimal)
        price = float(price_decimal)
        # ------------------------
        
        print(f"\nProduct: {product_name}")
        print(f"Available: {available_qty} {unit}")
        print(f"Price: ₹{price} per {unit}")
        
        qty = get_valid_number(f"Enter quantity to buy ({unit}): ", float, 0.01)
        
        if available_qty < qty:
            print(f"Only {available_qty} {unit} of {product_name} available.")
            return
        
        total_cost = qty * price
        print(f"Total cost: ₹{total_cost:.2f}")
        
        # Address handling
        if saved_address:
            print(f"Saved address: {saved_address}")
            use_saved = input("Use saved address? (y/n): ").strip().lower()
            if use_saved == 'y':
                address = saved_address
                pincode = saved_pincode
            else:
                address, pincode = input_address()
                cursor.execute("UPDATE buyers SET address=%s, pincode=%s WHERE id=%s", (address, pincode, buyer_id))
        else:
            address, pincode = input_address()
            cursor.execute("UPDATE buyers SET address=%s, pincode=%s WHERE id=%s", (address, pincode, buyer_id))
        
        cursor.execute("""
            INSERT INTO orders (buyer_id, product_id, quantity, address, pincode) 
            VALUES (%s, %s, %s, %s, %s)
        """, (buyer_id, product_id, qty, address, pincode))
        
        cursor.execute("UPDATE products SET quantity=quantity-%s WHERE id=%s", (qty, product_id))
        
        conn.commit()
        
        print(f"\nOrder placed successfully!")
        print(f"Ordered: {qty} {unit} of {product_name}")
        print(f"Total: ₹{total_cost:.2f}")
        print("Payment: Cash on Delivery")

    except Exception as e:
        print(f"An error occurred during order placement: {e}")
        conn.rollback() # Rollback transaction on error
    finally:
        conn.close()

def add_feedback(buyer):
    buyer_id = buyer[0]
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    # Show products purchased by buyer
    cursor.execute("""
        SELECT DISTINCT p.id, p.name 
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.buyer_id=%s
        ORDER BY p.name
    """, (buyer_id,))
    purchased = cursor.fetchall()
    
    if not purchased:
        print("You haven't purchased any product yet.")
        conn.close()
        return
    
    print("\n=== Your Purchased Products ===")
    headers = ["Product ID", "Product Name"]
    print(tabulate(purchased, headers=headers, tablefmt="grid"))
    
    prod_id = input_int("Enter product ID to review: ")
    purchased_ids = [p[0] for p in purchased]
    
    if prod_id not in purchased_ids:
        print("You can only review products you purchased.")
        conn.close()
        return
    
    rating = input_int("Enter rating (1-5): ", min_val=1, max_val=5)
    comment = input("Enter review: ").strip()
    
    cursor.execute("""
        INSERT INTO feedback (buyer_id, product_id, rating, comment) 
        VALUES (%s, %s, %s, %s)
    """, (buyer_id, prod_id, rating, comment))
    
    conn.commit()
    conn.close()
    
    print("Feedback submitted. Thank you!")

def view_orders(buyer):
    buyer_id = buyer[0]
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.id, p.name, o.quantity, p.unit, o.address, s.username, o.status, o.order_date,
                         (o.quantity * p.price) as total_cost
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN sellers s ON p.seller_id = s.id
        WHERE o.buyer_id=%s
        ORDER BY o.order_date DESC
    """, (buyer_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        print("No orders yet.")
    else:
        headers = ["Order ID", "Product", "Qty", "Unit", "Address", "Seller", "Status", "Order Date", "Total Cost"]
        print("\n=== Your Orders ===")
        print(tabulate(orders, headers=headers, tablefmt="grid"))

def add_to_wishlist(buyer):
    browse_products()
    prod_id = input_int("Enter product ID to add to wishlist: ", min_val=1)
    
    buyer_id = buyer[0]
    
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM products WHERE id=%s AND available=TRUE AND status='Approved'", (prod_id,))
    product = cursor.fetchone()
    
    if not product:
        print("Product not found or not available.")
        conn.close()
        return
    
    try:
        cursor.execute("""
            INSERT INTO wishlist (buyer_id, product_id) 
            VALUES (%s, %s)
        """, (buyer_id, prod_id))
        
        conn.commit()
        print(f"'{product[0]}' added to wishlist!")
    except psycopg2.IntegrityError:
        print("Product is already in your wishlist.")
        conn.rollback()
    finally:
        conn.close()

def view_wishlist(buyer):
    buyer_id = buyer[0]
    
    conn = get_db_connection()
    if not conn:
        return False
        
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.id, p.name, p.price, p.category, s.username, p.quantity, p.unit
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        JOIN sellers s ON p.seller_id = s.id
        WHERE w.buyer_id=%s
        ORDER BY w.date_added DESC
    """, (buyer_id,))
    
    wishlist_items = cursor.fetchall()
    conn.close()
    
    if not wishlist_items:
        print("Your wishlist is empty.")
        return False
    else:
        headers = ["ID", "Name", "Price", "Category", "Seller", "Stock", "Unit"]
        print("\n=== Your Wishlist ===")
        print(tabulate(wishlist_items, headers=headers, tablefmt="grid"))
        return True

def buy_from_wishlist(buyer):
    if not view_wishlist(buyer):
        return
    
    prod_id = input_int("Enter product ID to buy from wishlist: ", min_val=1)
    
    buyer_id = buyer[0]
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    cursor.execute("SELECT product_id FROM wishlist WHERE buyer_id=%s AND product_id=%s", (buyer_id, prod_id))
    if not cursor.fetchone():
        print("This product is not in your wishlist.")
        conn.close()
        return
    
    conn.close()
    
    buy_product(buyer, prod_id)

def remove_from_wishlist(buyer):
    if not view_wishlist(buyer):
        return
        
    prod_id = input_int("Enter product ID to remove from wishlist: ", min_val=1)
    
    buyer_id = buyer[0]
    
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM wishlist 
        WHERE buyer_id=%s AND product_id=%s
    """, (buyer_id, prod_id))
    
    if cursor.rowcount > 0:
        print("Product removed from wishlist.")
    else:
        print("Product not found in your wishlist.")
    
    conn.commit()
    conn.close()

def buyer_main():
    while True:
        print("\n--- Buyer Menu ---")
        print("1. Register")
        print("2. Login")
        print("3. Password Reset")
        print("4. Exit")
        choice = input("Choose: ").strip()
        
        if choice == "1":
            register_buyer()
        elif choice == "2":
            buyer = login_buyer()
            if buyer:
                while True:
                    print("\n--- Buyer Dashboard ---")
                    print("1. Browse Products")
                    print("2. Browse by Category")
                    print("3. Search Products")
                    print("4. Buy Product")
                    print("5. View My Orders")
                    print("6. Add Feedback")
                    print("7. Wishlist")
                    print("8. Logout")
                    sub = input("Choose: ").strip()
                    
                    if sub == "1":
                        browse_products()
                    elif sub == "2":
                        browse_by_category()
                    elif sub == "3":
                        search_products()
                    elif sub == "4":
                        buy_product(buyer)
                    elif sub == "5":
                        view_orders(buyer)
                    elif sub == "6":
                        add_feedback(buyer)
                    elif sub == "7":
                        print("\n--- Wishlist ---")
                        print("1. View Wishlist")
                        print("2. Add to Wishlist")
                        print("3. Buy from Wishlist")
                        print("4. Remove from Wishlist")
                        wish_choice = input("Choose: ").strip()
                        
                        if wish_choice == "1":
                            view_wishlist(buyer)
                        elif wish_choice == "2":
                            add_to_wishlist(buyer)
                        elif wish_choice == "3":
                            buy_from_wishlist(buyer)
                        elif wish_choice == "4":
                            remove_from_wishlist(buyer)
                        else:
                            print("Invalid option.")
                    elif sub == "8":
                        break
                    else:
                        print("Invalid option.")
        elif choice == "3":
            reset_buyer_password()
            token = input("Enter reset token from email: ").strip()
            if token:
                complete_password_reset("buyer")
        elif choice == "4":
            break
        else:
            print("Invalid option.")

if __name__ == '__main__':
    buyer_main()