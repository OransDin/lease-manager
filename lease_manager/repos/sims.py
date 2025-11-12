from ..db import get_conn

def load_sims(unit_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("SELECT slot, imei, vendor FROM sims WHERE unit_id=%s ORDER BY slot", (unit_id,))
        return cur.fetchall()

def upsert_sim(unit_id, slot, imei, vendor):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO sims(unit_id, slot, imei, vendor)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (unit_id, slot)
            DO UPDATE SET imei=EXCLUDED.imei, vendor=EXCLUDED.vendor
        """, (unit_id, slot, imei, vendor))
        con.commit()

def replace_sims_for_unit(unit_id, rows):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM sims WHERE unit_id=%s", (unit_id,))
        cur.executemany(
            "INSERT INTO sims(unit_id, slot, imei, vendor) VALUES (%s,%s,%s,%s)",
            [(unit_id, int(slot), (imei or None), (vendor or None)) for slot, imei, vendor in rows]
        )
        con.commit()