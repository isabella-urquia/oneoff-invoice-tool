# One Off Usage Invoice Tool

A standalone Streamlit application for creating one-off usage invoices in the Tabs platform.

## Features

- Upload CSV files with customer usage data
- Map customer names to Tabs customers
- Configure net terms for each customer
- Generate invoices with customizable product names, descriptions, and service periods

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure `.env` file:
Create a `.env` file in the root directory with:
```env
MODE="local"
ENVIRONMENT="prod"
DEFAULT_TABS_API_KEY="your_api_key_here"
DEFAULT_MERCHANT_NAME="Your Merchant Name"
DEFAULT_ENVIRONMENT="prod"
```

## Running the Application

```bash
streamlit run app.py
```

The application will be available at http://localhost:8501

## Usage

1. **Upload Usage Data**: Upload a CSV file with customer usage data
2. **Map Customers**: Map your customer names to Tabs customers and configure net terms
3. **Configure Invoice Details**: Set invoice date, product name, description, revenue category, and integration item
4. **Generate Invoices**: Create invoices using the "Create invoices" button

## CSV Format

Your CSV file should have the following columns:
- `Rep Invoicing Tabs Customer Name` (required)
- `Rep Invoicing Tabs Customer ID` (optional)
- `Rep Invoicing Invoice Type` (optional - product name)
- `Rep Invoicing Invoice Quantity` (required)
- `Rep Invoicing Invoice Value` (required)

## License

Internal tool for Tabs platform usage.
