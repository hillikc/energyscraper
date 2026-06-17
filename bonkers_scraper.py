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
            options_text = [option.text.strip() for option in select.options]

            if text in options_text:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_element)
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

    for _ in range(15):
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1)

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)


def extract_results():
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    with open("bonkers_debug_text.txt", "w", encoding="utf-8") as f:
        f.write(page_text)

    driver.save_screenshot("bonkers_debug.png")

    companies = [
        "Yuno Energy",
        "Electric Ireland",
        "Bord Gáis Energy",
        "SSE Airtricity",
        "Energia",
        "Flogas",
        "Pinergy",
        "PrepayPower",
        "Waterpower",
        "Community Power"
    ]

    results = []
    seen = set()

    for i, line in enumerate(lines):
        matched_company = None

        for company in companies:
            if company.lower() in line.lower():
                matched_company = company
                break

        if not matched_company:
            continue

        nearby = lines[i:i + 60]
        nearby_text = " | ".join(nearby)

        euro_matches = re.findall(
            r"€\s?\d{1,3}(?:,\d{3})?(?:\.\d{2})?",
            nearby_text
        )

        if not euro_matches:
            continue

        annual_bill = euro_matches[0].replace(" ", "")

        plan = line

        if line.strip() == matched_company and i + 1 < len(lines):
            plan = matched_company + " - " + lines[i + 1]

        key = (matched_company, plan, annual_bill)

        if key not in seen:
            seen.add(key)
            results.append({
                "Rank": len(results) + 1,
                "Company": matched_company,
                "Plan": plan,
                "Estimated Annual Bill": annual_bill,
                "Source": "Bonkers.ie",
                "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

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
