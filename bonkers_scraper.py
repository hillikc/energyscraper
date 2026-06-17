from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
import time

csv_path = "bonkers_rankings.csv"

url = "https://www.bonkers.ie/compare-gas-electricity-prices/results/"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.get(url)
time.sleep(10)

cards = driver.find_elements(By.CSS_SELECTOR, "div")

known_companies = [
    "Electric Ireland",
    "Yuno Energy",
    "Bord Gáis Energy",
    "SSE Airtricity",
    "Flogas",
    "Energia",
    "PrepayPower",
    "Waterpower",
    "Pinergy",
    "Ecopower",
    "Community Power"
]

results = []
seen_plans = set()

for card in cards:
    try:
        text = card.text.strip()

        if "Est. 1-year cost" not in text:
            continue

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        plan_name = ""

        for line in lines:
            if " - " in line and any(company.lower() in line.lower() for company in known_companies):
                plan_name = line
                break

        if plan_name == "":
            continue

        if plan_name in seen_plans:
            continue

        seen_plans.add(plan_name)

        company = ""
        for company_name in known_companies:
            if company_name.lower() in plan_name.lower():
                company = company_name
                break

        if company == "":
            company = plan_name.split(" - ")[0]

        annual_bill = ""

        for i, line in enumerate(lines):
            if "est. 1-year cost" in line.lower():
                if i + 1 < len(lines):
                    annual_bill = lines[i + 1]
                break

        if annual_bill == "" or "€" not in annual_bill:
            euro_lines = [line for line in lines if line.startswith("€")]
            for euro in euro_lines:
                if "," in euro:
                    annual_bill = euro
                    break

        if annual_bill == "":
            continue

        results.append({
            "Rank": len(results) + 1,
            "Company": company,
            "Plan": plan_name,
            "Estimated Annual Bill": annual_bill,
            "Source": "Bonkers.ie",
            "Last Checked": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

    except Exception:
        pass

driver.quit()

if len(results) == 0:
    print("No Bonkers results found. CSV not updated.")
    exit()

df = pd.DataFrame(results[:8])
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(df)
print(f"Saved to {csv_path}")
