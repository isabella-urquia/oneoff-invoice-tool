# Standard Operating Procedure (SOP)
## One Off Usage Invoice Tool

**Version:** 1.0  
**Last Updated:** November 2024  
**Tool Purpose:** Create one-off usage invoices in the Tabs platform from CSV data

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Tool Workflow Overview](#tool-workflow-overview)
4. [Step-by-Step Instructions](#step-by-step-instructions)
5. [CSV File Requirements](#csv-file-requirements)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Prerequisites

Before using this tool, ensure you have:
- Python 3.x installed on your system
- Access to the Tabs platform API credentials
- A CSV file with customer usage data (see [CSV File Requirements](#csv-file-requirements))
- Network access to the Tabs API endpoints

---

## Initial Setup

### 1. Environment Setup

1. **Navigate to the project directory:**
   ```bash
   cd /path/to/oneoff-invoice-tool-1
   ```

2. **Create a virtual environment (if not already created):**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 2. Configuration

1. **Create or update the `.env` file** in the project root with your credentials:
   ```env
   MODE="local"
   ENVIRONMENT="prod"
   DEFAULT_TABS_API_KEY="your_api_key_here"
   DEFAULT_MERCHANT_NAME="Your Merchant Name"
   DEFAULT_MERCHANT_ID="your_merchant_id"
   DEFAULT_ENVIRONMENT="prod"
   FALL_BACK_LOGO="your_logo_url_here"
   ```

2. **Verify your API credentials** are correct for the environment you're using (`prod` or `dev`)

### 3. Start the Application

1. **Start the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

2. **Access the application** at `http://localhost:8501`

3. **Verify API connection** - The app should display your merchant name and environment in the sidebar if configured correctly

---

## Tool Workflow Overview

The tool follows a **4-step process**:

1. **Step 1: Upload Usage Data** - Upload and validate your CSV file
2. **Step 2: Customer Mapping & Net Term Setup** - Map customers and configure net terms
3. **Step 3: Configure Invoice Details** - Set invoice parameters
4. **Step 4: Generate Invoices** - Create invoices in bulk

---

## Step-by-Step Instructions

### Step 1: Upload Usage Data

**Objective:** Upload your CSV file containing customer usage data

1. **Navigate to Step 1** (should be active by default)

2. **Review the required columns:**
   - `Rep Invoicing Tabs Customer Name` (required)
   - `Rep Invoicing Tabs Customer ID` (optional, but recommended)
   - `Rep Invoicing Invoice Type` (optional - product name)
   - `Rep Invoicing Invoice Quantity` (required)
   - `Rep Invoicing Invoice Value` (required)

3. **Download the template** (optional):
   - Click "Download template" to get a CSV template with the correct column headers
   - Use this as a reference for formatting your data

4. **Upload your CSV file:**
   - Click "Upload your usage data"
   - Select your CSV file
   - Click "Set file" to process the data

5. **Verify the upload:**
   - The tool will automatically:
     - Validate required columns are present
     - Clean numeric values (remove $ and commas)
     - Attempt to match customer names to Tabs customers
     - Show a toast notification with match results

6. **Proceed to Step 2** - The tool will automatically advance once the file is processed

**Notes:**
- If customer IDs are provided in the CSV, the tool will use them directly
- If no customer IDs are provided, the tool will attempt fuzzy matching
- You can see how many customers were matched in the toast notification

---

### Step 2: Customer Mapping & Net Term Setup

**Objective:** Ensure all customers are mapped correctly and configure net payment terms

#### 2.1 Customer Mapping

1. **Review customer mapping status:**
   - A progress bar shows how many customers are mapped vs. unmapped
   - Unmapped customers will be highlighted

2. **Use filtering options:**
   - **Customer Display:** Choose to show "Mapped", "Unmapped", or both
   - **Matching Logic:** Enable/disable fuzzy matching and adjust threshold (0.0-1.0)
   - **Net Term Mode:** Select how net terms should be determined:
     - "Most Common Net Term" (default)
     - "Smallest Net Term"
     - "Largest Net Term"

3. **Map unmapped customers:**
   - For each unmapped customer:
     - Review the suggested matches (if fuzzy matching is enabled)
     - Select the correct Tabs customer from the dropdown
     - Click "Map customer" to save the mapping
   - For mapped customers that need correction:
     - Select a different customer from the dropdown
     - Click "Update Mapping" to save changes

4. **Verify all customers are mapped:**
   - Ensure the progress bar shows 100% mapped
   - The "Map net terms" button will only be enabled when all customers are mapped

#### 2.2 Net Term Configuration

1. **Select Net Term Mode:**
   - Choose from the dropdown:
     - **Most Common Net Term:** Uses the most frequently used net term for each customer
     - **Smallest Net Term:** Uses the smallest net term value
     - **Largest Net Term:** Uses the largest net term value

2. **Map net terms:**
   - Click "Map net terms" button
   - **Important:** Do not refresh or navigate away during this process
   - The tool will:
     - Pull net terms dynamically from Tabs for each customer
     - Show a progress bar with status updates
     - Display a toast notification when complete

3. **Verify completion:**
   - Once net terms are mapped, you'll automatically advance to Step 3

**Troubleshooting:**
- If a customer cannot be mapped, verify the customer name matches exactly or use fuzzy matching
- If net term mapping fails, check your API connection and try again

---

### Step 3: Configure Invoice Details

**Objective:** Set invoice parameters that will be applied to all invoices

1. **Set Invoice Date:**
   - Select the invoice date using the date picker
   - Default is today's date
   - Format: YYYY-MM-DD

2. **Configure Product Information:**
   
   **If your CSV has product names (`Rep Invoicing Invoice Type` column):**
   - The tool will automatically use product names from your CSV
   - Each row will use its own product name
   - You can set a "Default Product Name" as a fallback for rows without product names
   - A preview will show unique product types found in your CSV
   
   **If your CSV does NOT have product names:**
   - Enter a "Product name" (default: "Usage Credits")
   - This will be used for all invoices

3. **Set Product Description (Optional):**
   - Enter a description for the product/service
   - This is optional - leave empty if not needed
   - The description will appear on invoices below the product name

4. **Select Revenue Category:**
   - Choose the appropriate revenue category from the dropdown
   - Categories are pulled from your Tabs account

5. **Select Integration Item:**
   - Choose the integration item from the dropdown
   - Items are pulled from your Tabs account

6. **Review Invoice Preview:**
   - Click "Save invoice details" to see a preview
   - Review the preview dialog showing:
     - Invoice date
     - Net terms
     - Product name and description
     - Service period (automatically calculated)
     - Quantity and amount

7. **Confirm and Save:**
   - Review the preview carefully
   - Click "Confirm" to save invoice details
   - **Note:** Once saved, invoice details are locked. Use the reset function to change them.

8. **Proceed to Step 4** - You'll automatically advance after confirming

**Service Period Calculation:**
- For Capitalize billing, service period is calculated as:
  - Start date: First day of the invoice date's month
  - End date: The invoice date itself
  - Example: Invoice date 2026-01-31 → Service period: 2026-01-01 to 2026-01-31

---

### Step 4: Generate Invoices

**Objective:** Create invoices in bulk using the configured settings

1. **Set Contract Name:**
   - Enter a contract name (default: "Usage Credits for [Month Year]")
   - This name will be used for all contracts created

2. **Review Configuration:**
   - Verify all previous steps are complete:
     - ✅ CSV uploaded and processed
     - ✅ All customers mapped
     - ✅ Net terms configured
     - ✅ Invoice details saved

3. **Create Invoices:**
   - Click "Create invoices" button
   - The tool will:
     - Create a task queue for invoice generation
     - Process each row from your CSV
     - Generate invoices in the background
     - Show progress in the sidebar (if task queue control panel is visible)

4. **Monitor Progress:**
   - The app icon will change to 🚧 while processing
   - Do not close the browser or refresh during processing
   - Processing happens in the background - you can keep the page open

5. **View Results:**
   - Once complete, you'll see:
     - A "View invoices" button linking to all generated invoices
     - A results table showing:
       - Customer names
       - Quantities
       - Values
       - Invoice links
     - A "Download invoice generation results" button to export the results

6. **Download Results:**
   - Click "Download invoice generation results" to save a CSV with all invoice links
   - Use this for record-keeping and tracking

**Important Notes:**
- Invoice generation happens asynchronously - be patient
- Each invoice is created as a separate contract in Tabs
- The tool uses a throttling mechanism (1 second between requests) to avoid rate limiting
- If processing fails, check the task queue control panel for error details

---

## CSV File Requirements

### Required Columns

| Column Name | Required | Description | Example |
|------------|----------|-------------|---------|
| `Rep Invoicing Tabs Customer Name` | ✅ Yes | Customer name as it appears in your system | "Acme Corp" |
| `Rep Invoicing Invoice Quantity` | ✅ Yes | Quantity/units for the invoice line item | 100 |
| `Rep Invoicing Invoice Value` | ✅ Yes | Dollar amount (can include $ and commas) | "$1,234.56" or "1234.56" |

### Optional Columns

| Column Name | Required | Description | Example |
|------------|----------|-------------|---------|
| `Rep Invoicing Tabs Customer ID` | ❌ No | Tabs customer ID (speeds up mapping) | "c17ddc7f-097c-4d9c-b92d-ec39c1fd8e1d" |
| `Rep Invoicing Invoice Type` | ❌ No | Product/service name (per row) | "API Credits" |

### CSV Format Guidelines

1. **File Format:** CSV (Comma-Separated Values)
2. **Encoding:** UTF-8 recommended
3. **Headers:** Must match column names exactly (case-sensitive)
4. **Numeric Values:**
   - Can include dollar signs ($) and commas (,)
   - Will be automatically cleaned by the tool
   - Example: "$1,234.56" → 1234.56
5. **Customer Names:**
   - Should match Tabs customer names as closely as possible
   - Include Customer IDs if available for faster processing
6. **Multiple Rows:**
   - Each row represents one invoice line item
   - Multiple rows for the same customer will create multiple line items

### Example CSV Structure

```csv
Rep Invoicing Tabs Customer Name,Rep Invoicing Tabs Customer ID,Rep Invoicing Invoice Type,Rep Invoicing Invoice Quantity,Rep Invoicing Invoice Value
Acme Corp,c17ddc7f-097c-4d9c-b92d-ec39c1fd8e1d,API Credits,1000,5000.00
Beta Inc,,Storage GB,500,2500.00
Gamma LLC,c18ddc8f-098d-4e9d-c93e-ec40c2fe9e2e,Compute Hours,200,3000.00
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Backend URL or API key is None"
**Solution:**
- Verify your `.env` file exists and contains `DEFAULT_TABS_API_KEY`
- Check that the API key is valid for your environment (prod/dev)
- Restart the Streamlit app after updating `.env`

#### Issue: "Missing required columns" error
**Solution:**
- Verify your CSV has the exact column names (case-sensitive)
- Check for extra spaces in column headers
- Download the template CSV to see the correct format
- Ensure columns are named exactly:
  - `Rep Invoicing Tabs Customer Name`
  - `Rep Invoicing Invoice Quantity`
  - `Rep Invoicing Invoice Value`

#### Issue: Customers not matching
**Solution:**
- Enable fuzzy matching in Step 2
- Adjust the fuzzy matching threshold (try 0.85-0.95)
- Manually map customers using the dropdown
- Verify customer names match Tabs exactly
- Include Customer IDs in your CSV for automatic matching

#### Issue: Net terms mapping fails
**Solution:**
- Verify API connection is working
- Check that customers have existing contracts/obligations in Tabs
- Try a different Net Term Mode (Most Common, Smallest, Largest)
- Ensure you don't refresh the page during net term mapping

#### Issue: Invoice generation stuck or slow
**Solution:**
- Processing happens in the background - be patient
- Check the task queue control panel (if visible) for status
- The tool throttles requests (1 second between each) to avoid rate limiting
- Large batches may take several minutes
- Do not refresh or close the browser during processing

#### Issue: Logo not displaying
**Solution:**
- Verify `FALL_BACK_LOGO` is set in `.env` with a valid image URL
- Ensure the URL is publicly accessible
- Check that the URL points directly to an image file (not a webpage)

#### Issue: App won't start
**Solution:**
- Verify virtual environment is activated: `source venv/bin/activate`
- Check Python version: `python3 --version` (should be 3.x)
- Reinstall dependencies: `pip install -r requirements.txt`
- Check for port conflicts (default port 8501)

### Getting Help

If you encounter issues not covered here:
1. Check the browser console for error messages
2. Review the Streamlit terminal output for detailed errors
3. Verify your API credentials are correct
4. Ensure you're using the correct environment (prod vs dev)

---

## Best Practices

### Before Starting

1. **Prepare your CSV file:**
   - Use the template as a reference
   - Include Customer IDs if available
   - Verify all required columns are present
   - Clean your data (remove empty rows, fix formatting)

2. **Verify API access:**
   - Test your API key works
   - Confirm you have access to the customers you're invoicing
   - Check that revenue categories and integration items exist

3. **Plan your invoice details:**
   - Decide on invoice date
   - Determine product names/descriptions
   - Select appropriate revenue category and integration item

### During Processing

1. **Don't refresh during critical operations:**
   - Net term mapping
   - Invoice generation
   - Large file processing

2. **Review each step carefully:**
   - Verify customer mappings before proceeding
   - Check invoice preview before confirming
   - Double-check contract name before generating

3. **Use the reset function:**
   - If you need to go back, use the sidebar reset controls
   - Reset to the appropriate step to make changes

### After Completion

1. **Download results:**
   - Always download the invoice generation results CSV
   - Keep this for your records

2. **Verify invoices:**
   - Click "View invoices" to review in Tabs
   - Check a few invoices manually to ensure accuracy
   - Verify amounts, dates, and customer mappings

3. **Documentation:**
   - Save your CSV file used for the run
   - Keep the results CSV for audit trail
   - Note any manual corrections made

### Data Quality Tips

1. **Customer Names:**
   - Use exact names from Tabs when possible
   - Include Customer IDs for 100% accuracy
   - Avoid special characters or extra spaces

2. **Numeric Values:**
   - Use consistent formatting
   - Tool handles $ and commas, but consistent format is better
   - Verify totals match your expectations

3. **Product Names:**
   - Use descriptive, consistent names
   - Consider including product names in CSV for flexibility
   - Keep names concise but clear

---

## Appendix

### Reset Function

The tool includes a reset function in the sidebar:
- Select the step number (1-4) you want to reset to
- Click "Reset" button
- This will clear all data from that step forward
- Useful for making corrections without starting over

### Refresh Data Function

Use "Refresh Data" button in sidebar to:
- Reload customers from Tabs
- Refresh revenue categories
- Update integration items
- Useful if data changes in Tabs after you've started

### Task Queue

The tool uses a background task queue for invoice generation:
- Processes invoices asynchronously
- Shows progress in sidebar (if enabled)
- Handles rate limiting automatically
- Can process large batches efficiently

---

**End of SOP**

For questions or issues, contact the development team or refer to the project README.md file.

