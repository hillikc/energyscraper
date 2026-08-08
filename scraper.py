from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime
import time
import re
import os

csv_path = "energy_rankings.csv"
markdown_path = "energy_rankings.md"
history_path = "switcher_history.csv"

url = "https://switcher.ie/gas-electricity/comparison/"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)


def click_id(element_id, wait_time=30):
    for _ in range(wait_time):
        try:
            element = driver.find_element(By.ID, element_id)

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                element
            )

            time.sleep(0.5)

            driver.execute_script(
                "arguments[0].click();",
                element
            )

            time.sleep(0.8)
            return

        except Exception:
            time.sleep(1)

    raise Exception(f"Could not find element ID: {element_id}")


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


def get_annual_bill(lines):
    for i, line in enumerate(lines):
        if "estimated annual bill" in line.lower() and i > 0:
            price = lines[i - 1]

            if re.fullmatch(r"€[\d,]+\.\d{2}", price):
                return price

    return ""


def get_plan_name(lines):
    banned = [
        "direct debit",
        "credit/debit card",
        "online billing",
        "variable rate",
        "12 months",
        "available",
        "payment type",
        "billing type",
        "rate type",
        "contract length",
        "exit fee",
        "payment plan",
        "estimated annual bill",
        "see calculations",
        "not available through switcher.ie",
        "plan info",
        "switch now",
        "green electricity",
        "cashback not included",
        "you save",
        "welcome bonus",
    ]

    for line in lines:
        lower = line.lower()

        if any(b in lower for b in banned):
            continue

        if line.startswith("€"):
            continue

        if (
            "electricity" in lower
            or "energy" in lower
            or "flogas" in lower
            or "waterpower" in lower
        ):
            return line

    return ""


def escape_markdown(value):
    """
    Prevent pipe characters in scraped text from breaking the Markdown table.
    """
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def create_markdown_table(df):
    """
    Creates a bot-friendly Markdown rankings table.
    """
    lines = [
        "| Rank | Supplier | Plan | Estimated Annual Bill | Source | Last Checked |",
        "|---:|---|---|---:|---|---|"
    ]

    for _, row in df.iterrows():
        rank = int(row["Rank"])
        company = escape_markdown(row["Company"])
        plan = escape_markdown(row["Plan"])
        annual_bill = escape_markdown(row["Estimated Annual Bill"])
        source = escape_markdown(row["Source"])
        last_checked = escape_markdown(row["Last Checked"])

        lines.append(
            f"| **{rank}** | "
            f"{company} | "
            f"{plan} | "
            f"**{annual_bill}** | "
            f"{source} | "
            f"{last_checked} |"
        )

    return "\n".join(lines)


try:
    checked_time = datetime.now().strftime("%d/%m/%Y %H:%M")

    driver.get(url)
    time.sleep(12)

    click_id("switch_electricity")
    click_id("comparison_electricity_current_supplier_prepaypower")
    click_id("comparison_electricity_payment_type_direct_debit")
    click_id("comparison_electricity_meter_type_twenty_four_hour")
    click_id("comparison_electricity_bill_type_online")
    click_id(
        "comparison_electricity_consumption_calculation_type_national_average"
    )
    click_id("comparison_electricity_search_type_all")
    click_id("comparison_electricity_include_cashback_1")

    form = driver.find_element(
        By.XPATH,
        "//input[@id='comparison_electricity_current_supplier_prepaypower']/ancestor::form"
    )

    driver.execute_script("arguments[0].submit();", form)

    time.sleep(12)

    cards = driver.find_elements(By.CSS_SELECTOR, ".c-result-row")
    results = []

    for card in cards:
        try:
            lines = [
                line.strip()
                for line in card.text.splitlines()
                if line.strip()
            ]

            annual_bill = get_annual_bill(lines)
            plan_name = get_plan_name(lines)

            if not annual_bill or not plan_name:
                continue

            results.append({
                "Company": get_company(plan_name),
                "Plan": plan_name,
                "Estimated Annual Bill": annual_bill,
                "Source": "Switcher.ie",
                "Last Checked": checked_time
            })

        except Exception as e:
            print("Skipped card:", e)

    df = pd.DataFrame(results)

    if not df.empty:
        df["Price Number"] = (
            df["Estimated Annual Bill"]
            .str.replace("€", "", regex=False)
            .str.replace(",", "", regex=False)
            .astype(float)
        )

        df = df[df["Price Number"] > 500]
        df = df.sort_values("Price Number", ascending=True)
        df = df.drop(columns=["Price Number"])
        df = df.head(8)

        df.insert(
            0,
            "Rank",
            range(1, len(df) + 1)
        )

        df = df[
            [
                "Rank",
                "Company",
                "Plan",
                "Estimated Annual Bill",
                "Source",
                "Last Checked"
            ]
        ]

    else:
        df = pd.DataFrame(
            columns=[
                "Rank",
                "Company",
                "Plan",
                "Estimated Annual Bill",
                "Source",
                "Last Checked"
            ]
        )

    # -----------------------------
    # SAVE CURRENT CSV
    # -----------------------------

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------
    # SAVE BOT-FRIENDLY MARKDOWN
    # -----------------------------

    markdown_table = create_markdown_table(df)

    with open(
        markdown_path,
        "w",
        encoding="utf-8"
    ) as markdown_file:
        markdown_file.write(markdown_table)

    # -----------------------------
    # APPEND HISTORY
    # -----------------------------

    history_df = df.copy()

    if os.path.exists(history_path):
        existing_history = pd.read_csv(history_path)

        combined_history = pd.concat(
            [existing_history, history_df],
            ignore_index=True
        )

    else:
        combined_history = history_df

    combined_history.to_csv(
        history_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(df)

    print(
        f"Saved latest rankings to {csv_path}"
    )

    print(
        f"Saved bot-friendly rankings to {markdown_path}"
    )

    print(
        f"Appended history to {history_path}"
    )

finally:
    driver.quit()
