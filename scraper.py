from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime
import time
import re
import os

# ============================================================
# FILE PATHS
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
# CLICK ELEMENT BY ID
# ============================================================

def click_id(element_id, wait_time=30):

    for _ in range(wait_time):

        try:

            element = driver.find_element(
                By.ID,
                element_id
            )

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

    raise Exception(
        f"Could not find element ID: {element_id}"
    )


# ============================================================
# NORMALISE SUPPLIER NAME
# ============================================================

def normalise_supplier(value):

    if not value:
        return None

    value = value.strip()
    lower = value.lower()

    supplier_checks = [

        (
            ["electric ireland", "electric-ireland", "electric_ireland"],
            "Electric Ireland"
        ),

        (
            ["sse airtricity", "airtricity", "sse-airtricity", "sse_airtricity"],
            "SSE Airtricity"
        ),

        (
            ["bord gáis", "bord gais", "bord-gais", "bord_gais", "bordgais"],
            "Bord Gáis Energy"
        ),

        (
            ["yuno energy", "yuno-energy", "yuno_energy", "yuno"],
            "Yuno Energy"
        ),

        (
            ["prepaypower", "prepay power", "prepay-power", "prepay_power"],
            "PrepayPower"
        ),

        (
            ["energia"],
            "Energia"
        ),

        (
            ["flogas"],
            "Flogas"
        ),

        (
            ["pinergy"],
            "Pinergy"
        ),

        (
            ["waterpower", "water power", "water-power", "water_power"],
            "Waterpower"
        ),

        (
            ["community power", "community-power", "community_power"],
            "Community Power"
        ),

        (
            ["ecopower", "eco power", "eco-power", "eco_power"],
            "Ecopower"
        ),
    ]

    for search_terms, supplier_name in supplier_checks:

        for term in search_terms:

            if term in lower:
                return supplier_name

    return None


# ============================================================
# GET SUPPLIER FROM LOGO
# ============================================================

def get_company_from_card(card):

    """
    Switcher appears to display the supplier as a logo rather
    than normal visible text.

    Search all images inside the result card and inspect:
    - alt
    - title
    - src
    - data-src
    - aria-label

    We also inspect links/classes as fallbacks.
    """

    try:

        images = card.find_elements(
            By.TAG_NAME,
            "img"
        )

        for image in images:

            attributes = [
                image.get_attribute("alt"),
                image.get_attribute("title"),
                image.get_attribute("src"),
                image.get_attribute("data-src"),
                image.get_attribute("aria-label"),
                image.get_attribute("class"),
            ]

            for attribute in attributes:

                supplier = normalise_supplier(
                    attribute
                )

                if supplier:
                    return supplier

    except Exception as e:

        print(
            f"Image supplier detection error: {e}"
        )


    # --------------------------------------------------------
    # CHECK LINKS
    # --------------------------------------------------------

    try:

        links = card.find_elements(
            By.TAG_NAME,
            "a"
        )

        for link in links:

            attributes = [
                link.get_attribute("href"),
                link.get_attribute("title"),
                link.get_attribute("aria-label"),
                link.get_attribute("class"),
            ]

            for attribute in attributes:

                supplier = normalise_supplier(
                    attribute
                )

                if supplier:
                    return supplier

    except Exception as e:

        print(
            f"Link supplier detection error: {e}"
        )


    # --------------------------------------------------------
    # CHECK COMPLETE HTML
    # --------------------------------------------------------

    try:

        html = card.get_attribute(
            "outerHTML"
        )

        supplier = normalise_supplier(
            html
        )

        if supplier:
            return supplier

    except Exception as e:

        print(
            f"HTML supplier detection error: {e}"
        )


    # --------------------------------------------------------
    # LAST FALLBACK - VISIBLE TEXT
    # --------------------------------------------------------

    try:

        supplier = normalise_supplier(
            card.text
        )

        if supplier:
            return supplier

    except Exception:
        pass


    return "Unknown"


# ============================================================
# GET PLAN NAME
# ============================================================

def get_plan_name(lines):

    """
    Current Switcher result cards put the actual tariff
    name on the first visible line.
    """

    if not lines:
        return "Unknown Plan"

    return lines[0].strip()


# ============================================================
# GET ESTIMATED ANNUAL BILL
# ============================================================

def get_annual_bill(lines):

    """
    Find the euro price directly before
    'Estimated annual bill'.
    """

    for i, line in enumerate(lines):

        if (
            "estimated annual bill"
            in line.lower()
            and i > 0
        ):

            price = lines[i - 1].strip()

            if re.fullmatch(
                r"€[\d,]+\.\d{2}",
                price
            ):
                return price

    return ""


# ============================================================
# MARKDOWN CLEANING
# ============================================================

def escape_markdown(value):

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

    lines = [

        "| Rank | Supplier | Plan | Estimated Annual Bill | Source | Last Checked |",

        "|---:|---|---|---:|---|---|"
    ]

    for _, row in df.iterrows():

        rank = int(
            row["Rank"]
        )

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

    return "\n".join(
        lines
    )


# ============================================================
# MAIN SCRAPER
# ============================================================

try:

    checked_time = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )


    # --------------------------------------------------------
    # OPEN SWITCHER
    # --------------------------------------------------------

    print(
        "Opening Switcher.ie..."
    )

    driver.get(
        url
    )

    time.sleep(
        12
    )


    # --------------------------------------------------------
    # COMPLETE COMPARISON FORM
    # --------------------------------------------------------

    print(
        "Selecting electricity..."
    )

    click_id(
        "switch_electricity"
    )


    print(
        "Selecting PrepayPower..."
    )

    click_id(
        "comparison_electricity_current_supplier_prepaypower"
    )


    print(
        "Selecting Direct Debit..."
    )

    click_id(
        "comparison_electricity_payment_type_direct_debit"
    )


    print(
        "Selecting 24 hour meter..."
    )

    click_id(
        "comparison_electricity_meter_type_twenty_four_hour"
    )


    print(
        "Selecting online billing..."
    )

    click_id(
        "comparison_electricity_bill_type_online"
    )


    print(
        "Selecting national average usage..."
    )

    click_id(
        "comparison_electricity_consumption_calculation_type_national_average"
    )


    print(
        "Selecting all plans..."
    )

    click_id(
        "comparison_electricity_search_type_all"
    )


    print(
        "Including cashback..."
    )

    click_id(
        "comparison_electricity_include_cashback_1"
    )


    # --------------------------------------------------------
    # SUBMIT FORM
    # --------------------------------------------------------

    print(
        "Submitting comparison..."
    )

    form = driver.find_element(

        By.XPATH,

        "//input[@id='comparison_electricity_current_supplier_prepaypower']/ancestor::form"

    )

    driver.execute_script(
        "arguments[0].submit();",
        form
    )

    time.sleep(
        12
    )


    # --------------------------------------------------------
    # GET RESULT CARDS
    # --------------------------------------------------------

    cards = driver.find_elements(
        By.CSS_SELECTOR,
        ".c-result-row"
    )

    print(
        f"Found {len(cards)} result cards."
    )

    results = []


    # --------------------------------------------------------
    # READ EACH CARD
    # --------------------------------------------------------

    for card_number, card in enumerate(
        cards,
        start=1
    ):

        try:

            lines = [

                line.strip()

                for line in card.text.splitlines()

                if line.strip()

            ]


            # ------------------------------------------------
            # EXTRACT DATA
            # ------------------------------------------------

            plan_name = get_plan_name(
                lines
            )

            company = get_company_from_card(
                card
            )

            annual_bill = get_annual_bill(
                lines
            )


            # ------------------------------------------------
            # DEBUG OUTPUT
            # ------------------------------------------------

            print("\n")
            print(
                "=" * 80
            )

            print(
                f"RESULT CARD {card_number}"
            )

            print(
                "=" * 80
            )

            print(
                f"Supplier: {company}"
            )

            print(
                f"Plan: {plan_name}"
            )

            print(
                f"Annual Bill: {annual_bill}"
            )


            # Print logo information too
            try:

                images = card.find_elements(
                    By.TAG_NAME,
                    "img"
                )

                print(
                    f"Images found: {len(images)}"
                )

                for image_number, image in enumerate(
                    images,
                    start=1
                ):

                    print(
                        f"IMAGE {image_number}"
                    )

                    print(
                        "ALT:",
                        image.get_attribute("alt")
                    )

                    print(
                        "TITLE:",
                        image.get_attribute("title")
                    )

                    print(
                        "SRC:",
                        image.get_attribute("src")
                    )

                    print(
                        "DATA-SRC:",
                        image.get_attribute("data-src")
                    )

            except Exception as e:

                print(
                    f"Could not print image info: {e}"
                )


            print(
                "=" * 80
            )


            # ------------------------------------------------
            # SKIP INVALID RESULT
            # ------------------------------------------------

            if not annual_bill:

                print(
                    "Skipped - no annual bill detected."
                )

                continue


            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            results.append({

                "Company":
                    company,

                "Plan":
                    plan_name,

                "Estimated Annual Bill":
                    annual_bill,

                "Source":
                    "Switcher.ie",

                "Last Checked":
                    checked_time

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
    # CLEAN AND SORT
    # ========================================================

    if not df.empty:

        df["Price Number"] = (

            df[
                "Estimated Annual Bill"
            ]

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


        # ----------------------------------------------------
        # REMOVE OBVIOUSLY INVALID PRICES
        # ----------------------------------------------------

        df = df[
            df["Price Number"] > 500
        ]


        # ----------------------------------------------------
        # CHEAPEST FIRST
        # ----------------------------------------------------

        df = df.sort_values(
            "Price Number",
            ascending=True
        )


        # ----------------------------------------------------
        # REMOVE TEMP PRICE COLUMN
        # ----------------------------------------------------

        df = df.drop(
            columns=[
                "Price Number"
            ]
        )


        # ----------------------------------------------------
        # KEEP TOP 8
        # ----------------------------------------------------

        df = df.head(
            8
        )


        # ----------------------------------------------------
        # RESET INDEX
        # ----------------------------------------------------

        df = df.reset_index(
            drop=True
        )


        # ----------------------------------------------------
        # ADD RANK
        # ----------------------------------------------------

        df.insert(

            0,

            "Rank",

            range(
                1,
                len(df) + 1
            )

        )


        # ----------------------------------------------------
        # FINAL COLUMN ORDER
        # ----------------------------------------------------

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
    # SAVE MARKDOWN
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
    # FINAL OUTPUT
    # ========================================================

    print("\n")
    print(
        "=" * 80
    )

    print(
        "FINAL ENERGY RANKINGS"
    )

    print(
        "=" * 80
    )


    print(

        df.to_string(
            index=False
        )

    )


    print(
        "=" * 80
    )


# ============================================================
# ALWAYS CLOSE CHROME
# ============================================================

finally:

    driver.quit()

    print(
        "\nChrome closed."
    )
