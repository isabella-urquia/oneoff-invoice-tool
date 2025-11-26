import streamlit as st
from openai import OpenAI
from api.main import check_valid_token
from functools import wraps
import shutil
import os
import random
from helper.task_queue import TaskQueue
import time
from dotenv import load_dotenv
from helper.logger import print_logger



# Load environment variables from .env file (for local development)
load_dotenv()

# Helper function to get env vars from either secrets (Streamlit Cloud) or environment (local)
def get_env_var(key, default=None):
    """Get environment variable from Streamlit secrets (Cloud) or os.environ (local)"""
    # Try Streamlit secrets first (for Cloud deployment)
    try:
        import streamlit as st_module
        if hasattr(st_module, 'secrets'):
            try:
                secrets = st_module.secrets
                if key in secrets:
                    return secrets[key]
            except (AttributeError, RuntimeError, TypeError):
                # Streamlit not initialized yet or secrets not available
                pass
    except:
        pass
    # Fall back to environment variable (for local development)
    return os.getenv(key, default)

MODE = get_env_var("MODE")
# Get port safely - may not be available during import on Streamlit Cloud
try:
    PORT = st.get_option("server.port")
except:
    PORT = 8501  # Default port

def eval_bool_env_var(env_var_name, default_value=True):
    env_var_value = get_env_var(env_var_name, default_value)
    match env_var_value:
        case "True":
            return True
        case "False":
            return False
        case True:
            return True
        case False:
            return False
        case "true":
            return True
        case "false":
            return False
        case _:
            return default_value

custom_logos_enabled = eval_bool_env_var("LOGO_ENABLED", True) # If True, the custom logos will be enabled.
APPLICATION_URL = f"http://localhost:{PORT}" if MODE == "local" else "https://nos-kwoy.onrender.com"
TABS_LOGO = f"https://trust.tabs.inc/api/share/11385e5d-a2a5-4bd6-9e8d-c0721fbb422f/logo.png?version=2"
fall_back_logo = get_env_var("FALL_BACK_LOGO", TABS_LOGO) # If custom logos are not enabled, the fallback logo will be used.


if custom_logos_enabled:
    print("USING CUSTOM LOGOS")
    NOS_LOGO = f"{APPLICATION_URL}/app/static/Nos Profile Pic.png"
    NOS_MONEY_LOGO = f"{APPLICATION_URL}/app/static/Nos Gimme da maney.png"
    NOS_WORKING_LOGO = f"{APPLICATION_URL}/app/static/NOS Working.png"
    NOS_INSPECTOR_LOGO = f"{APPLICATION_URL}/app/static/NOS Inspector.png"
    NOS_DATA_LOGO = f"{APPLICATION_URL}/app/static/Nos data.png"
    WORKING_GIF = f"{APPLICATION_URL}/app/static/working.gif"
else:
    print("USING FALLBACK LOGOS")
    NOS_LOGO = fall_back_logo
    NOS_MONEY_LOGO = fall_back_logo
    NOS_WORKING_LOGO = fall_back_logo
    NOS_INSPECTOR_LOGO = fall_back_logo
    NOS_DATA_LOGO = fall_back_logo
    WORKING_GIF = fall_back_logo



def switch_to_default_env_merchant():
    default_tabs_api_token = get_env_var("DEFAULT_TABS_API_KEY")
    default_merchant_name = get_env_var("DEFAULT_MERCHANT_NAME", "Default Merchant")
    default_environment = get_env_var("DEFAULT_ENVIRONMENT", get_env_var("ENVIRONMENT", "prod"))
    default_merchant_id = get_env_var("DEFAULT_MERCHANT_ID", default_merchant_name)
    print_logger("Default Token Found: ", default_tabs_api_token is not None and default_tabs_api_token != "")
    print_logger("default_merchant_name:",default_merchant_name)
    print_logger("default_environment:",default_environment)
    # Only require API key - use defaults for merchant name and environment if not provided
    # Check that token exists and is not empty
    if default_tabs_api_token is not None and default_tabs_api_token.strip() != "":
        switch_token(
            merchant_id=default_merchant_id,
            merchant_name=default_merchant_name,
            tabs_api_token=default_tabs_api_token,
            environment=default_environment
        )
    else:
        print_logger("DEFAULT_TABS_API_KEY not found or empty in .env file - API key will need to be set manually")
   
def get_app_feature_flags():
    st.session_state.debug_mode_enabled = eval_bool_env_var("DEBUG_MODE_ENABLED", False) # If True, the debug mode will be enabled.
    st.session_state.salesforce_page_enabled = eval_bool_env_var("SALESFORCE_PAGE_ENABLED", True)    # If True, the Salesforce query page will be enabled.
    st.session_state.workflow_page_enabled = eval_bool_env_var("WORKFLOW_PAGE_ENABLED", True)                    # If True, the workflow page will be enabled.
    st.session_state.bulk_api_page_enabled = eval_bool_env_var("BULK_API_PAGE_ENABLED", True)                    # If True, the bulk API page will be enabled.
    st.session_state.object_viewer_page_enabled = eval_bool_env_var("OBJECT_VIEWER_PAGE_ENABLED", True)          # If True, the object viewer page will be enabled.
    st.session_state.usage_validator_page_enabled = eval_bool_env_var("USAGE_VALIDATOR_PAGE_ENABLED", True)      # If True, the usage validator page will be enabled.
    st.session_state.usage_analytics_page_enabled = eval_bool_env_var("USAGE_ANALYTICS_PAGE_ENABLED", True)      # If True, the usage analytics page will be enabled.
    st.session_state.data_app_page_enabled = eval_bool_env_var("DATA_APP_PAGE_ENABLED", True)                    # If True, the data app page will be enabled.
    st.session_state.request_history_page_enabled = eval_bool_env_var("REQUEST_HISTORY_PAGE_ENABLED", True)      # If True, the request history page will be enabled.
    st.session_state.super_powers_page_enabled = eval_bool_env_var("SUPER_POWERS_PAGE_ENABLED", True)            # If True, the super powers page will be enabled.
    st.session_state.customer_inspector_page_enabled = eval_bool_env_var("CUSTOMER_INSPECTOR_PAGE_ENABLED", True)# If True, the customer inspector page will be enabled.
    st.session_state.home_page_enabled = eval_bool_env_var("HOME_PAGE_ENABLED", True)                            # If True, the home page will be enabled.
    st.session_state.logo_enabled = eval_bool_env_var("LOGO_ENABLED", True)                                      # If True, the custom NOS logo will be enabled.
    st.session_state.fall_back_logo = eval_bool_env_var("FALL_BACK_LOGO", TABS_LOGO)                             # If LOGO_ENABLED is False, the fallback logo will be used
    st.session_state.fun_sidebar_enabled = eval_bool_env_var("FUN_SIDEBAR_ENABLED", True)                        # If True, the fun sidebar will be enabled.
    st.session_state.bulk_gifs = eval_bool_env_var("BULK_GIFS", True)                                            # If True, the bulk job completion will be celebrated + raccons will be shown.
    st.session_state.developer_settings_enabled = eval_bool_env_var("DEVELOPER_SETTINGS_ENABLED", True)          # If True, the developer settings will be enabled.
    st.session_state.one_off_usage_invoice_page_enabled = eval_bool_env_var("ONE_OFF_USAGE_INVOICES", True)      # If True, the one off usage invoice page will be enabled.
    st.session_state.simple_auth = eval_bool_env_var("SIMPLE_AUTH", False)                                       # If True, the simple auth will be enabled. It will only require a username and password to access the app.
    st.session_state.password = get_env_var("PASSWORD")
    st.session_state.page_title = get_env_var("PAGE_TITLE", "Tabs Internal Tool")
    st.session_state.max_allowed_threads = int(os.getenv("DEFAULT_THREADS", 1))

    print_logger("=============== APP FEATURE FLAGS ==================")
    print_logger(f"Salesforce page enabled: {st.session_state.salesforce_page_enabled}")
    print_logger(f"Workflow page enabled: {st.session_state.workflow_page_enabled}")
    print_logger(f"Bulk API page enabled: {st.session_state.bulk_api_page_enabled}")
    print_logger(f"Object viewer page enabled: {st.session_state.object_viewer_page_enabled}")
    print_logger(f"Usage validator page enabled: {st.session_state.usage_validator_page_enabled}")
    print_logger(f"Usage analytics page enabled: {st.session_state.usage_analytics_page_enabled}")
    print_logger(f"Data app page enabled: {st.session_state.data_app_page_enabled}")
    print_logger(f"Request history page enabled: {st.session_state.request_history_page_enabled}")
    print_logger(f"Super powers page enabled: {st.session_state.super_powers_page_enabled}")
    print_logger(f"Customer inspector page enabled: {st.session_state.customer_inspector_page_enabled}")
    print_logger(f"Home page enabled: {st.session_state.home_page_enabled}")
    print_logger(f"Logo enabled: {st.session_state.logo_enabled}")
    print_logger(f"Fall back logo: {st.session_state.fall_back_logo}")
    print_logger(f"Fun sidebar enabled: {st.session_state.fun_sidebar_enabled}")
    print_logger(f"Bulk gifs enabled: {st.session_state.bulk_gifs}")
    print_logger(f"Developer settings enabled: {st.session_state.developer_settings_enabled}")
    print_logger(f"One off usage invoice page enabled: {st.session_state.one_off_usage_invoice_page_enabled}")
    print_logger(f"Simple auth enabled: {st.session_state.simple_auth}")
    print_logger("======================================================\n\n")

def configure_page_config(expanded_sidebar=True):
    if "tabs_icon" not in st.session_state:
        st.session_state.tabs_icon = NOS_LOGO
    if "page_title" not in st.session_state:
        # Read from environment variable directly if not in session_state yet
        page_title = get_env_var("PAGE_TITLE", "Tabs Internal Tool")
        st.session_state.page_title = page_title
    else:
        page_title = st.session_state.page_title
    st.set_page_config(page_title=page_title, page_icon=st.session_state.tabs_icon,layout="wide", initial_sidebar_state="collapsed" if not expanded_sidebar else "expanded")

def configure_tabs_links(force=False, environment="prod"):
    if environment not in ["prod", "dev", None]:
        raise ValueError("Environment must be either 'prod' or 'dev'")
    if environment is None:
        environment = st.session_state.get("environment", "prod")
    # Ensure environment has a valid value
    if environment not in ["prod", "dev"]:
        environment = "prod"  # Default to prod if invalid
    match environment:
        case "prod":
            if "garage_link" not in st.session_state or force:
                st.session_state.garage_link = "https://garage.tabsplatform.com/"
            if "merchant_link" not in st.session_state or force:
                st.session_state.merchant_link = "https://merchant.tabsplatform.com/"
            if "backend_url" not in st.session_state or force:
                st.session_state.backend_url = "https://integrators.prod.api.tabsplatform.com"
        case "dev":
            if "garage_link" not in st.session_state or force:
                st.session_state.garage_link = "https://dev.garage.tabsplatform.com/dev"
            if "merchant_link" not in st.session_state or force:
                st.session_state.merchant_link = "https://dev.app.tabsplatform.com/merchant/"
            if "backend_url" not in st.session_state or force:
                st.session_state.backend_url = "https://integrators.dev.api.tabsplatform.com"
        case _:
            # Fallback to prod if somehow we get here
            if "backend_url" not in st.session_state or force:
                st.session_state.backend_url = "https://integrators.prod.api.tabsplatform.com"

def switch_token(merchant_id, merchant_name, tabs_api_token, environment):
    # Save the old values in case we need to revert
    old_merchant_id = st.session_state.merchant_id
    old_token = st.session_state.tabs_api_token
    old_merchant_name = st.session_state.merchant_name
    old_environment = st.session_state.environment
    old_valid_token = st.session_state.valid_token

    # Set the new values
    st.session_state.merchant_id = merchant_id
    st.session_state.tabs_api_token = tabs_api_token
    st.session_state.merchant_name = merchant_name
    st.session_state.environment = environment
    configure_tabs_links(force=True, environment=environment)
    st.session_state.valid_token = check_valid_token(tabs_api_token)

    if not st.session_state.valid_token:
        st.toast(f"Invalid token provided for {merchant_name}, reverting to old values")
        st.session_state.tabs_api_token = old_token
        st.session_state.merchant_name = old_merchant_name
        st.session_state.environment = old_environment
        st.session_state.merchant_id = old_merchant_id
        configure_tabs_links(force=True, environment=old_environment)
        st.session_state.valid_token = old_valid_token
    else:
        st.toast(f"Token set for {merchant_name}")
        time.sleep(1)
        st.rerun()

def set_up_openai_client(force=False):
    if "OPENAI_API_KEY" not in st.session_state or force:
        st.session_state["OPENAI_API_KEY"] = None
        if st.session_state.mode == "running_with_secrets":
            if "OPENAI_API_KEY" in st.secrets:
                st.session_state["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    if "OPENAI_CLIENT" not in st.session_state or force:
        st.session_state["OPENAI_CLIENT"] = None
        if st.session_state["OPENAI_API_KEY"] is not None:
            st.session_state["OPENAI_CLIENT"] = OpenAI(api_key=st.session_state["OPENAI_API_KEY"])

def initialize_core_session_state(force=False,environment=None):
    if "environment" not in st.session_state:
        get_app_feature_flags()
        st.session_state.environment = get_env_var("ENVIRONMENT", "prod")
    # Ensure environment is set before configuring links
    if environment is None:
        environment = st.session_state.environment or "prod"
    configure_tabs_links(force=force, environment=environment)
    # Ensure backend_url is always set (fallback to prod if somehow not set)
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = "https://integrators.prod.api.tabsplatform.com"
    # set_up_openai_client(force=force)
    if "valid_token" not in st.session_state:
        st.session_state.valid_token = False
    if "tabs_api_token" not in st.session_state:
        st.session_state.tabs_api_token = None
    if "merchant_name" not in st.session_state:
        st.session_state.merchant_name = None
    if "merchant_id" not in st.session_state:
        st.session_state.merchant_id = None
    if "tabs_icon" not in st.session_state:
        st.session_state.tabs_icon = NOS_LOGO
    if "request_history" not in st.session_state or force:
        st.session_state.request_history = []
    if "max_allowed_threads" not in st.session_state:
        st.session_state.max_allowed_threads = 1
    if "task_queue" not in st.session_state or force:
        st.session_state.task_queue = TaskQueue(
            api_key=st.session_state.tabs_api_token, 
            backend_url=st.session_state.backend_url,
            num_workers=st.session_state.max_allowed_threads
        )
    
    if "first_run" not in st.session_state:
        st.session_state.first_run = True
        print_logger("MODE:",MODE)
        print_logger("APPLICATION URL",APPLICATION_URL)
    
    # Try to load default merchant/env on every run if not already set (not just first run)
    # For local mode, always try to load; for other modes, only if token is missing
    should_try_load = False
    if MODE == "local" or MODE == "whitelisted":
        should_try_load = True
    elif MODE is None or MODE == "":
        # If MODE isn't set, assume local development and try to load
        should_try_load = True
    
    if should_try_load and (st.session_state.tabs_api_token is None or not st.session_state.valid_token):
        print_logger("Attempting to load default merchant and environment from .env")
        print_logger(f"MODE: {MODE}, Token exists: {st.session_state.tabs_api_token is not None}, Valid: {st.session_state.valid_token}")
        switch_to_default_env_merchant()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True
        if st.session_state.simple_auth: # If simple auth is enabled, the user will be prompted to enter a username and password to access the app.
            st.session_state.authenticated = False



def fun_sidebar():
    if st.session_state.fun_sidebar_enabled:
        with st.sidebar.expander("Music Settings", icon=":material/music_note:"):

            song_settings = st.radio("Choose a song",options=["No Music","Hyperdrive Mode","Vibe Mode","Go Fast Go Furious","Calm Mode"],index=0)

            if song_settings == "No Music":
                pass
            elif song_settings == "Hyperdrive Mode":
                video_url = "https://youtu.be/FTzJNutzUPs?&t=19"
                st.video(video_url,autoplay=True,loop=True,start_time=19)
            elif song_settings == "Vibe Mode":
                video_url = "https://youtu.be/UOYk5qT3ffo?feature=shared"
                st.video(video_url,autoplay=True,loop=True,start_time=0)
            elif song_settings == "Go Fast Go Furious":
                video_url = "https://youtu.be/pS5d77DQHOI"
                st.video(video_url,autoplay=True,loop=True)
            elif song_settings == "Calm Mode":
                video_url = "https://youtu.be/ANkxRGvl1VY?feature=shared"
                st.video(video_url,autoplay=True,loop=True,start_time=0)

@st.dialog("Developer Config",width="large")
def developer_config():


    with st.form("set_environment"):
        st.subheader("Set Environment & API Keys")
        merchant_id = st.text_input("Merchant ID",key="merchant_id_input",value=st.session_state.merchant_id, help="Enter the ID of the merchant you are using for this tool.")
        merchant_name = st.text_input("Merchant Name",key="merchant_name_input",value=st.session_state.merchant_name, help="Enter the name of the merchant you are using for this tool.")
        tabs_api_token = st.text_input("Tabs API Token",key="tabs_api_token_input",value=st.session_state.tabs_api_token, help="Place your merchants API key here and select the environment. In 99% of cases you will be using the **`prod`** environment.")
        cols = st.columns([1,1])

        environment = cols[0].segmented_control(
            label="Environment",
            options=["dev","prod"],
            default=st.session_state.environment,
            selection_mode="single",
        )
        cols[1].write(" ")
        if cols[1].form_submit_button("Update Environment & API Keys", icon=":material/update:", type="primary", use_container_width=True):
            is_merchant_id_blank = merchant_id is None or merchant_id == ""
            is_merchant_name_blank = merchant_name is None or merchant_name == ""
            is_tabs_api_token_blank = tabs_api_token is None or tabs_api_token == ""
            if is_merchant_id_blank or is_merchant_name_blank or is_tabs_api_token_blank:
                st.error("Please fill in all fields", icon=":material/error:")
            else:
                initialize_core_session_state(force=True,environment=environment)
                switch_token(
                    merchant_id=merchant_id,
                    merchant_name=merchant_name,
                    tabs_api_token=tabs_api_token,
                    environment=environment,
                )

    st.divider()
    st.write("**Status Overview & Helpful Links**")
    cols = st.columns(2)
    cols[0].write(f"*Environment:* `{st.session_state.environment}`")
    cols[1].write(f"*Valid Token:* `{st.session_state.valid_token}`")
    cols = st.columns(2)
    with cols[0]:
        st.link_button("Garage App",st.session_state.garage_link, use_container_width=True, icon=":material/car_crash:")
    with cols[1]:
        st.link_button("Merchant App",st.session_state.merchant_link, use_container_width=True, icon=":material/shopping_cart:")
    
def sidebar_config():
    if st.session_state.developer_settings_enabled:
        with st.sidebar.container(border=False):
            if st.button("Developer Settings", use_container_width=True, icon=":material/settings:"):
                developer_config()

def every_page_config(expanded_sidebar=True):
    configure_page_config(expanded_sidebar=expanded_sidebar)
    if "developer_settings_enabled" in st.session_state:
        if st.session_state.developer_settings_enabled:
            st.sidebar.write("**NOS** Version **`v2.0.1`**")
    
    st.logo(TABS_LOGO, icon_image=TABS_LOGO)
    initialize_core_session_state()
    if st.session_state.valid_token:
        if st.session_state.environment == "prod":
            icon = ":material/brightness_7:"
            color = "green"
        elif st.session_state.environment == "dev":
            icon = ":material/brightness_2:"
            color = "orange"
        st.sidebar.badge(f"**{st.session_state.merchant_name}** | {st.session_state.environment}", icon=icon, color=color, width="stretch")
    sidebar_config()
    fun_sidebar()

def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if st.session_state.tabs_api_token is None:
            return None
        if not st.session_state.valid_token:
            return None
        return func(*args, **kwargs)
    return wrapper

processing_messages = [
    "🛠️ Recalibrating quantum flux capacitors…",
    "🔦 Herding rogue photons back into the beam…",
    "📡 Decrypting alien transmission in base-42…",
    "🌀 Re-aligning the warp stabilizer array…",
    "☕ Synthesizing antimatter espresso shots…",
    "🐹 Engaging hyperdrive hamsters… please stand by.",
    "🤖 Negotiating peace with rebellious nanobots…",
    "🌌 Temporarily phasing into the multiverse…",
    "⚡ Converting thoughts into tachyon streams…",
    "🕳️ Assembling miniature black holes… just for fun.",
    "🧠 Downloading thoughts from the hive mind…",
    "🕶️ Polishing space goggles for better clarity…",
    "🍜 Spooling up the neutrino-powered noodle-maker…",
    "👽 Decoding Martian sarcasm algorithms…",
    "🎧 Tuning into the 7th dimension playlist…",
    "🔍 Running diagnostics on Schrödinger's toaster…",
    "🕰️ Aligning with parallel timelines (might take a sec)…",
    "🥤 Uploading zero-point energy smoothie recipes…",
    "❤️‍🔥 Teaching robots how to love (still loading…)",
    "🪙 Wrapping spacetime in aluminum foil…"
]

def return_processing_message():
    return processing_messages[random.randint(0, len(processing_messages) - 1)]


# def bulk_job_control_panel(render_object=st):

#     total_tasks = len(st.session_state.task_queue.tasks)
#     completed_tasks = len([task for task in st.session_state.task_queue.tasks.values() if task.status == 'completed'])
#     failed_tasks = len([task for task in st.session_state.task_queue.tasks.values() if task.status == 'failed'])
#     pending_tasks = len([task for task in st.session_state.task_queue.tasks.values() if task.status == 'pending'])
#     is_running = st.session_state.task_queue.processing



def control_panel(render_object=st.sidebar):
    with render_object.container(border=True):
        st.write("**Task Queue Control Panel**")

        # Pending tasks in the queue
        is_running = st.session_state.task_queue.processing
        pending_tasks = st.session_state.task_queue.pending_tasks
        total_tasks = st.session_state.task_queue.task_size
        completed_tasks = st.session_state.task_queue.completed_tasks
        failed_tasks = st.session_state.task_queue.failed_tasks
        done_tasks = completed_tasks + failed_tasks
        if total_tasks == 0:
            done_percentage = 0
            success_percentage = 0
            failure_percentage = 0
        else:
            done_percentage = done_tasks/total_tasks
            success_percentage = completed_tasks/total_tasks
            failure_percentage = failed_tasks/total_tasks
        has_tasks = total_tasks > 0
        has_remaining_tasks = pending_tasks > 0
        can_start = has_tasks and not is_running
        can_stop = is_running

        st.write(f"Running: `{is_running}`")
        if "developer_settings_enabled" in st.session_state:
            if st.session_state.developer_settings_enabled:
                st.write(f"Threads: `{st.session_state.max_allowed_threads}`")

        st.session_state.global_progress_bar = st.empty()


        st.session_state.global_progress_bar.progress(done_percentage, text=f"{done_tasks}/{total_tasks} Tasks Done")
        # success_bar = st.progress(success_percentage, text=f"{completed_tasks}/{total_tasks} Tasks Success")
        # failure_bar = st.progress(failure_percentage, text=f"{failed_tasks}/{total_tasks} Tasks Failure")
        cols = st.columns(2)
        start_button = cols[0].button("▶️", disabled=not can_start, use_container_width=True)
        stop_button = cols[1].button("⏸️", disabled=not can_stop, use_container_width=True)
        if start_button:
            with st.spinner("Starting task queue"):
                st.session_state.task_queue.start_processing()
            st.session_state.tabs_icon = "🚧"
            st.rerun()
        if stop_button:
            with st.spinner("Stopping task queue"):
                st.session_state.task_queue.stop_processing()
            with st.spinner("Syncing request history"):
                sync_request_history()
            st.session_state.tabs_icon = "🟠"
            st.rerun()
        help_text = "Hit refresh to get the latest success and failure counts, only the done progress bar is updated in real time for performance reasons."
        st.button("Refresh", use_container_width=True, icon=":material/refresh:", help=help_text)
        if is_running:
            if st.session_state.bulk_gifs:
                st.write("If you see this, it is running in the background")
                st.image(WORKING_GIF)



    


@st.fragment(run_every=1)
def update_task_queue():
    total_tasks = st.session_state.task_queue.task_size
    pending_tasks = st.session_state.task_queue.pending_tasks
    done_tasks = st.session_state.task_queue.completed_tasks + st.session_state.task_queue.failed_tasks
    is_running = st.session_state.task_queue.processing
    no_tasks_left = pending_tasks == 0
    if total_tasks == 0:
        done_percentage = 0
    else:
        done_percentage = done_tasks/total_tasks

    # Only update progress bar if it exists (control panel is visible)
    if "global_progress_bar" in st.session_state:
        st.session_state.global_progress_bar.progress(done_percentage, text=f"{done_tasks}/{total_tasks} Tasks Done")
        
    # If all tasks are completed, show the results
    if no_tasks_left and is_running:
        sync_request_history()
        st.toast("All tasks processed, automatically stopping the task queue and refreshing the page")
        st.session_state.tabs_icon = "✅"
        if st.session_state.bulk_gifs:
            st.balloons()
        st.session_state.task_queue.stop_processing()
        st.rerun()

def sync_request_history():
    st.toast("Updating request history")
    for task in st.session_state.task_queue.tasks:
        if st.session_state.task_queue.tasks[task].request_logs is not None:
            for request_log_i in st.session_state.task_queue.tasks[task].request_logs:
                found_hash = request_log_i.get("hash", None)
                already_synced = False
                checked_hashes = []
                for request_log in st.session_state.request_history:
                    if request_log is None:
                        request_log = {}
                    request_log_hash = request_log.get("hash", None)
                    checked_hashes.append(request_log_hash)
                    if request_log_hash == found_hash and found_hash is not None:
                        already_synced = True
                if not already_synced:
                    st.session_state.request_history.append(request_log_i)
                if already_synced:
                    pass


@token_required
def background_worker(render_object=st.sidebar):
    # Skip control panel for One Off Usage Invoices page (it has its own Help & Controls)
    if st.session_state.get("current_page") != "One Off Usage Invoices":
        control_panel(render_object)
    if st.session_state.task_queue.processing:
        update_task_queue()




