# Deployment Guide: Streamlit Cloud

This guide will help you deploy the One Off Usage Invoice Tool to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. A Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
3. Your code pushed to a GitHub repository

## Step 1: Prepare Your Repository

1. **Ensure your code is in a GitHub repository:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

2. **Verify `.gitignore` includes sensitive files:**
   - `.env` should be in `.gitignore` (already included)
   - `venv/` should be ignored
   - `__pycache__/` should be ignored

## Step 2: Create Streamlit Cloud Secrets

Streamlit Cloud uses a secrets management system instead of `.env` files.

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in with your GitHub account**
3. **Click "New app"**
4. **Select your repository and branch**
5. **Before deploying, click "Advanced settings"**
6. **Click "Secrets" to add your environment variables**

### Required Secrets

Add the following secrets in the Streamlit Cloud secrets manager:

```toml
# API Configuration
DEFAULT_TABS_API_KEY = "your_api_key_here"
DEFAULT_MERCHANT_NAME = "Capitalize"
DEFAULT_MERCHANT_ID = "your_merchant_id"
DEFAULT_ENVIRONMENT = "prod"

# Application Settings
MODE = "cloud"
ENVIRONMENT = "prod"
PAGE_TITLE = "Capitalize Invoice Tool"
FALL_BACK_LOGO = "https://media.licdn.com/dms/image/v2/C4E0BAQGLQa71dANC4A/company-logo_200_200/company-logo_200_200/0/1664205665099/capitalize_logo?e=2147483647&v=beta&t=jo_HCFILbmPtoAtGUVdGPe7oTn-nL5AEe3EmD2Tezfo"

# Feature Flags (optional - defaults shown)
LOGO_ENABLED = false
DEVELOPER_SETTINGS_ENABLED = true
ONE_OFF_USAGE_INVOICES = true
SALESFORCE_PAGE_ENABLED = false
WORKFLOW_PAGE_ENABLED = false
BULK_API_PAGE_ENABLED = false
OBJECT_VIEWER_PAGE_ENABLED = false
USAGE_VALIDATOR_PAGE_ENABLED = false
USAGE_ANALYTICS_PAGE_ENABLED = false
DATA_APP_PAGE_ENABLED = false
REQUEST_HISTORY_PAGE_ENABLED = true
SUPER_POWERS_PAGE_ENABLED = false
CUSTOMER_INSPECTOR_PAGE_ENABLED = false
HOME_PAGE_ENABLED = false
DEBUG_MODE_ENABLED = false

# Application Behavior (optional)
DEFAULT_THREADS = 5
SIMPLE_AUTH = false
PASSWORD = "your_password_if_using_simple_auth"
```

**Important:** 
- Replace `your_api_key_here` with your actual Tabs API key
- Replace `your_merchant_id` with your actual merchant ID
- Keep `MODE = "cloud"` for Streamlit Cloud deployment
- Set `ENVIRONMENT` to `"prod"` or `"dev"` based on your needs

## Step 3: Configure App Settings

1. **Main file path:** `app.py`
2. **Python version:** 3.9+ (Streamlit Cloud supports 3.9, 3.10, 3.11)
3. **Branch:** Select your main branch (usually `main` or `master`)

## Step 4: Deploy

1. **Click "Deploy!"**
2. **Wait for the build to complete** (usually 1-2 minutes)
3. **Your app will be available at:** `https://your-app-name.streamlit.app`

## Step 5: Verify Deployment

After deployment, verify:

1. ✅ App loads without errors
2. ✅ Logo displays correctly
3. ✅ Page title shows "Capitalize Invoice Tool"
4. ✅ API connection works (check sidebar for merchant name)
5. ✅ You can upload CSV files
6. ✅ Customer mapping works

## Troubleshooting

### Issue: "Backend URL or API key is None"

**Solution:**
- Verify all secrets are set correctly in Streamlit Cloud
- Check that `DEFAULT_TABS_API_KEY` is set
- Ensure `MODE = "cloud"` is set
- Restart the app from Streamlit Cloud dashboard

### Issue: App fails to start

**Solution:**
- Check the logs in Streamlit Cloud dashboard
- Verify `requirements.txt` includes all dependencies
- Ensure Python version is compatible (3.9+)
- Check that `app.py` is the correct entry point

### Issue: Logo or title not updating

**Solution:**
- Verify `FALL_BACK_LOGO` and `PAGE_TITLE` secrets are set
- Clear browser cache
- Restart the app

### Issue: Import errors

**Solution:**
- Verify all packages in `requirements.txt` are available on PyPI
- Check for any missing dependencies
- Review the build logs for specific import errors

## Updating Your App

To update your deployed app:

1. **Make changes to your code**
2. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
3. **Streamlit Cloud will automatically redeploy** (or click "Reboot app" in dashboard)

## Managing Secrets

To update secrets:

1. Go to your app in Streamlit Cloud dashboard
2. Click "Settings" → "Secrets"
3. Edit the secrets file
4. Click "Save"
5. The app will automatically restart

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use Streamlit secrets** for all sensitive data
3. **Rotate API keys** regularly
4. **Use environment-specific keys** (prod vs dev)
5. **Enable authentication** if needed (`SIMPLE_AUTH = true`)

## Cost

Streamlit Cloud offers:
- **Free tier:** Unlimited public apps, 1 private app
- **Team tier:** More private apps, custom domains (paid)

## Additional Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Streamlit Cloud Status](https://status.streamlit.io/)

---

**Need Help?** Check the Streamlit Cloud logs or refer to the main README.md for local development setup.

