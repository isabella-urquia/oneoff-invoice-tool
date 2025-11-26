import streamlit as st


def find_customer_id(name):
    matching_customers = []
    for customer in st.session_state.customers:
        if customer["name"] == name:
            matching_customers.append(customer)
    if len(matching_customers) == 1:
        customer = matching_customers[0]
        return customer["id"], customer["name"]
    return None

def find_contract_id(name,customer_id=None):
    matching_contracts = []
    for contract in st.session_state.contracts:
        if customer_id is not None:
            if contract["customerId"] == customer_id and contract["name"] == name:
                matching_contracts.append(contract)
    if len(matching_contracts) == 1:
        contract = matching_contracts[0]
        return contract["id"], contract["name"], contract["customerId"]
    return None

# HELPER FUNCTIONS
def map_customers(customer_name=[]):
    '''
    Map the customer names to the customer IDs
    '''
    if len(customer_name) > 0:
        st.write(customer_name)
        for name in customer_name:
            st.session_state.mapping_dictionary[name] = {"customer_id":None, "original_name":name, "name_in_tabs":None}
            result = find_customer_id(name)
            if result is not None:
                st.session_state.mapping_dictionary[name]["customer_id"] = result[0]
                st.session_state.mapping_dictionary[name]["name_in_tabs"] = result[1]
    else:
        for name in st.session_state.mapping_dictionary.keys():
            result = find_customer_id(name)
            if result is not None:
                st.session_state.mapping_dictionary[name]["customer_id"] = result[0]
                st.session_state.mapping_dictionary[name]["name_in_tabs"] = result[1]

def map_contracts(contract_name=[]):
    '''
    Map the contract names to the contract IDs
    '''
    if len(contract_name) > 0:
        st.write(contract_name)
        for name, customer_id in contract_name:
            st.session_state.mapping_dictionary[(name, customer_id)] = {"contract_id":None, "original_name":name, "name_in_tabs":None, "customer_id":  customer_id}
            result = find_contract_id(name, customer_id)
            if result is not None:
                st.session_state.mapping_dictionary[(name, customer_id)]["contract_id"] = result[0]
                st.session_state.mapping_dictionary[(name, customer_id)]["name_in_tabs"] = result[1]
                st.session_state.mapping_dictionary[(name, customer_id)]["customer_id"] = result[2]
    else:
        for name, customer_id in st.session_state.mapping_dictionary.keys():
            result = find_contract_id(name, customer_id)
            if result is not None:
                st.session_state.mapping_dictionary[(name, customer_id)]["contract_id"] = result[0]
                st.session_state.mapping_dictionary[(name, customer_id)]["name_in_tabs"] = result[1]
                st.session_state.mapping_dictionary[(name, customer_id)]["customer_id"] = result[2]

