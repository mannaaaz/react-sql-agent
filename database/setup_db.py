import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "database/sales.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Drop existing tables (safe rerun)
cursor.execute("DROP TABLE IF EXISTS orders;")
cursor.execute("DROP TABLE IF EXISTS customers;")
cursor.execute("DROP TABLE IF EXISTS products;")

# Create tables
cursor.execute("""
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    country TEXT,
    signup_date TEXT
);
""")

cursor.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    price REAL
);
""")

cursor.execute("""
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    order_date TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
""")

# ---------- Generate Customers ----------
countries = ["USA", "UK", "Qatar", "Canada", "Germany", "France", "UAE"]

customers = []
for i in range(1, 51):
    name = f"Customer_{i}"
    country = random.choice(countries)
    signup_date = datetime.now() - timedelta(days=random.randint(0, 365))
    customers.append((i, name, country, signup_date.strftime("%Y-%m-%d")))

cursor.executemany(
    "INSERT INTO customers VALUES (?, ?, ?, ?);",
    customers
)

# ---------- Generate Products ----------
categories = ["Electronics", "Furniture", "Stationery", "Clothing", "Sports"]

products = []
for i in range(1, 51):
    name = f"Product_{i}"
    category = random.choice(categories)
    price = round(random.uniform(10, 2000), 2)
    products.append((i, name, category, price))

cursor.executemany(
    "INSERT INTO products VALUES (?, ?, ?, ?);",
    products
)

# ---------- Generate Orders ----------
orders = []
for i in range(1, 101):  # 100 orders for better realism
    customer_id = random.randint(1, 50)
    product_id = random.randint(1, 50)
    quantity = random.randint(1, 5)
    order_date = datetime.now() - timedelta(days=random.randint(0, 180))
    orders.append((i, customer_id, product_id, quantity, order_date.strftime("%Y-%m-%d")))

cursor.executemany(
    "INSERT INTO orders VALUES (?, ?, ?, ?, ?);",
    orders
)

conn.commit()
conn.close()

print("Database setup complete with 50 customers, 50 products, 100 orders.")