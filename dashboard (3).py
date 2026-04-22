import streamlit as st
import pandas as pd
import zipfile
import os
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(
    page_title="Dashboard Analisis E-Commerce",
    layout="wide"
)

sns.set(style="whitegrid")

@st.cache_data
def load_data():
    zip_path = "E-commerce-public-dataset.zip"
    extract_path = "ecommerce_data"

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    base_path = os.path.join(extract_path, "E-Commerce Public Dataset")

    customers_df = pd.read_csv(os.path.join(base_path, "customers_dataset.csv"))
    orders_df = pd.read_csv(os.path.join(base_path, "orders_dataset.csv"))
    order_items_df = pd.read_csv(os.path.join(base_path, "order_items_dataset.csv"))
    order_payments_df = pd.read_csv(os.path.join(base_path, "order_payments_dataset.csv"))
    products_df = pd.read_csv(os.path.join(base_path, "products_dataset.csv"))
    category_df = pd.read_csv(os.path.join(base_path, "product_category_name_translation.csv"))

    datetime_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_customer_date"
    ]

    for col in datetime_cols:
        orders_df[col] = pd.to_datetime(orders_df[col], errors="coerce")

    products_df["product_category_name"] = products_df["product_category_name"].fillna("unknown")

    products_df = products_df.merge(
        category_df,
        on="product_category_name",
        how="left"
    )

    products_df["product_category_name_english"] = products_df["product_category_name_english"].fillna("unknown")

    all_df = orders_df.merge(order_items_df, on="order_id", how="inner")
    all_df = all_df.merge(products_df, on="product_id", how="left")
    all_df = all_df.merge(customers_df, on="customer_id", how="left")
    all_df = all_df.merge(order_payments_df, on="order_id", how="left")

    all_df["order_month"] = all_df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    all_df["order_date"] = all_df["order_purchase_timestamp"].dt.date

    return all_df


all_df = load_data()

st.title("📊 Dashboard Analisis E-Commerce")
st.caption("Periode Analisis: September 2016 - Agustus 2018")

st.sidebar.header("Filter Dashboard")

min_date = all_df["order_date"].min()
max_date = all_df["order_date"].max()

date_range = st.sidebar.date_input(
    "Pilih Rentang Tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

category_options = sorted(all_df["product_category_name_english"].dropna().unique())

selected_categories = st.sidebar.multiselect(
    "Pilih Kategori Produk",
    options=category_options,
    default=category_options[:10]
)

filtered_df = all_df[
    (all_df["order_date"] >= start_date) &
    (all_df["order_date"] <= end_date) &
    (all_df["product_category_name_english"].isin(selected_categories))
]

if filtered_df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

st.subheader("Ringkasan Utama")

total_orders = filtered_df["order_id"].nunique()
total_revenue = filtered_df["price"].sum()
total_customers = filtered_df["customer_unique_id"].nunique()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Orders", f"{total_orders:,}")

with col2:
    st.metric("Total Revenue", f"{total_revenue:,.2f}")

with col3:
    st.metric("Total Customers", f"{total_customers:,}")

monthly_orders = filtered_df.groupby("order_month")["order_id"].nunique().reset_index()
monthly_revenue = filtered_df.groupby("order_month")["price"].sum().reset_index()

st.subheader("Tren Jumlah Pesanan")

fig, ax = plt.subplots(figsize=(10, 4))
sns.lineplot(data=monthly_orders, x="order_month", y="order_id", marker="o", ax=ax)
plt.xticks(rotation=45)
st.pyplot(fig)

st.subheader("Tren Revenue")

fig, ax = plt.subplots(figsize=(10, 4))
sns.lineplot(data=monthly_revenue, x="order_month", y="price", marker="o", ax=ax)
plt.xticks(rotation=45)
st.pyplot(fig)

category_revenue = (
    filtered_df.groupby("product_category_name_english")["price"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

st.subheader("Top 10 Kategori Produk Berdasarkan Revenue")

fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(data=category_revenue, x="price", y="product_category_name_english", ax=ax)
st.pyplot(fig)

rfm_df = filtered_df.groupby("customer_unique_id").agg({
    "order_purchase_timestamp": "max",
    "order_id": "nunique",
    "price": "sum"
}).reset_index()

rfm_df.columns = ["customer_id", "last_order", "frequency", "monetary"]

recent_date = filtered_df["order_purchase_timestamp"].max()
rfm_df["recency"] = (recent_date - rfm_df["last_order"]).dt.days

st.subheader("Distribusi RFM")

fig, ax = plt.subplots(1, 3, figsize=(15, 4))

sns.histplot(rfm_df["recency"], ax=ax[0])
ax[0].set_title("Recency")

sns.histplot(rfm_df["frequency"], ax=ax[1])
ax[1].set_title("Frequency")

sns.histplot(rfm_df["monetary"], ax=ax[2])
ax[2].set_title("Monetary")

st.pyplot(fig)

st.subheader("Insight Utama")

st.markdown("""
- Tren pesanan dan revenue menunjukkan peningkatan hingga akhir 2017 sebelum mengalami fluktuasi, yang mengindikasikan dinamika permintaan dari waktu ke waktu.

- Kategori produk seperti *health_beauty*, *watches_gifts*, dan *bed_bath_table* menjadi kontributor utama revenue dan dapat diprioritaskan dalam strategi bisnis.

- Sebagian besar pelanggan memiliki frekuensi pembelian rendah, yang menunjukkan dominasi pembeli sesekali.

- Sebagian kecil pelanggan dengan nilai transaksi tinggi memberikan kontribusi besar terhadap revenue, sehingga perlu difokuskan dalam strategi retensi.
""")
