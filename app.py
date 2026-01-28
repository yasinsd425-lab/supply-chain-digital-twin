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
st.set_page_config(page_title="Supply Chain Control Tower V7.0", page_icon="🌍", layout="wide")

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
    # (کد بخش مانیتورینگ ثابت)
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

# --- MODE 2: AI ROUTE OPTIMIZER (VRP COMPLETE) ---
elif mode == "🚚 AI Route Optimizer (VRP)":
    st.success("🤖 Optimization Engine: Google OR-Tools")
    st.markdown("Solve VRP with **Dynamic Traffic, Load Balancing & Detailed Logistics**.")

    # Controls
    col1, col2, col3, col4 = st.columns(4)
    num_vehicles = col1.slider("🚚 Vehicles", 2, 5, 3)
    num_locations = col2.slider("📍 Stops", 5, 30, 15)
    base_speed = col3.number_input("⚡ Max Speed (km/h)", value=60) 
    depot_city = col4.selectbox("🏢 Depot City", ["Milan (Inland)", "Naples (Coastal)", "Rome (Central)"])

    # Traffic Simulation Slider
    traffic_intensity = st.slider("🚦 Traffic Intensity (Slows down operations)", 0, 90, 20, format="%d%%")
    
    # Calculate Effective Speed
    effective_speed = base_speed * (1 - (traffic_intensity / 100))
    st.caption(f"ℹ️ Effective Average Speed: **{effective_speed:.1f} km/h**")

    # SAFE ZONES
    city_zones = {
        "Milan (Inland)":   {'center': (45.4642, 9.1900),  'bounds': [45.40, 45.55, 9.10, 9.30]},
        "Naples (Coastal)": {'center': (40.8518, 14.2681), 'bounds': [40.86, 40.95, 14.20, 14.35]},
        "Rome (Central)":   {'center': (41.9028, 12.4964), 'bounds': [41.80, 42.00, 12.40, 12.60]}
    }
    selected_zone = city_zones[depot_city]
    depot_lat, depot_lon = selected_zone['center']

    if 'vrp_data_v7' not in st.session_state:
        st.session_state.vrp_data_v7 = None

    # --- BUTTON: GENERATE & SOLVE ---
    if st.button("🚀 Generate Scenario & Optimize"):
        
        # 1. GENERATE POINTS
        locations = [{'id': 0, 'lat': depot_lat, 'lon': depot_lon, 'name': 'Central Depot'}]
        bounds = selected_zone['bounds']
        for i in range(num_locations):
            lat = random.uniform(bounds[0], bounds[1])
            lon = random.uniform(bounds[2], bounds[3])
            locations.append({'id': i+1, 'lat': lat, 'lon': lon, 'name': f'Customer #{i+1}'})
        
        # 2. MATRIX
        dist_matrix = {}
        for i in range(len(locations)):
            dist_matrix[i] = {}
            for j in range(len(locations)):
                dist = haversine(locations[i]['lon'], locations[i]['lat'], 
                                 locations[j]['lon'], locations[j]['lat'])
                dist_matrix[i][j] = int(dist * 1000)

        # 3. OR-TOOLS CONFIG
        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # FORCE LOAD BALANCING
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            300000,  # vehicle maximum travel distance
            True,  # start cumul to zero
            dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100) 

        # 4. SOLVE
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            raw_routes = []
            colors = ['red', 'blue', 'green', 'orange', 'purple']
            
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route_legs = [] 
                
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
                    total_dist = sum([leg['dist_m'] for leg in route_legs])
                    if total_dist > 0:
                        raw_routes.append({
                            "vehicle_id": vehicle_id + 1,
                            "color": colors[vehicle_id % len(colors)],
                            "legs": route_legs
                        })
            
            st.session_state.vrp_data_v7 = {"center": [depot_lat, depot_lon], "raw_routes": raw_routes}
        else:
            st.error("Optimization Failed. Try again.")

    # --- DYNAMIC RENDERER & TABLE GENERATOR ---
    if st.session_state.vrp_data_v7:
        data = st.session_state.vrp_data_v7
        m2 = folium.Map(location=data["center"], zoom_start=11)
        
        total_fleet_km = 0
        total_fleet_hours = 0
        
        # Store detailed itinerary for the table below
        fleet_itinerary = []

        current_time_base = datetime.datetime.now().replace(hour=8, minute=0, second=0)
        
        for route in data["raw_routes"]:
            vehicle_time = current_time_base
            route_coords = [[data["center"][0], data["center"][1]]] 
            route_km = 0
            
            # For the Table
            truck_schedule = []
            
            for leg in route["legs"]:
                # Dynamic Time Calculation
                travel_min = (leg["dist_m"] / 1000) / max(effective_speed, 1) * 60 
                service_min = 15 
                
                vehicle_time += datetime.timedelta(minutes=travel_min + service_min)
                eta_str = vehicle_time.strftime("%H:%M")
                
                route_coords.append(leg["end_coords"])
                route_km += leg["dist_m"] / 1000
                
                # Append to Schedule List
                if "Depot" not in leg["end_name"]:
                    truck_schedule.append({
                        "Stop": leg["end_name"],
                        "ETA": eta_str,
                        "Distance (km)": f"{leg['dist_m']/1000:.1f}"
                    })

                # MAP MARKER
                if "Depot" not in leg["end_name"]:
                    popup_html = f"""
                    <div style='font-family: sans-serif; width: 150px;'>
                        <b>{leg['end_name']}</b><br>
                        🚚 Truck: {route['vehicle_id']}<br>
                        ⏱️ ETA: <b>{eta_str}</b><br>
                        📏 Dist: {leg['dist_m']/1000:.1f} km
                    </div>
                    """
                    folium.CircleMarker(
                        leg["end_coords"],
                        radius=7,
                        color=route["color"],
                        fill=True,
                        fill_opacity=1,
                        popup=folium.Popup(popup_html, max_width=200),
                        tooltip=f"{leg['end_name']} (ETA: {eta_str})"
                    ).add_to(m2)
            
            # Static & Animated Lines
            folium.PolyLine(route_coords, color=route["color"], weight=4, opacity=0.5).add_to(m2)
            plugins.AntPath(route_coords, color=route["color"], weight=4, delay=800, dash_array=[10, 20], pulse_color='white', opacity=1).add_to(m2)
            
            total_fleet_km += route_km
            hours = (vehicle_time - current_time_base).total_seconds() / 3600
            total_fleet_hours += hours
            
            # Save data for the table display
            fleet_itinerary.append({
                "id": route["vehicle_id"],
                "color": route["color"],
                "total_km": route_km,
                "total_time": hours,
                "stops": truck_schedule
            })

        # Depot Marker
        folium.Marker(data["center"], popup="DEPOT (Start 08:00)", icon=folium.Icon(color='black', icon='home')).add_to(m2)

        st_folium(m2, width=1000, height=600)

        # --- KPIs SECTION ---
        st.markdown("### 🚦 Operational Metrics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Effective Speed", f"{effective_speed:.1f} km/h", delta=f"-{traffic_intensity}% Traffic", delta_color="inverse")
        k2.metric("Total Fleet Dist.", f"{total_fleet_km:.1f} km")
        k3.metric("Fleet Working Hours", f"{total_fleet_hours:.1f} hrs")
        # Fuel Cost Calculation: Approx €1.5 per liter, Truck consumes ~30L/100km -> €0.45 per km
        k4.metric("Est. Fuel Cost", f"€ {total_fleet_km * 0.45:.2f}")

        # --- DETAILED ITINERARY TABLES ---
        st.markdown("### 📋 Detailed Driver Itineraries")
        for truck in fleet_itinerary:
            # Create a styled expander
            with st.expander(f"🚛 Truck {truck['id']} | Distance: {truck['total_km']:.1f} km | Time: {truck['total_time']:.1f} hrs", expanded=False):
                if truck["stops"]:
                    st.dataframe(pd.DataFrame(truck["stops"]), use_container_width=True)
                else:
                    st.warning("No stops assigned to this vehicle.")