"""
Simple Live IoT Analytics Dashboard
Real-time streaming dashboard with proper error handling
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.simple_live_consumer import initialize_live_streaming, get_live_data, get_live_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(
    page_title="Live IoT Device Analytics Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

class SimpleLiveDashboard:
    def __init__(self):
        self.consumer = None
        self.data_buffer = []
        self.last_refresh = datetime.now()
        
    def initialize_consumer(self):
        """Initialize the live data consumer"""
        try:
            self.consumer = initialize_live_streaming()
            logger.info("Live streaming consumer initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            return False
    
    def get_live_data(self):
        """Get live data from consumer"""
        try:
            if self.consumer:
                data = get_live_data()
                if data:
                    self.data_buffer.extend(data)
                    # Keep only last 1000 records for performance
                    if len(self.data_buffer) > 1000:
                        self.data_buffer = self.data_buffer[-1000:]
                return data
        except Exception as e:
            logger.error(f"Error getting live data: {e}")
        return []
    
    def render_header(self):
        """Render dashboard header"""
        st.title("⚡ Live IoT Device Analytics Dashboard")
        st.markdown("Real-time monitoring of IoT device performance and anomalies")
        
        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if self.consumer:
                st.metric("Status", "🟢 Connected", delta="Live")
            else:
                st.metric("Status", "🟡 Sample Data", delta="Demo")
        
        with col2:
            st.metric("Total Devices", len(set(d.get('device_id', 'unknown') for d in self.data_buffer)))
        
        with col3:
            st.metric("Data Points", len(self.data_buffer))
        
        with col4:
            st.metric("Last Update", self.last_refresh.strftime("%H:%M:%S"))
    
    def render_device_distribution(self):
        """Render device type distribution"""
        if not self.data_buffer:
            st.info("No data available yet. Waiting for live data...")
            return
        
        try:
            # Extract device types
            device_types = []
            for data in self.data_buffer:
                if isinstance(data, dict) and 'device_type' in data:
                    device_types.append(data['device_type'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'device_type' in item:
                            device_types.append(item['device_type'])
            
            if not device_types:
                st.info("No device type data available")
                return
            
            # Create distribution chart
            df_types = pd.DataFrame({'Device Type': device_types})
            type_counts = df_types['Device Type'].value_counts()
            
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Device Type Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        except Exception as e:
            logger.error(f"Error rendering device distribution: {e}")
            st.error(f"Error rendering device distribution: {e}")
    
    def render_temperature_trends(self):
        """Render temperature trends"""
        if not self.data_buffer:
            return
        
        try:
            # Extract temperature data
            temp_data = []
            timestamps = []
            
            for data in self.data_buffer[-100:]:  # Last 100 records
                if isinstance(data, dict) and 'temperature' in data and 'timestamp' in data:
                    temp_data.append(data['temperature'])
                    timestamps.append(data['timestamp'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'temperature' in item and 'timestamp' in item:
                            temp_data.append(item['temperature'])
                            timestamps.append(item['timestamp'])
            
            if not temp_data:
                st.info("No temperature data available")
                return
            
            # Create temperature chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=temp_data,
                mode='lines+markers',
                name='Temperature',
                line=dict(color='red', width=2),
                marker=dict(size=4)
            ))
            
            fig.update_layout(
                title="Temperature Trends (Last 100 Readings)",
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        except Exception as e:
            logger.error(f"Error rendering temperature trends: {e}")
            st.error(f"Error rendering temperature trends: {e}")
    
    def render_energy_consumption(self):
        """Render energy consumption chart"""
        if not self.data_buffer:
            return
        
        try:
            # Extract energy data
            energy_data = []
            timestamps = []
            
            for data in self.data_buffer[-100:]:  # Last 100 records
                if isinstance(data, dict) and 'energy_consumption' in data and 'timestamp' in data:
                    energy_data.append(data['energy_consumption'])
                    timestamps.append(data['timestamp'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'energy_consumption' in item and 'timestamp' in item:
                            energy_data.append(item['energy_consumption'])
                            timestamps.append(item['timestamp'])
            
            if not energy_data:
                st.info("No energy consumption data available")
                return
            
            # Create energy chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=energy_data,
                mode='lines+markers',
                name='Energy Consumption',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ))
            
            fig.update_layout(
                title="Energy Consumption Trends (Last 100 Readings)",
                xaxis_title="Time",
                yaxis_title="Energy Consumption (kWh)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        except Exception as e:
            logger.error(f"Error rendering energy consumption: {e}")
            st.error(f"Error rendering energy consumption: {e}")
    
    def render_anomaly_alerts(self):
        """Render anomaly alerts"""
        if not self.data_buffer:
            return
        
        try:
            # Extract anomaly data
            anomalies = []
            for data in self.data_buffer[-50:]:  # Last 50 records
                if isinstance(data, dict) and data.get('anomaly', False):
                    anomalies.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('anomaly', False):
                            anomalies.append(item)
            
            if not anomalies:
                st.info("No anomalies detected in recent data")
                return
            
            # Display anomalies
            st.subheader("🚨 Recent Anomaly Alerts")
            
            for i, anomaly in enumerate(anomalies[-10:]):  # Show last 10 anomalies
                with st.expander(f"Anomaly #{i+1} - {anomaly.get('device_id', 'Unknown')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Device ID:** {anomaly.get('device_id', 'Unknown')}")
                        st.write(f"**Device Type:** {anomaly.get('device_type', 'Unknown')}")
                        st.write(f"**Timestamp:** {anomaly.get('timestamp', 'Unknown')}")
                    
                    with col2:
                        st.write(f"**Temperature:** {anomaly.get('temperature', 'N/A')}°C")
                        st.write(f"**Energy:** {anomaly.get('energy_consumption', 'N/A')} kWh")
                        st.write(f"**Status:** {anomaly.get('status', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error rendering anomaly alerts: {e}")
            st.error(f"Error rendering anomaly alerts: {e}")
    
    def render_controls(self):
        """Render dashboard controls"""
        st.sidebar.header("Dashboard Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
        refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 2)
        
        # Manual refresh button
        if st.sidebar.button("🔄 Manual Refresh"):
            st.rerun()
        
        # Clear data button
        if st.sidebar.button("🗑️ Clear Data"):
            self.data_buffer = []
            st.rerun()
        
        # Data export
        if st.sidebar.button("📊 Export Data"):
            if self.data_buffer:
                df = pd.DataFrame(self.data_buffer)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.sidebar.warning("No data to export")
        
        return auto_refresh, refresh_interval
    
    def run_dashboard(self):
        """Run the main dashboard"""
        # Initialize consumer
        if not self.consumer:
            self.initialize_consumer()
        
        # Render controls
        auto_refresh, refresh_interval = self.render_controls()
        
        # Get live data
        self.get_live_data()
        self.last_refresh = datetime.now()
        
        # Render header
        self.render_header()
        
        st.markdown("---")
        
        # Main content
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Device Distribution")
            self.render_device_distribution()
        
        with col2:
            st.subheader("🌡️ Temperature Trends")
            self.render_temperature_trends()
        
        st.subheader("⚡ Energy Consumption")
        self.render_energy_consumption()
        
        st.subheader("🚨 Anomaly Detection")
        self.render_anomaly_alerts()
        
        # Auto-refresh logic
        if auto_refresh:
            time.sleep(refresh_interval)
            st.rerun()

def main():
    """Main function"""
    try:
        dashboard = SimpleLiveDashboard()
        dashboard.run_dashboard()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        st.error(f"Dashboard error: {e}")
        st.info("Please refresh the page to try again.")

if __name__ == "__main__":
    main()
