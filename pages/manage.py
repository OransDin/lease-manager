import datetime as dt
import pandas as pd
import streamlit as st
from lease_manager.repos.customers import load_customers, create_customer
from lease_manager.repos.units import load_units, create_unit
from lease_manager.repos.sims import load_sims, replace_sims_for_unit
from lease_manager.repos.leases import create_lease

st.title("🛠️ Manage")

# Add customer / unit
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Add customer**")
    new_cust = st.text_input("Customer name", key="cust_add")
    if st.button("Create customer"):
        if new_cust.strip():
            create_customer(new_cust.strip())
            st.success("Customer added.")
            st.rerun()
        else:
            st.error("Enter a name.")

with c2:
    st.markdown("**Add unit**")
    new_sn = st.text_input("Serial number (e.g., XXXXXX-XXXXX)", key="unit_add")
    model = st.text_input("Model (optional)")
    sim_set = st.number_input("SIM Set # (optional)", min_value=0, step=1, value=0)
    if st.button("Create unit"):
        if new_sn.strip():
            create_unit(new_sn.strip(), model.strip() or None, int(sim_set))
            st.success("Unit added.")
            st.rerun()
        else:
            st.error("Enter a serial number.")

units = load_units()
sn_map = {u["sn"]: u["id"] for u in units}

st.markdown("---")
# Create / replace active lease (on top)
st.markdown("**Create / replace active lease**")
if units:
    lease_unit_sn = st.selectbox("Unit for lease", options=list(sn_map.keys()), key="lease_unit")
    lease_unit_id = sn_map[lease_unit_sn]
    custs = load_customers()
    if custs:
        lease_cust_name = st.selectbox("Customer", options=[c["name"] for c in custs], key="lease_cust")
        lease_cust_id = next(c["id"] for c in custs if c["name"] == lease_cust_name)
        d1, d2 = st.columns(2)
        start = d1.date_input("Start date", value=dt.date.today())
        due = d2.date_input("Due date", value=dt.date.today() + dt.timedelta(days=14))
        if st.button("Start lease / replace current"):
            lease_id = create_lease(lease_unit_id, lease_cust_id, start, due)
            st.success(f"Lease created (id {lease_id}).")
            st.rerun()
    else:
        st.info("Add a customer first.")
else:
    st.info("Add a unit first.")

st.markdown("---")
# Attach SIMs – editable grid 1..8
st.markdown("**Attach SIMs to a unit**")
if units:
    sel_sn = st.selectbox("Unit", options=list(sn_map.keys()) or ["(no units yet)"], key="sim_unit")
    if sel_sn and sel_sn != "(no units yet)":
        unit_id = sn_map[sel_sn]
        existing = {row["slot"]: {"slot": row["slot"], "imei": row["imei"] or "", "vendor": row["vendor"] or ""}
                    for row in load_sims(unit_id)}
        table_rows = [existing.get(s, {"slot": s, "imei": "", "vendor": ""}) for s in range(1, 9)]
        df = pd.DataFrame(table_rows, columns=["slot", "imei", "vendor"])
        st.caption("Edit IMEI / Vendor. Use TAB. Exactly 8 rows.")
        edited = st.data_editor(
            df, hide_index=True, use_container_width=True,
            column_config={
                "slot": st.column_config.NumberColumn("Slot", min_value=1, max_value=8, step=1, disabled=True),
                "imei": "IMEI", "vendor": "Vendor",
            },
            num_rows="fixed",
        )
        if st.button("Save all SIMs", type="primary"):
            cleaned = []
            seen = set()
            for _, r in edited.iterrows():
                slot = int(r["slot"])
                if slot < 1 or slot > 8 or slot in seen:
                    continue
                seen.add(slot)
                imei = str(r.get("imei") or "").strip()
                vendor = str(r.get("vendor") or "").strip()
                cleaned.append((slot, imei if imei else None, vendor if vendor else None))
            if len(cleaned) != 8:
                st.error("You must keep all 8 slots.")
            else:
                replace_sims_for_unit(unit_id, cleaned)
                st.success("SIMs saved.")
else:
    st.info("Add a unit first.")
