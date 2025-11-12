import streamlit as st
from lease_manager.repos.leases import load_active_leases, cancel_lease

st.title("📅 Active Rents")

rows = load_active_leases()
st.caption(f"{len(rows)} active")
if not rows:
    st.info("No active leases.")
else:
    for r in rows:
        left, mid, right = st.columns([1.5, 1.5, 0.6])
        with left:
            st.markdown(f"**{r['sn']}**  ·  {r['model'] or '—'}")
            st.write(f"Customer: {r['customer']}")
            st.write(f"SIM Set #: {r.get('sim_set_number') if r.get('sim_set_number') is not None else '—'}")
        with mid:
            if r['overdue']:
                st.error(f"Due: **{r['due_date']}** (OVERDUE)")
            else:
                st.write(f"Due: **{r['due_date']}**")
            st.write(f"Start: {r['start_date']}")
        with right:
            if st.button("Mark returned", key=f"ret_{r['lease_id']}"):
                cancel_lease(r["lease_id"])
                st.success("Lease marked as returned.")
                st.rerun()