import streamlit as st
import pandas as pd
import os
from helper.data_helpers import dwnload_component
from helper.matching_helpers import (
    match_customer_name_to_tabs_customer, 
    find_index_of_customer_in_cache, 
    return_options_for_customer, 
    find_most_likely_customer
)
from helper.date_functions import create_time_stamp
from api.tools import find_net_terms_for_customer, generate_template_billing_term
from api.tabs_sdk import get_revenue_categories, get_integration_items
from api.main import get_customers
import time
from datetime import datetime
from helper.task_queue import TaskQueue, Task
from api.chains import one_off_invoice_chain
from api.links import invoices_for_contract_name
from calendar import monthrange

# Constants for product name column detection
POSSIBLE_PRODUCT_NAME_COLUMNS = [
    "Rep Invoicing Invoice Type",
    "Product Name",
    "ProductName", 
    "Item Name",
    "ItemName",
    "Invoice Type",
    "InvoiceType",
    "product_name",
    "item_name"
]

def find_product_name_column(df):
    """Find the product name column in the dataframe if it exists."""
    if df is None:
        return None
    for col_name in POSSIBLE_PRODUCT_NAME_COLUMNS:
        if col_name in df.columns:
            return col_name
    return None

def get_product_name_from_row(row, df, default_name="Usage Credits"):
    """Extract product name from CSV row, falling back to default if not found."""
    product_name_column = find_product_name_column(df)
    if product_name_column:
        try:
            product_name_value = row[product_name_column]
            if pd.notna(product_name_value) and str(product_name_value).strip():
                return str(product_name_value).strip()
        except (KeyError, IndexError):
            pass
    return default_name

def get_capitalize_service_period(invoice_date):
    '''
    Gets the service period for Capitalize's "last of period" billing.
    If invoice date is the end of the month, service period is first of that month to end of that month.
    ie: Invoice date is 2026-01-31, service period is 2026-01-01 to 2026-01-31
    '''
    # Service period is always first of month to invoice date
    start_date = invoice_date.replace(day=1)
    end_date = invoice_date
    return start_date, end_date

@st.cache_data
def template_data_frame():
    # Return empty DataFrame with only column headers
    template_df = pd.DataFrame(columns=[
        "Rep Invoicing Tabs Customer Name", 
        "Rep Invoicing Tabs Customer ID",
        "Rep Invoicing Invoice Type",
        "Rep Invoicing Invoice Quantity", 
        "Rep Invoicing Invoice Value"
    ])
    return template_df

def clean_number(string_number):
    string_number = str(string_number)
    string_number = string_number.replace("$", "").replace(",", "")
    return float(string_number)

def help_blurb():
    blurb = """
    **Quick Start Guide:**
    
    1. Upload your CSV file with customer usage data
    2. Map your customer names from your file to Tabs customers, additionally specify the net terms configuration for each customer (Most Common Net Term, Smallest Net Term, Largest Net Term)
    3. Configure the invoice details, including the invoice date, product name, product description, revenue category, and integration item
    4. Create the invoices using the **Create invoices** button
    
    Use the reset button below to go back to any step.
    """
    return blurb

def app_specific_session_state(refresh_from_db=False, reset_to_step=999):
    # Check if API key and backend URL are set before making API calls
    has_api_key = st.session_state.get("tabs_api_token") is not None
    has_backend_url = st.session_state.get("backend_url") is not None
    
    if has_api_key and has_backend_url:
        if "customers" not in st.session_state or refresh_from_db:
            st.session_state.customers = get_customers(get_all=True)
        if "revenue_categories" not in st.session_state or refresh_from_db:
            st.session_state.revenue_categories = get_revenue_categories(get_all=True)
        if "integration_items" not in st.session_state or refresh_from_db:
            st.session_state.integration_items = get_integration_items(get_all=True)

        if "task_queue" not in st.session_state:
            st.session_state.task_queue = TaskQueue(api_key=st.session_state.tabs_api_token, backend_url=st.session_state.backend_url, num_workers=st.session_state.max_allowed_threads)
    else:
        # Initialize empty lists if API key not set
        if "customers" not in st.session_state:
            st.session_state.customers = []
        if "revenue_categories" not in st.session_state:
            st.session_state.revenue_categories = []
        if "integration_items" not in st.session_state:
            st.session_state.integration_items = []

    # STEP 1
    if "base_data_for_usage_one_off_invoices" not in st.session_state or reset_to_step <= 1:
        st.session_state.base_data_for_usage_one_off_invoices = None
    # STEP 2
    if "matched_customers_for_usage_one_off_invoices" not in st.session_state:
        st.session_state.matched_customers_for_usage_one_off_invoices = {}

    if "all_customers_have_net_terms" not in st.session_state or reset_to_step <= 2:
        st.session_state.all_customers_have_net_terms = False
    # STEP 3
    if "invoice_details_for_usage_one_off_invoices" not in st.session_state or reset_to_step <= 3:
        st.session_state.invoice_details_for_usage_one_off_invoices = {}
    # STEP 4
    if "invoice_generation_results" not in st.session_state or reset_to_step <= 4:
        st.session_state.invoice_generation_results = None
    # STEP 4
    if "one_off_invoice_batch_id" not in st.session_state or reset_to_step <= 4:
        st.session_state.one_off_invoice_batch_id = None
    

def calculate_app_states():
    current_step = 1
    steps = {}
    steps[1] = {"Title": "Upload your usage data", "expanded": False}
    steps[2] = {"Title": "Customer Mapping & Net Term Setup", "expanded": False}
    steps[3] = {"Title": "Configure Invoice Details", "expanded": False}
    steps[4] = {"Title": "Generate Invoice", "expanded": False}

    if st.session_state.base_data_for_usage_one_off_invoices is None:
        current_step = 1
        steps[1]["expanded"] = True
    elif st.session_state.all_customers_have_net_terms is False:
        current_step = 2
        steps[2]["expanded"] = True
    elif st.session_state.invoice_details_for_usage_one_off_invoices == {}:
        current_step = 3
        steps[3]["expanded"] = True
    elif st.session_state.invoice_generation_results is None:
        current_step = 4
        steps[4]["expanded"] = True
    else:
        current_step = 4
        steps[4]["expanded"] = True

    if current_step > 1:
        steps[1]["expanded"] = False
    if current_step > 2:
        steps[2]["expanded"] = False
    if current_step > 3:
        steps[3]["expanded"] = False


    return current_step, steps

def format_invoice_product_name(product_name, product_description):
    template_string = """{product_name}<br>
    <i style="font-size: .8em;">{product_description}</i>"""
    return template_string.format(product_name=product_name, product_description=product_description)

def generate_task_payload_for_row(row, contract_name):
    customer_name = row["Rep Invoicing Tabs Customer Name"]
    current_customer_details = st.session_state.matched_customers_for_usage_one_off_invoices[customer_name]
    customer_id = current_customer_details["customer_id"]
    net_terms = current_customer_details["net_terms"]
    
    # Use CSV column values if available, otherwise use global defaults
    invoice_config = st.session_state.invoice_details_for_usage_one_off_invoices
    
    # Get product name from CSV row or use default
    df = st.session_state.base_data_for_usage_one_off_invoices
    product_name = get_product_name_from_row(row, df, invoice_config.get("product_name", "Usage Credits"))
    
    # Description is optional - only use if provided, otherwise leave empty
    product_description = invoice_config.get("product_description", "")
    if product_description:
        product_description = product_description.strip()
    else:
        product_description = ""  # Keep empty if not provided
    
    revenue_category = invoice_config.get("revenue_category")
    integration_item = invoice_config.get("integration_item")
    start_date = invoice_config["start_date"].strftime("%Y-%m-%d")
    end_date = invoice_config["end_date"].strftime("%Y-%m-%d")

    template_payload = generate_template_billing_term()

    template_payload["serviceStartDate"] = start_date
    template_payload["serviceEndDate"] = end_date
    template_payload["categoryId"] = revenue_category
    template_payload["billingSchedule"]["name"] = product_name
    template_payload["billingSchedule"]["description"] = product_description
    template_payload["billingSchedule"]["startDate"] = start_date
    template_payload["billingSchedule"]["duration"] = 1
    template_payload["billingSchedule"]["isRecurring"] = True
    template_payload["billingSchedule"]["interval"] = "MONTH"
    template_payload["billingSchedule"]["intervalFrequency"] = 1
    template_payload["billingSchedule"]["invoiceDateStrategy"] = "LAST_OF_PERIOD"
    template_payload["billingSchedule"]["netPaymentTerms"] = net_terms
    template_payload["billingSchedule"]["quantity"] = row["Rep Invoicing Invoice Quantity"]
    template_payload["billingSchedule"]["billingType"] = "FLAT"
    template_payload["billingSchedule"]["pricingType"] = "SIMPLE"
    template_payload["billingSchedule"]["itemId"] = integration_item
    template_payload["billingSchedule"]["pricing"][0]["amount"] = row["Rep Invoicing Invoice Value"]

    task_payload = {}
    task_payload["customer_id"] = customer_id
    task_payload["contract_name"] = contract_name
    task_payload["billing_term_payload"] = template_payload
    task_payload["merchant_link"] = st.session_state.merchant_link
    return task_payload

@st.dialog("Confirm invoice details", width="large")
def confirm_invoice_details(invoice_date, product_name, product_description, revenue_category, integration_item):
    with st.container(border=True):
        customer_name = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Tabs Customer Name"].iloc[0]
        net_terms = st.session_state.matched_customers_for_usage_one_off_invoices[customer_name]["net_terms"]

        st.subheader("**Invoice preview**")
        st.caption(f"Previewing invoice for {customer_name}")

        start_date, end_date = get_capitalize_service_period(invoice_date)
        formatted_end_date = end_date.strftime("%Y-%m-%d")

        st.write(f"**Invoice date:** {invoice_date.strftime('%B %d, %Y')}")
        st.write(f"**Net terms:** {net_terms}")

        # Check for product name in CSV - look for Rep Invoicing Invoice Type column
        df = st.session_state.base_data_for_usage_one_off_invoices
        first_row = df.iloc[0]
        preview_product_name = get_product_name_from_row(first_row, df, product_name)

        # Quantity, Name+Description, Service Period, Amount
        invoice_cols_header = st.columns([1,2,2,1])
        invoice_cols_header[0].write("**Quantity**")
        invoice_cols_header[1].write("**Product**")
        invoice_cols_header[2].write("**Service Period**")
        invoice_cols_header[3].write("**Amount**")

        first_row_quantity = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Quantity"].iloc[0]
        first_row_amount = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Value"].iloc[0]

        invoice_row = st.columns([1,2,2,1])
        invoice_row[0].write(first_row_quantity)

        invoice_row[1].write(format_invoice_product_name(preview_product_name, product_description), unsafe_allow_html=True)
        invoice_row[2].write(f"*{start_date.strftime('%Y-%m-%d')}* to *{formatted_end_date}*")
        invoice_row[3].write(f"${first_row_amount:,.2f}")

        confirm_button = st.button("Confirm", icon=":material/check:", type="primary", use_container_width=True)
        if confirm_button:
            st.session_state.invoice_details_for_usage_one_off_invoices = {
                    "product_name": product_name,
                    "product_description": product_description,
                    "revenue_category": revenue_category.get("id",None) if revenue_category is not None else None,
                    "integration_item": integration_item.get("id",None) if integration_item is not None else None,
                    "start_date": start_date,
                    "end_date": end_date,
                    "invoice_date": invoice_date
                }
            st.toast("Invoice details saved", icon=":material/check:")
            time.sleep(1)
            st.rerun()


    

# Step 1
def invoice_upload_step(current_step, steps, render_object=st):
    st.info(f"""Please upload your usage data in CSV format. The file should have the following columns:

**Required columns:**
- **Customer Name** → `Rep Invoicing Tabs Customer Name`
- **Customer ID** → `Rep Invoicing Tabs Customer ID` 
- **Product Name** → `Rep Invoicing Invoice Type`
- **Quantity** → `Rep Invoicing Invoice Quantity`
- **Amount** → `Rep Invoicing Invoice Value`""", icon=":material/info:")
    uploaded_file = st.file_uploader("Upload your usage data", type=["csv"])
    file_has_been_uploaded = uploaded_file is not None
    cols = st.columns([1,1])
    set_file = cols[0].button("Set file", disabled=not file_has_been_uploaded, icon=":material/cloud_upload:", type="primary", use_container_width=True)

    template_df = template_data_frame()
    dwnload_component(template_df, "Download template", "template_data_frame.csv", icon=":material/download:", use_container_width=True, render_object=cols[1])

    if set_file:
        st.session_state.matched_customers_for_usage_one_off_invoices = {}
        st.session_state.all_customers_have_net_terms = False
        with st.spinner("Processing usage data..."):
            st.session_state.base_data_for_usage_one_off_invoices = pd.read_csv(uploaded_file)
            
            # Normalize column names (strip whitespace)
            st.session_state.base_data_for_usage_one_off_invoices.columns = st.session_state.base_data_for_usage_one_off_invoices.columns.str.strip()
            
            # Validate required columns exist
            required_cols = ["Rep Invoicing Tabs Customer Name", "Rep Invoicing Invoice Quantity", "Rep Invoicing Invoice Value"]
            missing_cols = [col for col in required_cols if col not in st.session_state.base_data_for_usage_one_off_invoices.columns]
            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}. Found columns: {', '.join(st.session_state.base_data_for_usage_one_off_invoices.columns.tolist())}")
                st.stop()
            
            st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Value"] = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Value"].apply(clean_number)
            st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Quantity"] = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Invoice Quantity"].apply(clean_number)
        with st.spinner("Matching customer names to Tabs customers..."):
            unique_customer_names = st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Tabs Customer Name"].unique()
            total_customers = len(unique_customer_names)
            total_matched_customers = 0
            
            # Check if CSV has customer IDs
            customer_id_column = "Rep Invoicing Tabs Customer ID"
            has_customer_ids = customer_id_column in st.session_state.base_data_for_usage_one_off_invoices.columns
            
            for customer_name in unique_customer_names:
                matched_customer_id = None
                
                # First, try to use customer ID from CSV if available
                if has_customer_ids:
                    customer_rows = st.session_state.base_data_for_usage_one_off_invoices[
                        st.session_state.base_data_for_usage_one_off_invoices["Rep Invoicing Tabs Customer Name"] == customer_name
                    ]
                    customer_id_from_csv = customer_rows[customer_id_column].iloc[0] if len(customer_rows) > 0 else None
                    if pd.notna(customer_id_from_csv) and str(customer_id_from_csv).strip():
                        matched_customer_id = str(customer_id_from_csv).strip()
                
                # If no customer ID in CSV, try fuzzy matching
                if not matched_customer_id:
                    matched_customer_id = match_customer_name_to_tabs_customer(
                        customer_name=customer_name, 
                        tabs_customers=st.session_state.customers,
                        match_config="FUZZY", 
                        multiple_matches_allowed=False)
                
                st.session_state.matched_customers_for_usage_one_off_invoices[customer_name] = {"customer_id": matched_customer_id}
                if matched_customer_id is not None:
                    total_matched_customers += 1
            
            if has_customer_ids:
                st.toast(f"Matched {total_matched_customers} out of {total_customers} customers using Customer IDs from CSV", icon=":material/check:")
            else:
                st.toast(f"Matched {total_matched_customers} out of {total_customers} customers", icon=":material/check:")
        st.rerun()

# Step 2
def customer_mapping_step(current_step, steps, render_object=st):
    if current_step == 2:
        total_customers = len(st.session_state.matched_customers_for_usage_one_off_invoices.keys())
        unmapped_customers_count = len([customer for customer in st.session_state.matched_customers_for_usage_one_off_invoices.keys() if st.session_state.matched_customers_for_usage_one_off_invoices[customer]["customer_id"] is None])
        mapped_customers_count = total_customers - unmapped_customers_count

        customer_mapping_progress_bar = st.progress(value=mapped_customers_count / total_customers, text=f"Mapped {mapped_customers_count} out of {total_customers} customers")
        
        header_cols = st.columns([1,1,1])

        with header_cols[0].popover("Customer Display", icon=":material/person:", use_container_width=True, help="Choose to display mapped or unmapped customers"):
            customer_options = st.segmented_control("Customer options", options=["Mapped", "Unmapped"], default="Unmapped", label_visibility="collapsed", selection_mode="multi", width="stretch")

        with header_cols[1].popover("Matching Logic", icon=":material/all_match:", use_container_width=True, help="Choose to use fuzzy matching to find customers"):
            use_fuzzy_matching = st.toggle("Enable Fuzzy Matching", value=True)
            fuzzy_matching_threshold = st.slider("Fuzzy Matching Threshold", min_value=0.0, max_value=1.0, value=0.9, step=0.01, help="The threshold to use for fuzzy matching. 0.0 is no match, 1.0 is a perfect match.")

        with header_cols[2].popover("Net Term Mode", icon=":material/calendar_month:", use_container_width=True, help="Choose the mode to use for the net terms"):
            net_term_mode = st.segmented_control("Net term mode", options=["Most Common Net Term", "Smallest Net Term", "Largest Net Term"], width="stretch", label_visibility="collapsed", default="Most Common Net Term")

        all_options_for_mapping = st.session_state.customers
        show_mapped_customers = "Mapped" in customer_options
        show_unmapped_customers = "Unmapped" in customer_options
        

        for key in st.session_state.matched_customers_for_usage_one_off_invoices.keys():
            
            mapped = st.session_state.matched_customers_for_usage_one_off_invoices[key]["customer_id"] is not None
            map_customer_button = None
            if mapped and show_mapped_customers:
                cols = st.columns([1,2,1])
                cols[0].write(f"**{key}** maps to ")
                current_customer_id = st.session_state.matched_customers_for_usage_one_off_invoices[key]["customer_id"]
                current_index = find_index_of_customer_in_cache(current_customer_id, st.session_state.customers)
                mapped_customer = cols[1].selectbox(f"Map {key} to", options=all_options_for_mapping, format_func=lambda x: x["name"], index=current_index, label_visibility="collapsed")
                map_customer_button = cols[2].button("Update Mapping", icon=":material/frame_reload:", type="secondary", key=f"map_customer_button_{key}", use_container_width=True)
            elif not mapped and show_unmapped_customers:
                cols = st.columns([1,2,1])
                cols[0].write(f"**{key}** maps to")
                if use_fuzzy_matching:
                    options_for_mapping = return_options_for_customer(key, all_options_for_mapping, threshold=fuzzy_matching_threshold)
                    most_likely_customer = find_most_likely_customer(key, options_for_mapping)
                    index_of_most_likely_customer = find_index_of_customer_in_cache(most_likely_customer["id"], options_for_mapping)
                else:
                    options_for_mapping = all_options_for_mapping
                    index_of_most_likely_customer = 0
                mapped_customer = cols[1].selectbox(f"Map {key} to", options=options_for_mapping, format_func=lambda x: x["name"], label_visibility="collapsed", index=index_of_most_likely_customer)
                map_customer_button = cols[2].button("Map customer", icon=":material/sync_alt:", type="primary", key=f"map_customer_button_{key}", use_container_width=True)

            if map_customer_button:
                st.session_state.matched_customers_for_usage_one_off_invoices[key]["customer_id"] = mapped_customer["id"]
                st.rerun()

        ready_to_map_net_terms = unmapped_customers_count == 0
        map_net_terms_button = st.button("Map net terms", disabled=not ready_to_map_net_terms, icon=":material/map_search:", type="primary")
        if map_net_terms_button:
            with st.spinner("Pulling net terms dynamically from Tabs, please wait on the page and do not refresh the page, feel free keep the page open and come back later"):
                total_customers = len(st.session_state.matched_customers_for_usage_one_off_invoices.keys())
                net_terms_extracted_count = 0
                net_term_progress_bar = st.progress(value=net_terms_extracted_count / total_customers, text=f"Mapping net terms for {net_terms_extracted_count} out of {total_customers} customers")
                for customer_name in st.session_state.matched_customers_for_usage_one_off_invoices.keys():
                    customer_id = st.session_state.matched_customers_for_usage_one_off_invoices[customer_name]["customer_id"]
                    match net_term_mode:
                        case "Most Common Net Term":
                            mode = "MODE"
                        case "Smallest Net Term":
                            mode = "MIN"
                        case "Largest Net Term":
                            mode = "MAX"
                    net_terms = find_net_terms_for_customer(customer_id=customer_id, mode=mode)
                    st.session_state.matched_customers_for_usage_one_off_invoices[customer_name]["net_terms"] = net_terms
                    net_terms_extracted_count += 1
                    net_term_progress_bar.progress(value=net_terms_extracted_count / total_customers, text=f"Mapping net terms for {net_terms_extracted_count} out of {total_customers} customers")
            st.toast("Net terms mapped", icon=":material/check:")
            st.session_state.all_customers_have_net_terms = True
            time.sleep(1)
            st.rerun()

# Step 3
def invoice_configuration_step(current_step, steps, render_object=st):
    if current_step >= 3:

        if current_step > 3:
            locked = True
            st.info("Invoice details are locked in once you have saved them, if you need to change them, please reset this step using the controls at the top of the page", icon=":material/info:")
        else:
            locked = False

        st.write("Configure your invoices here")

        config_cols = st.columns(2)
        invoice_date = config_cols[0].date_input("Invoice date", value=datetime.now(), format="YYYY-MM-DD", disabled=locked)
        
        # Check if CSV has product name column
        df = st.session_state.base_data_for_usage_one_off_invoices
        product_name_column = find_product_name_column(df)
        
        if product_name_column:
            st.info(f"**Product names will come from your CSV** - Each row will use the value from the '{product_name_column}' column as the product/item name.", icon=":material/info:")
            
            # Show unique product names from CSV
            unique_types = df[product_name_column].unique() if df is not None else []
            if len(unique_types) > 0:
                with st.expander(f"Preview: {len(unique_types)} unique product types from CSV", expanded=False):
                    for inv_type in sorted(unique_types):
                        if pd.notna(inv_type):
                            count = len(df[df[product_name_column] == inv_type])
                            st.write(f"• **{inv_type}** ({count} line item{'s' if count != 1 else ''})")
            
            # Product name is not needed since it comes from CSV, but keep for fallback
            config_cols = st.columns(2)
            product_name = config_cols[0].text_input(
                "Default Product Name (fallback)", 
                value="Usage Credits", 
                icon=":material/credit_card:", 
                disabled=locked, 
                help=f"Only used if a row in CSV doesn't have a value in the '{product_name_column}' column"
            )
        else:
            config_cols = st.columns(2)
            product_name = config_cols[0].text_input("Product name", value="Usage Credits", icon=":material/credit_card:", disabled=locked)
        
        product_description = config_cols[1].text_input("Product description (Optional)", value="", icon=":material/subtitles:", disabled=locked, help="Optional description for the product/service. Leave empty if not needed.")
        integration_item = config_cols[1].selectbox("Integration item", format_func=lambda x: x["name"], options=st.session_state.integration_items, disabled=locked)
        revenue_category = config_cols[0].selectbox("Revenue category", format_func=lambda x: x["name"], options=st.session_state.revenue_categories, disabled=locked)
        

        save_invoice_details_button = st.button("Save invoice details", icon=":material/clarify:", type="primary", use_container_width=True, disabled=locked)
        if save_invoice_details_button:
            confirm_invoice_details(
                invoice_date=invoice_date, 
                product_name=product_name, 
                product_description=product_description, 
                revenue_category=revenue_category, 
                integration_item=integration_item)

# Step 4
def generate_invoice_step(current_step, steps, render_object=st):
    if current_step == 4:
        # Check if invoices are already completed (not just started)
        invoices_already_generated = False
        if st.session_state.one_off_invoice_batch_id is not None:
            batch_stats = st.session_state.task_queue.get_batch_stats(st.session_state.one_off_invoice_batch_id)
            total = batch_stats.get("total", 0)
            completed = batch_stats.get("completed", 0)
            failed = batch_stats.get("failed", 0)
            all_done = (completed + failed) == total and total > 0
            invoices_already_generated = all_done and st.session_state.invoice_generation_results is not None
        elif st.session_state.invoice_generation_results is not None:
            invoices_already_generated = True
        
        invoice_details = st.session_state.invoice_details_for_usage_one_off_invoices
        st.write("Configure the contract name and create the invoices")
        cols = st.columns([3,1])
        contract_name = cols[0].text_input("Contract name", value=f"Usage Credits for {invoice_details.get('invoice_date', None).strftime('%B %Y')}", label_visibility="collapsed")
        create_invoice_button = cols[1].button("Create invoices", icon=":material/rocket_launch:", type="primary", use_container_width=True, disabled=invoices_already_generated)


        if create_invoice_button:
            st.session_state.task_queue = TaskQueue(api_key=st.session_state.tabs_api_token, backend_url=st.session_state.backend_url, num_workers=st.session_state.max_allowed_threads)
            st.session_state.one_off_invoice_batch_id = f"bulk_action_WORKFLOW_CREATE_INVOICES_{create_time_stamp()}"
            copy_of_base_data_for_usage_one_off_invoices = st.session_state.base_data_for_usage_one_off_invoices.copy()
            st.session_state.invoice_generation_results = copy_of_base_data_for_usage_one_off_invoices
            for index, row in st.session_state.base_data_for_usage_one_off_invoices.iterrows():
                task_payload = generate_task_payload_for_row(row, contract_name)
                st.session_state.task_queue.add_task(
                    function=one_off_invoice_chain,
                    args=task_payload,
                    batch_id=st.session_state.one_off_invoice_batch_id,
                    throttle_time=1
                )
            st.session_state.task_queue.start_processing()
            st.session_state.tabs_icon = "🚧"
            st.rerun()


        # Show progress if invoices are being generated
        if st.session_state.one_off_invoice_batch_id is not None:
            batch_stats = st.session_state.task_queue.get_batch_stats(st.session_state.one_off_invoice_batch_id)
            total = batch_stats.get("total", 0)
            completed = batch_stats.get("completed", 0)
            failed = batch_stats.get("failed", 0)
            pending = batch_stats.get("pending", 0)
            running = batch_stats.get("running", 0)
            
            # Check if all tasks are done
            is_processing = st.session_state.task_queue.processing
            all_done = (completed + failed) == total and total > 0
            
            # Show simple progress bar
            progress_value = (completed + failed) / total if total > 0 else 0
            progress_text = f"{completed + failed}/{total} invoices processed"
            
            st.progress(progress_value, text=progress_text)
            
            # Show completion message when done
            if all_done:
                if failed == 0:
                    st.success(f"✅ **All {completed} invoice(s) generated successfully!**", icon=":material/check_circle:")
                else:
                    st.warning(f"⚠️ **Completed:** {completed} succeeded, {failed} failed", icon=":material/warning:")
            
            # Get results and update session state
            results = st.session_state.task_queue.get_batch_results(st.session_state.one_off_invoice_batch_id)
            if results and len(results) > 0:
                st.session_state.invoice_generation_results["Invoice Link"] = results
            
            # Update completion status
            invoices_already_generated = all_done

        if invoices_already_generated:
            invoice_link = invoices_for_contract_name(contract_name)
            st.link_button(label="View invoices", url=invoice_link, icon=":material/link:", type="secondary", use_container_width=True)
            st.write("**Invoice generation results**")
            dataframe = st.session_state.invoice_generation_results
            st.write(dataframe)
            dwnload_component(
                df=dataframe, 
                label="Download invoice generation results", 
                file_name="invoice_generation_results", 
                type="secondary",
                icon=":material/download:", use_container_width=True, render_object=st)

        else:
            st.info("Please create the invoices first using the **Create invoices** button", icon=":material/info:")



def usage_one_off_invoices_page():
    
    # Initialize session state first
    app_specific_session_state(refresh_from_db=False)
    
    # Check if API key is configured
    has_api_key = st.session_state.get("tabs_api_token") is not None
    has_backend_url = st.session_state.get("backend_url") is not None
    
    if not has_api_key or not has_backend_url:
        st.error("⚠️ **API Configuration Required**", icon=":material/error:")
        st.info("""
        Please configure your API key to use this page:
        
        1. **Option 1**: Set in `.env` file:
           - `DEFAULT_TABS_API_KEY="your_api_key"`
           - `DEFAULT_MERCHANT_NAME="Your Merchant Name"`
           - `DEFAULT_ENVIRONMENT="prod"` (or "dev")
        
        2. **Option 2**: Use Developer Settings in the sidebar to set your API token manually.
        """, icon=":material/info:")
        st.stop()
    
    # Calculate current step and steps
    current_step, steps = calculate_app_states()

    # Custom CSS for logo alignment and progress bar
    st.markdown("""
    <style>
        .logo-title-wrapper {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 1rem;
        }
        .logo-title-wrapper img {
            margin: 0;
            padding: 0;
            border-radius: 8px;
        }
        .stProgress > div > div > div > div {
            background-color: #1976d2;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display logo and title side by side
    # Default to Capitalize logo if FALL_BACK_LOGO is not set
    capitalize_logo_url = "https://media.licdn.com/dms/image/v2/C4E0BAQGLQa71dANC4A/company-logo_200_200/company-logo_200_200/0/1664205665099/capitalize_logo?e=2147483647&v=beta&t=jo_HCFILbmPtoAtGUVdGPe7oTn-nL5AEe3EmD2Tezfo"
    # Try Streamlit secrets first (for Cloud), then environment variable (for local)
    try:
        if hasattr(st, 'secrets') and "FALL_BACK_LOGO" in st.secrets:
            logo_url = st.secrets["FALL_BACK_LOGO"]
        else:
            logo_url = os.getenv("FALL_BACK_LOGO", capitalize_logo_url)
    except:
        logo_url = os.getenv("FALL_BACK_LOGO", capitalize_logo_url)
    if logo_url:
        st.markdown(f'''
        <div class="logo-title-wrapper">
            <img src="{logo_url}" width="70" style="vertical-align: middle; border-radius: 8px;">
            <h1 style="margin: 0; padding: 0;">Usage One Off Invoices</h1>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.title("Usage One Off Invoices")
    
    # Step progress bar
    step_progress = current_step / 4
    st.progress(step_progress, text=f"Step {current_step} of 4")
    
    # Step indicators
    step_indicator_cols = st.columns(4)
    step_names = ["Upload Usage Data", "Customer Mapping & Net Term Setup", "Configure Invoice Details", "Generate Invoices"]
    for i, (col, step_name) in enumerate(zip(step_indicator_cols, step_names), 1):
        with col:
            if i < current_step:
                st.success(f"✅ Step {i}: {step_name}")
            elif i == current_step:
                st.info(f"Step {i}: {step_name}")
            else:
                st.write(f"Step {i}: {step_name}")
    
    st.divider()
    
    # Help & Controls in sidebar
    st.sidebar.markdown("### Help & Controls")
    st.sidebar.markdown(help_blurb())
    st.sidebar.divider()
    st.sidebar.markdown("**Controls**")
    reset_to_step_selector = st.sidebar.radio("Reset to step", options=[1,2,3,4], label_visibility="collapsed")
    reset_to_step_button = st.sidebar.button("Reset", icon=":material/refresh:", type="secondary", use_container_width=True)

    if reset_to_step_button:
        app_specific_session_state(reset_to_step=reset_to_step_selector)
        st.rerun()

    refresh_from_db = st.sidebar.button("Refresh Data", icon=":material/refresh:", type="secondary", use_container_width=True)
    if refresh_from_db:
        app_specific_session_state(refresh_from_db=True)
        st.rerun()


    if current_step == 1:
        invoice_upload_step(current_step, steps)
    if current_step == 2:
        customer_mapping_step(current_step, steps)
    if current_step == 3:
        invoice_configuration_step(current_step, steps)
    if current_step == 4:
        # Auto-refresh invoice generation step every 2 seconds while processing
        @st.fragment(run_every=2)
        def auto_refresh_invoice_step():
            generate_invoice_step(current_step, steps)
        
        # Only use auto-refresh if invoices are being generated
        if (st.session_state.one_off_invoice_batch_id is not None and 
            st.session_state.task_queue.processing):
            auto_refresh_invoice_step()
        else:
            generate_invoice_step(current_step, steps)



usage_one_off_invoices_page()

