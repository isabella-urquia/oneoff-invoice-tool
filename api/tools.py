import pandas as pd
import streamlit as st
from api.tabs_sdk import get_obligations

VALID_INTERVALS = ["NONE", "DAY", "MONTH", "YEAR", "QUARTER", "SEMI_MONTH"]


def unformat_billing_type(billingtype, pricingtype):
    if billingtype == "FLAT":
        return "FLAT_PRICE"
    elif pricingtype == "TIERED":
        return "TIER_FLAT_PRICE"
    elif pricingtype == "SIMPLE":
        return "UNIT_PRICE"
    elif billingtype is None and pricingtype is None:
        return "NONE"
    else:
        raise Exception(f"Invalid billing type: {billingtype} | {pricingtype}")

def convert_billing_type(billing_type, is_volume=False):
    if billing_type == "FLAT_PRICE":
        return {"billingType": "FLAT", "pricingType": "SIMPLE"}
    elif billing_type == "UNIT_PRICE":
        return {"billingType": "UNIT", "pricingType": "SIMPLE"}
    elif billing_type == "TIER_FLAT_PRICE":
        if is_volume:
            return {"billingType": "FLAT", "pricingType": "VOLUME"}
        else:
            return {"billingType": "FLAT", "pricingType": "TIERED"}
    elif billing_type == "TIER_UNIT_PRICE":
        if is_volume:
            return {"billingType": "UNIT", "pricingType": "VOLUME"}
        else:
            return {"billingType": "UNIT", "pricingType": "TIERED"}
    else:
        raise Exception(f"Invalid billing type: {billing_type}")

def format_date(date_str):
    # FORMAT YYYY-MM-DD
    try:
        # If it's already in YYYY-MM-DD format, return as is
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str
        # Otherwise try to parse it
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except:
        raise Exception(f"Invalid date format: {date_str}")

def non_blank_or_nan(value):
    return value is not None and value != "" and not pd.isna(value)

def make_it_number(amount):
    try:
        if (type(amount) == str):
            if "," in amount:
                amount = amount.replace(",", "")
            if "$" in amount:
                amount = amount.replace("$", "")
        amount = float(amount)
    except Exception as e:
        raise Exception(f"Invalid number format: {amount} | {e}")
    return float(amount)

def make_discount_payload(row):
    discount_type_present = "discount_type" in row
    discount_value_present = "discount_amount" in row
    if not discount_type_present and not discount_value_present:
        return None
    non_blank_discount_value = non_blank_or_nan(row["discount_amount"])
    non_blank_discount_type = non_blank_or_nan(row["discount_type"])
    if discount_type_present and discount_value_present and non_blank_discount_value and non_blank_discount_type:
        discount_type = row["discount_type"]
        discount_value = row["discount_amount"]
        if discount_type not in ["FIXED", "PERCENTAGE"]:
            raise Exception(f"Invalid discount type: {discount_type}")
        
        if non_blank_or_nan(discount_value):
            discount_payload = {}
            discount_payload["type"] = discount_type
            discount_payload["amount"] = str(discount_value)
            if "discount_note" in row:
                if non_blank_or_nan(row["discount_note"]):
                    discount_payload["note"] = str(row["discount_note"])
                else:
                    discount_payload["note"] = ""
            else:
                discount_payload["note"] = ""
            return discount_payload
        else:
            return None
    else:
        return None

def make_pricing_payload(row, billing_type):

    if "UNIT" in billing_type or "TIER" in billing_type:
        amount_type = "PER_ITEM"
    else:
        amount_type = "TOTAL_INVOICE"

    cols = row.keys()
    col_mask_1 = "amount_"
    col_mask_2 = "value_"

    amount_cols = [col for col in cols if col_mask_1 in col]
    value_cols = [col for col in cols if col_mask_2 in col]

    # Validate that the amount_cols and value_cols are the same length
    if len(amount_cols) != len(value_cols):
        raise Exception(f"Amount and value columns are not the same length")
    
    # Sort the amount_cols and value_cols by the amount_cols with amount_1 and value_1 first
    amount_cols.sort()
    value_cols.sort()

    # Create the pricing payload
    pricing_payload = []

    for amount_col, value_col in zip(amount_cols, value_cols):
        current_tier = make_it_number(amount_col.split("_")[1])
        current_amount = row[amount_col]
        current_value = row[value_col]

        if current_tier == 1:
            # If value_1 is blank
            if not non_blank_or_nan(current_value):
                current_value = 0
            else:
                current_value = make_it_number(current_value)
            # check amount_1 is valid
            if not non_blank_or_nan(current_amount):
                raise Exception(f"Amount_1 is not valid: {current_amount}")
            else:
                current_amount = make_it_number(current_amount)

            pricing_payload.append({
                "tier": current_tier,
                "amount": current_amount,
                "tierMinimum": current_value,
                "amountType": amount_type
            })       
        elif non_blank_or_nan(row[amount_col]) and non_blank_or_nan(row[value_col]):
            current_amount = make_it_number(row[amount_col])
            current_value = make_it_number(row[value_col])


            pricing_payload.append({
                "tier": current_tier,
                "amount": current_amount,
                "tierMinimum": current_value,
                "amountType": amount_type
            })
    
    return pricing_payload

def make_billing_schedule_payload(row):
    payload = {}
    payload["name"] = row["name"]
    if non_blank_or_nan(row["note"]):
        payload["description"] = str(row["note"])
    payload["startDate"] = format_date(row["invoice_date"])
    payload["duration"] = int(row["duration"])

    if "is_arrears" in row:
        payload["isArrears"] = bool(row["is_arrears"])
    elif "invoiceDateStrategy" in row:
        invoiceDateStrategy = row["invoiceDateStrategy"]
        if invoiceDateStrategy not in ["FIRST_OF_PERIOD", "ADVANCED_DUE_START", "ARREARS", "LAST_OF_PERIOD", "ARREARS"]:
            raise Exception(f"Invalid invoice date strategy: {invoiceDateStrategy}")
        payload["invoiceDateStrategy"] = invoiceDateStrategy
    else:
        raise Exception("Neither isArrears nor invoiceDateStrategy is present in the row")

    payload["isRecurring"] = bool(row["is_recurring"])
    if row["due_interval_unit"] in VALID_INTERVALS:
        payload["interval"] = row["due_interval_unit"]
    else:
        raise Exception(f"Invalid interval: {row['due_interval_unit']}")
    payload["intervalFrequency"] = int(row["due_interval"])
    payload["netPaymentTerms"] = int(row["net_payment_terms"])
    payload["quantity"] = make_it_number(row["quantity"])
    if "is_volume" in row:
        is_volume = bool(row["is_volume"])
    else:
        is_volume = False
    payload.update(convert_billing_type(row["billing_type"], is_volume))
    if non_blank_or_nan(row["event_to_track"]):
        payload["eventTypeId"] = row["event_to_track"]
    if non_blank_or_nan(row["integration_item_id"]):
        payload["itemId"] = row["integration_item_id"]
    payload["invoiceType"] = row["invoice_type"]
    payload["pricing"] = make_pricing_payload(row, row["billing_type"])
    if non_blank_or_nan(row["classId"]):
        payload["classId"] = row["classId"]
    return payload

def create_obligation_payload(row):
    payload = {
        "serviceStartDate": format_date(row["revenue_start_date"]),
        "serviceEndDate": format_date(row["revenue_end_date"]),
    }

    if non_blank_or_nan(row["revenue_product_id"]):
        payload["categoryId"] = row["revenue_product_id"]

    payload["billingSchedule"] = make_billing_schedule_payload(row)
    discount_payload = make_discount_payload(row)
    if discount_payload is not None:
        payload["discount"] = discount_payload
    return payload

def find_name_for_revenue_category(revenue_category_id):
    for revenue_category in st.session_state.revenue_categories:
        if revenue_category["id"] == revenue_category_id:
            return revenue_category["name"]
    return "None"

def find_name_for_integration_item(integration_item_id):
    for integration_item in st.session_state.integration_items:
        if integration_item["id"] == integration_item_id:
            return integration_item["name"]
    return "None"

def find_name_for_event_type(event_type_id):
    for event_type in st.session_state.event_types:
        if event_type["id"] == event_type_id:
            return str(event_type["name"])
    return "None"

def find_name_for_customer(customer_id):
    for customer in st.session_state.customers:
        if customer["id"] == customer_id:
            return customer["name"]
    return "None"

def get_external_id_for_customer(customer_record, type):
    allowed_types = [
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
    if type not in allowed_types:
        raise Exception(f"Invalid type: {type}. Must be one of: {allowed_types}")
    for external_id in customer_record.get("externalIds", []):
        if external_id.get("type") == type:
            return external_id.get("id")
    return None

def get_most_frequent_number(numbers):
    frequency_dict = {}
    for number in numbers:
        if number in frequency_dict:
            frequency_dict[number] += 1
        else:
            frequency_dict[number] = 1
    return max(frequency_dict, key=frequency_dict.get)

def find_net_terms_for_customer(customer_id, mode="MODE"):
    if mode not in ["MODE", "MIN", "MAX"]:
        raise ValueError("Mode must be one of: MODE, MIN, MAX")

    data = get_obligations(customer_id=customer_id)
    if len(data) == 0:
        return 30
    
    net_terms = []
    for obligation in data:
        net_term_i = obligation.get("billingSchedule",{}).get("netPaymentTerms", None)
        if net_term_i:
            net_terms.append(int(net_term_i))

    if len(net_terms) == 0:
        return 30
    else:
        if mode == "MODE":
            return get_most_frequent_number(net_terms)
        elif mode == "MIN":
            return min(net_terms)
        elif mode == "MAX":
            return max(net_terms)

def generate_template_billing_term():
    payload = {
        "serviceStartDate": None,
        "serviceEndDate": None,
        "categoryId": None,
        "billingSchedule": {
            "name": None,
            "description": None,
            "startDate": None,
            "duration": None,
            "invoiceDateStrategy": None,
            "isRecurring": None,
            "interval": None,
            "intervalFrequency": None,
            "netPaymentTerms": None,
            "quantity": None,
            "billingType": None,
            "pricingType": None,
            "eventTypeId": None,
            "itemId": None,
            "invoiceType": "INVOICE",
            "pricing": [
                    {
                    "tier": 1,
                    "amount": None,
                    "amountType": "TOTAL_INVOICE",
                    "tierMinimum": 0
                    }
                ],
            },

        }
    return payload