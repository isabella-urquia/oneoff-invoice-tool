import streamlit as st
from api.main import create_contract, create_obligation, mark_contract_as_processed
from api.links import invoices_for_customer_and_contract_name


def one_off_invoice_chain(customer_id, contract_name, billing_term_payload, merchant_link=None, task=None):

    # try:
    contract_id = create_contract(customer_id=customer_id, contract_name=contract_name, task=task)
    # except Exception as e:
    #     st.toast(f"Error creating contract for customer {customer_id}: {e}", icon=":material/error:")
    #     raise Exception(f"Error creating contract for customer {customer_id}: {e}")
    
    try:
        obligation_id = create_obligation(payload=billing_term_payload, contract_id=contract_id, task=task)
    except Exception as e:
        st.toast(f"Error creating obligation for contract {contract_id}: {e}", icon=":material/error:")
        raise Exception(f"Error creating obligation for contract {contract_id}: {e}")
    
    try:
        results = mark_contract_as_processed(contract_id=contract_id, task=task)
    except Exception as e:
        st.toast(f"Error marking contract as processed for contract {contract_id}: {e}", icon=":material/error:")
        raise Exception(f"Error marking contract as processed for contract {contract_id}: {e}")

    if results is None:
        st.toast(f"Error marking contract as processed for contract {contract_id}, check the logs for more details", icon=":material/error:")
        raise Exception(f"Error marking contract as processed for contract {contract_id}, check the logs for more details")
    else:
        # TODO return the link to the invoice
        return invoices_for_customer_and_contract_name(customer_id, contract_name, merchant_link=merchant_link)
    

