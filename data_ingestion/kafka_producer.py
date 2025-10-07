"""
Real-time IoT Device Data Producer
Simulates smart device data streaming to Kafka for real-time processing
"""

import json
import time
import random
from datetime import datetime, timezone
from typing import Dict, List
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTDeviceDataProducer:
    """
    High-performance Kafka producer for IoT device data streaming
    Handles 1M+ events daily with optimized batching and error handling
    """
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'iot-device-data'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self.device_types = ['thermostat', 'security_camera', 'smart_lock', 'motion_sensor', 'air_quality']
        self.device_ids = [f"device_{i:04d}" for i in range(1, 1001)]  # 1000 devices
        
    def _create_producer(self):
        """Initialize Kafka producer with optimized configuration"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                batch_size=16384,  # Optimize for throughput
                linger_ms=10,      # Reduce latency
                compression_type='snappy',  # Compress for efficiency
                acks='all',        # Ensure durability
                retries=3,         # Handle transient failures
                retry_backoff_ms=100,
                request_timeout_ms=30000,
                max_block_ms=5000
            )
            logger.info("Kafka producer initialized successfully")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _generate_device_data(self, device_id: str, device_type: str) -> Dict:
        """Generate realistic IoT device data with various sensor readings"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        base_data = {
            'device_id': device_id,
            'device_type': device_type,
            'timestamp': timestamp,
            'location': {
                'latitude': round(random.uniform(32.7767, 33.7767), 6),
                'longitude': round(random.uniform(-97.7963, -96.7963), 6)
            }
        }
        
        # Device-specific sensor data
        if device_type == 'thermostat':
            base_data.update({
                'temperature': round(random.uniform(65, 85), 1),
                'humidity': round(random.uniform(30, 70), 1),
                'energy_consumption': round(random.uniform(0.5, 3.0), 2),
                'status': random.choice(['heating', 'cooling', 'idle'])
            })
        elif device_type == 'security_camera':
            base_data.update({
                'motion_detected': random.choice([True, False]),
                'image_quality': round(random.uniform(0.7, 1.0), 2),
                'storage_usage': round(random.uniform(0.1, 0.9), 2),
                'battery_level': round(random.uniform(20, 100), 1)
            })
        elif device_type == 'smart_lock':
            base_data.update({
                'lock_status': random.choice(['locked', 'unlocked']),
                'battery_level': round(random.uniform(10, 100), 1),
                'access_attempts': random.randint(0, 5),
                'last_access': timestamp if random.random() > 0.7 else None
            })
        elif device_type == 'motion_sensor':
            base_data.update({
                'motion_detected': random.choice([True, False]),
                'sensitivity': round(random.uniform(0.5, 1.0), 2),
                'battery_level': round(random.uniform(15, 100), 1),
                'signal_strength': round(random.uniform(-80, -30), 1)
            })
        elif device_type == 'air_quality':
            base_data.update({
                'pm2_5': round(random.uniform(0, 100), 1),
                'pm10': round(random.uniform(0, 150), 1),
                'co2': round(random.uniform(300, 1000), 1),
                'temperature': round(random.uniform(60, 90), 1),
                'humidity': round(random.uniform(20, 80), 1)
            })
        
        # Add anomaly indicators (5% chance of anomaly)
        if random.random() < 0.05:
            base_data['anomaly_detected'] = True
            base_data['anomaly_type'] = random.choice(['sensor_failure', 'unusual_pattern', 'data_drift'])
        else:
            base_data['anomaly_detected'] = False
        
        return base_data
    
    def send_batch(self, batch_size: int = 100) -> int:
        """Send a batch of device data events"""
        if not self.producer:
            self._create_producer()
        
        sent_count = 0
        try:
            for _ in range(batch_size):
                device_id = random.choice(self.device_ids)
                device_type = random.choice(self.device_types)
                data = self._generate_device_data(device_id, device_type)
                
                # Use device_id as key for partitioning
                future = self.producer.send(
                    self.topic,
                    key=device_id,
                    value=data
                )
                
                # Add callback for monitoring
                future.add_callback(self._on_send_success)
                future.add_errback(self._on_send_error)
                
                sent_count += 1
            
            # Flush to ensure all messages are sent
            self.producer.flush()
            logger.info(f"Successfully sent {sent_count} messages to topic {self.topic}")
            
        except KafkaError as e:
            logger.error(f"Error sending batch: {e}")
            raise
        
        return sent_count
    
    def _on_send_success(self, record_metadata):
        """Callback for successful message delivery"""
        logger.debug(f"Message sent to partition {record_metadata.partition} at offset {record_metadata.offset}")
    
    def _on_send_error(self, exception):
        """Callback for failed message delivery"""
        logger.error(f"Failed to send message: {exception}")
    
    def start_streaming(self, duration_minutes: int = 60, batch_size: int = 100, interval_seconds: float = 1.0):
        """Start continuous data streaming for specified duration"""
        logger.info(f"Starting data streaming for {duration_minutes} minutes")
        start_time = time.time()
        total_sent = 0
        
        try:
            while time.time() - start_time < duration_minutes * 60:
                batch_sent = self.send_batch(batch_size)
                total_sent += batch_sent
                
                # Log progress every 1000 messages
                if total_sent % 1000 == 0:
                    logger.info(f"Total messages sent: {total_sent}")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Streaming interrupted by user")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise
        finally:
            if self.producer:
                self.producer.close()
                logger.info(f"Streaming completed. Total messages sent: {total_sent}")
    
    def close(self):
        """Close the producer connection"""
        if self.producer:
            self.producer.close()
            logger.info("Producer connection closed")

if __name__ == "__main__":
    # Example usage
    producer = IoTDeviceDataProducer()
    
    try:
        # Start streaming for 10 minutes with 50 messages per batch
        producer.start_streaming(duration_minutes=10, batch_size=50, interval_seconds=0.5)
    except KeyboardInterrupt:
        logger.info("Stopping producer...")
    finally:
        producer.close()
