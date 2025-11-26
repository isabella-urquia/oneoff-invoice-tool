from datetime import datetime
import streamlit as st


def make_uniform_length_string(string, length):
    if len(string) < length:
        return string + " " * (length - len(string))
    else:
        return string[:length]

def format_timestamp():
    # Get the current timestamp in the format of YYYY-MM-DD HH:MM:SS AM/PM
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %p")
    return timestamp


def print_logger(*args, **kwargs):
    current_timestamp = format_timestamp()
    args_str = " ".join([str(arg) for arg in args])
    kwargs_str = " ".join([f"{key}={value}" for key, value in kwargs.items()])
    if "current_page" not in st.session_state:
        st.session_state.current_page = "GENERAL"
    formatted_current_page = make_uniform_length_string(st.session_state.current_page, 20)
    message = f"{current_timestamp} | {formatted_current_page} | {args_str} {kwargs_str}"
    print(message)
