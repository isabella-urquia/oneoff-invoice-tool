from dateutil import parser
from datetime import datetime
from calendar import monthrange
from datetime import timedelta

def parse_to_yyyy_mm_dd(date_str):
    """
    Attempts to parse a string into a date in YYYY-MM-DD format.
    
    Args:
        date_str (str): The input date string.

    Returns:
        str or None: The date in YYYY-MM-DD format, or None if parsing fails.
    """
    try:
        dt = parser.parse(date_str, dayfirst=False, yearfirst=False)
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    
def convert_string_number_to_float(value):
    """
    Attempts to convert a string number to a float.
    
    Args:
        value (str): The input string number.

    Returns:
        float or None: The float value, or None if conversion fails.
    """
    value = str(value)
    value = value.replace(",", "")
    value = value.replace(" ", "")
    value = value.replace("€", "")
    value = value.replace("£", "")
    value = value.replace("$", "")
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def get_service_period(invoice_date):
    '''
        Gets the service period for a given invoice date. 
        This assumes a 1 month service period in arrears.
        ie: Invoice date is 2025-11-01, service period is 2025-10-01 to 2025-10-31
    '''
    end_date = invoice_date
    # Subtract 1 month from invoice_date
    # Handle month/year wraparound
    year = end_date.year
    month = end_date.month
    day = end_date.day

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # Handle day overflow (e.g., March 31 -> Feb 28/29)
    # Find last day of previous month
    last_day_prev_month = monthrange(prev_year, prev_month)[1]
    start_day = min(day, last_day_prev_month)
    start_date = end_date.replace(year=prev_year, month=prev_month, day=start_day)

    return start_date, end_date

def subtract_days_from_date(date: str, days: int):
    # Convert string to datetime object
    date_object = datetime.strptime(date, "%Y-%m-%d")
    return date_object - timedelta(days=1)

def create_time_stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")