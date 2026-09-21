from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
from datetime import datetime
import time
import re
import os


# ============================================================
# SWITCHER
# ============================================================

URL = "https://switcher.ie/gas-electricity/comparison/"


# ============================================================
# OUTPUT FILES
# ============================================================

# 24 HOUR
HOUR24_CSV = "energy_rankings.csv"
HOUR24_MARKDOWN = "energy_rankings.md"
HOUR24_HISTORY = "switcher_history.csv"

# SMART
SMART_CSV = "smart_energy_rankings.csv"
SMART_MARKDOWN = "smart_energy_rankings.md"
SMART_HISTORY = "switcher_smart_history.csv"


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
# NORMALISE SUPPLIER
# ============================================================

def normalise_supplier(value):

    if not value:
        return None

    value = value.strip()
    lower = value.lower()

    supplier_checks = [

        (
            [
                "electric ireland",
                "electric-ireland",
                "electric_ireland"
            ],
            "Electric Ireland"
        ),

        (
            [
                "sse airtricity",
                "airtricity",
                "sse-airtricity",
                "sse_airtricity"
            ],
            "SSE Airtricity"
        ),

        (
            [
                "bord gáis",
                "bord gais",
                "bord-gais",
                "bord_gais",
                "bordgais"
            ],
            "Bord Gáis Energy"
        ),

        (
            [
                "yuno energy",
                "yuno-energy",
                "yuno_energy",
                "yuno"
            ],
            "Yuno Energy"
        ),

        (
            [
                "prepaypower",
                "prepay power",
                "prepay-power",
                "prepay_power"
            ],
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
            [
                "waterpower",
                "water power",
                "water-power",
                "water_power"
            ],
            "Waterpower"
        ),

        (
            [
                "community power",
                "community-power",
                "community_power"
            ],
            "Community Power"
        ),

        (
            [
                "ecopower",
                "eco power",
                "eco-power",
                "eco_power"
            ],
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

    # --------------------------------------------------------
    # CHECK IMAGES
    # --------------------------------------------------------

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

    if not lines:
        return "Unknown Plan"

    return lines[0].strip()


# ============================================================
# GET ESTIMATED ANNUAL BILL
# ============================================================

def get_annual_bill(lines):

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

def create_markdown_table(df, tariff_type):

    lines = [

        f"## Switcher.ie Electricity Rankings — {tariff_type}",
        "",
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

    return "\n".join(lines)


# ============================================================
# SET UP COMMON SWITCHER FORM
# ============================================================

def setup_common_form():

    print(
        "Opening Switcher.ie..."
    )

    driver.get(
        URL
    )

    time.sleep(
        12
    )


    # --------------------------------------------------------
    # ELECTRICITY
    # --------------------------------------------------------

    print(
        "Selecting electricity..."
    )

    click_id(
        "switch_electricity"
    )


    # --------------------------------------------------------
    # CURRENT SUPPLIER = PREPAYPOWER
    # --------------------------------------------------------

    print(
        "Selecting PrepayPower..."
    )

    click_id(
        "comparison_electricity_current_supplier_prepaypower"
    )


# ============================================================
# SELECT COMMON RESULT OPTIONS
# ============================================================

def select_common_result_options():

    # --------------------------------------------------------
    # NATIONAL AVERAGE USAGE
    # --------------------------------------------------------

    print(
        "Selecting national average usage..."
    )

    click_id(
        "comparison_electricity_consumption_calculation_type_national_average"
    )


    # --------------------------------------------------------
    # SHOW ALL PLANS
    # --------------------------------------------------------

    print(
        "Selecting all plans..."
    )

    click_id(
        "comparison_electricity_search_type_all"
    )


    # --------------------------------------------------------
    # INCLUDE CASHBACK
    # --------------------------------------------------------

    print(
        "Including cashback..."
    )

    click_id(
        "comparison_electricity_include_cashback_1"
    )


# ============================================================
# SUBMIT SWITCHER FORM
# ============================================================

def submit_form():

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


# ============================================================
# READ RESULT CARDS
# ============================================================

def read_results(tariff_label):

    cards = driver.find_elements(
        By.CSS_SELECTOR,
        ".c-result-row"
    )

    print(
        f"\n{tariff_label}: "
        f"Found {len(cards)} result cards."
    )

    results = []

    checked_time = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )


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
            # DEBUG
            # ------------------------------------------------

            print("\n")
            print(
                "=" * 80
            )

            print(
                f"{tariff_label} RESULT CARD {card_number}"
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


            if not annual_bill:

                print(
                    "Skipped - no annual bill detected."
                )

                continue


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


    return results


# ============================================================
# BUILD FINAL DATAFRAME
# ============================================================

def build_dataframe(results):

    df = pd.DataFrame(
        results
    )


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


        # Remove obviously invalid prices
        df = df[
            df["Price Number"] > 500
        ]


        # Cheapest first
        df = df.sort_values(
            "Price Number",
            ascending=True
        )


        # Remove temporary price
        df = df.drop(
            columns=[
                "Price Number"
            ]
        )


        # Top 8
        df = df.head(
            8
        )


        # Reset
        df = df.reset_index(
            drop=True
        )


        # Ranking
        df.insert(

            0,

            "Rank",

            range(
                1,
                len(df) + 1
            )

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


    return df


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    df,
    csv_path,
    markdown_path,
    history_path,
    tariff_label
):

    # --------------------------------------------------------
    # CURRENT CSV
    # --------------------------------------------------------

    df.to_csv(

        csv_path,

        index=False,

        encoding="utf-8-sig"

    )

    print(
        f"Saved {tariff_label} rankings to {csv_path}"
    )


    # --------------------------------------------------------
    # MARKDOWN
    # --------------------------------------------------------

    markdown_table = create_markdown_table(
        df,
        tariff_label
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
        f"Saved {tariff_label} Markdown to "
        f"{markdown_path}"
    )


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

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
        f"Updated {tariff_label} history: "
        f"{history_path}"
    )


# ============================================================
# 24 HOUR SCRAPE
# ============================================================

def scrape_24_hour():

    print("\n")
    print(
        "#" * 80
    )

    print(
        "STARTING 24 HOUR SWITCHER SCRAPE"
    )

    print(
        "#" * 80
    )


    setup_common_form()


    # --------------------------------------------------------
    # DIRECT DEBIT
    # --------------------------------------------------------

    print(
        "Selecting Direct Debit..."
    )

    click_id(
        "comparison_electricity_payment_type_direct_debit"
    )


    # --------------------------------------------------------
    # 24 HOUR
    # --------------------------------------------------------

    print(
        "Selecting 24 Hour tariff..."
    )

    click_id(
        "comparison_electricity_meter_type_twenty_four_hour"
    )


    # --------------------------------------------------------
    # ONLINE BILLING
    # --------------------------------------------------------

    print(
        "Selecting online billing..."
    )

    click_id(
        "comparison_electricity_bill_type_online"
    )


    select_common_result_options()

    submit_form()


    results = read_results(
        "24 Hour"
    )

    df = build_dataframe(
        results
    )


    save_results(

        df,

        HOUR24_CSV,

        HOUR24_MARKDOWN,

        HOUR24_HISTORY,

        "24 Hour"

    )


    print("\n")
    print(
        "=" * 80
    )

    print(
        "FINAL 24 HOUR RANKINGS"
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
# SMART SCRAPE
# ============================================================

def scrape_smart():

    print("\n")
    print(
        "#" * 80
    )

    print(
        "STARTING SMART SWITCHER SCRAPE"
    )

    print(
        "#" * 80
    )


    # Reload form from scratch
    setup_common_form()


    # --------------------------------------------------------
    # SELECT SMART
    # --------------------------------------------------------

    print(
        "Selecting Smart tariff..."
    )

    click_id(
        "comparison_electricity_meter_type_smart"
    )

    time.sleep(
        2
    )


    # --------------------------------------------------------
    # SMART CURRENT TARIFF
    # Classic Pay Time of Use Tariff
    # --------------------------------------------------------

    print(
        "Selecting Classic Pay Time of Use Tariff..."
    )

    tariff_select = Select(

        driver.find_element(

            By.ID,

            "comparison_electricity_current_plan"

        )

    )

    tariff_select.select_by_value(
        "prepaypower-electricity-smart-classic-pay-time-of-use"
    )

    time.sleep(
        1
    )


    # --------------------------------------------------------
    # SIGNUP DATE
    # Before October 2025
    # --------------------------------------------------------

    print(
        "Selecting Before October 2025..."
    )

    signup_select = Select(

        driver.find_element(

            By.ID,

            "comparison_electricity_signup_date"

        )

    )

    signup_select.select_by_value(
        "2025-09-01"
    )

    time.sleep(
        1
    )


    # --------------------------------------------------------
    # NATIONAL AVERAGE / ALL PLANS / CASHBACK
    # --------------------------------------------------------

    select_common_result_options()


    # --------------------------------------------------------
    # SUBMIT SMART COMPARISON
    # --------------------------------------------------------

    submit_form()


    # --------------------------------------------------------
    # READ SMART RESULTS
    # --------------------------------------------------------

    results = read_results(
        "Smart"
    )


    df = build_dataframe(
        results
    )


    # --------------------------------------------------------
    # SAVE SMART FILES
    # --------------------------------------------------------

    save_results(

        df,

        SMART_CSV,

        SMART_MARKDOWN,

        SMART_HISTORY,

        "Smart"

    )


    print("\n")
    print(
        "=" * 80
    )

    print(
        "FINAL SMART RANKINGS"
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
# RUN BOTH COMPARISONS
# ============================================================

try:

    # Existing 24 Hour rankings
    scrape_24_hour()

    # New Smart rankings
    scrape_smart()


    print("\n")
    print(
        "#" * 80
    )

    print(
        "ALL SWITCHER SCRAPES COMPLETED SUCCESSFULLY"
    )

    print(
        "#" * 80
    )

    print(
        "\nGenerated files:"
    )

    print(
        f"24 Hour Markdown: {HOUR24_MARKDOWN}"
    )

    print(
        f"24 Hour CSV: {HOUR24_CSV}"
    )

    print(
        f"24 Hour History: {HOUR24_HISTORY}"
    )

    print(
        f"Smart Markdown: {SMART_MARKDOWN}"
    )

    print(
        f"Smart CSV: {SMART_CSV}"
    )

    print(
        f"Smart History: {SMART_HISTORY}"
    )


# ============================================================
# ALWAYS CLOSE CHROME
# ============================================================

finally:

    driver.quit()

    print(
        "\nChrome closed."
    )
