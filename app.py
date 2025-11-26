import streamlit as st
from streamlit_config.config import every_page_config, background_worker
from helper.logger import print_logger

if "cycle" not in st.session_state:
    st.session_state.cycle = 0
else:
    st.session_state.cycle += 1


def prepare_pages():
    # Only show the one-off usage invoice page
    pages = {}
    pages["📦 Bulk Workflows"] = []
    pages["📦 Bulk Workflows"].append(st.Page("pages/one_off_usage_invoice.py", title="One Off Usage Invoices", icon=":material/receipt_long:"))
    return pages


every_page_config()
if "current_page" not in st.session_state:
    st.session_state.current_page = "One Off Usage Invoices"

print_logger(f"Cycle Start {st.session_state.cycle}================================================")
pages = prepare_pages()
pg = st.navigation(pages, position="top")
st.session_state.current_page = pg.title
background_worker()

pg.run()

# Reverting to default values on first run
if st.session_state.first_run:
    st.session_state.first_run = False
print_logger(f"Cycle Endng {st.session_state.cycle}================================================\n\n")

