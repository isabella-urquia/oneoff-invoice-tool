import pandas as pd
import streamlit as st
from datetime import datetime



@st.cache_data
def convert_for_download(df):
    return df.to_csv(index=False).encode("utf-8")

@st.cache_data
def flatten_dict(data, parent_key='', sep='_'):
    """
    Flatten a nested dictionary and list structure into a flat dictionary.
    
    Args:
        data: The data to flatten (dict, list, or primitive value)
        parent_key: The parent key for nested structures
        sep: Separator to use between nested keys
        
    Returns:
        A flattened dictionary with dot notation keys
    """
    items = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                items.extend(flatten_dict(value, new_key, sep).items())
            else:
                items.append((new_key, value))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            if isinstance(value, (dict, list)):
                items.extend(flatten_dict(value, new_key, sep).items())
            else:
                items.append((new_key, value))
    else:
        # Handle primitive values
        items.append((parent_key, data))
    
    return dict(items)

def dwnload_component(df, label, file_name, icon=":material/file_present:", type="primary", use_container_width=True, render_object=st):
    cached_data = convert_for_download(df)
    current_timestamp = datetime.now().strftime("%Y-%m-%d")
    merchant_name = st.session_state.merchant_name if st.session_state.merchant_name else "NOS"
    final_file_name = f"{file_name}_{current_timestamp}_{merchant_name}.csv"
    render_object.download_button(
        label=label, 
        data=cached_data, 
        file_name=final_file_name, 
        icon=icon, type=type, use_container_width=use_container_width)

def flatten_list_of_dicts(data):
    """
    Flattens a list of nested dictionaries.

    Parameters:
        data (list): List of nested dictionaries.

    Returns:
        list: List of flattened dictionaries.
    """
    return [flatten_dict(item) for item in data if isinstance(item, dict)]

def soql_response_to_flat(response):
    records = response.get('data',{}).get('records',[])
    flattened_records = flatten_list_of_dicts(records)
    return flattened_records