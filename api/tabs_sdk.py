import streamlit as st
from datetime import datetime
import hashlib
import requests
import math
from helper.logger import print_logger
import time
from helper.data_helpers import soql_response_to_flat

def get_generate_hash(hash_string):
    return hashlib.sha256(f"{hash_string}".encode()).hexdigest()

class Filters:
    def __init__(self):
        self.filter = ""
        self.filter_rules = ["eq", "neq", "gt", "gte", "lt", "lte", "like", "nlike", "in", "nin", "isnull", "isnotnull"]
    
    def add_filter(self, filter_col, filter_rule, filter_value=None):
        if filter_rule not in self.filter_rules:
            raise ValueError(f"Invalid filter rule: {filter_rule}")
        if filter_rule in ["isnull", "isnotnull"]:
            filter_formatted = f'{filter_col}:{filter_rule}:'
        else:
            filter_formatted = f'{filter_col}:{filter_rule}:"{filter_value}"'
        
        if self.filter == "":
            self.filter = filter_formatted
        else:
            self.filter += f',{filter_formatted}'

    def get_filter(self):
        return self.filter

    def format_params(self, params):
        if self.filter != "":
            params["filter"] = self.filter
        return params
    
class TabsRequest:

    def get_total_items(self, response):
        results = dict(response.json())
        payload = results.get("payload", {})
        total_items = payload.get("totalItems", 0)
        return total_items

    def get_limit(self, response):
        results = dict(response.json())
        payload = results.get("payload", {})
        limit = payload.get("limit", 0)
        return limit

    def get_data(self, response):
        results = dict(response.json())
        payload = results.get("payload", {})
        if type(payload) == list:
            return payload
        data = payload.get("data", None)
        if data is None:
            return payload
        else:
            return data

    def check_success(self, response, use_status_code=False):
        results = dict(response.json())
        success = results.get("success", False)
        if use_status_code:
            status_code = response.status_code
            if status_code >= 200 and status_code < 300:
                return results
            else:
                return None
        else:
            if success:
                return results
            else:
                return None

    def handle_request_log(self, request_log, using_session_state, task):
        if using_session_state:
            st.session_state.request_history.append(request_log)
        else:
            task.request_logs.append(request_log)
        return request_log

    def generate_request_log(self, method, backend_url, endpoint, payload, response, batch_id):
        timestamp = self.get_timestamp()
        request_hash = self.get_hash(precise=True)
        return {
            "method": method,
            "backend_url": backend_url,
            "endpoint": endpoint,
            "payload": payload,
            "response": response,
            "timestamp": timestamp,
            "hash": request_hash,
            "batch_id": batch_id,
        }

    def configure_request_attributes(self, task=None):
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

        return backend_url, api_key, using_session_state, batch_id
    
    def construct_url(self, backend_url, endpoint):
        return f"{backend_url}{endpoint}"

    def get_timestamp(self, precise=False):
        if precise:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_hash(self, precise=False):
        return get_generate_hash(f"{self.get_timestamp(precise)}")
    
    def generate_headers(self, api_key):
        return {"Authorization": f"{api_key}"}

    def get_method(self, method):
        match method:
            case "GET":
                return requests.get
            case "POST":
                return requests.post
            case "PUT":
                return requests.put
            case "DELETE":
                return requests.delete
            case "PATCH":
                return requests.patch
            case _:
                return None
    
    def is_rate_limited(self, response):
        try:
            response_status_code = response.status_code
            if response_status_code == 429:
                return True
            else:
                return False
        except:
            return False

    def make_request(self, endpoint, method, payload=None, files=None, params=None, task=None, attempts=0):
        if attempts > 30:
            raise ValueError("Max attempts reached (30), request failed")
        backend_url, api_key, using_session_state, batch_id = self.configure_request_attributes(task)

        if backend_url is None or api_key is None:
            return None
        
        final_url = self.construct_url(backend_url, endpoint)
        headers = self.generate_headers(api_key)
        request_method = self.get_method(method)
        print_logger(f"Making {method} request to {final_url}")
        response = request_method(
            url=final_url, 
            json=payload, 
            headers=headers, 
            files=files, 
            params=params)
        print_logger(f"Response for {method} request to {final_url} is {response.status_code}")
        request_log = self.generate_request_log(
            method=method, 
            backend_url=backend_url, 
            endpoint=endpoint, 
            payload=payload, 
            response=response, 
            batch_id=batch_id)
        self.handle_request_log(
            request_log=request_log, 
            using_session_state=using_session_state, 
            task=task)
        if self.is_rate_limited(response):
            print_logger("Rate limited response received, backing off for 1 second and retrying")
            attempts += 1
            print_logger("Attempting to make request again in", attempts, "seconds")
            time.sleep(attempts) # Linear backoff
            return self.make_request(endpoint=endpoint, method=method, payload=payload, files=files, params=params, task=task, attempts=attempts)
        else:
            return response
        
    def get_wrapper(self, endpoint, params=None, task=None, get_all=False):
        return_data = []
        if params is None:
            params = {}
        
        response = self.make_request(endpoint=endpoint, method="GET", params=params, task=task)
        success = self.check_success(response)
        if not success:
            return return_data
        elif success and not get_all:
            return_data = self.get_data(response)
            return return_data
        elif success:
            return_data = self.get_data(response)
            total_items = self.get_total_items(response)
            limit = self.get_limit(response)
            pages = math.ceil(total_items / limit)
            for page in range(2, pages + 1):
                print_logger("\n\n************************************************")
                print_logger(f"**Getting data from page {page}")
                print_logger(f"Current return data length: {len(return_data)}")
                print_logger(f"Current return data: {return_data}")
                params["page"] = page
                params["limit"] = limit
                response = self.make_request(endpoint=endpoint, method="GET", params=params, task=task)
                print_logger(f"Found {len(self.get_data(response))} items on page {page}")
                success = self.check_success(response)
                if not success:
                    return return_data
                elif success:
                    print_logger(f"Found data on page {page} : {self.get_data(response)}")
                    return_data.extend(self.get_data(response))
                    print_logger(f"Return data after extension: {return_data}")
                print_logger("************************************************")
                

            return return_data

        
def get_events(event_type_id=None, customer_id=None, differentiator=None, before_date=None, after_date=None, get_all=False, task=None, limit=1000):
    endpoint = "/v3/events"

    tabs_request = TabsRequest()
    filters = Filters()
    if event_type_id:
        filters.add_filter(filter_col="eventTypeId", filter_rule="eq", filter_value=event_type_id)
    if customer_id:
        filters.add_filter(filter_col="customerId", filter_rule="eq", filter_value=customer_id)
    if differentiator:
        filters.add_filter(filter_col="differentiator", filter_rule="eq", filter_value=differentiator)
    if before_date:
        filters.add_filter(filter_col="datetime", filter_rule="lte", filter_value=before_date)
    if after_date:
        filters.add_filter(filter_col="datetime", filter_rule="gte", filter_value=after_date)

    params = {"limit": limit}
    params = filters.format_params(params)

    data = tabs_request.get_wrapper(endpoint=endpoint, params=params, task=task, get_all=get_all)

    return data

def get_event_types(limit=500, task=None, get_all=False):
    endpoint = "/v3/events/types"
    params = {"limit": limit}
    tabs_request = TabsRequest()
    data = tabs_request.get_wrapper(endpoint=endpoint, params=params, task=task, get_all=get_all)
    return data
        
def get_customers(limit=500, name=None, external_id=None, has_external_id=None, task=None, get_all=False):
    endpoint = "/v3/customers"
    tabs_request = TabsRequest()
    filters = Filters()
    if name:
        filters.add_filter(filter_col="name", filter_rule="eq", filter_value=name)
    if external_id:
        filters.add_filter(filter_col="externalId", filter_rule="eq", filter_value=external_id)
    if has_external_id is not None:
        if has_external_id:
            filters.add_filter(filter_col="externalId", filter_rule="isnotnull", filter_value="")
        else:
            filters.add_filter(filter_col="externalId", filter_rule="isnull", filter_value="")
    params = {"limit": limit}
    params = filters.format_params(params)
    data = tabs_request.get_wrapper(endpoint=endpoint, params=params, task=task, get_all=get_all)
    return data
   
def get_custom_fields(task=None, get_all=False):
    url = "/v3/custom-fields"
    tabs_request = TabsRequest()
    data = tabs_request.get_wrapper(endpoint=url, task=task, get_all=False)
    return data
        
def get_classes(task=None, get_all=False):
    url = "/v3/classes"
    tabs_request = TabsRequest()
    data = tabs_request.get_wrapper(endpoint=url, task=task, get_all=False)
    return data

def get_obligations(customer_id=None, task=None, get_all=False):
    endpoint = "/v3/obligations"
    tabs_request = TabsRequest()
    filters = Filters()
    if customer_id:
        filters.add_filter(filter_col="customerId", filter_rule="eq", filter_value=customer_id)
    params = {"limit": 500}
    params = filters.format_params(params)
    data = tabs_request.get_wrapper(endpoint=endpoint, params=params, task=task, get_all=get_all)
    return data

def query_salesforce_data(merchant_id, soql_query, task=None):
    url = f"/v16/secrets/salesforce/query"
    payload = {}
    payload["query"] = soql_query
    payload["manufacturerId"] = merchant_id
    payload["useAuthenticatedConnection"] = True
    tabs_request = TabsRequest()
    response = tabs_request.make_request(endpoint=url, method="POST", payload=payload, task=task)
    status_code = response.status_code
    results = tabs_request.check_success(response, use_status_code=True)

    if results is None:
        st.toast(f"Error querying Salesforce data, code: {status_code}", icon=":material/error:")
        return None
    else:
        st.toast(f"Successfully queried Salesforce data, code: {status_code}", icon=":material/check:")
        return soql_response_to_flat(results)

def get_revenue_categories(task=None, get_all=False):
    url = "/v3/categories"
    tabs_request = TabsRequest()
    data = tabs_request.get_wrapper(endpoint=url, task=task, get_all=get_all)
    return data

def get_integration_items(task=None, get_all=False):
    url = "/v3/items"
    tabs_request = TabsRequest()
    data = tabs_request.get_wrapper(endpoint=url, task=task, get_all=get_all)
    return data