import logging
import time
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config_loader import get_config
from core import driver_manager
from pages.login_page import LoginPage
from pages.mva_input_page import MVAInputPage
from utils.data_loader import load_mvas
from utils.ui_helpers import is_mva_known

# Define the base file name to match the script name
SCRIPT_NAME = "ConfirmWorkItemStatus"

# --- Set up logging to a file ---
logging.basicConfig(
    filename=f'{SCRIPT_NAME}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a logger instance for this script
log = logging.getLogger(__name__)

# --- Load configuration from config.json ---
USERNAME = get_config("username")
PASSWORD = get_config("password")
LOGIN_ID = get_config("login_id")
DELAY = get_config("delay_seconds", default=2)

def check_work_item_status(driver, mva):
    """
    Checks the status of the single PM work item by reading its status div.
    Returns 'closed', 'open', or 'unknown'.
    """
    log.info(f"Checking work item status for {mva}")
    try:
        # Wait for the work item tab to be clickable and click it
        work_item_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-tab-id='workItems']"))
        )
        work_item_tab.click()
        log.info(f"Work item tab clicked for {mva}.")

        # Find the status div for the PM work item using the new, precise XPath
        status_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//strong[text()='Complaints']/parent::div/ancestor::div[contains(@class, 'fleet-operations-pwa__scan-record__')]/descendant::div[contains(@class, 'fleet-operations-pwa__scan-record-header-title-right')]")
            )
        )
        
        # Read the text from the status div
        status_text = status_div.text.strip().lower()
        log.info(f"Found PM work item status: {status_text}")

        if status_text == "complete":
            return {"status": "closed"}
        else:
            return {"status": "open"}

    except Exception:
        # If the work item tab or status div is not found, the status is unknown
        log.warning(f"Could not find a PM work item status for {mva}, status is UNKNOWN.")
        return {"status": "unknown"}

# --- Main script logic ---
if __name__ == "__main__":
    log.info("=" * 80)
    log.info(f">>> Starting Work Item Status Confirmation from {SCRIPT_NAME}.py")
    log.info("=" * 80)

    # Load MVAs from CSV
    try:
        csv_file_path = os.path.join(r"C:\Temp\Python\data", f"{SCRIPT_NAME}.csv")
        mvas = load_mvas(csv_file_path)
    except FileNotFoundError:
        log.error(f"Could not find the CSV file. Please make sure {csv_file_path} exists.")
        exit(1)

    # Initialize the web driver
    driver = driver_manager.get_or_create_driver()
    log.info(f"Driver initialized.")

    try:
        # Perform login
        login_page = LoginPage(driver)
        login_page.ensure_ready(USERNAME, PASSWORD, LOGIN_ID)
        log.info("Login successful.")
        time.sleep(DELAY)

        # Loop through all MVAs from the CSV
        for mva in mvas:
            log.info("=" * 80)
            log.info(f">>> Processing MVA: {mva}")
            log.info("=" * 80)

            # Enter the MVA into the input field
            mva_page = MVAInputPage(driver)
            field = mva_page.find_input()

            if not field:
                log.error(f"[MVA] {mva} — input field not found, skipping.")
                continue
            else:
                field.clear()
                field.send_keys(mva)
                time.sleep(5)

                # Check if MVA is valid before proceeding
                if not is_mva_known(driver, mva):
                    log.warning(f"[MVA] {mva} — invalid/unknown MVA, skipping.")
                    continue
                
                # Check the work item status using the new function
                res = check_work_item_status(driver, mva)
                
                # Confirm and log the status
                status = res.get("status", "unknown")
                if status == "closed":
                    log.info(f"[WORKITEM] {mva} — Work item is CLOSED.")
                elif status == "open":
                    log.info(f"[WORKITEM] {mva} — Work item is OPEN.")
                else:
                    log.warning(f"[WORKITEM] {mva} — Work item status is UNKNOWN: {status}.")

    except Exception as e:
        log.error(f"An error occurred: {e}")

    finally:
        log.info("Process finished. Closing browser...")
        driver_manager.quit_driver()
        log.info("Browser closed.")