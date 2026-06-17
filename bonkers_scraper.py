from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime
import time

csv_path = "bonkers_rankings.csv"

url = "https://www.bonkers.ie/compare-gas-electricity-prices/"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)


def get_company(plan_name):
    mappings = {
        "Yuno": "Yuno Energy",
        "Flogas": "Flogas",
        "SSE": "SSE Airtricity",
        "Airtricity": "SSE Airtricity",
        "Energia": "Energia",
        "Bord Gáis": "Bord Gáis Energy",
        "Bord Gais": "Bord Gáis Energy",
        "Electric Ireland": "Electric Ireland",
        "Waterpower": "Waterpower",
        "Community Power": "Community Power",
        "Ecopower": "Ecopower",
        "Pinergy": "Pinergy",
    }

    for key, company in mappings.items():
        if key.lower() in plan_name.lower():
            return company

    return plan_name.split(" - ")[0]


try:
    driver.get(url)
    time.sleep(8)

    cards = driver.find_elements(By.CSS_SELECTOR, ".result, .results-card, .product-card, .tariff-card")

    results = []

    for card in cards:
        try:
            text = card.text.strip()

            if not text:
                continue

            lines = [line.strip() for line in text.split("\n") if line.strip()]

            price_line = None
            for line in lines:
                if "€" in line and any(char.isdigit() for char in line):
                    price_line = line
                    break

            if not price_line:
                continue

            plan_name = lines[0]
            annual_bill = price_line
            company = get_company(plan_name)

            results.append({
                "Rank": len(results) + 1,
                "Company": company,
                "Plan": plan_name,
                "Estimated Annual Bill": annual_bill,
                "Source": "Bonkers.ie",
                "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            print(f"Skipped one card: {e}")

    df = pd.DataFrame(results[:8])

    if df.empty:
        print("No Bonkers results found. CSV not updated.")
    else:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(df)
        print(f"Saved to {csv_path}")

finally:
    driver.quit()
