import streamlit as st
from urllib.parse import quote


def normalize_merchant_link(merchant_link):
    """
    Normalizes merchant link to app.tabsplatform.com/merchant format.
    Removes trailing slashes and converts merchant.tabsplatform.com to app.tabsplatform.com/merchant.
    """
    if merchant_link is None:
        merchant_link = st.session_state.merchant_link
    
    # Remove trailing slash if present to avoid double slashes
    merchant_link = merchant_link.rstrip('/')
    
    # Convert merchant.tabsplatform.com to app.tabsplatform.com/merchant format
    if 'merchant.tabsplatform.com' in merchant_link:
        merchant_link = merchant_link.replace('merchant.tabsplatform.com', 'app.tabsplatform.com/merchant')
    elif 'dev.app.tabsplatform.com/merchant' in merchant_link:
        # Already in correct format for dev
        pass
    elif 'app.tabsplatform.com' not in merchant_link:
        # If it's a different format, try to construct it
        if 'dev' in merchant_link:
            merchant_link = 'https://dev.app.tabsplatform.com/merchant'
        else:
            merchant_link = 'https://app.tabsplatform.com/merchant'
    
    return merchant_link


def invoices_for_customer_and_contract_name(customer_id, contract_name, merchant_link=None):
    merchant_link = normalize_merchant_link(merchant_link)
    encoded_contract_name = quote(contract_name)
    template_link = f"{merchant_link}/customers/{customer_id}/billing/invoices?page=1&sort=issueDate&sortDir=desc&search={encoded_contract_name}"
    return template_link

def invoices_for_contract_name(contract_name, merchant_link=None):
    merchant_link = normalize_merchant_link(merchant_link)
    encoded_contract_name = quote(contract_name)
    template_link = f"{merchant_link}/billing/all?source=TABS&status=DRAFT%2CSENT%2CPAID%2CSCHEDULED%2COVERDUE%2CVOID%2CPENDING%2CDONE&page=1&sort=issueDate&sortDir=desc&search={encoded_contract_name}"
    return template_link
