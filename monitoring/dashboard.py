"""
Real-time IoT Analytics Dashboard
Interactive dashboard for monitoring device performance, anomalies, and business metrics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTDashboard:
    """
    Comprehensive IoT analytics dashboard
    Provides real-time monitoring and business intelligence
    """
    
    def __init__(self):
        self.setup_page_config()
        self.load_sample_data()
    
    def setup_page_config(self):
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title="IoT Device Analytics Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def load_sample_data(self):
        """Load sample data for demonstration"""
        # Generate sample IoT data
        np.random.seed(42)
        n_devices = 1000
        n_days = 7
        
        # Create time series data
        dates = pd.date_range(start=datetime.now() - timedelta(days=n_days), 
                            end=datetime.now(), freq='H')
        
        data = []
        for device_id in range(1, n_devices + 1):
            device_type = np.random.choice(['thermostat', 'security_camera', 'smart_lock', 'motion_sensor', 'air_quality'])
            
            for date in dates:
                data.append({
                    'device_id': f'device_{device_id:04d}',
                    'device_type': device_type,
                    'timestamp': date,
                    'temperature': np.random.normal(72, 10),
                    'humidity': np.random.normal(50, 15),
                    'battery_level': np.random.uniform(10, 100),
                    'energy_consumption': np.random.exponential(2),
                    'anomaly_detected': np.random.choice([True, False], p=[0.05, 0.95]),
                    'location_lat': np.random.uniform(32.7767, 33.7767),
                    'location_lon': np.random.uniform(-97.7963, -96.7963)
                })
        
        self.df = pd.DataFrame(data)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        # Add derived metrics
        self.df['hour'] = self.df['timestamp'].dt.hour
        self.df['day_of_week'] = self.df['timestamp'].dt.day_name()
        self.df['is_weekend'] = self.df['timestamp'].dt.dayofweek.isin([5, 6])
    
    def render_header(self):
        """Render dashboard header with key metrics"""
        st.title("🏠 IoT Device Analytics Dashboard")
        st.markdown("Real-time monitoring and analytics for smart home devices")
        
        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_devices = self.df['device_id'].nunique()
            st.metric("Total Devices", f"{total_devices:,}")
        
        with col2:
            active_devices = self.df[self.df['timestamp'] >= datetime.now() - timedelta(hours=1)]['device_id'].nunique()
            st.metric("Active Devices", f"{active_devices:,}")
        
        with col3:
            anomaly_rate = self.df['anomaly_detected'].mean() * 100
            st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")
        
        with col4:
            avg_battery = self.df['battery_level'].mean()
            st.metric("Avg Battery Level", f"{avg_battery:.1f}%")
        
        with col5:
            total_energy = self.df['energy_consumption'].sum()
            st.metric("Total Energy (kWh)", f"{total_energy:.1f}")
    
    def render_device_overview(self):
        """Render device type overview"""
        st.subheader("📱 Device Type Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Device type count
            device_counts = self.df['device_type'].value_counts()
            fig_pie = px.pie(
                values=device_counts.values,
                names=device_counts.index,
                title="Device Type Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Device status by type
            device_status = self.df.groupby(['device_type', 'anomaly_detected']).size().unstack(fill_value=0)
            fig_bar = px.bar(
                device_status,
                title="Device Status by Type",
                labels={'value': 'Count', 'index': 'Device Type'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    def render_temporal_analysis(self):
        """Render temporal analysis charts"""
        st.subheader("⏰ Temporal Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Hourly activity pattern
            hourly_activity = self.df.groupby('hour').size()
            fig_line = px.line(
                x=hourly_activity.index,
                y=hourly_activity.values,
                title="Hourly Activity Pattern",
                labels={'x': 'Hour of Day', 'y': 'Number of Readings'}
            )
            st.plotly_chart(fig_line, use_container_width=True)
        
        with col2:
            # Anomaly trends over time
            anomaly_trends = self.df.groupby(self.df['timestamp'].dt.date)['anomaly_detected'].mean()
            fig_trend = px.line(
                x=anomaly_trends.index,
                y=anomaly_trends.values * 100,
                title="Daily Anomaly Rate Trend",
                labels={'x': 'Date', 'y': 'Anomaly Rate (%)'}
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    
    def render_geospatial_analysis(self):
        """Render geospatial analysis"""
        st.subheader("🗺️ Geospatial Analysis")
        
        # Device locations with anomaly status
        fig_map = px.scatter_mapbox(
            self.df,
            lat='location_lat',
            lon='location_lon',
            color='anomaly_detected',
            size='battery_level',
            hover_data=['device_id', 'device_type', 'temperature', 'humidity'],
            title="Device Locations and Status",
            mapbox_style="open-street-map",
            zoom=10
        )
        
        fig_map.update_layout(
            height=500,
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
        
        st.plotly_chart(fig_map, use_container_width=True)
    
    def render_anomaly_analysis(self):
        """Render anomaly detection analysis"""
        st.subheader("🚨 Anomaly Detection Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Anomaly distribution by device type
            anomaly_by_type = self.df.groupby('device_type')['anomaly_detected'].mean() * 100
            fig_anomaly = px.bar(
                x=anomaly_by_type.index,
                y=anomaly_by_type.values,
                title="Anomaly Rate by Device Type",
                labels={'x': 'Device Type', 'y': 'Anomaly Rate (%)'}
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)
        
        with col2:
            # Anomaly correlation with battery level
            fig_corr = px.scatter(
                self.df,
                x='battery_level',
                y='energy_consumption',
                color='anomaly_detected',
                title="Battery Level vs Energy Consumption",
                labels={'battery_level': 'Battery Level (%)', 'energy_consumption': 'Energy Consumption (kWh)'}
            )
            st.plotly_chart(fig_corr, use_container_width=True)
    
    def render_energy_analysis(self):
        """Render energy consumption analysis"""
        st.subheader("⚡ Energy Consumption Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Energy consumption by device type
            energy_by_type = self.df.groupby('device_type')['energy_consumption'].mean()
            fig_energy = px.bar(
                x=energy_by_type.index,
                y=energy_by_type.values,
                title="Average Energy Consumption by Device Type",
                labels={'x': 'Device Type', 'y': 'Energy Consumption (kWh)'}
            )
            st.plotly_chart(fig_energy, use_container_width=True)
        
        with col2:
            # Energy efficiency over time
            daily_energy = self.df.groupby(self.df['timestamp'].dt.date)['energy_consumption'].sum()
            fig_energy_trend = px.line(
                x=daily_energy.index,
                y=daily_energy.values,
                title="Daily Energy Consumption Trend",
                labels={'x': 'Date', 'y': 'Total Energy (kWh)'}
            )
            st.plotly_chart(fig_energy_trend, use_container_width=True)
    
    def render_predictive_insights(self):
        """Render predictive analytics insights"""
        st.subheader("🔮 Predictive Insights")
        
        # Simulate predictive maintenance alerts
        maintenance_alerts = self.df[
            (self.df['battery_level'] < 20) | 
            (self.df['anomaly_detected'] == True)
        ].groupby('device_id').agg({
            'battery_level': 'min',
            'anomaly_detected': 'sum',
            'device_type': 'first'
        }).reset_index()
        
        maintenance_alerts['alert_priority'] = maintenance_alerts.apply(
            lambda row: 'HIGH' if row['battery_level'] < 15 or row['anomaly_detected'] > 3 else 'MEDIUM',
            axis=1
        )
        
        st.write("**Maintenance Alerts:**")
        st.dataframe(
            maintenance_alerts.head(10),
            use_container_width=True
        )
        
        # Energy consumption prediction
        col1, col2 = st.columns(2)
        
        with col1:
            # Predicted energy consumption for next 24 hours
            current_energy = self.df['energy_consumption'].mean()
            predicted_energy = current_energy * 1.1  # 10% increase prediction
            
            st.metric(
                "Predicted Energy (24h)",
                f"{predicted_energy:.2f} kWh",
                delta="10%"
            )
        
        with col2:
            # Maintenance cost prediction
            high_priority_alerts = len(maintenance_alerts[maintenance_alerts['alert_priority'] == 'HIGH'])
            estimated_cost = high_priority_alerts * 150  # $150 per device
            
            st.metric(
                "Estimated Maintenance Cost",
                f"${estimated_cost:,}",
                delta=f"{high_priority_alerts} devices"
            )
    
    def render_data_quality_metrics(self):
        """Render data quality and pipeline metrics"""
        st.subheader("📊 Data Quality Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_records = len(self.df)
            st.metric("Total Records", f"{total_records:,}")
        
        with col2:
            null_percentage = (self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
            st.metric("Null Percentage", f"{null_percentage:.2f}%")
        
        with col3:
            duplicate_records = self.df.duplicated().sum()
            st.metric("Duplicate Records", f"{duplicate_records:,}")
        
        with col4:
            data_quality_score = 100 - null_percentage - (duplicate_records / total_records * 100)
            st.metric("Data Quality Score", f"{data_quality_score:.1f}%")
    
    def render_sidebar_filters(self):
        """Render sidebar with filtering options"""
        st.sidebar.title("🔧 Dashboard Controls")
        
        # Device type filter
        device_types = ['All'] + list(self.df['device_type'].unique())
        selected_device_type = st.sidebar.selectbox(
            "Device Type",
            device_types
        )
        
        # Date range filter
        min_date = self.df['timestamp'].min().date()
        max_date = self.df['timestamp'].max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Anomaly filter
        show_anomalies_only = st.sidebar.checkbox("Show Anomalies Only", False)
        
        # Apply filters
        filtered_df = self.df.copy()
        
        if selected_device_type != 'All':
            filtered_df = filtered_df[filtered_df['device_type'] == selected_device_type]
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df['timestamp'].dt.date >= start_date) &
                (filtered_df['timestamp'].dt.date <= end_date)
            ]
        
        if show_anomalies_only:
            filtered_df = filtered_df[filtered_df['anomaly_detected'] == True]
        
        return filtered_df
    
    def render_export_options(self):
        """Render data export options"""
        st.sidebar.subheader("📥 Export Options")
        
        if st.sidebar.button("Export Current Data"):
            # Create downloadable CSV
            csv = self.df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        if st.sidebar.button("Generate Report"):
            # Generate summary report
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_devices': self.df['device_id'].nunique(),
                'total_records': len(self.df),
                'anomaly_rate': self.df['anomaly_detected'].mean() * 100,
                'avg_battery_level': self.df['battery_level'].mean(),
                'total_energy_consumption': self.df['energy_consumption'].sum()
            }
            
            json_report = json.dumps(report, indent=2)
            st.sidebar.download_button(
                label="Download Report (JSON)",
                data=json_report,
                file_name=f"iot_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    def run_dashboard(self):
        """Main dashboard execution"""
        # Render sidebar filters
        filtered_df = self.render_sidebar_filters()
        
        # Update main dataframe with filtered data
        self.df = filtered_df
        
        # Render main dashboard components
        self.render_header()
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", "⏰ Temporal", "🗺️ Geospatial", "🚨 Anomalies", "⚡ Energy"
        ])
        
        with tab1:
            self.render_device_overview()
            self.render_data_quality_metrics()
        
        with tab2:
            self.render_temporal_analysis()
        
        with tab3:
            self.render_geospatial_analysis()
        
        with tab4:
            self.render_anomaly_analysis()
            self.render_predictive_insights()
        
        with tab5:
            self.render_energy_analysis()
        
        # Render export options
        self.render_export_options()
        
        # Auto-refresh option
        if st.sidebar.checkbox("Auto-refresh (30s)", False):
            time.sleep(30)
            st.rerun()

def main():
    """Main function to run the dashboard"""
    dashboard = IoTDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
