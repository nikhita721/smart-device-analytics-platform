"""
Real-time Anomaly Detection System for IoT Data
Advanced ML-based anomaly detection with live streaming capabilities
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque
import logging
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from scipy import stats
import joblib
import json
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveAnomalyDetector:
    """
    Real-time anomaly detection system for IoT data streams
    """
    
    def __init__(self, 
                 window_size: int = 100,
                 anomaly_threshold: float = 0.1,
                 model_update_interval: int = 1000):
        """
        Initialize the live anomaly detector
        
        Args:
            window_size: Size of sliding window for analysis
            anomaly_threshold: Threshold for anomaly detection
            model_update_interval: How often to retrain the model
        """
        self.window_size = window_size
        self.anomaly_threshold = anomaly_threshold
        self.model_update_interval = model_update_interval
        
        # Data buffers
        self.data_buffer = deque(maxlen=window_size * 2)
        self.anomaly_scores = deque(maxlen=window_size)
        self.anomaly_alerts = deque(maxlen=1000)
        
        # ML models
        self.isolation_forest = IsolationForest(
            contamination=anomaly_threshold,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)
        
        # Statistical models
        self.statistical_thresholds = {}
        self.device_baselines = {}
        
        # Model training state
        self.model_trained = False
        self.last_model_update = 0
        self.training_data = deque(maxlen=window_size * 3)
        
        # Performance metrics
        self.detection_stats = {
            'total_anomalies': 0,
            'false_positives': 0,
            'true_positives': 0,
            'detection_rate': 0.0,
            'last_detection': None
        }
    
    def extract_features(self, data: Dict) -> np.ndarray:
        """Extract features for anomaly detection"""
        features = []
        
        # Basic sensor features
        features.extend([
            data.get('temperature', 0),
            data.get('humidity', 0),
            data.get('battery_level', 0),
            data.get('energy_consumption', 0),
            data.get('signal_strength', 0)
        ])
        
        # Derived features
        if 'temperature' in data and 'humidity' in data:
            # Heat index
            temp_f = data['temperature'] * 9/5 + 32
            humidity = data['humidity']
            if temp_f >= 80:
                heat_index = -42.379 + 2.04901523*temp_f + 10.14333127*humidity - 0.22475541*temp_f*humidity
                features.append(heat_index)
            else:
                features.append(temp_f)
        
        # Energy efficiency
        if 'energy_consumption' in data and 'device_type' in data:
            base_consumption = {
                'thermostat': 0.5, 'security_camera': 2.0, 'smart_lock': 0.1,
                'motion_sensor': 0.05, 'air_quality': 0.3
            }
            expected = base_consumption.get(data['device_type'], 1.0)
            efficiency = expected / max(data['energy_consumption'], 0.001)
            features.append(efficiency)
        
        # Temporal features
        timestamp = pd.to_datetime(data.get('timestamp', datetime.now().isoformat()))
        features.extend([
            timestamp.hour,
            timestamp.day_of_week,
            timestamp.day_of_year
        ])
        
        # Device type encoding
        device_type = data.get('device_type', 'unknown')
        device_encoding = {
            'thermostat': 1, 'security_camera': 2, 'smart_lock': 3,
            'motion_sensor': 4, 'air_quality': 5, 'unknown': 0
        }
        features.append(device_encoding.get(device_type, 0))
        
        return np.array(features)
    
    def update_statistical_baselines(self, data: Dict):
        """Update statistical baselines for each device"""
        device_id = data.get('device_id', 'unknown')
        
        if device_id not in self.device_baselines:
            self.device_baselines[device_id] = {
                'temperature': deque(maxlen=100),
                'humidity': deque(maxlen=100),
                'energy_consumption': deque(maxlen=100),
                'battery_level': deque(maxlen=100)
            }
        
        baseline = self.device_baselines[device_id]
        
        # Update baselines
        for metric in ['temperature', 'humidity', 'energy_consumption', 'battery_level']:
            if metric in data:
                baseline[metric].append(data[metric])
    
    def detect_statistical_anomalies(self, data: Dict) -> List[Dict]:
        """Detect anomalies using statistical methods"""
        anomalies = []
        device_id = data.get('device_id', 'unknown')
        
        if device_id not in self.device_baselines:
            return anomalies
        
        baseline = self.device_baselines[device_id]
        
        for metric in ['temperature', 'humidity', 'energy_consumption', 'battery_level']:
            if metric in data and len(baseline[metric]) > 10:
                values = list(baseline[metric])
                current_value = data[metric]
                
                # Z-score based detection
                mean_val = np.mean(values)
                std_val = np.std(values)
                
                if std_val > 0:
                    z_score = abs(current_value - mean_val) / std_val
                    
                    if z_score > 3:  # 3-sigma rule
                        anomalies.append({
                            'type': 'statistical',
                            'metric': metric,
                            'value': current_value,
                            'expected_range': [mean_val - 3*std_val, mean_val + 3*std_val],
                            'z_score': z_score,
                            'severity': 'high' if z_score > 5 else 'medium'
                        })
        
        return anomalies
    
    def detect_ml_anomalies(self, features: np.ndarray) -> Tuple[bool, float]:
        """Detect anomalies using ML models"""
        if not self.model_trained or len(self.training_data) < self.window_size:
            return False, 0.0
        
        try:
            # Prepare training data
            training_features = []
            for data_point in self.training_data:
                training_features.append(self.extract_features(data_point))
            
            training_features = np.array(training_features)
            
            # Fit models
            self.scaler.fit(training_features)
            scaled_features = self.scaler.transform([features])
            
            # Isolation Forest
            isolation_score = self.isolation_forest.decision_function(scaled_features)[0]
            is_anomaly = isolation_score < -0.1  # Threshold for anomaly
            
            # DBSCAN clustering
            cluster_labels = self.dbscan.fit_predict(scaled_features)
            is_outlier = cluster_labels[0] == -1  # -1 indicates outlier
            
            # Combined score
            anomaly_score = -isolation_score  # Convert to positive score
            if is_outlier:
                anomaly_score += 0.5
            
            return is_anomaly or is_outlier, anomaly_score
            
        except Exception as e:
            logger.error(f"Error in ML anomaly detection: {e}")
            return False, 0.0
    
    def detect_pattern_anomalies(self, data: Dict) -> List[Dict]:
        """Detect pattern-based anomalies"""
        anomalies = []
        
        # Check for unusual patterns
        if 'temperature' in data and 'humidity' in data:
            temp = data['temperature']
            humidity = data['humidity']
            
            # Unusual temperature-humidity combination
            if temp > 30 and humidity > 80:  # Very hot and humid
                anomalies.append({
                    'type': 'pattern',
                    'description': 'Extreme heat and humidity combination',
                    'severity': 'high',
                    'details': f'Temperature: {temp}°C, Humidity: {humidity}%'
                })
        
        # Check for energy spikes
        if 'energy_consumption' in data:
            energy = data['energy_consumption']
            if energy > 10:  # Unusually high energy consumption
                anomalies.append({
                    'type': 'pattern',
                    'description': 'Energy consumption spike',
                    'severity': 'high',
                    'details': f'Energy: {energy}W'
                })
        
        # Check for battery anomalies
        if 'battery_level' in data:
            battery = data['battery_level']
            if battery < 10:  # Low battery
                anomalies.append({
                    'type': 'pattern',
                    'description': 'Low battery warning',
                    'severity': 'medium',
                    'details': f'Battery: {battery}%'
                })
        
        return anomalies
    
    def process_data_point(self, data: Dict) -> Dict:
        """Process a single data point for anomaly detection"""
        # Add to buffers
        self.data_buffer.append(data)
        self.training_data.append(data)
        
        # Update statistical baselines
        self.update_statistical_baselines(data)
        
        # Extract features
        features = self.extract_features(data)
        
        # Detect anomalies
        all_anomalies = []
        
        # Statistical anomalies
        stat_anomalies = self.detect_statistical_anomalies(data)
        all_anomalies.extend(stat_anomalies)
        
        # ML anomalies
        is_ml_anomaly, ml_score = self.detect_ml_anomalies(features)
        if is_ml_anomaly:
            all_anomalies.append({
                'type': 'ml',
                'description': 'ML-detected anomaly',
                'severity': 'high' if ml_score > 0.5 else 'medium',
                'score': ml_score
            })
        
        # Pattern anomalies
        pattern_anomalies = self.detect_pattern_anomalies(data)
        all_anomalies.extend(pattern_anomalies)
        
        # Create anomaly alert if any anomalies found
        if all_anomalies:
            alert = {
                'device_id': data.get('device_id', 'unknown'),
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'anomalies': all_anomalies,
                'severity': max([a.get('severity', 'low') for a in all_anomalies], 
                              key=lambda x: {'low': 0, 'medium': 1, 'high': 2}[x]),
                'total_anomalies': len(all_anomalies)
            }
            
            self.anomaly_alerts.append(alert)
            self.detection_stats['total_anomalies'] += 1
            self.detection_stats['last_detection'] = datetime.now()
            
            logger.info(f"Anomaly detected for device {data.get('device_id')}: {len(all_anomalies)} anomalies")
        
        # Update model if needed
        if len(self.training_data) >= self.model_update_interval:
            self.retrain_model()
        
        # Return processed data with anomaly information
        processed_data = data.copy()
        processed_data['anomaly_detected'] = len(all_anomalies) > 0
        processed_data['anomaly_count'] = len(all_anomalies)
        processed_data['anomaly_score'] = ml_score if is_ml_anomaly else 0.0
        
        return processed_data
    
    def retrain_model(self):
        """Retrain the ML models with recent data"""
        if len(self.training_data) < self.window_size:
            return
        
        try:
            # Prepare training data
            training_features = []
            for data_point in self.training_data:
                training_features.append(self.extract_features(data_point))
            
            training_features = np.array(training_features)
            
            # Retrain models
            self.scaler.fit(training_features)
            self.isolation_forest.fit(training_features)
            self.dbscan.fit(training_features)
            
            self.model_trained = True
            self.last_model_update = len(self.training_data)
            
            logger.info("ML models retrained successfully")
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    def get_anomaly_summary(self) -> Dict:
        """Get summary of recent anomalies"""
        recent_alerts = list(self.anomaly_alerts)[-100:]  # Last 100 alerts
        
        if not recent_alerts:
            return {
                'total_anomalies': 0,
                'severity_distribution': {},
                'device_anomaly_counts': {},
                'recent_alerts': []
            }
        
        # Calculate statistics
        severity_counts = {}
        device_counts = {}
        
        for alert in recent_alerts:
            severity = alert.get('severity', 'unknown')
            device_id = alert.get('device_id', 'unknown')
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            device_counts[device_id] = device_counts.get(device_id, 0) + 1
        
        return {
            'total_anomalies': len(recent_alerts),
            'severity_distribution': severity_counts,
            'device_anomaly_counts': device_counts,
            'recent_alerts': recent_alerts[-10:],  # Last 10 alerts
            'detection_rate': self.detection_stats['total_anomalies'] / max(1, len(self.data_buffer))
        }
    
    def get_detection_metrics(self) -> Dict:
        """Get anomaly detection performance metrics"""
        return {
            'total_anomalies': self.detection_stats['total_anomalies'],
            'detection_rate': self.detection_stats['detection_rate'],
            'last_detection': self.detection_stats['last_detection'],
            'model_trained': self.model_trained,
            'buffer_size': len(self.data_buffer),
            'training_samples': len(self.training_data)
        }

# Global anomaly detector instance
anomaly_detector = None

def initialize_anomaly_detector():
    """Initialize the global anomaly detector"""
    global anomaly_detector
    if anomaly_detector is None:
        anomaly_detector = LiveAnomalyDetector()
    return anomaly_detector

def detect_anomalies(data: Dict) -> Dict:
    """Detect anomalies in IoT data"""
    global anomaly_detector
    if anomaly_detector is None:
        anomaly_detector = initialize_anomaly_detector()
    
    return anomaly_detector.process_data_point(data)

def get_anomaly_summary() -> Dict:
    """Get anomaly detection summary"""
    global anomaly_detector
    if anomaly_detector is None:
        return {}
    
    return anomaly_detector.get_anomaly_summary()

def get_detection_metrics() -> Dict:
    """Get anomaly detection metrics"""
    global anomaly_detector
    if anomaly_detector is None:
        return {}
    
    return anomaly_detector.get_detection_metrics()
