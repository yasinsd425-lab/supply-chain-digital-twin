import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- تنظیمات صفحه ---
st.set_page_config(layout="wide", page_title="Supply Chain Control Tower", page_icon="🌍")

st.title("🌍 Global Logistics Control Tower")
st.markdown("**Real-time visibility of Suppliers, Plants, and Distribution Centers.**")

# --- سایدبار (تنظیمات) ---
with st.sidebar:
    st.header("⚙️ Network Filters")
    show_routes = st.checkbox("Show Logistics Routes", value=True)
    show_risk = st.checkbox("Highlight Risk Zones", value=False)
    
    st.divider()
    st.info("💡 Concept: Visualizing flow from Suppliers (Blue) to Warehouses (Green).")

# --- داده‌های ساختگی (کارخانه‌ها و انبارها) ---
# مختصات شهرهای مهم اروپا (Lat, Lon)
locations = {
    "Cassino Plant (Main)": [41.49, 13.83], # دانشگاه کاسینو :)
    "Milan Warehouse": [45.46, 9.19],
    "Berlin Hub": [52.52, 13.40],
    "Paris Center": [48.85, 2.35],
    "Supplier (Istanbul)": [41.00, 28.97],
    "Supplier (Hamburg)": [53.55, 9.99]
}

# وضعیت موجودی انبارها
inventory = {
    "Cassino Plant (Main)": {"Stock": "High", "Type": "Factory"},
    "Milan Warehouse": {"Stock": "Medium", "Type": "Warehouse"},
    "Berlin Hub": {"Stock": "Low", "Type": "Warehouse"},
    "Paris Center": {"Stock": "Critical", "Type": "Warehouse"},
    "Supplier (Istanbul)": {"Stock": "N/A", "Type": "Supplier"},
    "Supplier (Hamburg)": {"Stock": "N/A", "Type": "Supplier"},
}

# --- ساخت نقشه پایه ---
# زوم اولیه روی اروپا
m = folium.Map(location=[48.0, 12.0], zoom_start=4, tiles="CartoDB dark_matter")

# --- اضافه کردن نقاط (Markers) ---
for name, coords in locations.items():
    data = inventory[name]
    
    # تعیین رنگ و آیکون بر اساس نوع
    if data["Type"] == "Factory":
        icon_color = "red"
        icon_type = "cogs" # آیکون چرخ‌دنده
    elif data["Type"] == "Supplier":
        icon_color = "blue"
        icon_type = "ship" # آیکون کشتی
    else: # Warehouse
        # تغییر رنگ بر اساس موجودی
        if data["Stock"] == "Critical":
            icon_color = "orange"
        else:
            icon_color = "green"
        icon_type = "box" # آیکون جعبه

    folium.Marker(
        location=coords,
        tooltip=f"<b>{name}</b>",
        popup=f"Type: {data['Type']}<br>Status: {data['Stock']}",
        icon=folium.Icon(color=icon_color, prefix="fa", icon=icon_type)
    ).add_to(m)

# --- رسم مسیرها (Routes) ---
if show_routes:
    # مسیر تامین‌کننده استانبول به کاسینو
    folium.PolyLine(
        locations=[locations["Supplier (Istanbul)"], locations["Cassino Plant (Main)"]],
        color="cyan", weight=2, opacity=0.7, dash_array='5, 10', tooltip="Raw Material Flow"
    ).add_to(m)
    
    # مسیر هامبورگ به برلین
    folium.PolyLine(
        locations=[locations["Supplier (Hamburg)"], locations["Berlin Hub"]],
        color="cyan", weight=2, opacity=0.7, dash_array='5, 10'
    ).add_to(m)

    # مسیر توزیع از کاسینو به میلان و پاریس
    folium.PolyLine(
        locations=[locations["Cassino Plant (Main)"], locations["Milan Warehouse"]],
        color="yellow", weight=3, tooltip="Distribution Route"
    ).add_to(m)
    
    folium.PolyLine(
        locations=[locations["Milan Warehouse"], locations["Paris Center"]],
        color="yellow", weight=3
    ).add_to(m)

# --- نمایش مناطق خطر (Risk Zones) ---
if show_risk:
    # مثلاً منطقه دریایی (ریسک طوفان)
    folium.Circle(
        location=[40.0, 18.0], # وسط دریای مدیترانه
        radius=200000, # متر
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=0.2,
        tooltip="⚠️ Storm Warning Zone"
    ).add_to(m)

# --- نمایش نقشه در استریم‌لیت ---
col1, col2 = st.columns([3, 1])

with col1:
    st_folium(m, width=800, height=500)

with col2:
    st.subheader("📊 Warehouse Status")
    # تبدیل دیکشنری به دیتافریم برای نمایش جدول
    df = pd.DataFrame.from_dict(inventory, orient='index')
    st.dataframe(df)
    
    st.metric("Total Active Routes", "4")
    st.metric("Critical Alerts", "1", delta="-2", delta_color="inverse")