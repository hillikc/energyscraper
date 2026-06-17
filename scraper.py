from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime
import time
import re

csv_path = "energy_rankings.csv"
url = "https://switcher.ie/gas-electricity/comparison/"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)


def click_id(element_id):
    element = driver.find_element(By.ID, element_id)
    driver.execute_script("arguments[0].click();", element)
    time.sleep(0.7)


def get_company(plan_name):
    mappings = {
        "EnergySaver": "SSE Airtricity",
        "1 Year Electricity Variable Plan": "Yuno Energy",
        "New Elec Only": "Bord Gáis Energy",
        "1 Year Home Electricity": "Electric Ireland",
        "Green Electricity": "Electric Ireland",
        "Flogas": "Flogas",
        "Energia": "Energia",
        "Waterpower": "Waterpower",
        "Community Power": "Community Power",
        "Ecopower": "Ecopower",
        "Pinergy": "Pinergy",
    }

    for key, company in mappings.items():
        if key.lower() in plan_name.lower():
            return company

    return plan_name.split(" - ")[0]


def extract_price(text):
    matches = re.findall(r"€[\d,]+\.\d{2}", text)
    if matches:
        return matches[0]
    return ""


try:
    driver.get(url)
    time.sleep(5)

    click_id("switch_electricity")
    click_id("comparison_electricity_current_supplier_prepaypower")
    click_id("comparison_electricity_payment_type_direct_debit")
    click_id("comparison_electricity_meter_type_twenty_four_hour")
    click_id("comparison_electricity_bill_type_online")
    click_id("comparison_electricity_consumption_calculation_type_national_average")
    click_id("comparison_electricity_search_type_all")
    click_id("comparison_electricity_include_cashback_1")

    form = driver.find_element(
        By.XPATH,
        "//input[@id='comparison_electricity_current_supplier_prepaypower']/ancestor::form"
    )
    driver.execute_script("arguments[0].submit();", form)

    time.sleep(10)

    cards = driver.find_elements(By.CSS_SELECTOR, ".c-result-row")
    results = []

    for card in cards:
        try:
            text = card.text.strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            annual_bill = extract_price(text)

            if not annual_bill:
                continue

            plan_name = ""

            for line in lines:
                lower_line = line.lower()

                if "estimated annual bill" in lower_line:
                    continue
                if "payment type" in lower_line:
                    continue
                if "billing type" in lower_line:
                    continue
                if "rate type" in lower_line:
                    continue
                if "contract length" in lower_line:
                    continue
                if "exit fee" in lower_line:
                    continue
                if "payment plan" in lower_line:
                    continue
                if "available" == lower_line:
                    continue
                if "not available through switcher.ie" in lower_line:
                    continue
                if "plan info" in lower_line:
                    continue
                if "switch now" in lower_line:
                    continue
                if line.startswith("€"):
                    continue
                if line.startswith("You save"):
                    continue
                if line in ["Direct Debit", "Online billing", "Variable rate", "12 months"]:
                    continue

                plan_name = line
                break

            if not plan_name:
                continue

            company = get_company(plan_name)

            results.append({
                "Rank": len(results) + 1,
                "Company": company,
                "Plan": plan_name,
                "Estimated Annual Bill": annual_bill,
                "Source": "Switcher.ie",
                "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            print("Skipped card:", e)

    df = pd.DataFrame(results)

    df["Price Number"] = (
        df["Estimated Annual Bill"]
        .str.replace("€", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    df = df.sort_values("Price Number", ascending=True)
    df = df.drop(columns=["Price Number"])
    df = df.head(8)
    df["Rank"] = range(1, len(df) + 1)

    if df.empty:
        print("No results found. Saving headers only.")
        df = pd.DataFrame(columns=[
            "Rank",
            "Company",
            "Plan",
            "Estimated Annual Bill",
            "Source",
            "Last Checked"
        ])

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(df)
    print(f"Saved to {csv_path}")

finally:
    driver.quit()
