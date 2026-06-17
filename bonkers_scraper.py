from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
from datetime import datetime
import time

csv_path = "bonkers_rankings.csv"

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)


def js_click(element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)
    time.sleep(1.2)


def click_text(text, wait_time=20):
    for _ in range(wait_time):
        elements = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(), '{text}')]")
        visible = [e for e in elements if e.is_displayed()]
        if visible:
            js_click(visible[-1])
            return
        time.sleep(1)
    raise Exception(f"Could not find text: {text}")


def click_by_id(element_id):
    element = driver.find_element(By.ID, element_id)
    js_click(element)


def accept_cookies():
    buttons = driver.find_elements(By.XPATH, "//*[contains(normalize-space(), 'I ACCEPT')]")
    for button in buttons:
        try:
            if button.is_displayed():
                driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                return
        except:
            pass


def choose_dropdown_by_text(text):
    selects = driver.find_elements(By.TAG_NAME, "select")
    for select_element in selects:
        try:
            select = Select(select_element)
            options_text = [option.text.strip() for option in select.options]
            if text in options_text:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_element)
                time.sleep(0.5)
                select.select_by_visible_text(text)
                time.sleep(1)
                return
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

    # Cashback Yes
    click_radio_true("cashback")

    # Available for sign-up Yes
    click_visible_yes(2)

    click_text("Compare prices")

    time.sleep(15)

    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    suppliers = [
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
        if " - " in line and any(supplier in line for supplier in suppliers):
            company = line.split(" - ")[0].strip()
            plan = line.strip()

            nearby = lines[i:i + 30]
            annual_bill = ""

            for item in nearby:
                if item.startswith("€") and "," in item:
                    annual_bill = item
                    break

            key = (company, plan)

            if key not in seen:
                seen.add(key)
                results.append({
                    "Rank": len(results) + 1,
                    "Company": company,
                    "Plan": plan,
                    "Estimated Annual Bill": annual_bill,
                    "Source": "Bonkers.ie",
                    "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
                })

    df = pd.DataFrame(results[:10])
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(df)
    print(f"Saved to {csv_path}")

finally:
    driver.quit()