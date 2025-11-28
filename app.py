import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TaxiFare Predictor", page_icon="🚕", layout="wide")

'''
# 🚕 TaxiFare Predictor
'''

st.markdown('''
**How to use this app:**
1. Enter a **pickup address** and click "Find Pickup" OR click on the map
2. Enter a **dropoff address** and click "Find Dropoff" OR click on the map
3. Use the slider to set the passenger count and pick date/time
4. Click **Get Fare Prediction** to see the estimated fare!
''')

# ─────────────────────────────────────────────────────────────────────────────
# API endpoint
# ─────────────────────────────────────────────────────────────────────────────
url = 'https://taxifare-812256971571.europe-west1.run.app/'

# ─────────────────────────────────────────────────────────────────────────────
# Geocoding API setup (geocode.maps.co)
# ─────────────────────────────────────────────────────────────────────────────
# Get API key from Streamlit secrets or environment variable
try:
    GEOCODING_API_KEY = st.secrets.get("GEOCODING_API_KEY", "")
except Exception:
    GEOCODING_API_KEY = ""

GEOCODING_BASE_URL = "https://geocode.maps.co"

def geocode_address(address: str):
    """Convert address to lat/lon coordinates using geocode.maps.co API."""
    if not address or len(address.strip()) < 2:
        return None
    
    if not GEOCODING_API_KEY:
        st.error("⚠️ Geocoding API key not configured. Please add GEOCODING_API_KEY to Streamlit secrets.")
        return None
    
    try:
        # Try with NYC context for better results
        query = f"{address}, New York, NY, USA"
        
        params = {
            "q": query,
            "api_key": GEOCODING_API_KEY,
            "format": "json"
        }
        
        response = requests.get(
            f"{GEOCODING_BASE_URL}/search",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            # Get the first result
            result = data[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            
            # Verify it's in NYC area (roughly)
            if 40.5 <= lat <= 41.0 and -74.3 <= lon <= -73.7:
                return {
                    'lat': lat,
                    'lon': lon,
                    'address': result.get('display_name', query)
                }
        
        return None
        
    except requests.exceptions.Timeout:
        st.warning("⏱️ Geocoding timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🌐 Cannot connect to geocoding service. Please try again later.")
        return None
    except Exception as e:
        st.warning(f"⚠️ Geocoding error: {str(e)}")
        return None

def get_address_suggestions(query: str):
    """Get autocomplete suggestions for NYC addresses using geocode.maps.co API."""
    if not query or len(query) < 3:
        return []
    
    if not GEOCODING_API_KEY:
        return []
    
    try:
        # Search with NYC context
        search_query = f"{query}, New York City"
        
        params = {
            "q": search_query,
            "api_key": GEOCODING_API_KEY,
            "format": "json"
        }
        
        response = requests.get(
            f"{GEOCODING_BASE_URL}/search",
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        suggestions = []
        if data:
            for result in data[:5]:  # Limit to 5 suggestions
                lat = float(result['lat'])
                lon = float(result['lon'])
                
                # Verify it's in NYC area
                if 40.5 <= lat <= 41.0 and -74.3 <= lon <= -73.7:
                    suggestions.append({
                        'display_name': result.get('display_name', ''),
                        'lat': lat,
                        'lon': lon
                    })
        
        return suggestions[:5]
        
    except Exception:
        # Silent fail for autocomplete
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Session state for markers
# ─────────────────────────────────────────────────────────────────────────────
if 'pickup_lat' not in st.session_state:
    st.session_state.pickup_lat = 40.783282
if 'pickup_lon' not in st.session_state:
    st.session_state.pickup_lon = -73.950655
if 'dropoff_lat' not in st.session_state:
    st.session_state.dropoff_lat = 40.769802
if 'dropoff_lon' not in st.session_state:
    st.session_state.dropoff_lon = -73.984365
if 'pickup_address_text' not in st.session_state:
    st.session_state.pickup_address_text = ''
if 'dropoff_address_text' not in st.session_state:
    st.session_state.dropoff_address_text = ''

# ─────────────────────────────────────────────────────────────────────────────
# Layout: Controls on left, Map on right
# ─────────────────────────────────────────────────────────────────────────────
col_controls, col_map = st.columns([1, 2])

with col_controls:
    st.markdown("### 📍 Set Locations")
    
    # ─── Pickup Address ───
    st.markdown("#### 🟢 Pickup")
    pickup_address = st.text_input(
        "Pickup Address",
        value=st.session_state.pickup_address_text,
        placeholder="e.g. Times Square, Central Park...",
        key="pickup_address"
    )
    # Update session state
    st.session_state.pickup_address_text = pickup_address
    
    # Get and display suggestions as user types
    if pickup_address and len(pickup_address) > 2:
        suggestions = get_address_suggestions(pickup_address)
        if suggestions:
            st.markdown("**Suggestions:**")
            for i, sugg in enumerate(suggestions[:5], 1):
                if st.button(f"📍 {sugg['display_name']}", key=f"pickup_sugg_{i}"):
                    st.session_state.pickup_lat = sugg['lat']
                    st.session_state.pickup_lon = sugg['lon']
                    st.session_state.pickup_address_text = sugg['display_name']
                    st.rerun()
    
    if st.button("🔍 Search Pickup", key="geocode_pickup"):
        coords = geocode_address(pickup_address)
        if coords:
            st.session_state.pickup_lat = coords['lat']
            st.session_state.pickup_lon = coords['lon']
            st.success(f"✅ Found: {coords['lat']:.5f}, {coords['lon']:.5f}")
            st.rerun()
        else:
            st.error("❌ Address not found. Try a different query.")
    
    col_plat, col_plon = st.columns(2)
    with col_plat:
        new_pickup_lat = st.number_input(
            "Lat", value=st.session_state.pickup_lat,
            format="%.6f", label_visibility="collapsed",
            min_value=40.5, max_value=41.0, step=0.001
        )
    with col_plon:
        new_pickup_lon = st.number_input(
            "Lon", value=st.session_state.pickup_lon,
            format="%.6f", label_visibility="collapsed",
            min_value=-74.3, max_value=-73.7, step=0.001
        )
    
    # Update session state if values changed
    if new_pickup_lat != st.session_state.pickup_lat or new_pickup_lon != st.session_state.pickup_lon:
        st.session_state.pickup_lat = new_pickup_lat
        st.session_state.pickup_lon = new_pickup_lon
    
    st.markdown("---")
    
    # ─── Dropoff Address ───
    st.markdown("#### 🔴 Dropoff")
    dropoff_address = st.text_input(
        "Dropoff Address",
        value=st.session_state.dropoff_address_text,
        placeholder="e.g. JFK Airport, Brooklyn Bridge...",
        key="dropoff_address"
    )
    # Update session state
    st.session_state.dropoff_address_text = dropoff_address
    
    # Get and display suggestions as user types
    if dropoff_address and len(dropoff_address) > 2:
        suggestions = get_address_suggestions(dropoff_address)
        if suggestions:
            st.markdown("**Suggestions:**")
            for i, sugg in enumerate(suggestions[:5], 1):
                if st.button(f"📍 {sugg['display_name']}", key=f"dropoff_sugg_{i}"):
                    st.session_state.dropoff_lat = sugg['lat']
                    st.session_state.dropoff_lon = sugg['lon']
                    st.session_state.dropoff_address_text = sugg['display_name']
                    st.rerun()
    
    if st.button("🔍 Search Dropoff", key="geocode_dropoff"):
        coords = geocode_address(dropoff_address)
        if coords:
            st.session_state.dropoff_lat = coords['lat']
            st.session_state.dropoff_lon = coords['lon']
            st.success(f"✅ Found: {coords['lat']:.5f}, {coords['lon']:.5f}")
            st.rerun()
        else:
            st.error("❌ Address not found. Try a different query.")
    
    col_dlat, col_dlon = st.columns(2)
    with col_dlat:
        new_dropoff_lat = st.number_input(
            "Lat", value=st.session_state.dropoff_lat,
            format="%.6f", label_visibility="collapsed",
            min_value=40.5, max_value=41.0, step=0.001
        )
    with col_dlon:
        new_dropoff_lon = st.number_input(
            "Lon", value=st.session_state.dropoff_lon,
            format="%.6f", label_visibility="collapsed",
            min_value=-74.3, max_value=-73.7, step=0.001
        )
    
    # Update session state if values changed
    if new_dropoff_lat != st.session_state.dropoff_lat or new_dropoff_lon != st.session_state.dropoff_lon:
        st.session_state.dropoff_lat = new_dropoff_lat
        st.session_state.dropoff_lon = new_dropoff_lon
    
    st.markdown("---")
    
    # ─── Passengers & DateTime ───
    st.markdown("#### 👥 Passengers")
    passenger_count = st.slider("Number of passengers", 1, 8, 2)
    
    st.markdown("#### 📅 Pickup Date & Time")
    col_date, col_time = st.columns(2)
    with col_date:
        pickup_date = st.date_input("Date", value=datetime(2013, 7, 6))
    with col_time:
        pickup_time = st.time_input("Time", value=datetime(2013, 7, 6, 17, 18).time())
    pickup_datetime = f"{pickup_date} {pickup_time}"
    
    st.markdown("---")
    
    # ─── Submit Button ───
    if st.button("🚕 Get Fare Prediction", type="primary", use_container_width=True):
        with st.spinner("🚕 Calculating your fare..."):
            params = {
                "pickup_datetime": pickup_datetime,
                "pickup_longitude": st.session_state.pickup_lon,
                "pickup_latitude": st.session_state.pickup_lat,
                "dropoff_longitude": st.session_state.dropoff_lon,
                "dropoff_latitude": st.session_state.dropoff_lat,
                "passenger_count": passenger_count
            }
            
            try:
                response = requests.get(f"{url}/predict", params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                fare = data.get('fare', data.get('fare_amount', None))
                
                if fare is not None:
                    st.success(f"### 💵 Estimated Fare: ${round(fare, 2)}")
                    # st.balloons()
                else:
                    st.error(f"Unexpected response: {data}")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ API request failed: {e}")

with col_map:
    st.markdown("### 🗺️ NYC Map")
    
    # Calculate map center
    center_lat = (st.session_state.pickup_lat + st.session_state.dropoff_lat) / 2
    center_lon = (st.session_state.pickup_lon + st.session_state.dropoff_lon) / 2
    
    # Create folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # Add pickup marker (green)
    folium.Marker(
        location=[st.session_state.pickup_lat, st.session_state.pickup_lon],
        popup="🟢 Pickup",
        tooltip="Pickup location",
        icon=folium.Icon(color='green', icon='play', prefix='fa'),
    ).add_to(m)
    
    # Add dropoff marker (red)
    folium.Marker(
        location=[st.session_state.dropoff_lat, st.session_state.dropoff_lon],
        popup="🔴 Dropoff",
        tooltip="Dropoff location",
        icon=folium.Icon(color='red', icon='stop', prefix='fa'),
    ).add_to(m)
    
    # Render map with dynamic key to force refresh when coordinates change
    map_key = f"map_{st.session_state.pickup_lat:.5f}_{st.session_state.pickup_lon:.5f}_{st.session_state.dropoff_lat:.5f}_{st.session_state.dropoff_lon:.5f}"
    st_folium(
        m,
        width=700,
        height=500,
        key=map_key
    )
    
    # Show current coordinates
    st.info(f"""
    **📍 Current Coordinates:**
    - 🟢 **Pickup:** {st.session_state.pickup_lat:.5f}, {st.session_state.pickup_lon:.5f}
    - 🔴 **Dropoff:** {st.session_state.dropoff_lat:.5f}, {st.session_state.dropoff_lon:.5f}
    """)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    🚕 TaxiFare Predictor — Powered by ML | 
    <a href="https://taxifare-812256971571.europe-west1.run.app/docs" target="_blank">API Docs</a>
</div>
""", unsafe_allow_html=True)
