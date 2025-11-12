from lease_manager.db import get_conn

def load_units(sn_filter=None, customer_id=None):
    sql = """
        SELECT u.id, u.sn, COALESCE(u.model,'') AS model, u.sim_set_number,
               l.id AS lease_id, l.status, l.start_date, l.due_date,
               c.name AS customer
        FROM units u
        LEFT JOIN leases l ON l.unit_id=u.id AND l.status='active'
        LEFT JOIN customers c ON c.id=l.customer_id
        WHERE 1=1
    """
    params = []
    if sn_filter:
        like = "%" + sn_filter + "%"
        # אם זה בדיוק 5 ספרות – חפש כסיומת
        if len(sn_filter) == 5 and sn_filter.isdigit():
            like = "%" + sn_filter
        sql += " AND u.sn LIKE %s"
        params.append(like)
    if customer_id:
        sql += " AND l.customer_id=%s AND l.status='active'"
        params.append(customer_id)
    sql += " ORDER BY u.sn"
    with get_conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def create_unit(sn, model=None, sim_set_number=None):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO units(sn, model, sim_set_number)
            VALUES(%s,%s,%s)
            ON CONFLICT (sn)
            DO UPDATE SET
              model = COALESCE(EXCLUDED.model, units.model),
              sim_set_number = COALESCE(EXCLUDED.sim_set_number, units.sim_set_number)
        """, (sn, model, sim_set_number))
        con.commit()

def update_unit_set_number(unit_id, n:int):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("UPDATE units SET sim_set_number=%s WHERE id=%s", (n, unit_id))
        con.commit()