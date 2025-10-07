"""
Comprehensive Test Suite for IoT Data Engineering Pipeline
Tests data quality, ETL processes, ML models, and system integration
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing.spark_etl import IoTDataETLProcessor
from ml_ops.model_training import IoTMLPipeline
from data_ingestion.kafka_producer import IoTDeviceDataProducer

class TestIoTDataPipeline:
    """Test suite for IoT data engineering pipeline"""
    
    @pytest.fixture
    def sample_iot_data(self):
        """Create sample IoT data for testing"""
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'device_id': [f'device_{i%100:04d}' for i in range(n_samples)],
            'device_type': np.random.choice(['thermostat', 'security_camera', 'smart_lock'], n_samples),
            'timestamp': pd.date_range(start=datetime.now() - timedelta(days=7), 
                                    periods=n_samples, freq='H'),
            'temperature': np.random.normal(72, 10, n_samples),
            'humidity': np.random.normal(50, 15, n_samples),
            'battery_level': np.random.uniform(10, 100, n_samples),
            'energy_consumption': np.random.exponential(2, n_samples),
            'anomaly_detected': np.random.choice([True, False], n_samples, p=[0.05, 0.95])
        }
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def etl_processor(self):
        """Create ETL processor instance for testing"""
        return IoTDataETLProcessor()
    
    @pytest.fixture
    def ml_pipeline(self):
        """Create ML pipeline instance for testing"""
        return IoTMLPipeline()
    
    def test_data_quality_checks(self, sample_iot_data, etl_processor):
        """Test data quality validation"""
        # Test with clean data
        df_clean = etl_processor.apply_data_quality_checks(sample_iot_data)
        
        # Assertions
        assert len(df_clean) > 0, "Data quality check should not remove all data"
        assert 'data_quality_score' in df_clean.columns, "Data quality score should be added"
        assert df_clean['data_quality_score'].min() >= 0, "Quality score should be non-negative"
        assert df_clean['data_quality_score'].max() <= 1, "Quality score should be at most 1"
    
    def test_time_series_features(self, sample_iot_data, etl_processor):
        """Test time series feature creation"""
        df_features = etl_processor.create_time_series_features(sample_iot_data)
        
        # Check for new features
        expected_features = [
            'hour_of_day', 'day_of_week', 'is_weekend',
            'temp_rolling_avg', 'humidity_rolling_avg', 'battery_trend'
        ]
        
        for feature in expected_features:
            assert feature in df_features.columns, f"Feature {feature} should be created"
    
    def test_anomaly_detection(self, sample_iot_data, etl_processor):
        """Test anomaly detection functionality"""
        df_anomalies = etl_processor.detect_anomalies(sample_iot_data)
        
        # Check for anomaly-related columns
        assert 'statistical_anomaly' in df_anomalies.columns, "Statistical anomaly column should exist"
        assert 'pattern_anomaly' in df_anomalies.columns, "Pattern anomaly column should exist"
        assert 'anomaly_score' in df_anomalies.columns, "Anomaly score column should exist"
        
        # Check anomaly score range
        assert df_anomalies['anomaly_score'].min() >= 0, "Anomaly score should be non-negative"
        assert df_anomalies['anomaly_score'].max() <= 1, "Anomaly score should be at most 1"
    
    def test_aggregated_metrics(self, sample_iot_data, etl_processor):
        """Test aggregated metrics creation"""
        device_metrics, location_metrics, hourly_metrics = etl_processor.create_aggregated_metrics(sample_iot_data)
        
        # Check device metrics
        assert len(device_metrics) > 0, "Device metrics should not be empty"
        assert 'total_readings' in device_metrics.columns, "Total readings should be calculated"
        assert 'avg_temperature' in device_metrics.columns, "Average temperature should be calculated"
        
        # Check location metrics
        assert len(location_metrics) > 0, "Location metrics should not be empty"
        assert 'device_density' in location_metrics.columns, "Device density should be calculated"
        
        # Check hourly metrics
        assert len(hourly_metrics) > 0, "Hourly metrics should not be empty"
        assert 'readings_count' in hourly_metrics.columns, "Readings count should be calculated"
    
    def test_ml_model_training(self, sample_iot_data, ml_pipeline):
        """Test ML model training"""
        # Prepare features
        df_processed = ml_pipeline.prepare_features(sample_iot_data)
        
        # Test anomaly detection model
        anomaly_metrics = ml_pipeline.train_anomaly_detection_model(df_processed)
        
        # Check metrics
        assert 'accuracy' in anomaly_metrics, "Accuracy should be calculated"
        assert 'precision' in anomaly_metrics, "Precision should be calculated"
        assert 'recall' in anomaly_metrics, "Recall should be calculated"
        assert 'f1_score' in anomaly_metrics, "F1 score should be calculated"
        
        # Check metric ranges
        assert 0 <= anomaly_metrics['accuracy'] <= 1, "Accuracy should be between 0 and 1"
        assert 0 <= anomaly_metrics['precision'] <= 1, "Precision should be between 0 and 1"
        assert 0 <= anomaly_metrics['recall'] <= 1, "Recall should be between 0 and 1"
        assert 0 <= anomaly_metrics['f1_score'] <= 1, "F1 score should be between 0 and 1"
    
    def test_predictive_maintenance_model(self, sample_iot_data, ml_pipeline):
        """Test predictive maintenance model training"""
        # Prepare features
        df_processed = ml_pipeline.prepare_features(sample_iot_data)
        
        # Create maintenance target
        df_processed['needs_maintenance'] = (
            (df_processed['battery_level'] < 20) | 
            (df_processed['anomaly_detected'] == True)
        )
        
        # Train model
        maintenance_metrics = ml_pipeline.train_predictive_maintenance_model(df_processed)
        
        # Check metrics
        assert 'accuracy' in maintenance_metrics, "Accuracy should be calculated"
        assert 'f1_score' in maintenance_metrics, "F1 score should be calculated"
        
        # Check metric ranges
        assert 0 <= maintenance_metrics['accuracy'] <= 1, "Accuracy should be between 0 and 1"
        assert 0 <= maintenance_metrics['f1_score'] <= 1, "F1 score should be between 0 and 1"
    
    def test_energy_consumption_model(self, sample_iot_data, ml_pipeline):
        """Test energy consumption prediction model"""
        # Prepare features
        df_processed = ml_pipeline.prepare_features(sample_iot_data)
        
        # Train model
        energy_metrics = ml_pipeline.train_energy_consumption_model(df_processed)
        
        # Check metrics
        assert 'mse' in energy_metrics, "MSE should be calculated"
        assert 'rmse' in energy_metrics, "RMSE should be calculated"
        assert 'r2_score' in energy_metrics, "R² score should be calculated"
        
        # Check metric ranges
        assert energy_metrics['mse'] >= 0, "MSE should be non-negative"
        assert energy_metrics['rmse'] >= 0, "RMSE should be non-negative"
        assert -1 <= energy_metrics['r2_score'] <= 1, "R² score should be between -1 and 1"
    
    def test_model_predictions(self, sample_iot_data, ml_pipeline):
        """Test model prediction functionality"""
        # Prepare features
        df_processed = ml_pipeline.prepare_features(sample_iot_data)
        
        # Train models
        ml_pipeline.train_anomaly_detection_model(df_processed)
        ml_pipeline.train_predictive_maintenance_model(df_processed)
        ml_pipeline.train_energy_consumption_model(df_processed)
        
        # Test predictions
        anomaly_predictions = ml_pipeline.predict_anomalies(df_processed)
        maintenance_predictions = ml_pipeline.predict_maintenance(df_processed)
        energy_predictions = ml_pipeline.predict_energy_consumption(df_processed)
        
        # Check prediction columns
        assert 'predicted_anomaly' in anomaly_predictions.columns, "Predicted anomaly should be added"
        assert 'anomaly_probability' in anomaly_predictions.columns, "Anomaly probability should be added"
        assert 'predicted_maintenance' in maintenance_predictions.columns, "Predicted maintenance should be added"
        assert 'predicted_energy_consumption' in energy_predictions.columns, "Predicted energy should be added"
    
    def test_kafka_producer(self):
        """Test Kafka producer functionality"""
        producer = IoTDeviceDataProducer()
        
        # Test data generation
        device_data = producer._generate_device_data('test_device', 'thermostat')
        
        # Check required fields
        required_fields = ['device_id', 'device_type', 'timestamp', 'location']
        for field in required_fields:
            assert field in device_data, f"Field {field} should be present in device data"
        
        # Check data types
        assert isinstance(device_data['device_id'], str), "Device ID should be string"
        assert isinstance(device_data['device_type'], str), "Device type should be string"
        assert isinstance(device_data['timestamp'], str), "Timestamp should be string"
        assert isinstance(device_data['location'], dict), "Location should be dictionary"
    
    def test_data_validation(self, sample_iot_data):
        """Test data validation and quality checks"""
        # Test for required columns
        required_columns = [
            'device_id', 'device_type', 'timestamp', 'temperature',
            'humidity', 'battery_level', 'energy_consumption'
        ]
        
        for column in required_columns:
            assert column in sample_iot_data.columns, f"Required column {column} should be present"
        
        # Test data types
        assert sample_iot_data['device_id'].dtype == 'object', "Device ID should be string"
        assert sample_iot_data['device_type'].dtype == 'object', "Device type should be string"
        assert pd.api.types.is_datetime64_any_dtype(sample_iot_data['timestamp']), "Timestamp should be datetime"
        assert pd.api.types.is_numeric_dtype(sample_iot_data['temperature']), "Temperature should be numeric"
        assert pd.api.types.is_numeric_dtype(sample_iot_data['battery_level']), "Battery level should be numeric"
    
    def test_performance_metrics(self, sample_iot_data, etl_processor):
        """Test performance and scalability metrics"""
        import time
        
        # Test processing time
        start_time = time.time()
        df_processed = etl_processor.apply_data_quality_checks(sample_iot_data)
        processing_time = time.time() - start_time
        
        # Check processing time is reasonable (less than 10 seconds for 1000 records)
        assert processing_time < 10, f"Processing time {processing_time:.2f}s is too slow for 1000 records"
        
        # Test memory usage
        memory_usage = df_processed.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        assert memory_usage < 100, f"Memory usage {memory_usage:.2f}MB is too high"
    
    def test_error_handling(self, etl_processor):
        """Test error handling and edge cases"""
        # Test with empty dataframe
        empty_df = pd.DataFrame()
        
        with pytest.raises(Exception):
            etl_processor.apply_data_quality_checks(empty_df)
        
        # Test with invalid data
        invalid_df = pd.DataFrame({
            'device_id': [None, '', 'valid_id'],
            'temperature': [np.nan, np.inf, 72.0],
            'battery_level': [-1, 101, 50.0]
        })
        
        # Should handle invalid data gracefully
        try:
            result = etl_processor.apply_data_quality_checks(invalid_df)
            assert len(result) >= 0, "Should handle invalid data gracefully"
        except Exception as e:
            # Should raise informative error
            assert "data quality" in str(e).lower() or "validation" in str(e).lower()
    
    def test_integration_workflow(self, sample_iot_data, etl_processor, ml_pipeline):
        """Test end-to-end integration workflow"""
        # Step 1: Data quality checks
        df_quality = etl_processor.apply_data_quality_checks(sample_iot_data)
        assert len(df_quality) > 0, "Quality check should not remove all data"
        
        # Step 2: Feature engineering
        df_features = etl_processor.create_time_series_features(df_quality)
        assert len(df_features) > 0, "Feature engineering should not remove all data"
        
        # Step 3: Anomaly detection
        df_anomalies = etl_processor.detect_anomalies(df_features)
        assert len(df_anomalies) > 0, "Anomaly detection should not remove all data"
        
        # Step 4: ML model training
        df_processed = ml_pipeline.prepare_features(df_anomalies)
        anomaly_metrics = ml_pipeline.train_anomaly_detection_model(df_processed)
        
        # Check end-to-end results
        assert anomaly_metrics['accuracy'] > 0, "Model should have positive accuracy"
        assert 'anomaly_score' in df_anomalies.columns, "Anomaly score should be calculated"
        assert 'data_quality_score' in df_quality.columns, "Data quality score should be calculated"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
