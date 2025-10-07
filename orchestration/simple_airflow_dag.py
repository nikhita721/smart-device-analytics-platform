"""
Simple Apache Airflow DAG for IoT Data Pipeline
Simplified version without complex provider dependencies
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'iot-data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'iot_data_pipeline',
    default_args=default_args,
    description='Comprehensive IoT Data Processing Pipeline',
    schedule='@hourly',
    max_active_runs=1,
    catchup=False,
    tags=['iot', 'data-engineering', 'ml-ops']
)

def check_data_quality(**context):
    """Check data quality metrics"""
    logger.info("Starting data quality checks...")
    
    # Simulate data quality checks
    quality_metrics = {
        'total_records': 100000,
        'null_values': 50,
        'duplicate_records': 25,
        'anomaly_rate': 2.5
    }
    
    # Log quality metrics
    for metric, value in quality_metrics.items():
        logger.info(f"{metric}: {value}")
    
    # Push metrics to XCom for downstream tasks
    context['task_instance'].xcom_push(key='quality_metrics', value=quality_metrics)
    
    return quality_metrics

def process_iot_data(**context):
    """Process IoT data using PySpark"""
    logger.info("Starting IoT data processing...")
    
    try:
        # Simulate data processing
        # In production, this would read from Kafka/S3
        logger.info("Processing IoT device data...")
        
        # Simulate processing metrics
        processing_metrics = {
            'records_processed': 100000,
            'processing_time_seconds': 120,
            'anomalies_detected': 150,
            'maintenance_alerts': 25
        }
        
        # Log processing results
        for metric, value in processing_metrics.items():
            logger.info(f"{metric}: {value}")
        
        # Push metrics to XCom
        context['task_instance'].xcom_push(key='processing_metrics', value=processing_metrics)
        
        return processing_metrics
        
    except Exception as e:
        logger.error(f"Error in data processing: {str(e)}")
        raise

def train_ml_models(**context):
    """Train ML models for anomaly detection"""
    logger.info("Starting ML model training...")
    
    try:
        # Simulate ML model training
        logger.info("Training anomaly detection models...")
        
        # Simulate training metrics
        training_metrics = {
            'model_accuracy': 0.95,
            'training_time_minutes': 30,
            'features_used': 15,
            'cross_validation_score': 0.92
        }
        
        # Log training results
        for metric, value in training_metrics.items():
            logger.info(f"{metric}: {value}")
        
        # Push metrics to XCom
        context['task_instance'].xcom_push(key='training_metrics', value=training_metrics)
        
        return training_metrics
        
    except Exception as e:
        logger.error(f"Error in model training: {str(e)}")
        raise

def load_to_warehouse(**context):
    """Load processed data to data warehouse"""
    logger.info("Starting data warehouse load...")
    
    try:
        # Simulate data warehouse load
        logger.info("Loading data to Redshift...")
        
        # Simulate load metrics
        load_metrics = {
            'records_loaded': 100000,
            'load_time_seconds': 60,
            'success_rate': 1.0
        }
        
        # Log load results
        for metric, value in load_metrics.items():
            logger.info(f"{metric}: {value}")
        
        # Push metrics to XCom
        context['task_instance'].xcom_push(key='load_metrics', value=load_metrics)
        
        return load_metrics
        
    except Exception as e:
        logger.error(f"Error in data warehouse load: {str(e)}")
        raise

def send_notifications(**context):
    """Send notifications about pipeline completion"""
    logger.info("Sending pipeline completion notifications...")
    
    # Get metrics from previous tasks
    quality_metrics = context['task_instance'].xcom_pull(task_ids='data_quality_check')
    processing_metrics = context['task_instance'].xcom_pull(task_ids='process_iot_data')
    training_metrics = context['task_instance'].xcom_pull(task_ids='train_ml_models')
    load_metrics = context['task_instance'].xcom_pull(task_ids='load_to_warehouse')
    
    # Create summary
    summary = {
        'pipeline_status': 'SUCCESS',
        'total_processing_time': '4.5 hours',
        'records_processed': processing_metrics.get('records_processed', 0),
        'anomalies_detected': processing_metrics.get('anomalies_detected', 0),
        'model_accuracy': training_metrics.get('model_accuracy', 0),
        'data_quality_score': 1.0 - (quality_metrics.get('anomaly_rate', 0) / 100)
    }
    
    # Log summary
    logger.info("=== PIPELINE SUMMARY ===")
    for key, value in summary.items():
        logger.info(f"{key}: {value}")
    
    return summary

# Define tasks
start_task = EmptyOperator(
    task_id='start_pipeline',
    dag=dag
)

data_quality_check = PythonOperator(
    task_id='data_quality_check',
    python_callable=check_data_quality,
    dag=dag
)

process_iot_data = PythonOperator(
    task_id='process_iot_data',
    python_callable=process_iot_data,
    dag=dag
)

train_ml_models = PythonOperator(
    task_id='train_ml_models',
    python_callable=train_ml_models,
    dag=dag
)

load_to_warehouse = PythonOperator(
    task_id='load_to_warehouse',
    python_callable=load_to_warehouse,
    dag=dag
)

send_notifications = PythonOperator(
    task_id='send_notifications',
    python_callable=send_notifications,
    dag=dag
)

end_task = EmptyOperator(
    task_id='end_pipeline',
    dag=dag
)

# Define task dependencies
start_task >> data_quality_check >> process_iot_data >> train_ml_models >> load_to_warehouse >> send_notifications >> end_task
