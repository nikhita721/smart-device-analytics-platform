"""
Live IoT Data Producer for Real-time Streaming
Generates and streams live IoT device data for testing and demonstration
"""

import json
import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Generator
import logging
import numpy as np
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveIoTDataProducer:
    """
    Live IoT data producer for real-time streaming
    """
    
    def __init__(self, 
                 bootstrap_servers: str = 'localhost:9092',
                 topic: str = 'iot-device-data',
                 production_rate: float = 10.0):
        """
        Initialize the live data producer
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Kafka topic to produce to
            production_rate: Messages per second
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.production_rate = production_rate
        self.is_running = False
        
        # Device configurations
        self.device_types = ['thermostat', 'security_camera', 'smart_lock', 'motion_sensor', 'air_quality']
        self.device_ids = [f"device_{i:04d}" for i in range(1, 1001)]
        
        # Location data (Dallas area)
        self.locations = [
            {'lat': 32.7767, 'lon': -96.7970, 'name': 'Downtown Dallas'},
            {'lat': 32.7505, 'lon': -96.8078, 'name': 'Deep Ellum'},
            {'lat': 32.7831, 'lon': -96.8067, 'name': 'Uptown'},
            {'lat': 32.7942, 'lon': -96.8085, 'name': 'Victory Park'},
            {'lat': 32.7505, 'lon': -96.8078, 'name': 'Arts District'}
        ]
        
        # Initialize Kafka producer
        self.producer = None
        self._initialize_producer()
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_per_second': 0,
            'start_time': None,
            'errors': 0
        }
    
    def _initialize_producer(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                batch_size=16384,
                linger_ms=10,
                compression_type='snappy',
                acks='all',
                retries=3,
                retry_backoff_ms=100,
                request_timeout_ms=30000,
                max_block_ms=5000
            )
            logger.info("Kafka producer initialized successfully")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def generate_device_data(self, device_id: str, device_type: str) -> Dict:
        """Generate realistic IoT device data"""
        # Get device location
        location = random.choice(self.locations)
        
        # Generate sensor data based on device type
        if device_type == 'thermostat':
            temperature = np.random.normal(22, 3)  # Room temperature
            humidity = np.random.normal(45, 10)
            energy_consumption = np.random.exponential(0.5)
            battery_level = np.random.uniform(80, 100)
            
        elif device_type == 'security_camera':
            temperature = np.random.normal(25, 2)
            humidity = np.random.normal(40, 5)
            energy_consumption = np.random.exponential(2.0)
            battery_level = np.random.uniform(60, 100)
            
        elif device_type == 'smart_lock':
            temperature = np.random.normal(20, 1)
            humidity = np.random.normal(35, 3)
            energy_consumption = np.random.exponential(0.1)
            battery_level = np.random.uniform(70, 100)
            
        elif device_type == 'motion_sensor':
            temperature = np.random.normal(23, 2)
            humidity = np.random.normal(50, 8)
            energy_consumption = np.random.exponential(0.05)
            battery_level = np.random.uniform(50, 100)
            
        else:  # air_quality
            temperature = np.random.normal(24, 2)
            humidity = np.random.normal(55, 12)
            energy_consumption = np.random.exponential(0.3)
            battery_level = np.random.uniform(60, 100)
        
        # Add some noise to location
        latitude = location['lat'] + np.random.normal(0, 0.01)
        longitude = location['lon'] + np.random.normal(0, 0.01)
        
        # Generate anomaly (5% chance)
        is_anomaly = np.random.random() < 0.05
        if is_anomaly:
            temperature += np.random.normal(0, 10)
            energy_consumption *= np.random.uniform(2, 5)
            battery_level *= np.random.uniform(0.5, 0.8)
        
        # Create data record
        data = {
            'device_id': device_id,
            'device_type': device_type,
            'timestamp': datetime.now().isoformat(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'battery_level': round(battery_level, 1),
            'energy_consumption': round(energy_consumption, 3),
            'latitude': round(latitude, 6),
            'longitude': round(longitude, 6),
            'is_anomaly': is_anomaly,
            'signal_strength': round(np.random.uniform(-80, -30), 1),
            'location_name': location['name'],
            'firmware_version': f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            'uptime_hours': round(np.random.uniform(1, 8760), 1)  # Up to 1 year
        }
        
        return data
    
    def produce_message(self, data: Dict) -> bool:
        """Produce a single message to Kafka"""
        if not self.producer:
            logger.warning("Kafka producer not initialized")
            return False
        
        try:
            # Send message to Kafka
            future = self.producer.send(
                self.topic,
                value=data,
                key=data['device_id']
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            # Update statistics
            self.stats['messages_sent'] += 1
            
            logger.debug(f"Message sent to {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.stats['errors'] += 1
            return False
    
    def start_production(self):
        """Start producing messages"""
        if self.is_running:
            logger.warning("Producer is already running")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        def production_loop():
            while self.is_running:
                try:
                    # Generate random device data
                    device_id = random.choice(self.device_ids)
                    device_type = random.choice(self.device_types)
                    
                    # Generate data
                    data = self.generate_device_data(device_id, device_type)
                    
                    # Produce message
                    success = self.produce_message(data)
                    
                    if success:
                        logger.debug(f"Produced message for device {device_id}")
                    
                    # Calculate messages per second
                    if self.stats['start_time']:
                        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                        if elapsed > 0:
                            self.stats['messages_per_second'] = self.stats['messages_sent'] / elapsed
                    
                    # Sleep to control production rate
                    time.sleep(1.0 / self.production_rate)
                    
                except Exception as e:
                    logger.error(f"Error in production loop: {e}")
                    time.sleep(1)
        
        # Start production thread
        self.production_thread = threading.Thread(target=production_loop, daemon=True)
        self.production_thread.start()
        
        logger.info(f"Started producing {self.production_rate} messages/second to topic {self.topic}")
    
    def stop_production(self):
        """Stop producing messages"""
        self.is_running = False
        if self.producer:
            self.producer.flush()
            self.producer.close()
        logger.info("Stopped producing messages")
    
    def get_statistics(self) -> Dict:
        """Get producer statistics"""
        return self.stats.copy()
    
    def generate_burst_data(self, count: int = 100) -> List[Dict]:
        """Generate a burst of data for testing"""
        data_list = []
        
        for _ in range(count):
            device_id = random.choice(self.device_ids)
            device_type = random.choice(self.device_types)
            data = self.generate_device_data(device_id, device_type)
            data_list.append(data)
        
        return data_list

def start_live_producer(production_rate: float = 10.0):
    """Start the live data producer"""
    producer = LiveIoTDataProducer(production_rate=production_rate)
    
    try:
        producer.start_production()
        
        # Keep running
        while True:
            time.sleep(1)
            stats = producer.get_statistics()
            logger.info(f"Produced {stats['messages_sent']} messages at {stats['messages_per_second']:.1f} msg/s")
            
    except KeyboardInterrupt:
        logger.info("Stopping producer...")
        producer.stop_production()
    except Exception as e:
        logger.error(f"Error in producer: {e}")
        producer.stop_production()

if __name__ == "__main__":
    # Start the live producer
    start_live_producer(production_rate=5.0)  # 5 messages per second
