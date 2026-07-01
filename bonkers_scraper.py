from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
from datetime import datetime
import time
import re

csv_path = "bonkers_rankings.csv"
history_path = "bonkers_history.csv"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)


def js_click(element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)
    time.sleep(1.2)


def click_text(text, wait_time=25):
    for _ in range(wait_time):
        elements = driver.find_elements(
            By.XPATH,
            f"//*[contains(normalize-space(), \"{text}\")]"
        )

        visible = []

        for element in elements:
            try:
                if element.is_displayed():
                    visible.append(element)
            except:
                pass

        if visible:
            js_click(visible[-1])
            return True

        time.sleep(1)

    raise Exception(f"Could not find text: {text}")


def click_by_id(element_id):
    element = driver.find_element(By.ID, element_id)
    js_click(element)


def accept_cookies():
    buttons = driver.find_elements(
        By.XPATH,
        "//*[contains(normalize-space(), 'I ACCEPT') or contains(normalize-space(), 'Accept all') or contains(normalize-space(), 'Accept')]"
    )

    for button in buttons:
        try:
            if button.is_displayed():
                driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                return True
        except:
            pass

    return False


def remove_cookie_popups():
    driver.execute_script("""
        const selectors = [
            '[id*="cookie"]',
            '[class*="cookie"]',
            '[id*="consent"]',
            '[class*="consent"]',
            '[aria-label*="cookie"]',
            '[aria-label*="Cookie"]',
            '[id*="privacy"]',
            '[class*="privacy"]'
        ];

        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => el.remove());
        });

        document.body.style.overflow = 'auto';
    """)

    time.sleep(1)


def choose_dropdown_by_text(text):
    selects = driver.find_elements(By.TAG_NAME, "select")

    for select_element in selects:
        try:
            if not select_element.is_displayed():
                continue

            select = Select(select_element)

            for option in select.options:
                if option.text.strip() == text:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        select_element
                    )
                    time.sleep(0.5)
                    select.select_by_visible_text(text)
                    time.sleep(1)
                    return True
        except:
            pass

    raise Exception(f"Could not choose dropdown option: {text}")


def click_radio_true(field_name):
    element = driver.find_element(
        By.XPATH,
        f"//fieldset[@data-field='{field_name}']//input[@value='true']"
    )
    driver.execute_script("arguments[0].click();", element)
    time.sleep(1)


def click_visible_yes(number):
    yes_options = driver.find_elements(By.XPATH, "//*[normalize-space()='Yes']")
    visible_yes = []

    for option in yes_options:
        try:
            if option.is_displayed():
                visible_yes.append(option)
        except:
            pass

    if len(visible_yes) >= number:
        js_click(visible_yes[number - 1])
    else:
        raise Exception(f"Could not find visible Yes number {number}")


def click_compare_prices():
    compare_buttons = driver.find_elements(
        By.XPATH,
        "//button[contains(normalize-space(), 'Compare prices')] | //input[@value='Compare prices']"
    )

    for button in compare_buttons:
        try:
            if button.is_displayed():
                js_click(button)
                return True
        except:
            pass

    # Fallback: click visible text if the real button selector changes
    return click_text("Compare prices", wait_time=10)


def scroll_results_page():
    time.sleep(10)

    remove_cookie_popups()

    for _ in range(35):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1)
        remove_cookie_popups()

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)


def money_to_float(value):
    return float(value.replace("€", "").replace(",", "").replace(" ", ""))


def normalise_company(plan):
    lower = plan.lower()

    if "electric ireland" in lower:
        return "Electric Ireland"
    if "yuno" in lower:
        return "Yuno Energy"
    if "bord gáis" in lower or "bord gais" in lower:
        return "Bord Gáis Energy"
    if "sse" in lower or "airtricity" in lower:
        return "SSE Airtricity"
    if "energia" in lower:
        return "Energia"
    if "flogas" in lower:
        return "Flogas"
    if "pinergy" in lower:
        return "Pinergy"
    if "prepaypower" in lower:
        return "PrepayPower"
    if "waterpower" in lower:
        return "Waterpower"
    if "community power" in lower:
        return "Community Power"
    if "ecopower" in lower:
        return "Ecopower"

    return None


def is_plan_line(line):
    lower = line.lower()

    bad_phrases = [
        "off ",
        "account access",
        "smart meter",
        "show rates",
        "see details",
        "contract term",
        "payment type",
        "billing method",
        "rate type",
        "est 1-year cost",
        "save now",
        "save (first year)",
        "cashback",
        "cookies",
        "privacy",
        "terms",
        "conditions",
        "includes",
        "price change"
    ]

    for phrase in bad_phrases:
        if phrase in lower:
            return False

    return "electricity" in lower and normalise_company(line) is not None


def extract_results():
    page_text = driver.find_element(By.TAG_NAME, "body").text

    print("=" * 80)
    print("BONKERS PAGE TEXT START")
    print(page_text[:10000])
    print("BONKERS PAGE TEXT END")
    print("=" * 80)

    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    with open("bonkers_debug_text.txt", "w", encoding="utf-8") as f:
        f.write(page_text)

    driver.save_screenshot("bonkers_debug.png")

    results = []
    seen = set()
    plan_indexes = []

    for i, line in enumerate(lines):
        if is_plan_line(line):
            plan_indexes.append(i)

    print("Plan indexes found:", plan_indexes)

    for position, start_index in enumerate(plan_indexes):
        plan = lines[start_index]
        company = normalise_company(plan)

        if not company:
            continue

        end_index = (
            plan_indexes[position + 1]
            if position + 1 < len(plan_indexes)
            else min(start_index + 100, len(lines))
        )

        block = lines[start_index:end_index]
        block_text = " | ".join(block)

        annual_bill = None

        matches = re.findall(
            r"€\s?\d{1,3}(?:,\d{3})?(?:\.\d{2})?",
            block_text
        )

        valid_bills = []

        for match in matches:
            try:
                amount = money_to_float(match)
                if amount >= 1000:
                    valid_bills.append(match.replace(" ", ""))
            except:
                pass

        if valid_bills:
            annual_bill = valid_bills[0]

        if not annual_bill:
            print(f"Skipped plan without annual bill: {plan}")
            continue

        key = (plan, annual_bill)

        if key in seen:
            print(f"Duplicate skipped: {key}")
            continue

        seen.add(key)

        results.append({
            "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Rank": len(results) + 1,
            "Company": company,
            "Plan": plan,
            "Estimated Annual Bill": annual_bill,
            "Source": "Bonkers.ie"
        })

    results = sorted(
        results,
        key=lambda x: money_to_float(x["Estimated Annual Bill"])
    )

    for index, result in enumerate(results, start=1):
        result["Rank"] = index

    print(f"Found {len(results)} results")

    for result in results:
        print(result)

    return results[:8]


def save_results(results):
    df = pd.DataFrame(results)

    if df.empty:
        print("No Bonkers results found. CSV not updated.")
        return

    df = df[
        [
            "Last Checked",
            "Rank",
            "Company",
            "Plan",
            "Estimated Annual Bill",
            "Source"
        ]
    ]

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"Saved latest rankings to {csv_path}")

    try:
        history_df = pd.read_csv(history_path)
    except:
        history_df = pd.DataFrame()

    updated_history = pd.concat(
        [history_df, df],
        ignore_index=True
    )

    updated_history.to_csv(
        history_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Updated history file: {history_path}")
    print(df)


try:
    driver.get(f"https://www.bonkers.ie/compare-gas-electricity-prices/electricity/?t={int(time.time())}")
    time.sleep(5)

    accept_cookies()
    remove_cookie_popups()

    click_text("Continue without upload")

    accept_cookies()
    remove_cookie_popups()

    click_by_id("supplier-prepaypower-ie")

    click_text("Urban (DG1)")
    click_text("Standard Meter")
    click_text("24-hour meter (MCC01)")
    click_text("Pay As You Go / Prepayment")

    choose_dropdown_by_text("Classic Pay")
    choose_dropdown_by_text("October 2011")

    click_text("Not sure, use national average")

    click_radio_true("cashback")
    click_visible_yes(2)

    click_compare_prices()

    time.sleep(20)
    print("After compare URL:", driver.current_url)

    remove_cookie_popups()
    scroll_results_page()
    remove_cookie_popups()

    results = extract_results()
    save_results(results)

except Exception as e:
    print("ERROR:", e)
    print("Current URL:", driver.current_url)

    try:
        print(driver.find_element(By.TAG_NAME, "body").text)
        driver.save_screenshot("bonkers_error.png")
    except:
        pass

finally:
    driver.quit()
