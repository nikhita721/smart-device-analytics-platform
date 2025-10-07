"""
Live Streaming IoT Analytics Dashboard
Real-time dashboard with live data updates and streaming analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import json
import threading
import queue
from collections import deque
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.simple_live_consumer import initialize_live_streaming, get_live_data, get_live_metrics

class LiveIoTDashboard:
    """
    Live streaming IoT analytics dashboard
    """
    
    def __init__(self):
        self.setup_page_config()
        self.initialize_session_state()
        self.setup_live_streaming()
    
    def setup_page_config(self):
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title="Live IoT Analytics Dashboard",
            page_icon="📡",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'live_data' not in st.session_state:
            st.session_state.live_data = deque(maxlen=1000)
        if 'live_metrics' not in st.session_state:
            st.session_state.live_metrics = {}
        if 'anomaly_alerts' not in st.session_state:
            st.session_state.anomaly_alerts = deque(maxlen=100)
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 2
        if 'streaming_stats' not in st.session_state:
            st.session_state.streaming_stats = {
                'total_messages': 0,
                'messages_per_second': 0,
                'last_update': None,
                'connection_status': 'Disconnected'
            }
    
    def setup_live_streaming(self):
        """Initialize live streaming components"""
        try:
            self.consumer, self.processor = initialize_live_streaming()
            st.session_state.streaming_stats['connection_status'] = 'Connected' if self.consumer else 'Sample Data'
        except Exception as e:
            st.error(f"Failed to initialize live streaming: {e}")
            self.consumer = None
            self.processor = None
    
    def update_live_data(self):
        """Update live data from streaming source"""
        try:
            # Get new data
            new_data = get_live_data()
            if new_data:
                st.session_state.live_data.append(new_data)
                
                # Update streaming statistics
                st.session_state.streaming_stats['total_messages'] += 1
                st.session_state.streaming_stats['last_update'] = datetime.now()
                
                # Calculate messages per second
                if len(st.session_state.live_data) > 1:
                    time_diff = (datetime.now() - st.session_state.live_data[0].get('timestamp', datetime.now())).total_seconds()
                    if time_diff > 0:
                        st.session_state.streaming_stats['messages_per_second'] = len(st.session_state.live_data) / time_diff
                
                # Check for anomalies
                if new_data.get('is_anomaly', False):
                    alert = {
                        'device_id': new_data['device_id'],
                        'timestamp': new_data['timestamp'],
                        'type': 'sensor_anomaly',
                        'severity': 'high' if new_data.get('temperature', 0) > 30 else 'medium',
                        'details': f"Temperature: {new_data.get('temperature', 0)}°C, Energy: {new_data.get('energy_consumption', 0)}W"
                    }
                    st.session_state.anomaly_alerts.append(alert)
            
            # Update live metrics
            st.session_state.live_metrics = get_live_metrics()
            
        except Exception as e:
            st.error(f"Error updating live data: {e}")
    
    def render_header(self):
        """Render dashboard header with live status"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_color = "🟢" if st.session_state.streaming_stats['connection_status'] == 'Connected' else "🟡"
            st.metric(
                "Connection Status",
                f"{status_color} {st.session_state.streaming_stats['connection_status']}"
            )
        
        with col2:
            st.metric(
                "Messages/Second",
                f"{st.session_state.streaming_stats['messages_per_second']:.1f}"
            )
        
        with col3:
            st.metric(
                "Total Messages",
                f"{st.session_state.streaming_stats['total_messages']:,}"
            )
        
        with col4:
            last_update = st.session_state.streaming_stats.get('last_update')
            if last_update:
                time_diff = (datetime.now() - last_update).total_seconds()
                st.metric(
                    "Last Update",
                    f"{time_diff:.1f}s ago"
                )
            else:
                st.metric("Last Update", "Never")
    
    def render_live_metrics(self):
        """Render live metrics overview"""
        st.subheader("📊 Live Metrics Overview")
        
        if not st.session_state.live_metrics:
            st.info("No live data available yet. Waiting for data stream...")
            return
        
        metrics = st.session_state.live_metrics
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Active Devices",
                f"{metrics.get('total_devices', 0)}"
            )
        
        with col2:
            st.metric(
                "Avg Temperature",
                f"{metrics.get('avg_temperature', 0):.1f}°C"
            )
        
        with col3:
            st.metric(
                "Avg Energy",
                f"{metrics.get('avg_energy', 0):.2f}W"
            )
        
        with col4:
            anomaly_rate = metrics.get('anomaly_rate', 0) * 100
            st.metric(
                "Anomaly Rate",
                f"{anomaly_rate:.1f}%"
            )
    
    def render_device_distribution(self):
        """Render live device type distribution"""
        st.subheader("📱 Device Distribution")
        
        if not st.session_state.live_data:
            st.info("No device data available yet.")
            return
        
        # Get device type counts
        device_types = {}
        for data in st.session_state.live_data:
            device_type = data.get('device_type', 'unknown')
            device_types[device_type] = device_types.get(device_type, 0) + 1
        
        if device_types:
            # Create pie chart
            fig = px.pie(
                values=list(device_types.values()),
                names=list(device_types.keys()),
                title="Live Device Type Distribution"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No device data available for distribution chart.")
    
    def render_temperature_trends(self):
        """Render live temperature trends"""
        st.subheader("🌡️ Live Temperature Trends")
        
        if len(st.session_state.live_data) < 2:
            st.info("Insufficient data for temperature trends. Need at least 2 data points.")
            return
        
        # Prepare data for plotting
        df = pd.DataFrame(list(st.session_state.live_data))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create temperature trend chart
        fig = go.Figure()
        
        # Add temperature line
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['temperature'],
            mode='lines+markers',
            name='Temperature',
            line=dict(color='red', width=2),
            marker=dict(size=4)
        ))
        
        # Add anomaly markers
        anomalies = df[df.get('is_anomaly', False)]
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['timestamp'],
                y=anomalies['temperature'],
                mode='markers',
                name='Anomalies',
                marker=dict(
                    color='red',
                    size=10,
                    symbol='x'
                )
            ))
        
        fig.update_layout(
            title="Live Temperature Monitoring",
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    def render_energy_consumption(self):
        """Render live energy consumption analytics"""
        st.subheader("⚡ Live Energy Consumption")
        
        if len(st.session_state.live_data) < 2:
            st.info("Insufficient data for energy analysis.")
            return
        
        df = pd.DataFrame(list(st.session_state.live_data))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create energy consumption chart
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Energy Consumption Over Time', 'Energy by Device Type'),
            vertical_spacing=0.1
        )
        
        # Energy over time
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['energy_consumption'],
            mode='lines+markers',
            name='Energy Consumption',
            line=dict(color='blue', width=2)
        ), row=1, col=1)
        
        # Energy by device type
        energy_by_type = df.groupby('device_type')['energy_consumption'].mean().reset_index()
        fig.add_trace(go.Bar(
            x=energy_by_type['device_type'],
            y=energy_by_type['energy_consumption'],
            name='Avg Energy by Type',
            marker_color='lightblue'
        ), row=2, col=1)
        
        fig.update_layout(
            title="Live Energy Consumption Analytics",
            height=600,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    def render_anomaly_alerts(self):
        """Render live anomaly alerts"""
        st.subheader("🚨 Live Anomaly Alerts")
        
        if not st.session_state.anomaly_alerts:
            st.success("No anomalies detected in the current data stream.")
            return
        
        # Show recent alerts
        recent_alerts = list(st.session_state.anomaly_alerts)[-10:]
        
        for alert in reversed(recent_alerts):
            severity_color = "🔴" if alert.get('severity') == 'high' else "🟡"
            
            with st.expander(f"{severity_color} Alert - {alert['device_id']} at {alert['timestamp']}"):
                st.write(f"**Type:** {alert.get('type', 'Unknown')}")
                st.write(f"**Severity:** {alert.get('severity', 'Unknown')}")
                st.write(f"**Details:** {alert.get('details', 'No details available')}")
    
    def render_geographic_view(self):
        """Render live geographic device distribution"""
        st.subheader("🗺️ Live Device Locations")
        
        if len(st.session_state.live_data) < 1:
            st.info("No location data available yet.")
            return
        
        df = pd.DataFrame(list(st.session_state.live_data))
        
        # Create map
        fig = px.scatter_map(
            df,
            lat='latitude',
            lon='longitude',
            color='device_type',
            size='energy_consumption',
            hover_data=['device_id', 'temperature', 'battery_level'],
            title="Live Device Locations",
            mapbox_style="open-street-map"
        )
        
        fig.update_layout(
            mapbox=dict(
                center=dict(lat=32.7767, lon=-96.7970),  # Dallas center
                zoom=10
            ),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    def render_sidebar_controls(self):
        """Render sidebar controls"""
        st.sidebar.header("🎛️ Live Dashboard Controls")
        
        # Auto-refresh toggle
        st.session_state.auto_refresh = st.sidebar.checkbox(
            "Auto Refresh",
            value=st.session_state.auto_refresh,
            help="Automatically refresh dashboard with new data"
        )
        
        # Refresh interval
        st.session_state.refresh_interval = st.sidebar.slider(
            "Refresh Interval (seconds)",
            min_value=1,
            max_value=10,
            value=st.session_state.refresh_interval,
            help="How often to refresh the dashboard"
        )
        
        # Manual refresh button
        if st.sidebar.button("🔄 Manual Refresh"):
            st.rerun()
        
        # Clear data button
        if st.sidebar.button("🗑️ Clear Data"):
            st.session_state.live_data.clear()
            st.session_state.anomaly_alerts.clear()
            st.session_state.streaming_stats = {
                'total_messages': 0,
                'messages_per_second': 0,
                'last_update': None,
                'connection_status': 'Disconnected'
            }
            st.rerun()
        
        # Export data button
        if st.sidebar.button("📥 Export Data"):
            if st.session_state.live_data:
                df = pd.DataFrame(list(st.session_state.live_data))
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"iot_live_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.sidebar.warning("No data to export")
    
    def run_dashboard(self):
        """Run the live streaming dashboard"""
        # Render sidebar controls
        self.render_sidebar_controls()
        
        # Update live data
        self.update_live_data()
        
        # Render main dashboard
        st.title("📡 Live IoT Analytics Dashboard")
        st.markdown("Real-time streaming analytics for IoT devices")
        
        # Header with live status
        self.render_header()
        
        st.divider()
        
        # Live metrics overview
        self.render_live_metrics()
        
        st.divider()
        
        # Main content in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", "🌡️ Temperature", "⚡ Energy", "🚨 Alerts", "🗺️ Locations"
        ])
        
        with tab1:
            self.render_device_distribution()
        
        with tab2:
            self.render_temperature_trends()
        
        with tab3:
            self.render_energy_consumption()
        
        with tab4:
            self.render_anomaly_alerts()
        
        with tab5:
            self.render_geographic_view()
        
        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(st.session_state.refresh_interval)
            st.rerun()

def main():
    """Main function to run the live dashboard"""
    dashboard = LiveIoTDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
