import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# NEXUS AI — An Intelligent Business Decision Lab
# --------------------------------------------------

st.set_page_config(
    page_title="NEXUS AI | Business Decision Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Data loading
# --------------------------------------------------

@st.cache_data(show_spinner="Loading and preparing the project data...")
def load_data():
    required_files = [
        "nexus_ai_sales_data.zip",
        "nexus_ai_monthly_sales.csv",
        "nexus_ai_segment_summary.csv",
        "nexus_ai_customer_segments.csv",
    ]

    missing_files = [
        filename for filename in required_files
        if not Path(filename).exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "The following required files are missing from the "
            "GitHub repository: " + ", ".join(missing_files)
        )

    # Load sales data from the ZIP file.
    # IMPORTANT: Keep InvoiceNo as text to avoid mixed-type parsing.
    with zipfile.ZipFile("nexus_ai_sales_data.zip", "r") as archive:
        csv_files = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
            and not name.startswith("__MACOSX/")
        ]

        if not csv_files:
            raise ValueError(
                "The ZIP file does not contain a CSV file."
            )

        with archive.open(csv_files[0]) as file:
            sales = pd.read_csv(
                file,
                dtype={"InvoiceNo": "string"},
                low_memory=False,
            )

    monthly = pd.read_csv("nexus_ai_monthly_sales.csv")
    segment_summary = pd.read_csv("nexus_ai_segment_summary.csv")
    customers = pd.read_csv("nexus_ai_customer_segments.csv")

    # Check that the expected columns exist.
    required_sales_columns = {
        "InvoiceNo",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
        "CustomerID",
        "LineValue",
    }

    required_customer_columns = {
        "CustomerID",
        "Segment",
        "Recency",
        "Frequency",
        "Monetary",
        "LastPurchaseDate",
    }

    required_monthly_columns = {
        "YearMonth",
        "SalesValue",
    }

    if not required_sales_columns.issubset(sales.columns):
        missing = sorted(
            required_sales_columns - set(sales.columns)
        )
        raise ValueError(
            "Sales CSV is missing these columns: "
            + ", ".join(missing)
        )

    if not required_customer_columns.issubset(customers.columns):
        missing = sorted(
            required_customer_columns - set(customers.columns)
        )
        raise ValueError(
            "Customer segments CSV is missing these columns: "
            + ", ".join(missing)
        )

    if not required_monthly_columns.issubset(monthly.columns):
        missing = sorted(
            required_monthly_columns - set(monthly.columns)
        )
        raise ValueError(
            "Monthly sales CSV is missing these columns: "
            + ", ".join(missing)
        )

    # Normalize invoice numbers consistently.
    # This removes accidental whitespace and preserves invoice IDs
    # as text, so the distinct invoice count is calculated correctly.
    sales["InvoiceNo"] = (
        sales["InvoiceNo"]
        .astype("string")
        .str.strip()
    )

    sales["InvoiceNo"] = sales["InvoiceNo"].replace("", pd.NA)

    # Convert sales columns to appropriate data types.
    sales["InvoiceDate"] = pd.to_datetime(
        sales["InvoiceDate"],
        errors="coerce",
    )

    sales["LineValue"] = pd.to_numeric(
        sales["LineValue"],
        errors="coerce",
    )

    sales["Quantity"] = pd.to_numeric(
        sales["Quantity"],
        errors="coerce",
    )

    sales["UnitPrice"] = pd.to_numeric(
        sales["UnitPrice"],
        errors="coerce",
    )

    # Prepare monthly sales data.
    monthly["YearMonth"] = monthly["YearMonth"].astype(str)

    monthly["SalesValue"] = pd.to_numeric(
        monthly["SalesValue"],
        errors="coerce",
    )

    # Prepare customer segmentation data.
    customers["CustomerID"] = (
        customers["CustomerID"]
        .astype("string")
        .str.strip()
    )

    customers["CustomerID"] = customers["CustomerID"].replace(
        "",
        pd.NA,
    )

    customers["Segment"] = customers["Segment"].astype(str)

    for column in ["Recency", "Frequency", "Monetary"]:
        customers[column] = pd.to_numeric(
            customers[column],
            errors="coerce",
        )

    customers["LastPurchaseDate"] = pd.to_datetime(
        customers["LastPurchaseDate"],
        errors="coerce",
    )

    return sales, monthly, segment_summary, customers


# --------------------------------------------------
# Load data and handle errors clearly
# --------------------------------------------------

try:
    sales, monthly, segment_summary, customers = load_data()

except Exception as error:
    st.error("NEXUS AI could not load the project data.")

    st.markdown(
        "Check that all four data files are uploaded to the same "
        "GitHub repository as `app.py`."
    )

    st.code(str(error))
    st.stop()


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("📊 NEXUS AI")
st.subheader("An Intelligent Business Decision Lab")

st.markdown(
    """
    **AI for Business | MS5061T | MBA Project**

    NEXUS AI transforms historical retail transaction data into
    business insights through sales analytics, customer segmentation,
    and evidence-informed decision support.
    """
)

st.caption(
    "Dataset: UCI Online Retail | Historical observation period: "
    "December 2010 to December 2011. December 2011 is incomplete."
)

st.divider()


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.title("Dashboard controls")
st.sidebar.markdown("Filter the analysis below.")

segment_options = sorted(
    customers["Segment"].dropna().unique().tolist()
)

selected_segments = st.sidebar.multiselect(
    "Customer segments",
    options=segment_options,
    default=segment_options,
)

sales_dates = sales["InvoiceDate"].dropna()

if not sales_dates.empty:
    min_date = sales_dates.min().date()
    max_date = sales_dates.max().date()

    date_range = st.sidebar.date_input(
        "Sales date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if (
        isinstance(date_range, (tuple, list))
        and len(date_range) == 2
    ):
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

else:
    start_date, end_date = None, None


# Filter customer data by selected segments.
filtered_customers = customers[
    customers["Segment"].isin(selected_segments)
].copy()


# Filter sales data by selected dates.
filtered_sales = sales.copy()

if start_date is not None and end_date is not None:
    filtered_sales = filtered_sales[
        filtered_sales["InvoiceDate"].dt.date.between(
            start_date,
            end_date,
        )
    ]


# Filter monthly sales using the selected date range.
filtered_monthly = monthly.copy()

if start_date is not None and end_date is not None:
    filtered_monthly["_MonthDate"] = pd.to_datetime(
        filtered_monthly["YearMonth"] + "-01",
        errors="coerce",
    )

    filtered_monthly = filtered_monthly[
        (filtered_monthly["_MonthDate"].dt.date <= end_date)
        & (
            filtered_monthly["_MonthDate"].dt.to_period("M")
            >= pd.Period(start_date, freq="M")
        )
    ]


# --------------------------------------------------
# Section 1: Business overview
# --------------------------------------------------

st.header("1. Business overview")

total_sales = filtered_sales["LineValue"].sum()

# Count unique, non-missing invoice IDs.
# InvoiceNo is normalized as text in load_data().
total_invoices = filtered_sales["InvoiceNo"].nunique(
    dropna=True
)

identified_customers = filtered_sales["CustomerID"].nunique(
    dropna=True
)

average_invoice_value = (
    total_sales / total_invoices
    if total_invoices
    else 0
)

missing_customer_rows = (
    filtered_sales["CustomerID"].isna().sum()
)

total_sales_rows = len(filtered_sales)

missing_customer_pct = (
    missing_customer_rows / total_sales_rows * 100
    if total_sales_rows
    else 0
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    "Recorded sales value",
    f"{total_sales:,.2f}",
)

kpi2.metric(
    "Distinct invoices",
    f"{total_invoices:,}",
)

kpi3.metric(
    "Identified customers",
    f"{identified_customers:,}",
)

kpi4.metric(
    "Average invoice value",
    f"{average_invoice_value:,.2f}",
)

st.caption(
    "Sales value is calculated as the sum of Quantity × UnitPrice "
    "in the prepared transaction data. Currency is not independently "
    "verified here. These figures describe recorded data, not audited "
    "financial results."
)

st.divider()


# --------------------------------------------------
# Section 2: Sales performance
# --------------------------------------------------

st.header("2. Sales performance")

left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Monthly recorded sales value")

    if not filtered_monthly.empty:
        fig_monthly = px.line(
            filtered_monthly,
            x="YearMonth",
            y="SalesValue",
            markers=True,
            title="Monthly sales trend",
            labels={
                "YearMonth": "Month",
                "SalesValue": "Recorded sales value",
            },
        )

        fig_monthly.update_layout(
            xaxis_title="Month",
            yaxis_title="Recorded sales value",
            hovermode="x unified",
        )

        st.plotly_chart(
            fig_monthly,
            use_container_width=True,
        )

    else:
        st.info(
            "No monthly sales data is available for this date range."
        )


with right_chart:
    st.subheader("Transaction activity")

    if not filtered_sales.empty:
        invoice_activity = (
            filtered_sales.groupby(
                filtered_sales["InvoiceDate"].dt.to_period("M")
            )
            .agg(
                TransactionLines=("InvoiceNo", "size"),
                DistinctInvoices=("InvoiceNo", "nunique"),
            )
            .reset_index()
        )

        invoice_activity["Month"] = (
            invoice_activity["InvoiceDate"].astype(str)
        )

        fig_activity = px.bar(
            invoice_activity,
            x="Month",
            y="DistinctInvoices",
            title="Distinct invoices by month",
            labels={
                "Month": "Month",
                "DistinctInvoices": "Distinct invoices",
            },
        )

        st.plotly_chart(
            fig_activity,
            use_container_width=True,
        )

    else:
        st.info(
            "No transaction activity is available for this date range."
        )


st.subheader("Sales data quality")

quality1, quality2 = st.columns(2)

quality1.metric(
    "Rows missing CustomerID",
    f"{missing_customer_rows:,}",
)

quality2.metric(
    "Rows missing CustomerID (%)",
    f"{missing_customer_pct:.2f}%",
)

st.caption(
    "Customers without a CustomerID cannot be reliably included in "
    "individual customer-level RFM segmentation."
)

st.divider()


# --------------------------------------------------
# Section 3: Customer segmentation
# --------------------------------------------------

st.header("3. Customer segmentation")

st.markdown(
    """
    Customer segments are based on historical Recency, Frequency,
    and Monetary (RFM) measures and the K-Means clustering model
    created during the analysis. Segment labels are descriptive;
    they are not guarantees of future customer behaviour.
    """
)

if not filtered_customers.empty:
    segment_counts = (
        filtered_customers.groupby("Segment")
        .size()
        .reset_index(name="Customers")
    )

    segment_chart_col, segment_table_col = st.columns(2)

    with segment_chart_col:
        fig_segments = px.bar(
            segment_counts,
            x="Segment",
            y="Customers",
            color="Segment",
            text="Customers",
            title="Customers by segment",
        )

        fig_segments.update_layout(
            showlegend=False
        )

        st.plotly_chart(
            fig_segments,
            use_container_width=True,
        )

    with segment_table_col:
        st.subheader("Segment profile")

        segment_metrics = (
            filtered_customers.groupby("Segment")
            .agg(
                CustomerCount=("CustomerID", "nunique"),
                MedianRecency=("Recency", "median"),
                MedianFrequency=("Frequency", "median"),
                MedianMonetary=("Monetary", "median"),
            )
            .reset_index()
            .round(2)
        )

        st.dataframe(
            segment_metrics,
            use_container_width=True,
            hide_index=True,
        )

    fig_rfm = px.bar(
        segment_metrics,
        x="Segment",
        y="MedianMonetary",
        color="Segment",
        text="MedianMonetary",
        title="Median recorded customer sales value by segment",
        labels={
            "Segment": "Customer segment",
            "MedianMonetary": "Median recorded sales value",
        },
    )

    fig_rfm.update_layout(
        showlegend=False
    )

    st.plotly_chart(
        fig_rfm,
        use_container_width=True,
    )

else:
    st.warning(
        "No customers match the selected segment filters."
    )

st.divider()


# --------------------------------------------------
# Section 4: Customer explorer
# --------------------------------------------------

st.header("4. Customer explorer")

st.markdown(
    "Search and inspect the customer-level RFM results."
)

search_id = st.text_input(
    "Search by CustomerID (optional)",
    placeholder="For example, 12347",
)

table_data = filtered_customers.copy()

if search_id.strip():
    table_data = table_data[
        table_data["CustomerID"].str.contains(
            search_id.strip(),
            case=False,
            na=False,
            regex=False,
        )
    ]

columns_to_show = [
    "CustomerID",
    "Segment",
    "Recency",
    "Frequency",
    "Monetary",
    "LastPurchaseDate",
]

st.caption(
    f"Matching customers: {len(table_data):,}"
)

st.dataframe(
    table_data[columns_to_show],
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    label="Download filtered customer data",
    data=table_data.to_csv(index=False).encode("utf-8"),
    file_name="nexus_ai_filtered_customers.csv",
    mime="text/csv",
)

st.divider()


# --------------------------------------------------
# Section 5: Decision support
# --------------------------------------------------

st.header("5. Decision support")

st.markdown(
    """
    The following are **potential business actions to test**, based
    on the observed historical segment profiles. They are hypotheses,
    not proven business outcomes.
    """
)

st.subheader("More engaged, higher-value customers")

st.markdown(
    """
    - Test relevant loyalty benefits or early access to selected products.
    - Evaluate whether these customers respond to cross-selling or
      complementary product recommendations.
    - Track repeat purchase rate and recorded sales value before and
      after a campaign, using an appropriate comparison group where possible.
    """
)

st.subheader("Less recently active, lower-value customers")

st.markdown(
    """
    - Test a re-engagement campaign with a limited, measurable offer.
    - Compare response rates across customer groups before expanding
      campaign spending.
    - Monitor reactivation, repeat purchase, and campaign cost rather
      than assuming that every inactive customer will return.
    """
)

st.subheader("Data and modelling considerations")

st.markdown(
    f"""
    - **Customer coverage:** {missing_customer_pct:.2f}% of the currently
      filtered transaction rows have no CustomerID, so the segmentation
      does not represent every transaction.
    - **Historical scope:** the dataset ends on 9 December 2011, so
      December is a partial month.
    - **Model selection:** the analysis selected K-Means with two clusters
      from the tested candidates using a silhouette-score comparison.
    - **Validation:** segment stability and the effect of proposed
      campaigns should be tested before making operational decisions.
    """
)

st.divider()


# --------------------------------------------------
# Section 6: Methodology and project notes
# --------------------------------------------------

st.header("6. Methodology and project notes")

with st.expander(
    "View data preparation and analytical approach"
):
    st.markdown(
        """
        **Data preparation**

        - Positive-quantity and positive-unit-price transaction rows
          were retained for the prepared sales analysis.
        - Cancellation invoices beginning with `C` were excluded.
        - Exact duplicate rows were removed under the documented
          preprocessing rule.
        - Line value was calculated as Quantity × UnitPrice.
        - Rows without CustomerID were excluded from customer-level RFM
          segmentation but retained in the prepared transaction data
          when they met the sales inclusion rules.

        **Customer analytics**

        - Recency: days since the customer's latest recorded purchase
          relative to the analysis cutoff.
        - Frequency: number of distinct invoices associated with the customer.
        - Monetary: sum of recorded transaction line values for the customer.
        - K-Means was applied to log-transformed RFM variables after
          standardisation.
        - Candidate cluster counts from 2 through 6 were compared using
          silhouette scores on a reproducible sample.

        **Interpretation**

        This dashboard is a decision-support prototype built from
        historical data. It does not establish causation, forecast future
        sales, or demonstrate that a recommended action will be profitable.
        """
    )

st.caption(
    "NEXUS AI | MBA AI for Business Project | MS5061T"
)
