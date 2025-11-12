import datetime as dt
from lease_manager.db import get_conn

def create_lease(unit_id, customer_id, start_date, due_date):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("UPDATE leases SET status='returned' WHERE unit_id=%s AND status='active'", (unit_id,))
        cur.execute("""
            INSERT INTO leases(unit_id, customer_id, start_date, due_date, status)
            VALUES (%s,%s,%s,%s,'active') RETURNING id
        """, (unit_id, customer_id, start_date, due_date))
        lease_id = cur.fetchone()["id"]
        con.commit()
        return lease_id

def count_extensions(lease_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM lease_extensions WHERE lease_id=%s", (lease_id,))
        return cur.fetchone()["cnt"]

def extend_lease(lease_id, new_due_date, reason):
    if count_extensions(lease_id) >= 5:
        return False, "Maximum of 5 extensions reached."
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO lease_extensions(lease_id, extended_due_date, reason)
            VALUES (%s,%s,%s)
        """, (lease_id, new_due_date, reason))
        cur.execute("UPDATE leases SET due_date=%s WHERE id=%s", (new_due_date, lease_id))
        con.commit()
    return True, "Lease extended."

def due_today():
    today = dt.date.today()
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT u.sn, c.name AS customer, l.due_date
            FROM leases l
            JOIN units u ON u.id = l.unit_id
            JOIN customers c ON c.id = l.customer_id
            WHERE l.status='active' AND l.due_date=%s
            ORDER BY c.name, u.sn
        """, (today,))
        return cur.fetchall()

def load_active_leases():
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT l.id AS lease_id,
                   u.id AS unit_id, u.sn, COALESCE(u.model,'') AS model, u.sim_set_number,
                   c.name AS customer,
                   l.start_date, l.due_date,
                   CASE WHEN l.due_date < CURRENT_DATE THEN TRUE ELSE FALSE END AS overdue
            FROM leases l
            JOIN units u ON u.id = l.unit_id
            JOIN customers c ON c.id = l.customer_id
            WHERE l.status = 'active'
            ORDER BY l.due_date ASC, u.sn ASC
        """)
        return cur.fetchall()

def cancel_lease(lease_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("UPDATE leases SET status='returned', returned_at=now() WHERE id=%s", (lease_id,))
        con.commit()
