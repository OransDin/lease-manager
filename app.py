import streamlit as st
from lease_manager.config import APP_TITLE
from lease_manager.repos.leases import due_today

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

due = due_today()
if due:
    st.info("**Due today**:\n" + "\n".join([f"- {r['sn']} — {r['customer']} (due {r['due_date']})" for r in due]))
st.write("Manage rents in the easiest way! \n Choose from menu on the left.")