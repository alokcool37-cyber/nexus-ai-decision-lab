
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="NEXUS AI Decision Lab",
    page_icon="📊",
    layout="wide"
)

st.title("NEXUS AI Decision Lab")
st.caption("Interactive Sales & Customer Analytics Dashboard")

DATA_DIR = Path(__file__).parent

@st.cache_data
def load_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    return pd.read_csv(path)

sales = load_csv("nexus_ai_sales_data.csv")
monthly = load_csv("nexus_ai_monthly_sales.csv")
segment_summary = load_csv("nexus_ai_segment_summary.csv")
customers = load_csv("nexus_ai_customer_segments.csv")

missing = [
    name for name, data in [
        ("nexus_ai_sales_data.csv", sales),
        ("nexus_ai_monthly_sales.csv", monthly),
        ("nexus_ai_segment_summary.csv", segment_summary),
        ("nexus_ai_customer_segments.csv", customers),
    ] if data is None
]

if missing:
    st.warning("Please upload these CSV files to the repository:")
    for filename in missing:
        st.write(f"- {filename}")
    st.info("The dashboard will display your analysis after the files are added.")
    st.stop()

st.sidebar.header("Dashboard Filters")

if "Segment" in customers.columns:
    segments = sorted(
        customers["Segment"].dropna().astype(str).unique()
    )
    selected_segments = st.sidebar.multiselect(
        "Customer segments",
        segments,
        default=segments
    )
    filtered_customers = customers[
        customers["Segment"].astype(str).isin(selected_segments)
    ]
else:
    filtered_customers = customers.copy()
    st.sidebar.info("No Segment column found in customer data.")

if "LineValue" in sales.columns:
    sales["LineValue"] = pd.to_numeric(
        sales["LineValue"], errors="coerce"
    )
    total_sales = sales["LineValue"].sum()
else:
    total_sales = None

invoice_count = (
    sales["InvoiceNo"].nunique()
    if "InvoiceNo" in sales.columns else None
)
customer_count = (
    sales["CustomerID"].nunique()
    if "CustomerID" in sales.columns else None
)

if total_sales is not None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Candidate Sales Value", f"{total_sales:,.2f}")
    col2.metric(
        "Distinct Invoices",
        f"{invoice_count:,}" if invoice_count is not None else "N/A"
    )
    col3.metric(
        "Identified Customers",
        f"{customer_count:,}" if customer_count is not None else "N/A"
    )
else:
    st.warning("The sales CSV does not contain a LineValue column.")

st.divider()
st.subheader("1. Monthly Sales Performance")

if {"YearMonth", "SalesValue"}.issubset(monthly.columns):
    monthly["SalesValue"] = pd.to_numeric(
        monthly["SalesValue"], errors="coerce"
    )
    fig = px.line(
        monthly,
        x="YearMonth",
        y="SalesValue",
        markers=True,
        title="Monthly Sales Trend"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(monthly, use_container_width=True)
else:
    st.warning("Check the monthly CSV column names.")

st.divider()
st.subheader("2. Customer Segment Overview")

if "Segment" in filtered_customers.columns:
    counts = (
        filtered_customers["Segment"]
        .value_counts()
        .rename_axis("Segment")
        .reset_index(name="Customers")
    )
    fig = px.bar(
        counts,
        x="Segment",
        y="Customers",
        color="Segment",
        title="Customers by Segment"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Customer segment chart requires a Segment column.")

if {"Segment", "CustomerID"}.issubset(segment_summary.columns):
    st.subheader("Segment Summary")
    st.dataframe(segment_summary, use_container_width=True)

st.divider()
st.subheader("3. Customer Explorer")

st.write(f"Customers matching the selected filters: {len(filtered_customers):,}")

search = st.text_input(
    "Search customer data",
    placeholder="Enter a customer ID or keyword"
)

display_customers = filtered_customers.copy()

if search:
    mask = display_customers.astype(str).apply(
        lambda column: column.str.contains(
            search, case=False, na=False
        )
    ).any(axis=1)
    display_customers = display_customers[mask]

st.dataframe(display_customers, use_container_width=True)

csv_data = display_customers.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download filtered customers CSV",
    data=csv_data,
    file_name="nexus_ai_filtered_customers.csv",
    mime="text/csv"
)

st.caption(
    "NEXUS AI Decision Lab | Analytics prototype. "
    "Figures depend on the uploaded analysis files."
)
