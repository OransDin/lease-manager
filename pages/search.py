import datetime as dt
import streamlit as st
from lease_manager.repos.customers import load_customers
from lease_manager.repos.units import load_units
from lease_manager.repos.sims import load_sims
from lease_manager.repos.notes import get_notes, update_note, delete_note
from lease_manager.repos.leases import extend_lease

st.title("🔎 Search")

c1, c2, c3 = st.columns([1,1,1])
with c1:
    customers = load_customers()
    cust_options = ["(any)"] + [c["name"] for c in customers]
    cust_choice = st.selectbox("Customer (active lease)", options=cust_options)
    customer_id = None
    if cust_choice != "(any)":
        customer_id = next(c["id"] for c in customers if c["name"] == cust_choice)
with c2:
    sn_q = st.text_input("Serial number (supports last 5 digits)", placeholder="e.g. 12345 or ABC-123")
with c3:
    st.write("") ; st.write("")
    trigger = st.button("Search", type="primary")

if trigger:
    rows = load_units(sn_filter=sn_q or None, customer_id=customer_id)
    st.caption(f"Found {len(rows)}")
    for r in rows:
        with st.expander(f"{r['sn']}  ·  {r.get('customer') or '—'}  ·  {r.get('status') or '—'}"):
            st.write(f"Model: {r['model'] or '—'}")
            st.write(f"SIM Set #: {r.get('sim_set_number') if r.get('sim_set_number') is not None else '—'}")

            if r.get("lease_id"):
                st.write(f"Lease: {r['start_date']} → {r['due_date']} ({r['status']})")
                with st.form(f"extend_{r['lease_id']}"):
                    st.write("Extend lease (max 5)")
                    new_due = st.date_input("New due date", value=(r['due_date'] or dt.date.today()) + dt.timedelta(days=7))
                    reason = st.text_input("Reason (optional)")
                    if st.form_submit_button("Extend"):
                        ok, msg = extend_lease(r["lease_id"], new_due, reason.strip() or None)
                        (st.success if ok else st.error)(msg)

            sims = load_sims(r["id"])
            if sims:
                st.write("SIMs:")
                st.table(sims)

            notes = get_notes(r["id"])
            st.write("Notes:")
            if not notes:
                st.caption("No notes yet.")
            for n in notes:
                col1, col2, col3 = st.columns([3, 0.8, 0.8])
                with col1:
                    new_txt = st.text_area(f"Note #{n['id']}", value=n["note_text"], key=f"note_text_{n['id']}", height=60)
                    st.caption(f"by {n['author'] or 'unknown'} at {n['created_at']}")
                with col2:
                    if st.button("Save", key=f"save_note_{n['id']}"):
                        update_note(n["id"], new_txt.strip())
                        st.success("Note updated.")
                with col3:
                    if st.button("Delete", key=f"delete_note_{n['id']}"):
                        delete_note(n["id"])
                        st.warning("Note deleted.")