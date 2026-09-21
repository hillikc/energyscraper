from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime
import time
import re
import os

# ============================================================
# FILES
# ============================================================

csv_path = "energy_rankings.csv"
markdown_path = "energy_rankings.md"
history_path = "switcher_history.csv"

url = "https://switcher.ie/gas-electricity/comparison/"


# ============================================================
# SELENIUM SETUP
# ============================================================

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)


# ============================================================
# HELPER - CLICK ELEMENT BY ID
# ============================================================

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


# ============================================================
# KNOWN IRISH ENERGY SUPPLIERS
# ============================================================

SUPPLIERS = [
    "PrepayPower",
    "Yuno Energy",
    "SSE Airtricity",
    "Electric Ireland",
    "Bord Gáis Energy",
    "Bord Gais Energy",
    "Energia",
    "Flogas",
    "Pinergy",
    "Waterpower",
    "Community Power",
    "Ecopower",
]


# ============================================================
# DETECT SUPPLIER
# ============================================================

def get_company(lines):
    """
    Detect the supplier from all text contained in the result card.
    This prevents plan descriptions from being treated as suppliers.
    """

    full_text = " ".join(lines).lower()

    for supplier in SUPPLIERS:
        if supplier.lower() in full_text:

            # Normalise Bord Gais spelling
            if supplier == "Bord Gais Energy":
                return "Bord Gáis Energy"

            return supplier

    return "Unknown"


# ============================================================
# GET ESTIMATED ANNUAL BILL
# ============================================================

def get_annual_bill(lines):
    """
    Find the price directly before 'Estimated Annual Bill'.
    """

    for i, line in enumerate(lines):

        if "estimated annual bill" in line.lower() and i > 0:

            price = lines[i - 1].strip()

            if re.fullmatch(r"€[\d,]+\.\d{2}", price):
                return price

    return ""


# ============================================================
# GET PLAN NAME
# ============================================================

def get_plan_name(lines, company):
    """
    Attempts to identify the actual tariff/plan name while
    ignoring descriptions, discounts and account information.
    """

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
        "cashback not included",
        "you save",
        "welcome bonus",
        "loyalty discount",
        "smart meter",
        "esb networks",
        "on your behalf",
        "when you join",
        "standard electricity 30%",
        "standard electricity",
    ]

    candidates = []

    for line in lines:

        line = line.strip()
        lower = line.lower()

        if not line:
            continue

        # Ignore supplier itself
        if company != "Unknown" and lower == company.lower():
            continue

        # Ignore unwanted descriptive text
        if any(item in lower for item in banned):
            continue

        # Ignore prices
        if re.fullmatch(r"€[\d,]+\.\d{2}", line):
            continue

        if line.startswith("€"):
            continue

        # Ignore standalone percentages
        if re.fullmatch(r"\d+%", line):
            continue

        # Likely plan names
        plan_words = [
            "energysaver",
            "electricity",
            "elec",
            "home",
            "green",
            "smart",
            "variable",
        ]

        if any(word in lower for word in plan_words):
            candidates.append(line)

    if candidates:
        return candidates[0]

    return "Unknown Plan"


# ============================================================
# MARKDOWN CLEANUP
# ============================================================

def escape_markdown(value):
    """
    Prevent pipe characters or newlines from breaking
    the Markdown table.
    """

    return (
        str(value)
        .replace("|", "\\|")
        .replace("\n", " ")
        .strip()
    )


# ============================================================
# CREATE MARKDOWN TABLE
# ============================================================

def create_markdown_table(df):
    """
    Creates the bot-friendly Markdown rankings table.
    """

    lines = [
        "| Rank | Supplier | Plan | Estimated Annual Bill | Source | Last Checked |",
        "|---:|---|---|---:|---|---|"
    ]

    for _, row in df.iterrows():

        rank = int(row["Rank"])

        company = escape_markdown(
            row["Company"]
        )

        plan = escape_markdown(
            row["Plan"]
        )

        annual_bill = escape_markdown(
            row["Estimated Annual Bill"]
        )

        source = escape_markdown(
            row["Source"]
        )

        last_checked = escape_markdown(
            row["Last Checked"]
        )

        lines.append(
            f"| **{rank}** | "
            f"{company} | "
            f"{plan} | "
            f"**{annual_bill}** | "
            f"{source} | "
            f"{last_checked} |"
        )

    return "\n".join(lines)


# ============================================================
# MAIN SCRAPER
# ============================================================

try:

    checked_time = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    print("Opening Switcher.ie...")

    driver.get(url)

    time.sleep(12)


    # ========================================================
    # COMPLETE SWITCHER FORM
    # ========================================================

    print("Selecting electricity...")

    click_id(
        "switch_electricity"
    )

    print("Selecting PrepayPower...")

    click_id(
        "comparison_electricity_current_supplier_prepaypower"
    )

    print("Selecting Direct Debit...")

    click_id(
        "comparison_electricity_payment_type_direct_debit"
    )

    print("Selecting 24 hour meter...")

    click_id(
        "comparison_electricity_meter_type_twenty_four_hour"
    )

    print("Selecting online billing...")

    click_id(
        "comparison_electricity_bill_type_online"
    )

    print("Selecting national average usage...")

    click_id(
        "comparison_electricity_consumption_calculation_type_national_average"
    )

    print("Selecting all plans...")

    click_id(
        "comparison_electricity_search_type_all"
    )

    print("Including cashback...")

    click_id(
        "comparison_electricity_include_cashback_1"
    )


    # ========================================================
    # SUBMIT FORM
    # ========================================================

    print("Submitting comparison...")

    form = driver.find_element(
        By.XPATH,
        "//input[@id='comparison_electricity_current_supplier_prepaypower']/ancestor::form"
    )

    driver.execute_script(
        "arguments[0].submit();",
        form
    )

    time.sleep(12)


    # ========================================================
    # GET RESULT CARDS
    # ========================================================

    cards = driver.find_elements(
        By.CSS_SELECTOR,
        ".c-result-row"
    )

    print(
        f"Found {len(cards)} Switcher result cards."
    )

    results = []


    # ========================================================
    # READ EACH RESULT
    # ========================================================

    for card_number, card in enumerate(cards, start=1):

        try:

            lines = [
                line.strip()
                for line in card.text.splitlines()
                if line.strip()
            ]

            # Debug output
            print("\n")
            print("=" * 80)
            print(
                f"RESULT CARD {card_number}"
            )
            print("=" * 80)

            for line in lines:
                print(line)

            print("=" * 80)


            # Extract information
            annual_bill = get_annual_bill(
                lines
            )

            company = get_company(
                lines
            )

            plan_name = get_plan_name(
                lines,
                company
            )


            print(
                f"Detected supplier: {company}"
            )

            print(
                f"Detected plan: {plan_name}"
            )

            print(
                f"Detected annual bill: {annual_bill}"
            )


            # Skip cards where no valid price exists
            if not annual_bill:
                print(
                    "Skipped - no annual bill detected."
                )
                continue


            results.append({
                "Company": company,
                "Plan": plan_name,
                "Estimated Annual Bill": annual_bill,
                "Source": "Switcher.ie",
                "Last Checked": checked_time
            })


        except Exception as e:

            print(
                f"Skipped card {card_number}: {e}"
            )


    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        results
    )


    # ========================================================
    # SORT BY PRICE
    # ========================================================

    if not df.empty:

        df["Price Number"] = (
            df["Estimated Annual Bill"]
            .str.replace(
                "€",
                "",
                regex=False
            )
            .str.replace(
                ",",
                "",
                regex=False
            )
            .astype(float)
        )


        # Ignore obviously incorrect prices
        df = df[
            df["Price Number"] > 500
        ]


        # Cheapest first
        df = df.sort_values(
            "Price Number",
            ascending=True
        )


        # Remove temporary numeric column
        df = df.drop(
            columns=["Price Number"]
        )


        # Keep top 8
        df = df.head(8)


        # Reset row numbers
        df = df.reset_index(
            drop=True
        )


        # Add ranking
        df.insert(
            0,
            "Rank",
            range(
                1,
                len(df) + 1
            )
        )


        # Final column order
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


    # ========================================================
    # SAVE CURRENT CSV
    # ========================================================

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nSaved latest rankings to {csv_path}"
    )


    # ========================================================
    # SAVE BOT-FRIENDLY MARKDOWN
    # ========================================================

    markdown_table = create_markdown_table(
        df
    )

    with open(
        markdown_path,
        "w",
        encoding="utf-8"
    ) as markdown_file:

        markdown_file.write(
            markdown_table
        )

    print(
        f"Saved bot-friendly rankings to {markdown_path}"
    )


    # ========================================================
    # APPEND HISTORY
    # ========================================================

    history_df = df.copy()


    if os.path.exists(
        history_path
    ):

        existing_history = pd.read_csv(
            history_path
        )

        combined_history = pd.concat(
            [
                existing_history,
                history_df
            ],
            ignore_index=True
        )

    else:

        combined_history = history_df


    combined_history.to_csv(
        history_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Appended history to {history_path}"
    )


    # ========================================================
    # PRINT FINAL RANKINGS
    # ========================================================

    print("\n")
    print("=" * 80)
    print("FINAL ENERGY RANKINGS")
    print("=" * 80)

    print(
        df.to_string(
            index=False
        )
    )

    print("=" * 80)


# ============================================================
# ALWAYS CLOSE CHROME
# ============================================================

finally:

    driver.quit()

    print(
        "\nChrome closed."
    )
