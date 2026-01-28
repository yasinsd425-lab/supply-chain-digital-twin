import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import random
from math import radians, cos, sin, asin, sqrt
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# --- PAGE CONFIG ---
st.set_page_config(page_title="Supply Chain Control Tower V2.0", page_icon="🌍", layout="wide")

st.title("🌍 Supply Chain Digital Twin & AI Optimizer")
st.markdown("### Industrial Engineering Portfolio | Unicas")

# --- SIDEBAR ---
st.sidebar.header("Control Panel")
mode = st.sidebar.radio("Select Mode:", ["📊 Network Monitoring (Digital Twin)", "🚚 AI Route Optimizer (VRP)"])

# --- HELPER: HAVERSINE DISTANCE (For Calc) ---
def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance in km between two points"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers
    return c * r

# --- MODE 1: MONITORING (OLD FEATURE) ---
if mode == "📊 Network Monitoring (Digital Twin)":
    st.info("Visualizing static nodes and inventory levels.")
    
    # Mock Data Generation
    data = {
        'Location': ['Factory Rome', 'DC Milan', 'Warehouse Naples', 'Supplier Turin', 'Port Genoa'],
        'Type': ['Plant', 'DC', 'Warehouse', 'Supplier', 'Port'],
        'Lat': [41.9028, 45.4642, 40.8518, 45.0703, 44.4056],
        'Lon': [12.4964, 9.1900, 14.2681, 7.6869, 8.9463],
        'Inventory': [1200, 8500, 3400, 0, 5600],
        'Status': ['Normal', 'Critical', 'Normal', 'Normal', 'Risk']
    }
    df = pd.DataFrame(data)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Nodes", len(df))
    col2.metric("Critical Alerts", df[df['Status']=='Critical'].count())
    col3.metric("Total Inventory", f"{df['Inventory'].sum():,}")

    # Map
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

    st_folium(m, width=800, height=500)

# --- MODE 2: AI ROUTE OPTIMIZER (NEW FEATURE!) ---
elif mode == "🚚 AI Route Optimizer (VRP)":
    st.success("🤖 Optimization Engine: Google OR-Tools")
    st.markdown("Solve the **Vehicle Routing Problem (VRP)**: Distribute deliveries among trucks to minimize total distance.")

    # Controls
    col1, col2, col3 = st.columns(3)
    num_vehicles = col1.slider("Number of Vehicles", 1, 5, 3)
    num_locations = col2.slider("Number of Deliveries", 5, 20, 10)
    depot_city = col3.selectbox("Depot Location", ["Rome", "Milan", "Naples"])

    coords = {"Rome": (41.9028, 12.4964), "Milan": (45.4642, 9.1900), "Naples": (40.8518, 14.2681)}
    depot_lat, depot_lon = coords[depot_city]

    # Generate Random Deliveries around Depot
    if st.button("🚀 Run AI Optimization"):
        locations = [{'id': 0, 'lat': depot_lat, 'lon': depot_lon, 'name': 'Depot'}]
        for i in range(num_locations):
            # Random points within ~100km
            lat = depot_lat + random.uniform(-1, 1)
            lon = depot_lon + random.uniform(-1, 1)
            locations.append({'id': i+1, 'lat': lat, 'lon': lon, 'name': f'Customer {i+1}'})
        
        # Create Distance Matrix
        dist_matrix = {}
        for i in range(len(locations)):
            dist_matrix[i] = {}
            for j in range(len(locations)):
                dist = haversine(locations[i]['lon'], locations[i]['lat'], 
                                 locations[j]['lon'], locations[j]['lat'])
                dist_matrix[i][j] = int(dist * 1000) # Convert to meters for OR-Tools

        # OR-Tools Setup
        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            st.markdown("### 🗺️ Optimized Routes")
            m2 = folium.Map(location=[depot_lat, depot_lon], zoom_start=8)
            
            colors = ['blue', 'green', 'orange', 'purple', 'red']
            
            # Draw Routes
            total_dist_all = 0
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route_coords = []
                route_load = 0
                route_text = f"<b>Vehicle {vehicle_id+1}:</b> Depot"
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    lat, lon = locations[node_index]['lat'], locations[node_index]['lon']
                    route_coords.append((lat, lon))
                    
                    if node_index != 0: route_text += f" ➝ Customer {node_index}"
                    
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    
                    # Add simple marker
                    if node_index == 0:
                        folium.Marker([lat, lon], popup="DEPOT", icon=folium.Icon(color='black', icon='home')).add_to(m2)
                    else:
                        folium.CircleMarker([lat, lon], radius=5, color=colors[vehicle_id], fill=True).add_to(m2)

                # Close the loop
                node_index = manager.IndexToNode(index)
                route_coords.append((locations[node_index]['lat'], locations[node_index]['lon']))
                route_text += " ➝ Depot"
                
                # Plot Path
                folium.PolyLine(route_coords, color=colors[vehicle_id], weight=3, opacity=0.8, tooltip=f"Vehicle {vehicle_id+1}").add_to(m2)
                st.caption(route_text)

            st_folium(m2, width=800, height=500)
        else:
            st.error("No solution found!")