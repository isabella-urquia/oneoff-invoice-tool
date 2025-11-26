import re
import streamlit as st

@st.cache_data
def clean_name(name):
    # Convert to string, lowercase, and remove all non-alphabet characters
    cleaned = re.sub(r'[^a-zA-Z]', '', str(name).lower())
    return cleaned

@st.cache_data
def fuzzy_match(name_1, name_2, threshold=0.8, return_score=False):

    name_1 = clean_name(name_1)
    name_2 = clean_name(name_2)

    # Check if more than 80% of characters match
    if not name_1 or not name_2:
        return False
    
    # Convert to strings and normalize
    str1 = str(name_1).lower()
    str2 = str(name_2).lower()
    
    # Find the longer string to use as reference
    if len(str1) >= len(str2):
        longer, shorter = str1, str2
    else:
        longer, shorter = str2, str1
    
    if len(shorter) == 0:
        return len(longer) == 0
    
    # Count matching characters
    matches = 0
    for i, char in enumerate(shorter):
        if i < len(longer) and char == longer[i]:
            matches += 1
    
    # Calculate match percentage
    match_percentage = matches / len(shorter)
    if return_score:
        return match_percentage
    return match_percentage > threshold

@st.cache_data
def strict_match(name_1, name_2):
    return clean_name(name_1) == clean_name(name_2)

@st.cache_data
def find_most_likely_customer(customer_name, customer_options):
    most_likely_customer = customer_options[0]
    most_likely_customer_score = 0
    for customer in customer_options:
        score = fuzzy_match(customer_name, customer.get("name", ""), return_score=True)
        if score > most_likely_customer_score:
            most_likely_customer = customer
            most_likely_customer_score = score
    return most_likely_customer

@st.cache_data
def find_index_of_customer_in_cache(customer_id, tabs_customers):
    index = 0
    for customer in tabs_customers:
        if customer.get("id", "") == customer_id:
            return index
        index += 1
    return 0

@st.cache_data
def return_options_for_customer(customer_name, tabs_customers, threshold=0.8):
    options = []
    for tab_customer in tabs_customers:
        if fuzzy_match(customer_name, tab_customer.get("name", ""), threshold):
            options.append(tab_customer)
    return options

@st.cache_data
def match_customer_name_to_tabs_customer(customer_name, tabs_customers, match_config="STRICT", multiple_matches_allowed=False):
    # Configs: STRICT, FUZZY
    # STRICT: Match exactly and only return if one one record matches
    # FUZZY: Match if customer names are similar
    match match_config:
        case "STRICT":
            matching_function = strict_match
        case "FUZZY":
            matching_function = fuzzy_match
        case _:
            raise ValueError("Invalid match config")

    matches = 0
    customer_id = []
    prime_customer_name = customer_name
    for tab_customer in tabs_customers:
        current_customer_name = tab_customer.get("name", "")
        if matching_function(prime_customer_name, current_customer_name):
            matches += 1
            customer_id.append(tab_customer.get("id", ""))
        
    if matches == 0:
        return None
    elif matches == 1:
        return customer_id[0]
    elif multiple_matches_allowed:
        return customer_id
    else:
        return None