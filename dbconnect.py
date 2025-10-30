import psycopg2

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="organicshopdb",
            user="postgres",
            password="12345"
        )
        print("Connected to database!")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None