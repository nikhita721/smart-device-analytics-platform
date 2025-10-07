"""
Live Kafka Consumer for Real-time IoT Data Streaming
Handles real-time data consumption from Kafka topics
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import pandas as pd
import numpy as np
from collections import deque
import threading
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveIoTDataConsumer:
    """
    Real-time Kafka consumer for IoT device data streaming
    """
    
    def __init__(self, 
                 bootstrap_servers: str = 'localhost:9092',
                 topic: str = 'iot-device-data',
                 group_id: str = 'iot-dashboard-consumer',
                 auto_offset_reset: str = 'latest',
                 max_records: int = 1000):
        """
        Initialize the live Kafka consumer
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Kafka topic to consume from
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading from
            max_records: Maximum records to fetch per poll
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.max_records = max_records
        
        self.consumer = None
        self.is_running = False
        self.data_buffer = deque(maxlen=10000)  # Keep last 10k records
        self.data_queue = queue.Queue(maxsize=1000)
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'messages_per_second': 0,
            'last_message_time': None,
            'error_count': 0,
            'start_time': None
        }
        
        self._initialize_consumer()
    
    def _initialize_consumer(self):
        """Initialize Kafka consumer with optimized settings"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                max_poll_records=self.max_records,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_interval_ms=300000,
                fetch_min_bytes=1,
                fetch_max_wait_ms=500,
                consumer_timeout_ms=1000
            )
            logger.info(f"Kafka consumer initialized successfully for topic: {self.topic}")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def start_consuming(self):
        """Start consuming messages in a separate thread"""
        if self.is_running:
            logger.warning("Consumer is already running")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        def consume_loop():
            try:
                while self.is_running:
                    message_batch = self.consumer.poll(timeout_ms=1000)
                    
                    if message_batch:
                        for topic_partition, messages in message_batch.items():
                            for message in messages:
                                try:
                                    # Process message
                                    data = message.value
                                    data['kafka_timestamp'] = message.timestamp
                                    data['kafka_offset'] = message.offset
                                    data['kafka_partition'] = message.partition
                                    
                                    # Add to buffer and queue
                                    self.data_buffer.append(data)
                                    if not self.data_queue.full():
                                        self.data_queue.put(data)
                                    
                                    # Update statistics
                                    self.stats['total_messages'] += 1
                                    self.stats['last_message_time'] = datetime.now()
                                    
                                except Exception as e:
                                    logger.error(f"Error processing message: {e}")
                                    self.stats['error_count'] += 1
                    
                    # Calculate messages per second
                    if self.stats['start_time']:
                        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                        if elapsed > 0:
                            self.stats['messages_per_second'] = self.stats['total_messages'] / elapsed
                            
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                self.stats['error_count'] += 1
            finally:
                self.is_running = False
        
        # Start consumer thread
        self.consumer_thread = threading.Thread(target=consume_loop, daemon=True)
        self.consumer_thread.start()
        logger.info("Started consuming messages from Kafka")
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.is_running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Stopped consuming messages from Kafka")
    
    def get_latest_data(self, limit: int = 100) -> List[Dict]:
        """Get latest data from buffer"""
        return list(self.data_buffer)[-limit:]
    
    def get_data_from_queue(self, timeout: float = 1.0) -> Optional[Dict]:
        """Get data from queue (non-blocking)"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_statistics(self) -> Dict:
        """Get consumer statistics"""
        return self.stats.copy()
    
    def generate_sample_data(self) -> Generator[Dict, None, None]:
        """
        Generate sample IoT data for testing when Kafka is not available
        """
        device_types = ['thermostat', 'security_camera', 'smart_lock', 'motion_sensor', 'air_quality']
        device_ids = [f"device_{i:04d}" for i in range(1, 1001)]
        
        while True:
            try:
                # Generate sample data
                device_id = np.random.choice(device_ids)
                device_type = np.random.choice(device_types)
                
                # Generate realistic sensor data
                if device_type == 'thermostat':
                    temperature = np.random.normal(22, 3)  # Room temperature
                    humidity = np.random.normal(45, 10)
                    energy_consumption = np.random.exponential(0.5)
                elif device_type == 'security_camera':
                    temperature = np.random.normal(25, 2)
                    humidity = np.random.normal(40, 5)
                    energy_consumption = np.random.exponential(2.0)
                elif device_type == 'smart_lock':
                    temperature = np.random.normal(20, 1)
                    humidity = np.random.normal(35, 3)
                    energy_consumption = np.random.exponential(0.1)
                elif device_type == 'motion_sensor':
                    temperature = np.random.normal(23, 2)
                    humidity = np.random.normal(50, 8)
                    energy_consumption = np.random.exponential(0.05)
                else:  # air_quality
                    temperature = np.random.normal(24, 2)
                    humidity = np.random.normal(55, 12)
                    energy_consumption = np.random.exponential(0.3)
                
                # Generate location data
                latitude = np.random.uniform(32.7, 33.0)  # Dallas area
                longitude = np.random.uniform(-96.9, -96.7)
                
                # Generate anomaly (5% chance)
                is_anomaly = np.random.random() < 0.05
                if is_anomaly:
                    temperature += np.random.normal(0, 10)
                    energy_consumption *= np.random.uniform(2, 5)
                
                # Create data record
                data = {
                    'device_id': device_id,
                    'device_type': device_type,
                    'timestamp': datetime.now().isoformat(),
                    'temperature': round(temperature, 2),
                    'humidity': round(humidity, 2),
                    'battery_level': round(np.random.uniform(20, 100), 1),
                    'energy_consumption': round(energy_consumption, 3),
                    'latitude': round(latitude, 6),
                    'longitude': round(longitude, 6),
                    'is_anomaly': is_anomaly,
                    'signal_strength': round(np.random.uniform(-80, -30), 1),
                    'kafka_timestamp': int(time.time() * 1000),
                    'kafka_offset': self.stats['total_messages'],
                    'kafka_partition': 0
                }
                
                yield data
                time.sleep(0.1)  # 10 messages per second
                
            except Exception as e:
                logger.error(f"Error generating sample data: {e}")
                time.sleep(1)

class LiveDataProcessor:
    """
    Process live streaming data for real-time analytics
    """
    
    def __init__(self, consumer: LiveIoTDataConsumer):
        self.consumer = consumer
        self.processed_data = deque(maxlen=1000)
        self.anomaly_alerts = deque(maxlen=100)
        self.device_stats = {}
        
    def process_live_data(self, data: Dict) -> Dict:
        """Process incoming live data"""
        processed = data.copy()
        
        # Add processing timestamp
        processed['processed_at'] = datetime.now().isoformat()
        
        # Calculate derived metrics
        if 'temperature' in data and 'humidity' in data:
            # Heat index calculation
            temp_f = data['temperature'] * 9/5 + 32
            humidity = data['humidity']
            if temp_f >= 80:
                heat_index = -42.379 + 2.04901523*temp_f + 10.14333127*humidity - 0.22475541*temp_f*humidity - 6.83783e-3*temp_f**2 - 5.481717e-2*humidity**2 + 1.22874e-3*temp_f**2*humidity + 8.5282e-4*temp_f*humidity**2 - 1.99e-6*temp_f**2*humidity**2
                processed['heat_index'] = round((heat_index - 32) * 5/9, 2)
            else:
                processed['heat_index'] = data['temperature']
        
        # Energy efficiency score
        if 'energy_consumption' in data and 'device_type' in data:
            base_consumption = {'thermostat': 0.5, 'security_camera': 2.0, 'smart_lock': 0.1, 'motion_sensor': 0.05, 'air_quality': 0.3}
            expected = base_consumption.get(data['device_type'], 1.0)
            efficiency = max(0, min(100, (expected / data['energy_consumption']) * 100))
            processed['efficiency_score'] = round(efficiency, 1)
        
        # Update device statistics
        device_id = data['device_id']
        if device_id not in self.device_stats:
            self.device_stats[device_id] = {
                'message_count': 0,
                'last_seen': None,
                'avg_temperature': 0,
                'avg_energy': 0,
                'anomaly_count': 0
            }
        
        stats = self.device_stats[device_id]
        stats['message_count'] += 1
        stats['last_seen'] = datetime.now()
        
        # Update running averages
        if stats['message_count'] == 1:
            stats['avg_temperature'] = data['temperature']
            stats['avg_energy'] = data['energy_consumption']
        else:
            alpha = 0.1  # Exponential smoothing factor
            stats['avg_temperature'] = alpha * data['temperature'] + (1 - alpha) * stats['avg_temperature']
            stats['avg_energy'] = alpha * data['energy_consumption'] + (1 - alpha) * stats['avg_energy']
        
        if data.get('is_anomaly', False):
            stats['anomaly_count'] += 1
            self.anomaly_alerts.append({
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'anomaly_type': 'sensor_anomaly',
                'severity': 'high' if data['temperature'] > 30 or data['energy_consumption'] > 5 else 'medium',
                'details': f"Temperature: {data['temperature']}°C, Energy: {data['energy_consumption']}W"
            })
        
        self.processed_data.append(processed)
        return processed
    
    def get_live_metrics(self) -> Dict:
        """Get live metrics from processed data"""
        if not self.processed_data:
            return {}
        
        recent_data = list(self.processed_data)[-100:]  # Last 100 records
        
        metrics = {
            'total_devices': len(set(d['device_id'] for d in recent_data)),
            'avg_temperature': np.mean([d['temperature'] for d in recent_data]),
            'avg_humidity': np.mean([d['humidity'] for d in recent_data]),
            'avg_energy': np.mean([d['energy_consumption'] for d in recent_data]),
            'anomaly_rate': sum(1 for d in recent_data if d.get('is_anomaly', False)) / len(recent_data),
            'device_types': {d['device_type']: sum(1 for x in recent_data if x['device_type'] == d['device_type']) for d in recent_data},
            'recent_alerts': list(self.anomaly_alerts)[-10:],
            'processing_rate': len(self.processed_data) / max(1, (datetime.now() - self.consumer.stats['start_time']).total_seconds()) if self.consumer.stats['start_time'] else 0
        }
        
        return metrics

# Global instances for dashboard integration
live_consumer = None
live_processor = None

def initialize_live_streaming():
    """Initialize live streaming components"""
    global live_consumer, live_processor
    
    try:
        # Try to connect to Kafka first
        live_consumer = LiveIoTDataConsumer()
        live_consumer.start_consuming()
        logger.info("Connected to Kafka for live streaming")
    except Exception as e:
        logger.warning(f"Could not connect to Kafka: {e}. Using sample data generator.")
        # Fallback to sample data generator
        live_consumer = None
    
    live_processor = LiveDataProcessor(live_consumer)
    return live_consumer, live_processor

def get_live_data():
    """Get live data for dashboard"""
    global live_consumer, live_processor
    
    if live_consumer and live_consumer.is_running:
        # Get data from Kafka
        data = live_consumer.get_data_from_queue(timeout=0.1)
        if data:
            return live_processor.process_live_data(data)
    else:
        # Generate sample data
        if not hasattr(get_live_data, 'sample_generator'):
            get_live_data.sample_generator = LiveIoTDataConsumer().generate_sample_data()
        
        try:
            data = next(get_live_data.sample_generator)
            return live_processor.process_live_data(data)
        except:
            return None
    
    return None

def get_live_metrics():
    """Get live metrics for dashboard"""
    global live_processor
    return live_processor.get_live_metrics() if live_processor else {}
