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
    col2.metric("Critical Alerts", len(df[df['Status']=='Critical']))
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
    num_vehicles = col1.slider("Number of Vehicles", 2, 5, 3) # Min 2 vehicles
    num_locations = col2.slider("Number of Deliveries", 5, 50, 15)
    depot_city = col3.selectbox("Depot Location", ["Rome", "Milan", "Naples", "Turin"])

    coords = {
        "Rome": (41.9028, 12.4964), 
        "Milan": (45.4642, 9.1900), 
        "Naples": (40.8518, 14.2681),
        "Turin": (45.0703, 7.6869)
    }
    depot_lat, depot_lon = coords[depot_city]

    # Initialize Session State for Results (This keeps map stable after refresh)
    if 'vrp_map_data' not in st.session_state:
        st.session_state.vrp_map_data = None

    # TRIGGER BUTTON
    if st.button("🚀 Generate New Scenario & Solve"):
        
        # 1. Generate FRESH Random Data (No fixed seed)
        locations = [{'id': 0, 'lat': depot_lat, 'lon': depot_lon, 'name': 'Depot'}]
        for i in range(num_locations):
            # Reduced radius to ~15km (City Scale) to avoid sea
            lat = depot_lat + random.uniform(-0.15, 0.15) 
            lon = depot_lon + random.uniform(-0.15, 0.15)
            locations.append({'id': i+1, 'lat': lat, 'lon': lon, 'name': f'Customer {i+1}'})
        
        # 2. Create Distance Matrix
        dist_matrix = {}
        for i in range(len(locations)):
            dist_matrix[i] = {}
            for j in range(len(locations)):
                dist = haversine(locations[i]['lon'], locations[i]['lat'], 
                                 locations[j]['lon'], locations[j]['lat'])
                dist_matrix[i][j] = int(dist * 1000) # Meters

        # 3. OR-Tools Setup
        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # --- FORCE LOAD BALANCING (Add Distance Dimension) ---
        # This forces the solver to use multiple vehicles by limiting max distance per truck
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            200000,  # max distance per vehicle (200km) - Forces split
            True,  # start cumul to zero
            dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100) # Try to balance distances

        # 4. Solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            # Prepare data for plotting (Store in Session State)
            routes_data = []
            colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231'] # Distinct colors
            
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route_coords = []
                route_names = []
                total_dist = 0
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    lat, lon = locations[node_index]['lat'], locations[node_index]['lon']
                    route_coords.append((lat, lon))
                    route_names.append(locations[node_index]['name'])
                    
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    # Calculate segment distance
                    if not routing.IsEnd(index): 
                         total_dist += dist_matrix[node_index][manager.IndexToNode(index)]

                # Add return to depot
                node_index = manager.IndexToNode(index)
                route_coords.append((locations[node_index]['lat'], locations[node_index]['lon']))
                route_names.append("Back to Depot")
                
                if len(route_coords) > 2: # Only save if vehicle actually moved
                    routes_data.append({
                        "vehicle_id": vehicle_id + 1,
                        "color": colors[vehicle_id % len(colors)],
                        "coords": route_coords,
                        "names": route_names,
                        "distance_km": total_dist / 1000
                    })

            st.session_state.vrp_map_data = {"center": [depot_lat, depot_lon], "routes": routes_data, "locations": locations}
        else:
            st.error("Could not find a solution. Try reducing constraints.")

    # RENDER MAP (From Session State)
    if st.session_state.vrp_map_data:
        data = st.session_state.vrp_map_data
        m2 = folium.Map(location=data["center"], zoom_start=11) # Zoom closer
        
        # Plot Routes
        for route in data["routes"]:
            # Draw Line
            folium.PolyLine(
                route["coords"], 
                color=route["color"], 
                weight=5, 
                opacity=0.7, 
                tooltip=f"Vehicle {route['vehicle_id']} ({route['distance_km']:.1f} km)"
            ).add_to(m2)
            
            # Draw Markers (Only Customers)
            for i, (lat, lon) in enumerate(route["coords"][:-1]): # Skip last duplicate depot
                name = route["names"][i]
                if "Depot" in name:
                    folium.Marker([lat, lon], popup="DEPOT", icon=folium.Icon(color='black', icon='home')).add_to(m2)
                else:
                    folium.CircleMarker(
                        [lat, lon], 
                        radius=6, 
                        color=route["color"], 
                        fill=True, 
                        fill_opacity=1,
                        tooltip=f"{name} (Truck {route['vehicle_id']})" # Proper Tooltip
                    ).add_to(m2)

        st_folium(m2, width=800, height=500, key="vrp_map_render") # Add key to prevent rerender loop
        
        # Show Stats
        st.markdown("### 📊 Route Analytics")
        cols = st.columns(len(data["routes"]))
        for i, route in enumerate(data["routes"]):
            cols[i].metric(f"Vehicle {route['vehicle_id']}", f"{route['distance_km']:.1f} km", delta_color="off")