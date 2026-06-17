from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
from datetime import datetime
import time
import re

csv_path = "bonkers_rankings.csv"

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
        elements = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(), \"{text}\")]")
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
        "//*[contains(normalize-space(), 'I ACCEPT') or contains(normalize-space(), 'Accept')]"
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


def scroll_results_page():
    time.sleep(15)

    for _ in range(25):
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1)

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)


def money_to_float(value):
    return float(value.replace("€", "").replace(",", "").replace(" ", ""))


def normalise_company(line):
    lower = line.lower()

    if "electric ireland" in lower:
        return "Electric Ireland"
    if "yuno" in lower:
        return "Yuno Energy"
    if "bord gáis" in lower or "bord gais" in lower or "bord gáís" in lower:
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
        "account access",
        "smart meter",
        "will be requested",
        "standard electricity unit rates",
        "cashback",
        "includes",
        "save now",
        "show rates",
        "see details",
        "contract term",
        "payment type",
        "billing method",
        "rate type",
        "est 1-year cost",
        "terms",
        "conditions"
    ]

    for phrase in bad_phrases:
        if phrase in lower:
            return False

    if "electricity" in lower:
        return True

    if "-" in line and normalise_company(line):
        return True

    return False


def find_annual_bill(lines, start_index):
    nearby = lines[start_index:start_index + 45]

    for i, line in enumerate(nearby):
        if "est 1-year cost" in line.lower() or "1-year cost" in line.lower():
            search_area = nearby[i:i + 6]
            joined = " ".join(search_area)

            euro_matches = re.findall(
                r"€\s?\d{1,3}(?:,\d{3})?(?:\.\d{2})?",
                joined
            )

            for euro in euro_matches:
                try:
                    if money_to_float(euro) >= 1000:
                        return euro.replace(" ", "")
                except:
                    pass

    joined_nearby = " | ".join(nearby)

    euro_matches = re.findall(
        r"€\s?\d{1,3}(?:,\d{3})?(?:\.\d{2})?",
        joined_nearby
    )

    valid_bills = []

    for euro in euro_matches:
        try:
            amount = money_to_float(euro)
            if amount >= 1000:
                valid_bills.append(euro.replace(" ", ""))
        except:
            pass

    if valid_bills:
        return valid_bills[0]

    return None


def extract_results():
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    with open("bonkers_debug_text.txt", "w", encoding="utf-8") as f:
        f.write(page_text)

    driver.save_screenshot("bonkers_debug.png")

    results = []
    seen = set()

    for i, line in enumerate(lines):
        company = normalise_company(line)

        if not company:
            continue

        if not is_plan_line(line):
            continue

        annual_bill = find_annual_bill(lines, i)

        if not annual_bill:
            continue

        plan = line

        key = (company, plan, annual_bill)

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "Rank": len(results) + 1,
            "Company": company,
            "Plan": plan,
            "Estimated Annual Bill": annual_bill,
            "Source": "Bonkers.ie",
            "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

    print(f"Found {len(results)} results")

    for result in results:
        print(result)

    return results[:10]


try:
    driver.get("https://www.bonkers.ie/compare-gas-electricity-prices/electricity/")
    time.sleep(5)

    accept_cookies()

    click_text("Continue without upload")

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

    click_text("Compare prices")

    scroll_results_page()

    results = extract_results()

    df = pd.DataFrame(results)

    if df.empty:
        print("No Bonkers results found. CSV not updated.")
    else:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(df)
        print(f"Saved to {csv_path}")

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
