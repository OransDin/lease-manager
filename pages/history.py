import streamlit as st
from lease_manager.repos.units import load_units
from lease_manager.repos.leases import due_today  # או פונקציית היסטוריה אם מימשת
from lease_manager.db import get_conn

st.title("📜 History")

units = load_units()
if not units:
    st.info("No units yet.")
else:
    pick_sn = st.selectbox("Pick a unit", options=[u["sn"] for u in units], key="hist_sn")
    unit_id = next(u["id"] for u in units if u["sn"] == pick_sn)
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT l.id, c.name AS customer, l.start_date, l.due_date, l.status,
                   (SELECT COUNT(*) FROM lease_extensions e WHERE e.lease_id=l.id) AS extensions
            FROM leases l
            JOIN customers c ON c.id = l.customer_id
            WHERE l.unit_id = %s
            ORDER BY l.start_date DESC
        """, (unit_id,))
        hist = cur.fetchall()
    if hist:
        st.table(hist)
    else:
        st.write("No history yet for this unit.")