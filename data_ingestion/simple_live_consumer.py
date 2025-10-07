"""
Simple Live Consumer with Proper Fallback Mechanism
Handles real-time data consumption with automatic fallback to sample data
"""

import json
import time
import logging
from datetime import datetime, timedelta
from threading import Thread, Event
import pandas as pd
import random

logger = logging.getLogger(__name__)

class SimpleLiveIoTDataConsumer:
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'iot-device-data'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer = None
        self.running = False
        self.data_buffer = []
        self.buffer_lock = Event()
        self.thread = None
        self.message_count = 0
        self.last_update_time = datetime.now()
        self.device_types = ['thermostat', 'security_camera', 'smart_lock', 'motion_sensor', 'air_quality']
        self.device_ids = [f"device_{i:04d}" for i in range(1, 1001)]
        self.initialize_consumer()

    def initialize_consumer(self):
        try:
            from kafka import KafkaConsumer
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='streamlit-consumer-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=1000
            )
            logger.info(f"Kafka consumer initialized for topic: {self.topic}")
            self.running = True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            self.consumer = None
            self.running = False
            logger.warning("Could not connect to Kafka. Using sample data generator.")

    def _consume_data(self):
        if not self.consumer:
            self._generate_sample_data_stream()
            return

        while self.running:
            try:
                for message in self.consumer:
                    if not self.running:
                        break
                    data = message.value
                    self.data_buffer.append(data)
                    self.message_count += 1
                    self.last_update_time = datetime.now()
                    self.buffer_lock.set()
            except Exception as e:
                logger.error(f"Error consuming from Kafka: {e}")
                self.running = False

    def _generate_sample_data_stream(self):
        while self.running:
            num_devices = random.randint(5, 20)
            for _ in range(num_devices):
                device_id = random.choice(self.device_ids)
                device_type = random.choice(self.device_types)
                timestamp = datetime.now().isoformat()
                temperature = round(random.uniform(18.0, 30.0), 2)
                humidity = round(random.uniform(30.0, 70.0), 2)
                battery_level = round(random.uniform(20.0, 100.0), 2)
                energy_consumption = round(random.uniform(0.5, 5.0), 2)
                latitude = round(random.uniform(34.0, 40.0), 4)
                longitude = round(random.uniform(-120.0, -70.0), 4)
                
                data = {
                    "device_id": device_id,
                    "device_type": device_type,
                    "timestamp": timestamp,
                    "temperature": temperature,
                    "humidity": humidity,
                    "battery_level": battery_level,
                    "energy_consumption": energy_consumption,
                    "latitude": latitude,
                    "longitude": longitude,
                    "status": random.choice(["active", "inactive", "alert"]),
                    "firmware_version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}",
                    "anomaly": random.choice([True, False, False, False, False])
                }
                self.data_buffer.append(data)
                self.message_count += 1
                self.last_update_time = datetime.now()
            self.buffer_lock.set()
            time.sleep(random.uniform(0.1, 0.5))

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.running = True
            self.thread = Thread(target=self._consume_data)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Live IoT data consumer started.")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        if self.consumer:
            self.consumer.close()
        logger.info("Live IoT data consumer stopped.")

    def get_latest_data(self):
        self.buffer_lock.clear()
        data = list(self.data_buffer)
        self.data_buffer.clear()
        return data

    def get_metrics(self):
        return {
            "message_count": self.message_count,
            "last_update_time": self.last_update_time.isoformat(),
            "is_kafka_connected": self.consumer is not None
        }

# Global instance
live_consumer = None

def initialize_live_streaming():
    global live_consumer
    if live_consumer is None:
        live_consumer = SimpleLiveIoTDataConsumer()
        live_consumer.start()
    return live_consumer

def get_live_data():
    if live_consumer:
        return live_consumer.get_latest_data()
    return []

def get_live_metrics():
    if live_consumer:
        return live_consumer.get_metrics()
    return {
        "message_count": 0,
        "last_update_time": datetime.now().isoformat(),
        "is_kafka_connected": False
    }
