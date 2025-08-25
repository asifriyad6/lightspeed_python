import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# --- Environment variables for secrets ---
EMAIL = os.getenv("KOUNTA_EMAIL")
PASSWORD = os.getenv("KOUNTA_PASSWORD")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# --- Helper functions ---
def safe_click(driver, element, retries=3, delay=1):
    """Click element safely, retrying if intercepted"""
    for attempt in range(retries):
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            time.sleep(delay)
    return False

def safe_find(driver, by, selector, timeout=10):
    """Return element if found, else None"""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    except (TimeoutException, NoSuchElementException):
        return None

def safe_find_all(driver, by, selector, timeout=10):
    """Return list of elements, empty if none found"""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, selector)))
    except (TimeoutException, NoSuchElementException):
        return []

def select_hours_using_keyboard(driver, dropdown_element):
    """Switch dropdown from 'months' to 'hours' using keyboard"""
    try:
        if not safe_click(driver, dropdown_element):
            print("⚠️ Could not click dropdown")
            return False
        time.sleep(0.5)
        dropdown_element.send_keys(Keys.ARROW_UP * 3)
        time.sleep(0.2)
        dropdown_element.send_keys(Keys.ENTER)
        time.sleep(1)
        print("✅ Switched dropdown from 'months' to 'hours'")
        return True
    except Exception as e:
        print(f"⚠️ Exception selecting hours: {e}")
        return False

def force_switch_months_to_hours(driver):
    """Ensure all dropdowns set to 'hours'"""
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        months_dropdowns = safe_find_all(driver, By.CSS_SELECTOR, "input.kYwJhe[readonly][value='months']")
        if not months_dropdowns:
            print("✅ All dropdowns switched to 'hours'")
            return True
        print(f"🔁 Found {len(months_dropdowns)} dropdown(s) still set to 'months', attempt {attempt+1}")
        all_success = True
        for i, dropdown in enumerate(months_dropdowns):
            success = select_hours_using_keyboard(driver, dropdown)
            if not success:
                all_success = False
        if all_success:
            print("✅ Verified: all dropdowns now show 'hours'")
            return True
        attempt += 1
        time.sleep(2)
    print("❌ Could not switch all dropdowns to 'hours' after multiple attempts")
    return False

# --- Set up Chrome ---
options = Options()
options.binary_location = "/usr/bin/chromium-browser"  # Chromium binary path
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)

try:
    # --- LOGIN ---
    driver.get("https://insights.kounta.com/insights?url=/embed/dashboards-next/1231")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "btnLogin"))).click()
    print("✅ Logged in")

    # --- Switch to iframe ---
    WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "lookerFrame")))
    print("✅ Switched to iframe")

    # --- Apply filters ---
    last_7_days_filter = safe_find(driver, By.XPATH, "//span[contains(text(),'is in the last 7 days')]")
    if last_7_days_filter: safe_click(driver, last_7_days_filter)

    modal_input = safe_find(driver, By.CSS_SELECTOR, "input.kYwJhe[readonly][value*='is in the last']")
    if modal_input: safe_click(driver, modal_input)

    is_option = safe_find(driver, By.XPATH, "//div[text()='is'] | //span[text()='is']")
    if is_option: safe_click(driver, is_option)

    dropdowns = safe_find_all(driver, By.CSS_SELECTOR, "input.kYwJhe[readonly][value='months']")
    if dropdowns: safe_click(driver, dropdowns[0])

    hours_option_1 = safe_find(driver, By.XPATH, "//div[contains(text(),'hours')] | //span[contains(text(),'hours')]")
    if hours_option_1: safe_click(driver, hours_option_1)

    input_values = safe_find_all(driver, By.CSS_SELECTOR, "input[data-testid='interval-value']")
    if input_values:
        input_values[0].clear()
        input_values[0].send_keys("228")
    if len(input_values) >= 2:
        input_values[1].clear()
        input_values[1].send_keys("158")

    force_switch_months_to_hours(driver)

    value_required_btn = safe_find(driver, By.XPATH, "//span[contains(@class, 'ChipButton-sc-1ov80kq-0') and .//span[text()='Value required']]")
    if value_required_btn: safe_click(driver, value_required_btn)

    modal_value_input = safe_find(driver, By.CSS_SELECTOR, "input.InputText__StyledInput-sc-6cvg1f-0.iOZCVS")
    if modal_value_input:
        safe_click(driver, modal_value_input)
        modal_value_input.clear()
        modal_value_input.send_keys("Donny|s Bar")
        time.sleep(0.5)
        modal_value_input.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.3)
        modal_value_input.send_keys(Keys.RETURN)

    update_btn = safe_find(driver, By.CSS_SELECTOR, "button.ButtonBase__ButtonOuter-sc-1bpio6j-0.RunButton__IconButtonWithBackground-sc-skoy04-0")
    if update_btn: driver.execute_script("arguments[0].click();", update_btn)

    time.sleep(5)

    # --- Dashboard 1 data retrieval ---
    reconciliations_section = safe_find(driver, By.CSS_SELECTOR, "section[aria-label='No. of Reconciliations']")
    reconciliations_value = "0"
    if reconciliations_section:
        value_span = safe_find(reconciliations_section, By.CSS_SELECTOR, "span.TextBase-sc-90l5yt-0.Span-sc-1e8sfe6-0.Text-sc-1d84yfs-0.jPObWb.eCUHIC > span")
        if value_span:
            reconciliations_value = value_span.text.strip()

    # --- JSON extraction helper ---
    def get_dashboard_json(driver):
        try:
            pre_tag = safe_find(driver, By.TAG_NAME, "pre")
            if pre_tag and pre_tag.text.strip():
                return json.loads(pre_tag.text)
            else:
                return []
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            return []

    # --- Dashboard 1 JSON ---
    data = get_dashboard_json(driver)

    # --- Dashboard 2 ---
    driver.get("https://insights.kounta.com/insights?url=/embed/dashboards-next/1216")
    WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "lookerFrame")))
    print("✅ Switched to iframe for second dashboard")

    this_week_btn = safe_find(driver, By.XPATH, "//span[@role='button' and .//span[normalize-space()='This Week']]")
    if this_week_btn: safe_click(driver, this_week_btn)

    more_btn = safe_find(driver, By.XPATH, "//div[normalize-space()='More'] | //span[normalize-space()='More']")
    if more_btn: safe_click(driver, more_btn)

    previous_week_btn = safe_find(driver, By.XPATH, "//button[.//div[normalize-space()='Previous Week']]")
    if previous_week_btn: safe_click(driver, previous_week_btn)

    site_name_chip = safe_find(driver, By.XPATH, "//div[.//span[normalize-space()='Site Name']]//span[@role='button' and .//span[normalize-space()='is any value']]")
    if site_name_chip: safe_click(driver, site_name_chip)

    site_name_input = safe_find(driver, By.CSS_SELECTOR, "input.InputText__StyledInput-sc-6cvg1f-0.iOZCVS")
    if site_name_input:
        safe_click(driver, site_name_input)
        site_name_input.clear()
        site_name_input.send_keys("Donny|s Bar")
        time.sleep(0.5)
        site_name_input.send_keys(Keys.ARROW_DOWN)
        site_name_input.send_keys(Keys.RETURN)

    # Click outside to close modal
    body_elem = safe_find(driver, By.TAG_NAME, "body")
    if body_elem: safe_click(driver, body_elem)

    update_btn_2 = safe_find(driver, By.CSS_SELECTOR, "button.ButtonBase__ButtonOuter-sc-1bpio6j-0.RunButton__IconButtonWithBackground-sc-skoy04-0")
    if update_btn_2: driver.execute_script("arguments[0].click();", update_btn_2)

    time.sleep(5)

    # --- Dashboard 2 JSON ---
    data1 = get_dashboard_json(driver)

    # --- Prepare payload ---
    payload = {
        "no_of_reconciliations": reconciliations_value,
        "data": data,
        "data1": data1
    }
    print("🔹 Payload ready:", payload)

    # --- POST to n8n ---
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload)
        print("✅ Posted to N8N, response:", resp.status_code)
    except Exception as e:
        print(f"❌ Failed to post to N8N: {e}")

except Exception as e:
    print(f"❌ Exception occurred: {e}")
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
finally:
    driver.quit()
