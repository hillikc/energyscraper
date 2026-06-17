from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
import time
import os

folder = r"C:\Users\paulh\Desktop\Energy Scraper"
csv_path = os.path.join(folder, "energy_rankings.csv")

url = "https://switcher.ie/gas-electricity/comparison/"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

def click_id(element_id):
    element = driver.find_element(By.ID, element_id)
    driver.execute_script("arguments[0].click();", element)
    time.sleep(0.5)

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
        "Pinergy": "Pinergy"
    }

    for key, company in mappings.items():
        if key.lower() in plan_name.lower():
            return company

    return plan_name.split(" - ")[0]

driver.get(url)
time.sleep(3)

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

time.sleep(8)

cards = driver.find_elements(By.CSS_SELECTOR, ".c-result-row")

results = []

for card in cards:
    try:
        plan_name = card.find_element(By.CSS_SELECTOR, ".c-result-row__plan-name").text.strip()
        price_text = card.find_element(By.CSS_SELECTOR, ".c-result-row__plan-detail__price-amount").text.strip()
        annual_bill = price_text.split("\n")[0].strip()
        company = get_company(plan_name)

        results.append({
            "Rank": len(results) + 1,
            "Company": company,
            "Plan": plan_name,
            "Estimated Annual Bill": annual_bill,
            "Source": "Switcher.ie",
            "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

    except:
        pass

driver.quit()

df = pd.DataFrame(results[:8])
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(df)
print(f"Saved to {csv_path}")