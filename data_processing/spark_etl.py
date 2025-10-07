"""
Advanced PySpark ETL Pipeline for IoT Device Data
Implements optimized data processing with window functions, CTEs, and partitioning
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window
import logging
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTDataETLProcessor:
    """
    High-performance PySpark ETL processor for IoT device data
    Handles complex transformations, aggregations, and data quality checks
    """
    
    def __init__(self, app_name: str = "IoT-Data-ETL"):
        self.spark = None
        self.app_name = app_name
        self._initialize_spark()
    
    def _initialize_spark(self):
        """Initialize Spark session with optimized configuration"""
        try:
            self.spark = SparkSession.builder \
                .appName(self.app_name) \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.sql.adaptive.skewJoin.enabled", "true") \
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
                .config("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB") \
                .getOrCreate()
            
            # Set log level to reduce noise
            self.spark.sparkContext.setLogLevel("WARN")
            logger.info("Spark session initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Spark session: {e}")
            raise
    
    def read_kafka_stream(self, kafka_bootstrap_servers: str, topic: str):
        """Read streaming data from Kafka topic"""
        try:
            df = self.spark \
                .readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
                .option("subscribe", topic) \
                .option("startingOffsets", "latest") \
                .option("maxOffsetsPerTrigger", 10000) \
                .load()
            
            # Parse JSON data from Kafka
            schema = self._get_iot_data_schema()
            df_parsed = df.select(
                col("key").cast("string").alias("device_id"),
                from_json(col("value").cast("string"), schema).alias("data"),
                col("timestamp").alias("kafka_timestamp")
            ).select("device_id", "data.*", "kafka_timestamp")
            
            logger.info("Kafka stream reader initialized")
            return df_parsed
            
        except Exception as e:
            logger.error(f"Error reading from Kafka: {e}")
            raise
    
    def _get_iot_data_schema(self):
        """Define schema for IoT device data"""
        return StructType([
            StructField("device_id", StringType(), True),
            StructField("device_type", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("location", StructType([
                StructField("latitude", DoubleType(), True),
                StructField("longitude", DoubleType(), True)
            ]), True),
            StructField("temperature", DoubleType(), True),
            StructField("humidity", DoubleType(), True),
            StructField("energy_consumption", DoubleType(), True),
            StructField("status", StringType(), True),
            StructField("motion_detected", BooleanType(), True),
            StructField("image_quality", DoubleType(), True),
            StructField("storage_usage", DoubleType(), True),
            StructField("battery_level", DoubleType(), True),
            StructField("lock_status", StringType(), True),
            StructField("access_attempts", IntegerType(), True),
            StructField("last_access", StringType(), True),
            StructField("sensitivity", DoubleType(), True),
            StructField("signal_strength", DoubleType(), True),
            StructField("pm2_5", DoubleType(), True),
            StructField("pm10", DoubleType(), True),
            StructField("co2", DoubleType(), True),
            StructField("anomaly_detected", BooleanType(), True),
            StructField("anomaly_type", StringType(), True)
        ])
    
    def apply_data_quality_checks(self, df):
        """Apply comprehensive data quality checks and validation"""
        logger.info("Applying data quality checks...")
        
        # Remove null device_ids
        df_clean = df.filter(col("device_id").isNotNull())
        
        # Validate timestamp format
        df_clean = df_clean.filter(
            col("timestamp").rlike(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        )
        
        # Validate numeric ranges
        df_clean = df_clean.filter(
            (col("temperature").between(-50, 150)) |
            col("temperature").isNull()
        )
        
        df_clean = df_clean.filter(
            (col("humidity").between(0, 100)) |
            col("humidity").isNull()
        )
        
        df_clean = df_clean.filter(
            (col("battery_level").between(0, 100)) |
            col("battery_level").isNull()
        )
        
        # Add data quality metrics
        df_with_quality = df_clean.withColumn(
            "data_quality_score",
            when(col("anomaly_detected") == True, 0.5)
            .when(col("battery_level") < 20, 0.7)
            .when(col("signal_strength") < -70, 0.8)
            .otherwise(1.0)
        )
        
        logger.info("Data quality checks completed")
        return df_with_quality
    
    def create_time_series_features(self, df):
        """Create advanced time series features using window functions"""
        logger.info("Creating time series features...")
        
        # Define window specifications
        device_window = Window.partitionBy("device_id").orderBy("timestamp")
        device_time_window = Window.partitionBy("device_id").orderBy("timestamp").rowsBetween(-4, 0)
        
        # Add time-based features
        df_with_features = df.withColumn(
            "hour_of_day", hour(to_timestamp(col("timestamp")))
        ).withColumn(
            "day_of_week", dayofweek(to_timestamp(col("timestamp")))
        ).withColumn(
            "is_weekend", when(col("day_of_week").isin([1, 7]), True).otherwise(False)
        )
        
        # Calculate rolling averages and trends
        df_with_features = df_with_features.withColumn(
            "temp_rolling_avg",
            avg("temperature").over(device_time_window)
        ).withColumn(
            "humidity_rolling_avg", 
            avg("humidity").over(device_time_window)
        ).withColumn(
            "battery_trend",
            (col("battery_level") - lag("battery_level", 1).over(device_window))
        )
        
        # Add lag features for anomaly detection
        df_with_features = df_with_features.withColumn(
            "temp_lag_1", lag("temperature", 1).over(device_window)
        ).withColumn(
            "temp_lag_2", lag("temperature", 2).over(device_window)
        ).withColumn(
            "temp_change_rate",
            (col("temperature") - col("temp_lag_1")) / 
            when(col("temp_lag_1") != 0, col("temp_lag_1")).otherwise(1)
        )
        
        # Calculate device activity patterns
        df_with_features = df_with_features.withColumn(
            "activity_count",
            count("*").over(device_window.rowsBetween(-23, 0))  # Last 24 records
        ).withColumn(
            "anomaly_count",
            sum(when(col("anomaly_detected") == True, 1).otherwise(0))
            .over(device_window.rowsBetween(-23, 0))
        )
        
        logger.info("Time series features created successfully")
        return df_with_features
    
    def create_aggregated_metrics(self, df):
        """Create business metrics and KPIs using advanced SQL operations"""
        logger.info("Creating aggregated metrics...")
        
        # Device-level aggregations
        device_metrics = df.groupBy("device_id", "device_type") \
            .agg(
                count("*").alias("total_readings"),
                avg("temperature").alias("avg_temperature"),
                stddev("temperature").alias("temp_volatility"),
                avg("battery_level").alias("avg_battery"),
                min("battery_level").alias("min_battery"),
                sum(when(col("anomaly_detected") == True, 1).otherwise(0)).alias("anomaly_count"),
                max("timestamp").alias("last_seen"),
                countDistinct("hour_of_day").alias("active_hours")
            )
        
        # Location-based aggregations
        location_metrics = df.groupBy(
            round(col("location.latitude"), 2).alias("lat_rounded"),
            round(col("location.longitude"), 2).alias("lon_rounded")
        ).agg(
            count("*").alias("device_density"),
            avg("temperature").alias("area_avg_temp"),
            avg("humidity").alias("area_avg_humidity"),
            sum(when(col("motion_detected") == True, 1).otherwise(0)).alias("motion_events")
        )
        
        # Time-based aggregations
        hourly_metrics = df.groupBy(
            "device_type",
            hour(to_timestamp(col("timestamp"))).alias("hour")
        ).agg(
            count("*").alias("readings_count"),
            avg("temperature").alias("avg_temp"),
            sum(when(col("anomaly_detected") == True, 1).otherwise(0)).alias("anomalies")
        )
        
        logger.info("Aggregated metrics created successfully")
        return device_metrics, location_metrics, hourly_metrics
    
    def detect_anomalies(self, df):
        """Advanced anomaly detection using statistical methods"""
        logger.info("Detecting anomalies...")
        
        # Statistical anomaly detection
        device_window = Window.partitionBy("device_id")
        
        df_with_anomalies = df.withColumn(
            "temp_zscore",
            (col("temperature") - avg("temperature").over(device_window)) / 
            stddev("temperature").over(device_window)
        ).withColumn(
            "battery_zscore",
            (col("battery_level") - avg("battery_level").over(device_window)) / 
            stddev("battery_level").over(device_window)
        ).withColumn(
            "statistical_anomaly",
            (abs(col("temp_zscore")) > 3) | (abs(col("battery_zscore")) > 3)
        )
        
        # Pattern-based anomaly detection
        df_with_anomalies = df_with_anomalies.withColumn(
            "pattern_anomaly",
            (col("temperature") > 100) |  # Unrealistic temperature
            (col("humidity") > 100) |     # Unrealistic humidity
            (col("battery_level") < 0) |  # Negative battery
            (col("signal_strength") > 0)  # Invalid signal strength
        )
        
        # Combined anomaly score
        df_with_anomalies = df_with_anomalies.withColumn(
            "anomaly_score",
            when(col("statistical_anomaly") & col("pattern_anomaly"), 1.0)
            .when(col("statistical_anomaly") | col("pattern_anomaly"), 0.7)
            .otherwise(0.0)
        )
        
        logger.info("Anomaly detection completed")
        return df_with_anomalies
    
    def optimize_for_storage(self, df, partition_columns=None):
        """Optimize DataFrame for storage with partitioning and compression"""
        logger.info("Optimizing for storage...")
        
        if partition_columns:
            df_optimized = df.repartition(*partition_columns)
        else:
            # Default partitioning by device_type and date
            df_optimized = df.repartition(
                col("device_type"),
                date_format(to_timestamp(col("timestamp")), "yyyy-MM-dd").alias("date")
            )
        
        # Add storage optimization columns
        df_optimized = df_optimized.withColumn(
            "storage_date", date_format(to_timestamp(col("timestamp")), "yyyy-MM-dd")
        ).withColumn(
            "storage_hour", hour(to_timestamp(col("timestamp")))
        )
        
        logger.info("Storage optimization completed")
        return df_optimized
    
    def write_to_s3(self, df, s3_path: str, format_type: str = "parquet"):
        """Write DataFrame to S3 with optimized settings"""
        try:
            df.write \
                .format(format_type) \
                .mode("append") \
                .option("compression", "snappy") \
                .option("maxRecordsPerFile", 100000) \
                .partitionBy("device_type", "storage_date") \
                .save(s3_path)
            
            logger.info(f"Data successfully written to S3: {s3_path}")
            
        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            raise
    
    def write_to_redshift(self, df, redshift_table: str, s3_temp_path: str):
        """Write DataFrame to Redshift using S3 as staging area"""
        try:
            # First write to S3
            df.write \
                .format("parquet") \
                .mode("overwrite") \
                .option("compression", "snappy") \
                .save(s3_temp_path)
            
            # Then copy to Redshift
            df_redshift = self.spark.read.parquet(s3_temp_path)
            df_redshift.write \
                .format("jdbc") \
                .option("url", "jdbc:redshift://your-cluster.region.redshift.amazonaws.com:5439/database") \
                .option("dbtable", redshift_table) \
                .option("user", "your_username") \
                .option("password", "your_password") \
                .mode("append") \
                .save()
            
            logger.info(f"Data successfully written to Redshift table: {redshift_table}")
            
        except Exception as e:
            logger.error(f"Error writing to Redshift: {e}")
            raise
    
    def process_streaming_data(self, kafka_config: dict, s3_path: str):
        """Complete streaming ETL pipeline"""
        logger.info("Starting streaming ETL pipeline...")
        
        try:
            # Read from Kafka
            df_stream = self.read_kafka_stream(
                kafka_config["bootstrap_servers"],
                kafka_config["topic"]
            )
            
            # Apply transformations
            df_quality = self.apply_data_quality_checks(df_stream)
            df_features = self.create_time_series_features(df_quality)
            df_anomalies = self.detect_anomalies(df_features)
            df_optimized = self.optimize_for_storage(df_anomalies)
            
            # Write to S3
            query = df_optimized.writeStream \
                .format("parquet") \
                .option("path", s3_path) \
                .option("checkpointLocation", f"{s3_path}/checkpoints") \
                .trigger(processingTime="60 seconds") \
                .start()
            
            logger.info("Streaming ETL pipeline started successfully")
            return query
            
        except Exception as e:
            logger.error(f"Error in streaming pipeline: {e}")
            raise
    
    def close(self):
        """Close Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("Spark session closed")

if __name__ == "__main__":
    # Example usage
    etl_processor = IoTDataETLProcessor()
    
    try:
        # Process streaming data
        kafka_config = {
            "bootstrap_servers": "localhost:9092",
            "topic": "iot-device-data"
        }
        
        s3_path = "s3://your-bucket/iot-data/processed"
        query = etl_processor.process_streaming_data(kafka_config, s3_path)
        
        # Keep the stream running
        query.awaitTermination()
        
    except KeyboardInterrupt:
        logger.info("Stopping ETL pipeline...")
    finally:
        etl_processor.close()
