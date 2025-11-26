import streamlit as st
import requests
import math
from datetime import datetime
import pandas as pd
from urllib.parse import quote
import json
import time
import hashlib
import re
from helper.logger import print_logger
import random
### UTILITIES FUNCTIONS ###

def get_generate_hash(timestamp, random_string=None):
    return hashlib.sha256(f"{timestamp}".encode()).hexdigest()

def test_generate_hash():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = get_generate_hash(timestamp)
    return result

def generate_request_log(method, backend_url, endpoint, payload, response, batch_id=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    more_precise_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    random_string = str(random.randint(1, 1000000))
    hash_i = get_generate_hash(more_precise_timestamp, random_string)
    return {
        "method": method,
        "backend_url": backend_url,
        "endpoint": endpoint,
        "payload": payload,
        "response": response,
        "timestamp": timestamp,
        "hash": hash_i,
        "batch_id": batch_id
    }

def dummy_data(dummy, dummy2=None, task=None):
    print_logger("we fired the dummy data function")
    result = make_get_request(endpoint="/health", task=task)
    log = generate_request_log("GET", task.backend_url, "/health", {}, result, task.batch_id)
    task.request_log = log
    return dummy

def non_blank_or_nan(value):
    return value is not None and value != "" and not pd.isna(value)

def check_valid_token(token):
    endpoint = "/v3/customers?limit=1"
    response = make_get_request(endpoint)
    valid = check_success(response)
    if valid is None:
        return False
    else:
        return True

def is_rate_limited(response):
    try:
        response_status_code = response.status_code
        if response_status_code == 429:
            return True
        else:
            return False
    except:
        return False

def generalized_make_request(endpoint, method, payload=None, files=None, params=None, task=None, attempts=0):
    if attempts > 30:
        raise ValueError("Max attempts reached (30), request failed")
    print_logger("Making", method, "request to", endpoint)
    if task is None:
        backend_url = st.session_state.backend_url
        api_key = st.session_state.tabs_api_token
        using_session_state = True
        batch_id = "One Off Request"
    else:
        backend_url = task.backend_url
        api_key = task.api_key
        using_session_state = False
        batch_id = task.batch_id
    if backend_url is None or api_key is None:
        raise ValueError("Backend URL or API key is None")
    final_url = f"{backend_url}{endpoint}"
    headers = {"Authorization": f"{api_key}"}
    match method:
        case "GET":
            response = requests.get(final_url, headers=headers, params=params)
        case "POST":
            response = requests.post(final_url, headers=headers, json=payload, files=files)
        case "PUT":
            response = requests.put(final_url, headers=headers, json=payload)
        case "DELETE":
            response = requests.delete(final_url, headers=headers)
        case "PATCH":
            response = requests.patch(final_url, headers=headers, json=payload)
        case _:
            raise ValueError(f"Invalid method: {method}")
    request_log = generate_request_log(method, backend_url, endpoint, payload, response, batch_id)
    if using_session_state:
        st.toast(f"{method} Request to {endpoint} returned {response.status_code}")
        st.session_state.request_history.append(request_log)
    else:
        task.request_logs.append(request_log)
    if is_rate_limited(response):
        print_logger("Rate limited response received, backing off for 1 second and retrying")
        attempts += 1
        print_logger("Attempting to make request again in", attempts, "seconds")
        time.sleep(attempts) # Linear backoff
        return generalized_make_request(endpoint, method, payload, files, params, task, attempts)
    else:
        return response

def make_post_request(endpoint, payload=None, merchant_id=None, files=None, task=None):
    return generalized_make_request(endpoint, "POST", payload=payload, files=files, task=task)

def make_patch_request(endpoint, payload=None, merchant_id=None, task=None):
    return generalized_make_request(endpoint, "PATCH", payload=payload, task=task)

def make_get_request(endpoint, payload=None, merchant_id=None, task=None):
    return generalized_make_request(endpoint, "GET", payload=payload, task=task)

def make_put_request(endpoint, payload=None, merchant_id=None, task=None):
    return generalized_make_request(endpoint, "PUT", payload=payload, task=task)

def make_delete_request(endpoint, task=None):
    return generalized_make_request(endpoint, "DELETE", task=task)

def check_success(response):
    results = dict(response.json())
    if results.get("success") == False:
        st.error(f"Error: {results.get('message')}")
        return None
    elif results.get("success") == True:
        return results
    
def make_link_to_contract(contract_id):
    return f"{st.session_state.garage_link}/contracts/{contract_id}/terms/revenue"

def make_link_for_contracts_for_customer(customer_id):
    return f"{st.session_state.garage_link}/contracts?search={customer_id}"

def make_merchant_app_link_for_documents(customer_id):
    url = f"/customers/{customer_id}/obligations/documents"
    return f"{st.session_state.merchant_link}{url}"

def make_merchant_app_link_for_products(customer_id):
    url = f"/customers/{customer_id}/products"
    return f"{st.session_state.merchant_link}{url}"

def make_merchant_app_link_for_customer_info(customer_id):
    url = f"/customers/{customer_id}/profile/customer-info"
    return f"{st.session_state.merchant_link}{url}"

def make_merchant_app_link_for_additional_fields(customer_id):
    url = f"/customers/{customer_id}/profile/additional-fields"
    return f"{st.session_state.merchant_link}{url}"

def make_garage_link_for_contracts(customer_id):
    return f"{st.session_state.garage_link}/contracts?search={customer_id}"

# ===============================================

### FORMAL API CALLS ###

def create_customer(company_name, primary_biilling_contact_email=None, default_currency="USD",legal_name=None, task=None):
    """
    Create a new customer in the system.

    Args:
        company_name (str): The name of the company to create as a customer.
        primary_biilling_contact_email (str, optional): The primary billing contact's email address for the customer. 
            If not provided, the customer will be created without a billing contact email.

    Returns:
        bool or None: Returns True if the customer was created successfully, 
            or None if the creation failed (e.g., due to an API error or invalid input).
    """
    payload = {}
    payload["name"] = company_name
    if primary_biilling_contact_email and primary_biilling_contact_email != "":
        payload["primaryBillingContactEmail"] = primary_biilling_contact_email
    payload["defaultCurrency"] = default_currency
    if legal_name:
        payload["companyName"] = legal_name
    endpoint = "/v3/customers"
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def create_contract(customer_id, contract_name, external_id=None, external_id_source_type=None, close_date=None, task=None):
    payload = {}
    payload["customerId"] = customer_id
    payload["name"] = contract_name
    if external_id is not None or external_id_source_type is not None:
        # Validate both are not None
        if external_id is None or external_id_source_type is None:
            raise ValueError("External ID and Source Type must both be provided")
        if external_id_source_type not in ["QUICKBOOKS", "ORDERTIME", "NETSUITE", "SALESFORCE", "HUBSPOT", "BACKEND", "AVALARA", "ORUM", "ANROK", "STRIPE", "RILLET"]:
            raise ValueError(f"Invalid external_id_source_type: {external_id_source_type}. Must be one of: QUICKBOOKS, ORDERTIME, NETSUITE, SALESFORCE, HUBSPOT, BACKEND, AVALARA, ORUM, ANROK, STRIPE, RILLET")
        
        payload["externalId"] = {
            "externalId": external_id,
            "sourceType": external_id_source_type
        }
    
    if close_date:
        # Validate closeDate is of format YYYY-MM-DD
        if not isinstance(close_date, str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', close_date):
            raise ValueError("closeDate must be a string in the format YYYY-MM-DD")
        payload["closeDate"] = close_date

    endpoint = "/v3/contracts"
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload", {}).get("id","ID NOT FOUND")

def get_customers(limit=500, filter=None, get_all=False, task=None):
    """
    Get all customers with optional filtering, handling pagination automatically.
    
    Args:
        limit (int): Number of records per page (default: 500)
        filter (str): Optional filter string to search customers by name
        
    Returns:
        list: Complete list of customers across all pages
    """
    all_customers = []
    page = 1
    
    # Make initial request to get first page and total items
    endpoint = f"/v3/customers?limit={limit}&page={page}"
    if filter:
        filter = filter.replace(",", "")
        endpoint += f'&filter=name:like:"{filter}"'
    
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    
    if results is None:
        return []
    
    payload = results.get("payload", {})
    total_items = payload.get("totalItems", 0)
    all_customers.extend(payload.get("data", []))
    
    # Calculate total pages needed using ceiling division
    total_pages = math.ceil(total_items / limit)
    
    if get_all:
        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            endpoint = f"/v3/customers?limit={limit}&page={page}"
            if filter:
                endpoint += f'&filter=name:like:"{filter}"'
            
            response = make_get_request(endpoint=endpoint, task=task)
            results = check_success(response)
            
            if results is None:
                break
                
            page_data = results.get("payload", {}).get("data", [])
            all_customers.extend(page_data)
    
    return all_customers

def get_customer_by_id(customer_id, task=None):
    endpoint = f"/v3/customers/{customer_id}"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload",{})

def get_all_contracts(task=None,get_all=False):
    endpoint = f"/v3/contracts?limit=50000"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload",{}).get("data",[])

# NOTE: THIS IS A FAKE ENDPOINT, IT GETS ALL CONTRACTS FROM THE SESSION STATE, FILTERS VIA PANDAS
def get_contracts(
    customer_id: str | None = None,
    file_name: str | None = None,
    name: str | None = None,
    status: str | None = None,
    customer_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    ) -> pd.DataFrame:
    """Get contracts with flexible filtering options.
    
    This function filters contracts based on various criteria including customer information,
    contract details, and date ranges. All string-based filters are case-insensitive.
    
    Args:
        customer_id (str | None): Filter by customer ID (uses exact match)
        file_name (str | None): Filter by contract file name (case-insensitive)
        name (str | None): Filter by contract display name (case-insensitive)
        status (str | None): Filter by contract status. Must be one of: 
            DELETED, PROCESSED, APPROVED, NEW, IN_PROGRESS
        customer_name (str | None): Filter by customer name (case-insensitive)
        start_date (str | None): Filter by contract start date in format YYYY-MM-DD
        end_date (str | None): Filter by contract end date in format YYYY-MM-DD
        
    Returns:
        pd.DataFrame: Filtered DataFrame containing contract information
        
    Raises:
        ValueError: If status is provided but not one of the valid values
        ValueError: If start_date or end_date is provided in incorrect format
    """
    # Validate status if provided
    VALID_STATUSES = {"DELETED", "PROCESSED", "APPROVED", "NEW", "IN_PROGRESS"}
    if status is not None and status.upper() not in VALID_STATUSES:
        raise ValueError(f"Invalid status value. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
    
    # Get base dataframe from session state
    base_dataframe = st.session_state.contracts.copy()
    
    # Convert date columns to datetime
    base_dataframe["createdAt"] = pd.to_datetime(base_dataframe["createdAt"])
    base_dataframe["lastUpdatedAt"] = pd.to_datetime(base_dataframe["lastUpdatedAt"])
    
    # Date filtering
    try:
        if start_date:
            start_date = pd.to_datetime(start_date)
            base_dataframe = base_dataframe[base_dataframe["createdAt"] >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date)
            base_dataframe = base_dataframe[base_dataframe["createdAt"] <= end_date]
    except ValueError as e:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD format") from e
    
    # Apply filters
    if customer_id:
        base_dataframe = base_dataframe[base_dataframe["customerId"] == customer_id]
    if file_name:
        base_dataframe = base_dataframe[base_dataframe["fileName"].str.lower() == file_name.lower()]
    if name:
        base_dataframe = base_dataframe[base_dataframe["name"].str.lower().str.contains(name.lower())]
    if status:
        base_dataframe = base_dataframe[base_dataframe["status"] == status.upper()]
    if customer_name:
        base_dataframe = base_dataframe[base_dataframe["customerName"].str.lower().str.contains(customer_name.lower())]
    
    # Convert datetime columns to ISO format strings
    base_dataframe["createdAt"] = base_dataframe["createdAt"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    base_dataframe["lastUpdatedAt"] = base_dataframe["lastUpdatedAt"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # return dataframe as a list of dicts
    return base_dataframe.to_dict(orient="records")
    
def get_contract_by_id(contract_id, task=None):
    """
    Get a specific contract by its ID.
    
    Args:
        contract_id (str): The ID of the contract to retrieve
        
    Returns:
        dict: Contract details if found and request successful, None otherwise
    """
    endpoint = f"/v3/contracts/{contract_id}"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload", {})

def get_event_types(limit=500, filter=None, task=None):
    """
    Get event types with optional filtering.
    
    Args:
        limit (int): Maximum number of records to return
        filter (str): Filter by event type name
        
    Returns:
        list: List of event types if request successful, empty list otherwise
    """
    endpoint = f"/v3/events/types?limit={limit}"
    if filter:
        filter = filter.replace(",", "")
        endpoint += f"&filter=name:like:{filter}"
        
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        return results.get("payload", {}).get("data", [])

def get_obligations(contract_id, task=None):
    """
    Get billing terms (obligations) for a specific contract.
    Billing terms define the payment and billing conditions associated with a contract.
    
    Args:
        contract_id (str): The ID of the contract to get billing terms for
        
    Returns:
        list: List of billing terms if request successful, empty list otherwise
    """
    endpoint = f"/v3/contracts/{contract_id}/obligations?limit=500"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        return results.get("payload", {}).get("data", [])
    
def get_contract_obligations(contract_id=None, customer_id=None, obligation_name=None, customer_name=None, task=None, get_all=False, limit=500):
    """
    Get obligations (billing terms) with flexible filtering options.
    
    Args:
        contract_id (str, optional): Filter by contract ID
        customer_id (str, optional): Filter by customer ID
        obligation_name (str, optional): Filter by obligation name
        customer_name (str, optional): Filter by customer name
        
    Returns:
        list: List of obligations if request successful, empty list otherwise
    """
    endpoint = f"/v3/obligations?limit={limit}"
    filters = []
    
    if contract_id:
        filters.append(f'contractId:eq:"{contract_id}"')
    if customer_id:
        filters.append(f'customerId:eq:"{customer_id}"')
    if obligation_name:
        filters.append(f'name:eq:"{obligation_name}"')
    if customer_name:
        filters.append(f'customerName:eq:"{customer_name}"')
        
    if filters:
        endpoint += f"&filter={'+'.join(filters)}"
        
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        if get_all:
            all_obligations = results.get("payload", {}).get("data", [])
            total_items = results.get("payload", {}).get("totalItems", 0)
            for page in range(2, math.ceil(total_items / limit) + 1):
                endpoint = f"/v3/obligations?limit={limit}&page={page}&filter={'+'.join(filters)}"
                response = make_get_request(endpoint=endpoint, task=task)
                results = check_success(response)
                if results is None:
                    break
                fetched_objects = results.get("payload", {}).get("data", [])
                all_obligations.extend(fetched_objects)
            return all_obligations
        else:
            return results.get("payload", {}).get("data", [])

def get_revenue_categories(name=None,get_all=False, task=None):
    endpoint = "/v3/categories"
    if name:
        endpoint += f"?filter=name:like:{name}"
    if get_all:
        endpoint += f"?limit=50000"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        return results.get("payload", {}).get("data", [])
    
def create_revenue_category(name, task=None):
    endpoint = "/v3/categories"
    payload = {}
    payload["name"] = name
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload", {})

def bulk_upload_billing_schedule(files,merchant_name, task=None):
    endpoint = f"/v16/secrets/merchant/{merchant_name}/bulk-create-billing-schedules"
    response = make_post_request(endpoint=endpoint, files=files, task=task)
    results = dict(response.json())
    if response.status_code == 201:
        return results.get("billingTermIds", [])
    else:
        return []
    
def update_billing_terms(files, merchant_name, task=None):
    endpoint = f"v16/secrets/merchant/{merchant_name}/bulk-update-billing-schedules"
    response = make_post_request(endpoint=endpoint, files=files, task=task)
    results = dict(response.json())
    if response.status_code == 201:
        return True
    else:
        return False

def mark_invoice_to_sent_off_tabs(customer_id, invoice_id, task=None):
    endpoint = f"/v3/customers/{customer_id}/invoices/{invoice_id}/actions"
    payload = {}
    payload["action"] = "MARK_INVOICE_TO_SENT_OFF_TABS"
    payload["markInvoiceToSentOffTabs"] = True
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def create_event_type(name, task=None):
    endpoint = "/v3/events/types"
    payload = {}
    payload["name"] = str(name)
    print_logger("DEBUG JEAN 4")
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    print_logger(response)
    print_logger("DEBUG JEAN 5")
    if response.status_code == 201:
        return True
    elif response.status_code == 400:
        return None
    else:
        return None

def mark_contract_as_processed(contract_id, task=None):
    endpoint = f"/v3/contracts/{contract_id}/actions"
    payload = {}
    payload["action"] = "MARK_AS_PROCESSED"
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def mark_contract_as_deleted(contract_id, task=None):
    endpoint = f"/v3/contracts/{contract_id}/actions"
    payload = {}
    payload["action"] = "MARK_AS_DELETED"
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def get_all_items(task=None, get_all=False):
    endpoint = "/v3/items?limit=50000"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        return results.get("payload", {}).get("data", [])
        
def get_all_event_types(task=None, get_all=False):
    endpoint = "/v3/events/types?limit=50000"
    response = make_get_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return []
    else:
        return results.get("payload", {}).get("data", [])

def create_obligation(payload, contract_id, task=None):
    endpoint = f"/v3/contracts/{contract_id}/obligations"
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload", {}).get("id", None)
    
def update_obligation(
        contract_id, 
        obligation_id, 
        name=None, 
        description=None, 
        itemId=None, 
        classId=None, 
        categoryId=None, 
        eventTypeId=None, 
        price=None, 
        netPaymentTerms=None, 
        regenerateInvoices=False, 
        useNewEndpoint=False, 
        billingStartDate=None,
        billingFrequency=None,
        billingFrequencyUnit=None,
        totalNumberOfInvoices=None,
        revenueStartDate=None,
        revenueEndDate=None,
        invoiceDateStrategy=None,
        discount_type=None,
        discount_value=None,
        discount_name=None,
        task=None):
    
    if useNewEndpoint:
        endpoint = f"/v3.1.0/contracts/{contract_id}/obligation/{obligation_id}"
    else:
        endpoint = f"/v3/contracts/{contract_id}/obligation/{obligation_id}" # This is the old endpoint
    
    # WE ARE DEPRACTING THE v3.1.0 ENDPOINT
    endpoint = f"/v3/contracts/{contract_id}/obligation/{obligation_id}"




    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if itemId:
        payload["itemId"] = itemId
    if classId:
        payload["classId"] = classId
    if categoryId:
        payload["categoryId"] = categoryId
    if price or price == 0 or price == "0":
        payload["price"] = make_number(price, turn_back_to_string=True)
    if netPaymentTerms:
        payload["netPaymentTerms"] = int(netPaymentTerms)
    if eventTypeId:
        payload["eventTypeId"] = eventTypeId
    if regenerateInvoices:
        payload["regenerateInvoices"] = regenerateInvoices
    if billingStartDate:
        payload["billingStartDate"] = billingStartDate
    if billingFrequency:
        payload["billingFrequency"] = int(billingFrequency)
    if billingFrequencyUnit:
        payload["billingFrequencyUnit"] = billingFrequencyUnit
    if totalNumberOfInvoices:
        payload["totalNumberOfInvoices"] = int(totalNumberOfInvoices)
    if revenueStartDate:
        payload["revenueStartDate"] = revenueStartDate
    if revenueEndDate:
        payload["revenueEndDate"] = revenueEndDate
    if invoiceDateStrategy:
        if invoiceDateStrategy not in ["FIRST_OF_PERIOD", "ADVANCED_DUE_START", "ARREARS", "LAST_OF_PERIOD", "ARREARS"]:
            raise ValueError(f"Invalid invoice date strategy: {invoiceDateStrategy}. Must be one of: FIRST_OF_PERIOD, ADVANCED_DUE_START, ARREARS, LAST_OF_PERIOD, ARREARS")
        payload["invoiceDateStrategy"] = str(invoiceDateStrategy)
    if discount_type or discount_value or discount_name:
        if non_blank_or_nan(discount_type) and non_blank_or_nan(discount_value) and non_blank_or_nan(discount_name):
            if discount_type not in ["FIXED", "PERCENTAGE"]:
                raise ValueError(f"Invalid discount type: {discount_type}. Must be one of: FIXED, PERCENTAGE")
            payload["discount"] = {
                "type": discount_type,
                "amount": make_number(discount_value, turn_back_to_string=True),
                "note": discount_name
            }
        else:
            raise ValueError("Discount type, value, and name must all be provided to update the discount")
    

    response = make_patch_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True

def create_contacts(customer_id, email, first_name=None, last_name=None, task=None):
    endpoint = f"/v3/customers/{customer_id}/contacts"
    payload = {}
    payload["email"] = email
    if first_name:
        payload["firstName"] = first_name
    if last_name:
        payload["lastName"] = last_name
    final_payload = [payload]
    response = make_post_request(endpoint=endpoint, payload=final_payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("payload", [{}])[0].get("id", None)

def patch_contact(customer_id, contact_id, is_primary_contact, is_ccemail, task=None):
    endpoint = f"/v3/customers/{customer_id}/contacts/{contact_id}"
    payload = {}
    if is_primary_contact is True:
        payload["isPrimaryContact"] = is_primary_contact
    payload["isCCEmail"] = is_ccemail
    response = make_patch_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True

def create_sub_customer(parent_customer_id, name, task=None):
    endpoint = f"/v3/customers/{parent_customer_id}/sub-customers"
    payload = {}
    payload["customerName"] = name
    payload["currency"] = "USD"
    payload["useParentContactInfo"] = True
    final_payload = payload
    response = make_post_request(endpoint=endpoint, payload=final_payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def set_custom_field_for_customer(customer_id, field_id, value, task=None):
    endpoint = f"/v3/customers/{customer_id}/custom-field"
    payload = {}
    payload["manufacturerCustomFieldId"] = field_id
    payload["customFieldValue"] = str(value)
    final_payload = [payload]
    response = make_put_request(endpoint=endpoint, payload=final_payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def create_address_for_customer(customer_id, line1, line2, postalCode, city, state, country, addressee, isDefaultBilling, isDefaultShipping, task=None):
    endpoint = f"/v3/customers/{customer_id}/address"
    payload = {}
    if non_blank_or_nan(line1):
        payload["line1"] = line1
    if non_blank_or_nan(line2):
        payload["line2"] = line2
    if non_blank_or_nan(postalCode):
        string_postal_code = str(postalCode)
        if "ZIP:" not in string_postal_code:
            raise ValueError("Postal Code must start with ZIP:")
        zip_code = string_postal_code.split("ZIP:")[1]
        payload["postalCode"] = zip_code
    if non_blank_or_nan(city):
        payload["city"] = city
    if non_blank_or_nan(state):
        payload["state"] = state
    if non_blank_or_nan(country):
        payload["country"] = country
    if non_blank_or_nan(addressee):
        payload["addressee"] = addressee
    if non_blank_or_nan(isDefaultBilling):
        payload["isDefaultBilling"] = isDefaultBilling
    if non_blank_or_nan(isDefaultShipping):
        payload["isDefaultShipping"] = isDefaultShipping
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True
    
def delete_obligation(contract_id, obligation_id, task=None):
    endpoint = f"/v3/contracts/{contract_id}/obligations/{obligation_id}"
    response = make_delete_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return True

def get_invoices(task=None, get_all=False):
    endpoint = "/v3/invoices"
    response = make_get_request(endpoint=endpoint, task=task)
    print_logger(response.json())
    results = check_success(response)
    if results is None:
        print_logger("No results found")
        return []
    else:
        print_logger("Results found")
        if get_all:
            print_logger("Getting all invoices")
            all_invoices = results.get("payload", {}).get("data", [])
            total_items = results.get("payload", {}).get("totalItems", 0)
            print_logger("total_items", total_items)
            for page in range(2, math.ceil(total_items / 50000) + 1):
                endpoint = f"/v3/invoices?limit=50000&page={page}"
                response = make_get_request(endpoint=endpoint, task=task)
                results = check_success(response)
                if results is None:
                    print_logger("No more results found")
                    break
                fetched_objects = results.get("payload", {}).get("data", [])
                print_logger(fetched_objects)
                all_invoices.extend(fetched_objects)
            print_logger("All invoices found")
            print_logger(all_invoices)
            return all_invoices
        else:
            print_logger("Returning results")
            return results.get("payload", {}).get("data", [])

def set_customer_external_id(customer_id, type, external_id, task=None):
    url = f"/v3/customers/{customer_id}/external-ids"

    payload = {
        "sourceType": type,
        "externalId": str(external_id)
    }

    response = make_post_request(endpoint=url, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True
    
def enable_disable_auto_charge_for_a_customer(customer_id, enable, task=None):
    url = f"/v3/customers/{customer_id}/autocharge"
    payload = {}
    payload["autocharge"] = enable
    response = make_put_request(endpoint=url, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True

def register_event(customer_id, datetime, event_type_id, value, differentiator=None,invoiceGroup=None, task=None):
    """
    Create a new event in the system.
    
    Args:
        customer_id (str): The ID of the customer associated with the event
        datetime (str): The datetime of the event
        event_type_id (str): The ID of the event type
        value (str): The value associated with the event
        differentiator (str, optional): An optional differentiator for the event
        
    Returns:
        bool or None: Returns True if the event was created successfully,
            or None if the creation failed (e.g., due to an API error or invalid input).
    """
    endpoint = "/v3/events"
    payload = {
        "customerId": customer_id,
        "datetime": datetime,
        "eventTypeId": event_type_id,
        "value": str(value)
    }
    
    if non_blank_or_nan(differentiator):
        payload["differentiator"] = differentiator
    
    if non_blank_or_nan(invoiceGroup):
        payload["invoiceGroup"] = invoiceGroup
        
    response = make_post_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return None
    else:
        return results.get("data", {}).get("events", {}).get("id", None)

def make_number(string_number, turn_back_to_string=True):
    """
    Convert various number formats to float.
    
    Handles:
    - 200 -> 200.0
    - 200.00 -> 200.0
    - 2,000 -> 2000.0
    - 2,000,000 -> 2000000.0
    - 2,000.00 -> 2000.0
    - $200 -> 200.0
    - $200.00 -> 200.0
    
    Returns float or raises ValueError for invalid formats.
    """
    string_number = str(string_number)
    
    # Remove currency symbols and whitespace
    cleaned = string_number.strip().replace('$', '').replace('£', '').replace('€', '').replace('¥', '')
    
    # Remove commas from numbers
    cleaned = cleaned.replace(',', '')
    try:
        if turn_back_to_string:
            return str(cleaned)
    except Exception as e:
        print_logger(f"Error converting {string_number} to number: {e}")
        raise e

    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f"Could not convert '{string_number}' to number")

def prepare_revenue_payload(string_data):



    dates = string_data.split("|")[0].split(":")[1].split(",")
    values = string_data.split("|")[1].split(":")[1].split(",")

    if len(dates) != len(values):
        raise ValueError("Dates and values must be the same length")
    
    new_payload = []
    for date, value in zip(dates, values):
        if value == "":
            value = 0
        new_payload.append({
            "timeframe": date,
            "total": make_number(value)
        })

    return new_payload    

def create_custom_revenue(contract_id, obligation_id, custom_revenue_data, task=None):
    endpoint = f"/v3/contracts/{contract_id}/obligation/{obligation_id}/custom-revenue"

    custom_revenue_data = prepare_revenue_payload(custom_revenue_data)

    response = make_post_request(endpoint=endpoint, payload=custom_revenue_data, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True
    
def delete_customer(customer_id, task=None):
    endpoint = f"/v3/customers/{customer_id}"
    response = make_delete_request(endpoint=endpoint, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True
    
def set_memo_on_invoice(invoice_id, memo, task=None):
    endpoint = f"/v16/secrets/invoices/{invoice_id}/memo"
    payload = {}
    payload["memo"] = str(memo)
    response = make_put_request(endpoint=endpoint, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True

def patch_contract(contract_id, name=None, external_id_type=None, external_id=None, close_date=None, task=None):
    url = f"/v3/contracts/{contract_id}"
    ALLOWED_EXTERNAL_TYPE = [
    "QUICKBOOKS",
    "ORDERTIME",
    "NETSUITE",
    "SALESFORCE",
    "HUBSPOT",
    "BACKEND",
    "AVALARA",
    "ORUM",
    "ANROK",
    "STRIPE",
    "RILLET"
]
    payload = {}
    if name:
        payload["name"] = name
    if close_date:
        # Validate close date is of format YYYY-MM-DD
        if not isinstance(close_date, str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', close_date):
            raise ValueError("closeDate must be a string in the format YYYY-MM-DD")
        payload["closeDate"] = close_date
    if external_id_type and external_id:
        if external_id_type not in ALLOWED_EXTERNAL_TYPE:
            raise ValueError(f"Invalid external_id_type: {external_id_type}. Must be one of: {ALLOWED_EXTERNAL_TYPE}")
        payload["externalId"] = str(external_id)
        payload["sourceType"] = external_id_type
    elif external_id_type and not external_id:
        raise ValueError("External ID and Source Type must both be provided")
    elif not external_id_type and external_id:
        raise ValueError("External ID and Source Type must both be provided")
    response = make_patch_request(endpoint=url, payload=payload, task=task)
    results = check_success(response)
    if results is None:
        return False
    else:
        return True