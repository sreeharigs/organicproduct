import psycopg2 
import hashlib
from datetime import datetime
import buyer as buyer 
import seller as seller
import admin as admin 

# --- Database Configuration ---
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
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def hash_password(password):
    """Hashes a password for secure storage and comparison."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initializes all necessary tables for the application."""
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    # 1. approved_jaivik
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approved_jaivik (
            cert_number TEXT PRIMARY KEY,
            used INTEGER DEFAULT 0
        )
    """)

    # 2. buyers 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT NOT NULL,
            password TEXT NOT NULL,
            address TEXT,
            pincode TEXT,
            reset_token TEXT,
            reset_token_expiry TIMESTAMP WITHOUT TIME ZONE
        )
    """)
    
    # 3. sellers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            jaivik_cert TEXT NOT NULL UNIQUE,
            reset_token TEXT,
            reset_token_expiry TIMESTAMP WITHOUT TIME ZONE,
            FOREIGN KEY (jaivik_cert) REFERENCES approved_jaivik(cert_number)
        )
    """)
    
    # 4. products 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            seller_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            price NUMERIC CHECK(price >= 0),
            quantity NUMERIC CHECK(quantity >= 0),
            unit TEXT DEFAULT 'pcs',
            available BOOLEAN DEFAULT TRUE,
            jaivik_id TEXT,
            status TEXT DEFAULT 'Pending',
            discount NUMERIC DEFAULT 0,
            manufacture_date DATE,
            expiry_date DATE,
            FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE
        )
    """)
    
    # 5. orders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity NUMERIC NOT NULL,
            address TEXT NOT NULL,
            pincode TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            order_date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (buyer_id) REFERENCES buyers(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
        )
    """)
    
    # 6. feedback
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            date TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (buyer_id) REFERENCES buyers(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
        )
    """)
    
    # 7. wishlist 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            date_added TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (buyer_id) REFERENCES buyers(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(buyer_id, product_id)
        )
    """)
    
    # 8. admin_users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Insert default admin user if not exists
    try:
        cursor.execute("SELECT COUNT(*) FROM admin_users WHERE username=%s", ("admin",))
        if cursor.fetchone()[0] == 0:
            hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("INSERT INTO admin_users (username, password) VALUES (%s, %s)", 
                          ("admin", hashed_password))
    except psycopg2.Error as e:
        print(f"Error creating admin user: {e}")
        conn.rollback()
        
    # Pre-populate approved Jaivik IDs
    try:
        PRE_APPROVED_IDS = [f"JB{1000+i}" for i in range(50)]
        for jaivik_id in PRE_APPROVED_IDS:
            cursor.execute("""
                INSERT INTO approved_jaivik(cert_number) VALUES (%s)
                ON CONFLICT (cert_number) DO NOTHING
            """, (jaivik_id,))
    except psycopg2.Error as e:
        print(f"Error populating Jaivik IDs: {e}")
        conn.rollback()
    
    conn.commit()
    conn.close()

def main():
    """The main entry point and menu loop for the application."""
    # 1. Initialize database
    try:
        init_database()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    # 2. Main application loop
    while True:
        print("\n--- Organic Product Management ---")
        print("1. Seller Module")
        print("2. Buyer Module")
        print("3. Admin Module")
        print("4. Exit")
        print("------------------------------------")
        choice = input("Choose an option: ").strip()
        
        if choice == '1':
            # Call seller's main function
            seller.seller_main() 
        elif choice == '2':
            # Call buyer's main function
            buyer.buyer_main() 
        elif choice == '3':
            # Call admin's main function. Control returns here upon admin logout.
            admin.admin_main() 
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()