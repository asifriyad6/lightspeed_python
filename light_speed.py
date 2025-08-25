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
from selenium.common.exceptions import ElementClickInterceptedException

# Environment variables for secrets
EMAIL = os.getenv("KOUNTA_EMAIL")
PASSWORD = os.getenv("KOUNTA_PASSWORD")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# --- Helper functions ---
def safe_click(driver, element, retries=3, delay=1):
    for attempt in range(retries):
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            time.sleep(delay)
    return False

def select_hours_using_keyboard(driver, dropdown_element):
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
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        months_dropdowns = driver.find_elements(By.CSS_SELECTOR, "input.kYwJhe[readonly][value='months']")
        if not months_dropdowns:
            print("✅ All dropdowns switched to 'hours'")
            return True
        print(f"🔁 Found {len(months_dropdowns)} dropdown(s) still set to 'months', attempt {attempt+1}")
        all_success = True
        for i in range(len(months_dropdowns)):
            try:
                dropdown = driver.find_elements(By.CSS_SELECTOR, "input.kYwJhe[readonly][value='months']")[i]
                success = select_hours_using_keyboard(driver, dropdown)
                if not success:
                    all_success = False
            except Exception as e:
                print(f"❌ Exception during dropdown interaction: {e}")
                all_success = False
        if all_success:
            print("✅ Verified: all dropdowns now show 'hours'")
            return True
        attempt += 1
        time.sleep(2)
    raise Exception("❌ Could not switch all dropdowns to 'hours' after multiple attempts")
# --- Set up Chrome ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

try:
    # --- Login ---
    driver.get("https://insights.kounta.com/insights?url=/embed/dashboards-next/1231")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "btnLogin"))).click()
    print("✅ Logged in")

    # --- Switch to iframe ---
    WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "lookerFrame")))
    print("✅ Switched to iframe")

    last_7_days_filter = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'is in the last 7 days')]"))
    )
    safe_click(driver, last_7_days_filter)
    print("✅ Clicked on 'last 7 days' filter")

    time.sleep(1)

    modal_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.kYwJhe[readonly][value*='is in the last']"))
    )
    safe_click(driver, modal_input)
    print("✅ Clicked on modal dropdown input")

    time.sleep(1)

    is_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[text()='is'] | //span[text()='is']"))
    )
    safe_click(driver, is_option)
    print("✅ Selected 'is' from modal dropdown")

    time.sleep(1)

    dropdowns = driver.find_elements(By.CSS_SELECTOR, "input.kYwJhe[readonly][value='months']")
    safe_click(driver, dropdowns[0])
    print("✅ Clicked on first 'months' dropdown")

    time.sleep(1)

    hours_option_1 = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'hours')] | //span[contains(text(),'hours')]"))
    )
    safe_click(driver, hours_option_1)
    print("✅ Selected 'hours' from dropdown #1")

    time.sleep(1)

    input_value_1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='interval-value']"))
    )
    input_value_1.clear()
    input_value_1.send_keys("228")
    print("✅ Entered value 228 for input #1")

    time.sleep(1)

    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input[data-testid='interval-value']")
    if len(all_inputs) >= 2:
        all_inputs[1].clear()
        all_inputs[1].send_keys("158")
        print("✅ Entered value 158 for input #2")

    time.sleep(1)

    force_switch_months_to_hours(driver)

    value_required_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'ChipButton-sc-1ov80kq-0') and .//span[text()='Value required']]"))
    )
    safe_click(driver, value_required_btn)
    print("✅ Clicked on 'Value required' button")

    time.sleep(2)

    modal_value_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.InputText__StyledInput-sc-6cvg1f-0.iOZCVS"))
    )
    safe_click(driver, modal_value_input)
    print("✅ Clicked on modal input for value selection")

    time.sleep(1)

    modal_value_input.clear()
    modal_value_input.send_keys("Donny|s Bar")
    print("✅ Typed 'Donny|s Bar' into the input")

    time.sleep(1)
    modal_value_input.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.5)
    modal_value_input.send_keys(Keys.RETURN)
    print("✅ Selected 'Donny|s Bar' from suggestions")

    update_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ButtonBase__ButtonOuter-sc-1bpio6j-0.RunButton__IconButtonWithBackground-sc-skoy04-0"))
    )
    safe_click(driver, update_btn)
    print("✅ Clicked on 'Update' button to view report")

    time.sleep(5)

    # ✅ Wait for the tile section
    reconciliations_section = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "section[aria-label='No. of Reconciliations']"))
    )

    # ✅ Find the value inside the section
    value_span = reconciliations_section.find_element(
        By.CSS_SELECTOR,
        "span.TextBase-sc-90l5yt-0.Span-sc-1e8sfe6-0.Text-sc-1d84yfs-0.jPObWb.eCUHIC > span"
    )

    # ✅ Extract text
    reconciliations_value = value_span.text.strip()
    print(f"✅ No. of Reconciliations value: {reconciliations_value}")

    from selenium.webdriver.common.action_chains import ActionChains

    # First find the tile container (even if button is not visible yet)
    tile_container = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "section[aria-label='Payments summary']"  # adjust to the tile's aria-label
        ))
    )

    # Hover over the tile container to reveal the actions button
    actions = ActionChains(driver)
    actions.move_to_element(tile_container).perform()
    print("✅ Hovered over the tile container to reveal actions menu")

    # Now wait for the three-dot button to become clickable
    tile_actions_btn = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button[aria-label*='Payments summary - Tile actions']"
        ))
    )
    safe_click(driver, tile_actions_btn)
    print("✅ Clicked tile actions menu")

    # Wait for the menu to appear and click 'Download data'
    download_data_btn = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[.//span[normalize-space()='Download data']]"
        ))
    )
    safe_click(driver, download_data_btn)
    print("✅ Clicked on 'Download data' button")

    # Wait for the combobox wrapper to be ready
    wrapper = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "qr-export-modal-format"))
    )

    # Now find and click the caret icon inside it
    caret_icon = wrapper.find_element(By.CSS_SELECTOR, "[data-testid='caret']")
    safe_click(driver, caret_icon)
    print("✅ Clicked caret icon to open dropdown")

    time.sleep(3)  # allow menu to open

    # Find the input inside combobox
    format_input = wrapper.find_element(By.CSS_SELECTOR, "input#listbox-input-qr-export-modal-format")

    # Press Arrow Down multiple times to reach JSON (4th option)
    for i in range(1):  # CSV is index 0, so press 3 times to reach index 3 (4th item)
        format_input.send_keys(Keys.ARROW_DOWN)
        time.sleep(2)
    print("⬇️ Pressed ARROW_DOWN 2 times to highlight JSON")

    # Now press ENTER to select JSON
    format_input.send_keys(Keys.ENTER)
    print("✅ Pressed ENTER to select JSON")

    # Wait for the "Open in Browser" button to be present and clickable
    try:
        open_browser_btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#qr-export-modal-open"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", open_browser_btn)
        safe_click(driver, open_browser_btn)  # use your safe_click helper
        print("✅ Clicked 'Open in Browser'")
    except Exception as e:
        print(f"❌ Could not click 'Open in Browser': {e}")

    # Wait for new tab
    time.sleep(3)
    tabs = driver.window_handles
    driver.switch_to.window(tabs[-1])
    print("✅ Switched to new tab")

    # Get JSON content
    json_text = driver.find_element(By.TAG_NAME, "pre").text
    print("✅ Retrieved JSON text")

    # Parse JSON
    import json
    data = json.loads(json_text)

    # -----------------------------------------------
    # 🚀 Go to the second dashboard
    # -----------------------------------------------
    driver.get("https://insights.kounta.com/insights?url=/embed/dashboards-next/1216")

    # Wait for iframe to load and switch to it
    WebDriverWait(driver, 20).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "lookerFrame"))
    )
    print("✅ Switched to iframe for second dashboard")

    # Wait for and click the "This Week" filter button
    this_week_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//span[@role='button' and .//span[normalize-space()='This Week']]"
        ))
    )
    safe_click(driver, this_week_btn)
    print("✅ Clicked on 'This Week' filter in second dashboard")

    time.sleep(1)

    # Now wait for and click the "More" button from the dropdown
    more_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[normalize-space()='More'] | //span[normalize-space()='More']"
        ))
    )
    safe_click(driver, more_btn)
    print("✅ Clicked on 'More' option from the dropdown")

    # After clicking "More", wait for the dropdown list to appear
    time.sleep(1)

    # Now wait for and click on "Previous Week"
    previous_week_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[.//div[normalize-space()='Previous Week']]"
        ))
    )
    safe_click(driver, previous_week_btn)
    print("✅ Selected 'Previous Week' from the More dropdown")

    time.sleep(1)

    # Wait for and click the "is any value" chip under "Site Name"
    site_name_chip = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[.//span[normalize-space()='Site Name']]//span[@role='button' and .//span[normalize-space()='is any value']]"
        ))
    )
    safe_click(driver, site_name_chip)
    print("✅ Clicked on 'is any value' filter for Site Name")

    # Wait for the input to appear
    site_name_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "input.InputText__StyledInput-sc-6cvg1f-0.iOZCVS"
        ))
    )
    safe_click(driver, site_name_input)
    print("✅ Focused on Site Name input")

    time.sleep(1)

    # Locate the combobox input by its placeholder or ID
    combo_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "div[role='combobox'] input.InputText__StyledInput-sc-6cvg1f-0.iOZCVS"
        ))
    )

    # Focus on the input
    safe_click(driver, combo_input)
    print("✅ Focused on combobox input")

    # Type your desired value
    combo_input.clear()
    combo_input.send_keys("Donny|s Bar")
    print("✅ Typed 'Donny|s Bar' into combobox input")

    # Wait a bit for suggestions to load
    time.sleep(1)

    # Press Arrow Down and Enter to select the first matching suggestion
    combo_input.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.3)
    combo_input.send_keys(Keys.RETURN)
    print("✅ Selected 'Donny|s Bar' from combobox suggestions")

    time.sleep(1)  # wait a bit for UI to update

    # Click outside input to close dropdown/modal
    driver.find_element(By.TAG_NAME, "body").click()
    print("✅ Clicked outside input to close modal/dropdown")

    time.sleep(1)  # wait for modal to close

    # Wait for the Update button to be clickable
    update_btn_2 = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ButtonBase__ButtonOuter-sc-1bpio6j-0.RunButton__IconButtonWithBackground-sc-skoy04-0"))
    )
    driver.execute_script("arguments[0].click();", update_btn_2)
    print("✅ Clicked Update button via JS")

    # Give it a moment to load the data
    time.sleep(5)

    from selenium.webdriver.common.action_chains import ActionChains

    # First find the tile container (even if button is not visible yet)
    tile_container_2 = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "section[aria-label='Top Reporting Groups']"  # adjust to the tile's aria-label
        ))
    )

    # Hover over the tile container to reveal the actions button
    actions_2 = ActionChains(driver)
    actions_2.move_to_element(tile_container_2).perform()
    print("✅ Hovered over the tile container to reveal actions menu")

    # Now wait for the three-dot button to become clickable
    tile_actions_btn_2 = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button[aria-label*='Top Reporting Groups - Tile actions']"
        ))
    )
    safe_click(driver, tile_actions_btn_2)
    print("✅ Clicked tile actions menu")

    # Wait for the menu to appear and click 'Download data'
    download_data_btn_2 = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[.//span[normalize-space()='Download data']]"
        ))
    )
    safe_click(driver, download_data_btn_2)
    print("✅ Clicked on 'Download data' button")

    # Wait for the combobox wrapper to be ready
    wrapper_2 = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "qr-export-modal-format"))
    )

    # Now find and click the caret icon inside it
    caret_icon_2 = wrapper_2.find_element(By.CSS_SELECTOR, "[data-testid='caret']")
    safe_click(driver, caret_icon_2)
    print("✅ Clicked caret icon to open dropdown")

    time.sleep(3)  # allow menu to open

    # Find the input inside combobox
    format_input_2 = wrapper_2.find_element(By.CSS_SELECTOR, "input#listbox-input-qr-export-modal-format")

    # Press Arrow Down multiple times to reach JSON (4th option)
    for i in range(1):  # CSV is index 0, so press 3 times to reach index 3 (4th item)
        format_input_2.send_keys(Keys.ARROW_DOWN)
        time.sleep(2)
    print("⬇️ Pressed ARROW_DOWN 2 times to highlight JSON")

    # Now press ENTER to select JSON
    format_input_2.send_keys(Keys.ENTER)
    print("✅ Pressed ENTER to select JSON")

    # Wait for the "Open in Browser" button to be present and clickable
    try:
        open_browser_btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#qr-export-modal-open"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", open_browser_btn)
        safe_click(driver, open_browser_btn)  # use your safe_click helper
        print("✅ Clicked 'Open in Browser'")
    except Exception as e:
        print(f"❌ Could not click 'Open in Browser': {e}")

    # Wait for new tab
    time.sleep(3)
    tabs = driver.window_handles
    driver.switch_to.window(tabs[-1])
    print("✅ Switched to new tab")

    # Get JSON content
    json_text = driver.find_element(By.TAG_NAME, "pre").text
    print("✅ Retrieved JSON text")

    # Parse JSON
    import json
    data1 = json.loads(json_text)
    payload = {
        "no_of_reconciliations": reconciliations_value,
        "data": data,
        "data1": data1
    }

    # POST data to n8n
    resp = requests.post(N8N_WEBHOOK_URL, json=payload)
    print("✅ Posted to N8N, response:", resp.status_code)

except Exception as e:
    print(f"❌ Exception occurred: {e}")
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
finally:
    driver.quit()
