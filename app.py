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

# --- MODE 2: AI ROUTE OPTIMIZER (VRP PRO) ---
elif mode == "🚚 AI Route Optimizer (VRP)":
    st.success("🤖 Optimization Engine: Google OR-Tools")
    st.markdown("Solve the **Vehicle Routing Problem (VRP)** with Time Estimation & Directional Flows.")

    # Controls
    col1, col2, col3, col4 = st.columns(4)
    num_vehicles = col1.slider("🚚 Vehicles", 2, 5, 3)
    num_locations = col2.slider("📍 Stops", 5, 30, 12)
    avg_speed = col3.number_input("⚡ Avg Speed (km/h)", value=40)
    depot_city = col4.selectbox("🏢 Depot City", ["Milan (Inland)", "Naples (Coastal)", "Rome (Central)"])

    # SAFE ZONES (BOUNDING BOXES) TO AVOID WATER
    # Format: [Min Lat, Max Lat, Min Lon, Max Lon]
    city_zones = {
        "Milan (Inland)":   {'center': (45.4642, 9.1900),  'bounds': [45.40, 45.55, 9.10, 9.30]},
        "Naples (Coastal)": {'center': (40.8518, 14.2681), 'bounds': [40.86, 40.95, 14.20, 14.35]}, # Shifted North to avoid Bay
        "Rome (Central)":   {'center': (41.9028, 12.4964), 'bounds': [41.80, 42.00, 12.40, 12.60]}
    }
    
    selected_zone = city_zones[depot_city]
    depot_lat, depot_lon = selected_zone['center']

    if 'vrp_data_v4' not in st.session_state:
        st.session_state.vrp_data_v4 = None

    if st.button("🚀 Generate Scenario & Optimize"):
        
        # 1. GENERATE SMART DATA (Within Safe Bounds)
        locations = [{'id': 0, 'lat': depot_lat, 'lon': depot_lon, 'name': 'Central Depot', 'demand': 0}]
        bounds = selected_zone['bounds']
        
        for i in range(num_locations):
            # Random points ONLY within safe land box
            lat = random.uniform(bounds[0], bounds[1])
            lon = random.uniform(bounds[2], bounds[3])
            locations.append({
                'id': i+1, 
                'lat': lat, 
                'lon': lon, 
                'name': f'Store #{i+1}', 
                'demand': random.randint(1, 10)
            })
        
        # 2. DISTANCE MATRIX
        dist_matrix = {}
        for i in range(len(locations)):
            dist_matrix[i] = {}
            for j in range(len(locations)):
                dist = haversine(locations[i]['lon'], locations[i]['lat'], 
                                 locations[j]['lon'], locations[j]['lat'])
                dist_matrix[i][j] = int(dist * 1000) # Meters

        # 3. OR-TOOLS SETUP
        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Constraint: Max distance per vehicle (Force split)
        dimension_name = 'Distance'
        routing.AddDimension(transit_callback_index, 0, 300000, True, dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        # 4. SOLVE
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            routes_data = []
            colors = ['#FF0000', '#0000FF', '#008000', '#FFA500', '#800080'] # Red, Blue, Green, Orange, Purple
            
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route_coords = []
                route_details = []
                total_dist_m = 0
                
                start_time = datetime.datetime.now().replace(hour=8, minute=0, second=0) # Starts at 8:00 AM
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    loc = locations[node_index]
                    route_coords.append([loc['lat'], loc['lon']])
                    
                    # Calculate Time
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    
                    if not routing.IsEnd(index):
                        dist_m = dist_matrix[node_index][manager.IndexToNode(index)]
                        total_dist_m += dist_m
                        travel_time_min = (dist_m / 1000) / avg_speed * 60
                        arrival_time = start_time + datetime.timedelta(minutes=travel_time_min + (15 * len(route_details))) # +15 min service time
                        
                        route_details.append({
                            "name": loc['name'],
                            "eta": arrival_time.strftime("%H:%M"),
                            "dist_leg": dist_m / 1000
                        })

                # Close loop
                node_index = manager.IndexToNode(index)
                loc = locations[node_index]
                route_coords.append([loc['lat'], loc['lon']])
                
                if len(route_coords) > 2:
                    routes_data.append({
                        "vehicle_id": vehicle_id + 1,
                        "color": colors[vehicle_id % len(colors)],
                        "coords": route_coords,
                        "total_dist_km": total_dist_m / 1000,
                        "total_time_h": (total_dist_m / 1000) / avg_speed,
                        "stops": route_details
                    })
            
            st.session_state.vrp_data_v4 = {"center": [depot_lat, depot_lon], "routes": routes_data, "locations": locations}
        else:
            st.error("Optimization Failed. Try fewer stops.")

    # RENDER MAP
    if st.session_state.vrp_data_v4:
        data = st.session_state.vrp_data_v4
        m2 = folium.Map(location=data["center"], zoom_start=11, tiles="cartodbpositron") # Clean map style
        
        total_km_fleet = 0
        
        for route in data["routes"]:
            total_km_fleet += route['total_dist_km']
            
            # 1. ANIMATED PATH (AntPath) - Shows Direction
            plugins.AntPath(
                locations=route["coords"],
                color=route["color"],
                weight=5,
                opacity=0.8,
                delay=1000, # Animation speed
                tooltip=f"Vehicle {route['vehicle_id']} | {route['total_dist_km']:.1f} km"
            ).add_to(m2)
            
            # 2. MARKERS with Stop Numbers
            for i, (lat, lon) in enumerate(route["coords"][:-1]):
                is_depot = (i == 0)
                icon_color = 'black' if is_depot else route["color"]
                icon_type = 'home' if is_depot else 'circle'
                
                # Dynamic Popup Content
                if is_depot:
                    popup_html = "<b>🏭 DEPOT</b><br>Start: 08:00 AM"
                else:
                    stop_info = route["stops"][i-1] # i-1 because 0 is depot
                    popup_html = f"""
                    <b>{stop_info['name']}</b><br>
                    🚚 Vehicle: {route['vehicle_id']}<br>
                    🕒 ETA: {stop_info['eta']}<br>
                    📦 Service: 15 min
                    """
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_html, max_width=200),
                    icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')
                ).add_to(m2)

        st_folium(m2, width=1000, height=600)

        # --- KPI DASHBOARD ---
        st.markdown("### 📈 Fleet Performance Metrics")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Fleet Distance", f"{total_km_fleet:.1f} km")
        kpi2.metric("Active Vehicles", len(data["routes"]))
        kpi3.metric("Est. Fuel Cost", f"€ {total_km_fleet * 0.15:.2f}") # Approx fuel cost

        # --- DETAILED ITINERARY TABLE ---
        st.markdown("### 📋 Detailed Itinerary")
        for route in data["routes"]:
            with st.expander(f"🚛 Vehicle {route['vehicle_id']} Itinerary ({route['total_dist_km']:.1f} km)"):
                st.write(f"**Total Drive Time:** {route['total_time_h']:.1f} hours")
                st.dataframe(pd.DataFrame(route['stops']))