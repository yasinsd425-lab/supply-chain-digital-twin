import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins
import random
from math import radians, cos, sin, asin, sqrt
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Supply Chain Control Tower V4.0", page_icon="🌍", layout="wide")

st.title("🌍 Supply Chain Digital Twin & AI Optimizer")
st.markdown("### Industrial Engineering Portfolio | Unicas")

# --- SIDEBAR ---
st.sidebar.header("Control Panel")
mode = st.sidebar.radio("Select Mode:", ["📊 Network Monitoring (Digital Twin)", "🚚 AI Route Optimizer (VRP)"])

# --- HELPER: HAVERSINE DISTANCE ---
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 
    return c * r

# --- MODE 1: MONITORING ---
if mode == "📊 Network Monitoring (Digital Twin)":
    st.info("Visualizing static nodes and inventory levels.")
    # (کد بخش مانیتورینگ بدون تغییر باقی می‌ماند برای خلاصه شدن)
    data = {
        'Location': ['Factory Rome', 'DC Milan', 'Warehouse Naples', 'Supplier Turin', 'Port Genoa'],
        'Type': ['Plant', 'DC', 'Warehouse', 'Supplier', 'Port'],
        'Lat': [41.9028, 45.4642, 40.8518, 45.0703, 44.4056],
        'Lon': [12.4964, 9.1900, 14.2681, 7.6869, 8.9463],
        'Inventory': [1200, 8500, 3400, 0, 5600],
        'Status': ['Normal', 'Critical', 'Normal', 'Normal', 'Risk']
    }
    df = pd.DataFrame(data)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Nodes", len(df))
    col2.metric("Critical Alerts", len(df[df['Status']=='Critical']))
    col3.metric("Total Inventory", f"{df['Inventory'].sum():,}")

    m = folium.Map(location=[42.5, 12.5], zoom_start=6)
    for index, row in df.iterrows():
        color = 'red' if row['Status'] in ['Critical', 'Risk'] else 'green'
        icon = 'industry' if row['Type'] == 'Plant' else 'truck'
        folium.Marker(
            [row['Lat'], row['Lon']],
            popup=f"<b>{row['Location']}</b><br>Stock: {row['Inventory']}",
            tooltip=row['Location'],
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    st_folium(m, width=1000, height=500)

# --- MODE 2: AI ROUTE OPTIMIZER (VRP PRO + REAL TIME TRAFFIC) ---
elif mode == "🚚 AI Route Optimizer (VRP)":
    st.success("🤖 Optimization Engine: Google OR-Tools")
    st.markdown("Solve VRP with **Dynamic Traffic Simulation**.")

    # Controls
    col1, col2, col3, col4 = st.columns(4)
    num_vehicles = col1.slider("🚚 Vehicles", 2, 5, 3)
    num_locations = col2.slider("📍 Stops", 5, 30, 15)
    # Speed is now used for dynamic calculation, not just initial solve
    base_speed = col3.number_input("⚡ Max Speed (km/h)", value=60) 
    depot_city = col4.selectbox("🏢 Depot City", ["Milan (Inland)", "Naples (Coastal)", "Rome (Central)"])

    # Traffic Simulation Slider
    traffic_intensity = st.slider("🚦 Traffic Intensity (Slows down operations)", 0, 100, 20, format="%d%%")
    
    # Calculate Effective Speed based on Traffic
    effective_speed = base_speed * (1 - (traffic_intensity / 100))
    st.caption(f"ℹ️ Effective Average Speed considering traffic: **{effective_speed:.1f} km/h**")

    # SAFE ZONES
    city_zones = {
        "Milan (Inland)":   {'center': (45.4642, 9.1900),  'bounds': [45.40, 45.55, 9.10, 9.30]},
        "Naples (Coastal)": {'center': (40.8518, 14.2681), 'bounds': [40.86, 40.95, 14.20, 14.35]},
        "Rome (Central)":   {'center': (41.9028, 12.4964), 'bounds': [41.80, 42.00, 12.40, 12.60]}
    }
    selected_zone = city_zones[depot_city]
    depot_lat, depot_lon = selected_zone['center']

    # Initialize Session State
    if 'vrp_data_v5' not in st.session_state:
        st.session_state.vrp_data_v5 = None

    # --- BUTTON: GENERATE GEOMETRY ONLY ---
    if st.button("🚀 Generate Scenario & Solve Routes"):
        
        # 1. GENERATE POINTS
        locations = [{'id': 0, 'lat': depot_lat, 'lon': depot_lon, 'name': 'Central Depot'}]
        bounds = selected_zone['bounds']
        for i in range(num_locations):
            lat = random.uniform(bounds[0], bounds[1])
            lon = random.uniform(bounds[2], bounds[3])
            locations.append({'id': i+1, 'lat': lat, 'lon': lon, 'name': f'Store #{i+1}'})
        
        # 2. MATRIX & SOLVER
        dist_matrix = {}
        for i in range(len(locations)):
            dist_matrix[i] = {}
            for j in range(len(locations)):
                dist = haversine(locations[i]['lon'], locations[i]['lat'], 
                                 locations[j]['lon'], locations[j]['lat'])
                dist_matrix[i][j] = int(dist * 1000)

        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        routing.AddDimension(transit_callback_index, 0, 300000, True, 'Distance')
        
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            # SAVE RAW GEOMETRY DATA ONLY (Distances, not Times)
            raw_routes = []
            colors = ['red', 'blue', 'green', 'orange', 'purple']
            
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route_legs = [] # Store individual legs to recalc time later
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    start_loc = locations[node_index]
                    
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    next_node_index = manager.IndexToNode(index)
                    end_loc = locations[next_node_index]
                    
                    dist_m = dist_matrix[node_index][next_node_index]
                    
                    route_legs.append({
                        "start_coords": [start_loc['lat'], start_loc['lon']],
                        "end_coords": [end_loc['lat'], end_loc['lon']],
                        "end_name": end_loc['name'],
                        "dist_m": dist_m
                    })
                
                if len(route_legs) > 0:
                    raw_routes.append({
                        "vehicle_id": vehicle_id + 1,
                        "color": colors[vehicle_id % len(colors)],
                        "legs": route_legs
                    })
            
            st.session_state.vrp_data_v5 = {"center": [depot_lat, depot_lon], "raw_routes": raw_routes}
        else:
            st.error("Optimization Failed. Try again.")

    # --- DYNAMIC RENDERER (Runs on every interaction) ---
    if st.session_state.vrp_data_v5:
        data = st.session_state.vrp_data_v5
        m2 = folium.Map(location=data["center"], zoom_start=11)
        
        total_fleet_km = 0
        total_fleet_hours = 0
        
        # Recalculate Times based on CURRENT Effective Speed
        current_time_base = datetime.datetime.now().replace(hour=8, minute=0, second=0)
        
        for route in data["raw_routes"]:
            vehicle_time = current_time_base
            route_coords = [[data["center"][0], data["center"][1]]] # Start at depot
            route_km = 0
            
            # Draw Route & Markers
            for leg in route["legs"]:
                # Logic: Time = Distance / Speed
                travel_min = (leg["dist_m"] / 1000) / max(effective_speed, 1) * 60 # Avoid div by zero
                service_min = 15 # Fixed service time
                
                vehicle_time += datetime.timedelta(minutes=travel_min + service_min)
                eta_str = vehicle_time.strftime("%H:%M")
                
                route_coords.append(leg["end_coords"])
                route_km += leg["dist_m"] / 1000
                
                # Add Marker with DYNAMIC ETA
                if "Depot" not in leg["end_name"]:
                    folium.CircleMarker(
                        leg["end_coords"],
                        radius=6,
                        color=route["color"],
                        fill=True,
                        fill_opacity=1,
                        popup=f"<b>{leg['end_name']}</b><br>ETA: {eta_str}<br>Dist: {leg['dist_m']/1000:.1f}km",
                        tooltip=f"{leg['end_name']} (ETA: {eta_str})"
                    ).add_to(m2)
            
            # Draw Lines
            folium.PolyLine(route_coords, color=route["color"], weight=4, opacity=0.8).add_to(m2)
            plugins.AntPath(route_coords, color=route["color"], weight=4, delay=800, opacity=0).add_to(m2) # Invisible antpath for flow
            
            # Stats per vehicle
            total_fleet_km += route_km
            total_fleet_hours += (vehicle_time - current_time_base).total_seconds() / 3600

        # Add Depot Marker
        folium.Marker(data["center"], popup="DEPOT (Start 08:00)", icon=folium.Icon(color='black', icon='home')).add_to(m2)

        st_folium(m2, width=1000, height=600)

        # Dynamic KPIs
        st.markdown("### 🚦 Live Operations Metrics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Effective Speed", f"{effective_speed:.1f} km/h", delta=f"-{traffic_intensity}% Traffic")
        k2.metric("Total Distance", f"{total_fleet_km:.1f} km")
        k3.metric("Total Time (Fleet)", f"{total_fleet_hours:.1f} hrs")
        k4.metric("Est. Cost", f"€ {total_fleet_km * 0.85:.0f}")