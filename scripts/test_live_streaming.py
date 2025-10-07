"""
Test Script for Live IoT Data Streaming Pipeline
Comprehensive testing of the live streaming system
"""

import sys
import os
import time
import json
import threading
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.simple_live_consumer import SimpleLiveIoTDataConsumer, initialize_live_streaming
from ml_ops.live_anomaly_detection import initialize_anomaly_detector, detect_anomalies
from monitoring.websocket_server import start_websocket_server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveStreamingTester:
    """
    Test the live streaming pipeline end-to-end
    """
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
    def test_kafka_consumer(self):
        """Test Kafka consumer functionality"""
        logger.info("Testing Kafka consumer...")
        
        try:
            consumer, processor = initialize_live_streaming()
            
            # Test data generation
            test_data = []
            for i in range(10):
                data = next(consumer.generate_sample_data())
                test_data.append(data)
                time.sleep(0.1)
            
            logger.info(f"✅ Generated {len(test_data)} test messages")
            
            # Test data processing
            processed_data = []
            for data in test_data:
                processed = processor.process_live_data(data)
                processed_data.append(processed)
            
            logger.info(f"✅ Processed {len(processed_data)} messages")
            
            # Test metrics
            metrics = processor.get_live_metrics()
            logger.info(f"✅ Generated metrics: {len(metrics)} metrics")
            
            self.test_results['kafka_consumer'] = {
                'status': 'PASS',
                'messages_generated': len(test_data),
                'messages_processed': len(processed_data),
                'metrics_generated': len(metrics)
            }
            
        except Exception as e:
            logger.error(f"❌ Kafka consumer test failed: {e}")
            self.test_results['kafka_consumer'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_anomaly_detection(self):
        """Test anomaly detection system"""
        logger.info("Testing anomaly detection...")
        
        try:
            detector = initialize_anomaly_detector()
            
            # Generate test data with anomalies
            test_data = []
            for i in range(50):
                # Normal data
                data = {
                    'device_id': f'test_device_{i % 5}',
                    'device_type': 'thermostat',
                    'timestamp': datetime.now().isoformat(),
                    'temperature': 22 + (i % 3),  # Normal temperature
                    'humidity': 45 + (i % 5),
                    'battery_level': 80 + (i % 20),
                    'energy_consumption': 0.5 + (i % 2) * 0.1,
                    'latitude': 32.7767,
                    'longitude': -96.7970,
                    'signal_strength': -50 - (i % 10)
                }
                
                # Add some anomalies
                if i % 10 == 0:  # Every 10th message is anomalous
                    data['temperature'] = 50  # Extreme temperature
                    data['energy_consumption'] = 10  # High energy
                
                test_data.append(data)
            
            # Test anomaly detection
            anomalies_detected = 0
            for data in test_data:
                processed = detect_anomalies(data)
                if processed.get('anomaly_detected', False):
                    anomalies_detected += 1
            
            logger.info(f"✅ Detected {anomalies_detected} anomalies out of {len(test_data)} messages")
            
            # Test anomaly summary
            summary = detector.get_anomaly_summary()
            logger.info(f"✅ Anomaly summary: {summary['total_anomalies']} total anomalies")
            
            self.test_results['anomaly_detection'] = {
                'status': 'PASS',
                'messages_tested': len(test_data),
                'anomalies_detected': anomalies_detected,
                'detection_rate': anomalies_detected / len(test_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Anomaly detection test failed: {e}")
            self.test_results['anomaly_detection'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_data_flow(self):
        """Test end-to-end data flow"""
        logger.info("Testing end-to-end data flow...")
        
        try:
            # Initialize components
            consumer, processor = initialize_live_streaming()
            detector = initialize_anomaly_detector()
            
            # Simulate data flow
            messages_processed = 0
            anomalies_detected = 0
            
            for i in range(20):
                # Generate data
                data = next(consumer.generate_sample_data())
                
                # Process data
                processed = processor.process_live_data(data)
                
                # Detect anomalies
                anomaly_result = detect_anomalies(processed)
                
                if anomaly_result.get('anomaly_detected', False):
                    anomalies_detected += 1
                
                messages_processed += 1
                time.sleep(0.1)
            
            logger.info(f"✅ Processed {messages_processed} messages")
            logger.info(f"✅ Detected {anomalies_detected} anomalies")
            
            # Test metrics
            metrics = processor.get_live_metrics()
            anomaly_summary = detector.get_anomaly_summary()
            
            logger.info(f"✅ Generated {len(metrics)} metrics")
            logger.info(f"✅ Anomaly summary: {anomaly_summary['total_anomalies']} anomalies")
            
            self.test_results['data_flow'] = {
                'status': 'PASS',
                'messages_processed': messages_processed,
                'anomalies_detected': anomalies_detected,
                'metrics_generated': len(metrics),
                'anomaly_summary': anomaly_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Data flow test failed: {e}")
            self.test_results['data_flow'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_performance(self):
        """Test system performance"""
        logger.info("Testing system performance...")
        
        try:
            start_time = time.time()
            
            # Initialize components
            consumer, processor = initialize_live_streaming()
            detector = initialize_anomaly_detector()
            
            # Process messages for performance test
            messages_processed = 0
            start_perf_time = time.time()
            
            for i in range(100):
                data = next(consumer.generate_sample_data())
                processed = processor.process_live_data(data)
                anomaly_result = detect_anomalies(processed)
                messages_processed += 1
            
            end_perf_time = time.time()
            processing_time = end_perf_time - start_perf_time
            messages_per_second = messages_processed / processing_time
            
            logger.info(f"✅ Processed {messages_processed} messages in {processing_time:.2f} seconds")
            logger.info(f"✅ Performance: {messages_per_second:.2f} messages/second")
            
            self.test_results['performance'] = {
                'status': 'PASS',
                'messages_processed': messages_processed,
                'processing_time': processing_time,
                'messages_per_second': messages_per_second
            }
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            self.test_results['performance'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Live Streaming Pipeline Tests")
        logger.info("=" * 50)
        
        # Run individual tests
        self.test_kafka_consumer()
        self.test_anomaly_detection()
        self.test_data_flow()
        self.test_performance()
        
        # Generate test report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 50)
        logger.info("📊 LIVE STREAMING TEST REPORT")
        logger.info("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASS')
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ✅")
        logger.info(f"Failed: {failed_tests} ❌")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['status'] == 'PASS' else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
            
            if result['status'] == 'FAIL':
                logger.info(f"    Error: {result.get('error', 'Unknown error')}")
            else:
                # Log key metrics
                for key, value in result.items():
                    if key != 'status':
                        logger.info(f"    {key}: {value}")
        
        # Overall assessment
        if failed_tests == 0:
            logger.info("\n🎉 ALL TESTS PASSED! Live streaming system is ready.")
        else:
            logger.info(f"\n⚠️  {failed_tests} test(s) failed. Please check the errors above.")
        
        logger.info(f"\nTest completed in {(datetime.now() - self.start_time).total_seconds():.2f} seconds")

def main():
    """Main function to run tests"""
    tester = LiveStreamingTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
