import os
import re
import datetime as dt
import psycopg2
import psycopg2.extras
import streamlit as st
import pandas as pd


DB_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)

st.set_page_config(page_title="Rent Manager", layout="wide")
st.title("📦 LiveU - Rent Manager")

# ---------- Small helpers ----------
def last5_like(sn_fragment: str):
    q = sn_fragment.strip()
    # if exactly 5 digits => suffix search; else substring
    if re.fullmatch(r"\d{5}", q):
        return "%"+q, True
    return "%"+q+"%", False

def load_customers():
    with get_conn() as con, con.cursor() as cur:
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        return cur.fetchall()

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
        like, _ = last5_like(sn_filter)
        sql += " AND u.sn LIKE %s"
        params.append(like)
    if customer_id:
        sql += " AND l.customer_id=%s AND l.status='active'"
        params.append(customer_id)
    sql += " ORDER BY u.sn"
    with get_conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def unit_history(unit_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT l.id, c.name AS customer, l.start_date, l.due_date, l.status,
                   (SELECT COUNT(*) FROM lease_extensions e WHERE e.lease_id=l.id) AS extensions
            FROM leases l
            JOIN customers c ON c.id = l.customer_id
            WHERE l.unit_id = %s
            ORDER BY l.start_date DESC
        """, (unit_id,))
        return cur.fetchall()

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

def add_note(unit_id, note, author):
    with get_conn() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO unit_notes(unit_id, note_text, author) VALUES (%s,%s,%s)",
            (unit_id, note, author),
        )
        con.commit()

def get_notes(unit_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, note_text, COALESCE(author,'' ) AS author, created_at
            FROM unit_notes
            WHERE unit_id=%s
            ORDER BY created_at DESC
        """, (unit_id,))
        return cur.fetchall()

def delete_note(note_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM unit_notes WHERE id=%s", (note_id,))
        con.commit()

def update_note(note_id, new_text):
    with get_conn() as con, con.cursor() as cur:
        cur.execute(
            "UPDATE unit_notes SET note_text=%s, created_at=now() WHERE id=%s",
            (new_text, note_id),
        )
        con.commit()

def create_customer(name):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO customers(name) VALUES(%s) ON CONFLICT (name) DO NOTHING", (name,))
        con.commit()

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

def create_lease(unit_id, customer_id, start_date, due_date):
    with get_conn() as con, con.cursor() as cur:
        # ensure no other active lease for this unit
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
    # cap at 5
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

def update_unit_set_number(unit_id, n):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("UPDATE units SET sim_set_number=%s WHERE id=%s", (n, unit_id))
        con.commit()

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

def replace_sims_for_unit(unit_id, rows):
    """rows = list of (slot:int, imei:str|None, vendor:str|None)"""
    with get_conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM sims WHERE unit_id=%s", (unit_id,))
        cur.executemany(
            "INSERT INTO sims(unit_id, slot, imei, vendor) VALUES (%s,%s,%s,%s)",
            [(unit_id, int(slot), (imei or None), (vendor or None)) for slot, imei, vendor in rows]
        )
        con.commit()

# ---------- Top banner reminders ----------
due = due_today()
if due:
    st.info("🔔 **Due today**:\n" + "\n".join([f"- {r['sn']} — {r['customer']} (due {r['due_date']})" for r in due]))

tab_search, tab_manage, tab_history, tab_active = st.tabs(["🔎 Search", "🛠️ Manage", "📜 History", "📅 Active Rents"])

# ---------- Search tab ----------
with tab_search:
    st.subheader("Search units")
    cols = st.columns([1,1,1])
    with cols[0]:
        customers = load_customers()
        cust_options = ["(any)"] + [c["name"] for c in customers]
        cust_choice = st.selectbox("Customer (active lease)", options=cust_options)
        customer_id = None
        if cust_choice != "(any)":
            customer_id = next(c["id"] for c in customers if c["name"] == cust_choice)
    with cols[1]:
        sn_q = st.text_input("Serial number (supports last 5 digits)", placeholder="e.g. 12345 or ABC-123")
    with cols[2]:
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
                    # extend if allowed
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
                            new_txt = st.text_area(
                                f"Note #{n['id']}",
                                value=n["note_text"],
                                key=f"note_text_{n['id']}",
                                height=60,
                            )
                            st.caption(f"by {n['author'] or 'unknown'} at {n['created_at']}")

                        with col2:
                            if st.button("Save", key=f"save_note_{n['id']}"):
                                update_note(n["id"], new_txt.strip())
                                st.success("Note updated.")

                        with col3:
                            if st.button("Delete", key=f"delete_note_{n['id']}"):
                                delete_note(n["id"])
                                st.warning("Note deleted.")



# ---------- Manage tab ----------
with tab_manage:
    st.subheader("Quick add / edit")

    # ---- Add customer / unit (with SIM set) ----
    c1, c2 = st.columns(2)

    # Add customer
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

    # Add unit
    with c2:
        st.markdown("**Add unit**")
        new_sn = st.text_input("Serial number (e.g., XXXXXX-XXXXX)", key="unit_add")
        model = st.text_input("Model (optional)")
        sim_set = st.number_input("SIM Set # (optional)", min_value=0, step=1, value=0)
        if st.button("Create unit"):
            if new_sn.strip():
                create_unit(new_sn.strip(), model.strip() or None, int(sim_set))
                st.success("Unit added.")
                st.rerun()   # כדי שהיחידה תופיע מיד בשאר הרשימות
            else:
                st.error("Enter a serial number.")

    # טען רשימת יחידות לאחר יצירה
    units = load_units()
    sn_map = {u["sn"]: u["id"] for u in units}

    st.markdown("---")

    # ---- Create / replace active lease (למעלה, כמו שביקשת) ----
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

    # ---- Attach SIMs to a unit (טבלה 1–8, אפשר TAB) ----
    st.markdown("**Attach SIMs to a unit**")
    if units:
        sel_sn = st.selectbox("Unit", options=list(sn_map.keys()) or ["(no units yet)"], key="sim_unit")
        if sel_sn and sel_sn != "(no units yet)":
            unit_id = sn_map[sel_sn]

            # Load existing SIMs and normalize to fixed rows (slots 1..8)
            existing = {
                row["slot"]: {
                    "slot": row["slot"],
                    "imei": row["imei"] or "",
                    "vendor": row["vendor"] or "",
                }
                for row in load_sims(unit_id)
            }
            table_rows = []
            for s in range(1, 9):
                r = existing.get(s, {"slot": s, "imei": "", "vendor": ""})
                table_rows.append(r)

            df = pd.DataFrame(table_rows, columns=["slot", "imei", "vendor"])

            st.caption("Edit IMEI and Vendor below. Use TAB to move between cells. Exactly 8 rows (slots 1–8).")
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "slot": st.column_config.NumberColumn("Slot", min_value=1, max_value=8, step=1, disabled=True),
                    "imei": "IMEI",
                    "vendor": "Vendor",
                },
                num_rows="fixed",  # keep exactly 8 rows
            )

            c1, c2 = st.columns([0.2, 0.8])
            if c1.button("Save all SIMs", type="primary"):
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
                    st.error("You must keep all 8 slots (1–8).")
                else:
                    replace_sims_for_unit(unit_id, cleaned)
                    st.success("SIMs saved.")
    else:
        st.info("Add a unit first.")

    st.markdown("---")

    # ---- Add note to unit ----
    st.markdown("**Add note to unit**")
    units = load_units()
    if units:
        sn_map = {u["sn"]: u["id"] for u in units}
        note_unit_sn = st.selectbox("Unit to note", options=list(sn_map.keys()), key="note_unit")
        note_unit_id = sn_map.get(note_unit_sn)
        note_txt = st.text_area("Note")
        author = st.text_input("Author (optional)", value="")
        if st.button("Add note"):
            if note_txt.strip():
                add_note(note_unit_id, note_txt.strip(), author.strip() or None)
                st.success("Note added.")
                st.rerun()
            else:
                st.error("Write a note.")
    else:
        st.info("Add a unit first.")

# ---------- History tab ----------
with tab_history:
    st.subheader("Unit history")
    units = load_units()
    if not units:
        st.info("No units yet.")
    else:
        pick_sn = st.selectbox("Pick a unit", options=[u["sn"] for u in units], key="hist_sn")
        unit_id = next(u["id"] for u in units if u["sn"] == pick_sn)
        hist = unit_history(unit_id)
        if hist:
            st.table(hist)
        else:
            st.write("No history yet for this unit.")

# ---------- Active leases tab ----------
with tab_active:
    st.subheader("Active rents")

    rows = load_active_leases()
    st.caption(f"{len(rows)} active")

    if not rows:
        st.info("No active rents.")
    else:
        for r in rows:
            with st.container(border=True):
                left, mid, right = st.columns([1.5, 1.5, 0.6])

                with left:
                    st.markdown(f"**{r['sn']}**  ·  {r['model'] or '—'}")
                    st.write(f"Customer: {r['customer']}")
                    st.write(
                        "SIM Set #: "
                        f"{r.get('sim_set_number') if r.get('sim_set_number') is not None else '—'}"
                    )

                with mid:
                    due_str = f"Due: **{r['due_date']}**"
                    if r['overdue']:
                        st.error(f"{due_str}  (OVERDUE)")
                    else:
                        st.write(due_str)
                    st.write(f"Start: {r['start_date']}")

                with right:
                    if st.button("Mark returned", key=f"ret_{r['lease_id']}"):
                        cancel_lease(r["lease_id"])
                        st.success("Lease marked as returned.")
                        st.rerun()