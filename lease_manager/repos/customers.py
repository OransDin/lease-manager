from lease_manager.db import get_conn

def load_customers():
    with get_conn() as con, con.cursor() as cur:
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        return cur.fetchall()

def create_customer(name: str):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO customers(name) VALUES(%s) ON CONFLICT (name) DO NOTHING", (name,))
        con.commit()