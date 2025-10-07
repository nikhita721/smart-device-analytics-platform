"""
ML Ops Pipeline for IoT Device Analytics
Automated model training, validation, and deployment for predictive maintenance
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import xgboost as xgb
import joblib
import mlflow
import mlflow.sklearn
from datetime import datetime
import logging
import os
from typing import Dict, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTMLPipeline:
    """
    Comprehensive ML pipeline for IoT device analytics
    Handles model training, validation, deployment, and monitoring
    """
    
    def __init__(self, experiment_name: str = "iot-device-analytics"):
        self.experiment_name = experiment_name
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.metrics = {}
        
        # Initialize MLflow
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow experiment '{experiment_name}' initialized")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and engineer features for ML models"""
        logger.info("Preparing features for ML models...")
        
        df_processed = df.copy()
        
        # Handle missing values
        numeric_columns = df_processed.select_dtypes(include=[np.number]).columns
        df_processed[numeric_columns] = df_processed[numeric_columns].fillna(
            df_processed[numeric_columns].mean()
        )
        
        # Create time-based features
        df_processed['timestamp'] = pd.to_datetime(df_processed['timestamp'])
        df_processed['hour'] = df_processed['timestamp'].dt.hour
        df_processed['day_of_week'] = df_processed['timestamp'].dt.dayofweek
        df_processed['is_weekend'] = df_processed['day_of_week'].isin([5, 6])
        
        # Create device interaction features
        df_processed['temp_humidity_ratio'] = df_processed['temperature'] / (df_processed['humidity'] + 1)
        df_processed['energy_efficiency'] = df_processed['energy_consumption'] / (df_processed['temperature'] + 1)
        
        # Create rolling statistics
        df_processed = df_processed.sort_values(['device_id', 'timestamp'])
        df_processed['temp_rolling_mean'] = df_processed.groupby('device_id')['temperature'].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean()
        )
        df_processed['battery_rolling_std'] = df_processed.groupby('device_id')['battery_level'].transform(
            lambda x: x.rolling(window=10, min_periods=1).std()
        )
        
        # Create lag features
        df_processed['temp_lag_1'] = df_processed.groupby('device_id')['temperature'].shift(1)
        df_processed['temp_lag_2'] = df_processed.groupby('device_id')['temperature'].shift(2)
        df_processed['battery_lag_1'] = df_processed.groupby('device_id')['battery_level'].shift(1)
        
        # Create change features
        df_processed['temp_change'] = df_processed['temperature'] - df_processed['temp_lag_1']
        df_processed['battery_change'] = df_processed['battery_level'] - df_processed['battery_lag_1']
        
        # Handle categorical variables
        categorical_columns = ['device_type', 'status', 'lock_status']
        for col in categorical_columns:
            if col in df_processed.columns:
                le = LabelEncoder()
                df_processed[f'{col}_encoded'] = le.fit_transform(df_processed[col].astype(str))
                self.encoders[col] = le
        
        logger.info("Feature engineering completed")
        return df_processed
    
    def train_anomaly_detection_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train anomaly detection model using isolation forest and autoencoders"""
        logger.info("Training anomaly detection model...")
        
        with mlflow.start_run(run_name="anomaly_detection"):
            # Prepare features
            feature_columns = [
                'temperature', 'humidity', 'battery_level', 'energy_consumption',
                'hour', 'day_of_week', 'temp_rolling_mean', 'battery_rolling_std',
                'temp_change', 'battery_change'
            ]
            
            # Filter available columns
            available_features = [col for col in feature_columns if col in df.columns]
            X = df[available_features].fillna(0)
            
            # Create target variable (1 for anomaly, 0 for normal)
            y = df['anomaly_detected'].astype(int)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers['anomaly'] = scaler
            
            # Train Random Forest for anomaly detection
            rf_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            
            rf_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = rf_model.predict(X_test_scaled)
            y_pred_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
            
            # Log metrics
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
            
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("precision", precision)
            mlflow.log_metric("recall", recall)
            mlflow.log_metric("f1_score", f1)
            mlflow.log_metric("roc_auc", roc_auc)
            
            # Log model
            mlflow.sklearn.log_model(rf_model, "anomaly_detection_model")
            
            self.models['anomaly_detection'] = rf_model
            self.metrics['anomaly_detection'] = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'roc_auc': roc_auc
            }
            
            logger.info(f"Anomaly detection model trained - F1 Score: {f1:.3f}")
            return self.metrics['anomaly_detection']
    
    def train_predictive_maintenance_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train predictive maintenance model for device failure prediction"""
        logger.info("Training predictive maintenance model...")
        
        with mlflow.start_run(run_name="predictive_maintenance"):
            # Create maintenance target (device needs maintenance if battery < 20% or anomaly detected)
            df['needs_maintenance'] = (
                (df['battery_level'] < 20) | 
                (df['anomaly_detected'] == True) |
                (df['energy_consumption'] > df['energy_consumption'].quantile(0.95))
            
        # Prepare features
        feature_columns = [
            'temperature', 'humidity', 'battery_level', 'energy_consumption',
            'hour', 'day_of_week', 'temp_rolling_mean', 'battery_rolling_std',
            'temp_change', 'battery_change', 'device_type_encoded'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0)
        y = df['needs_maintenance'].astype(int)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers['maintenance'] = scaler
        
        # Train XGBoost model
        xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss'
        )
        
        xgb_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            early_stopping_rounds=20,
            verbose=False
        )
        
        # Evaluate model
        y_pred = xgb_model.predict(X_test_scaled)
        y_pred_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        # Log metrics
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("roc_auc", roc_auc)
        
        # Log model
        mlflow.sklearn.log_model(xgb_model, "maintenance_prediction_model")
        
        self.models['maintenance_prediction'] = xgb_model
        self.metrics['maintenance_prediction'] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': roc_auc
        }
        
        logger.info(f"Predictive maintenance model trained - F1 Score: {f1:.3f}")
        return self.metrics['maintenance_prediction']
    
    def train_energy_consumption_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train energy consumption prediction model"""
        logger.info("Training energy consumption prediction model...")
        
        with mlflow.start_run(run_name="energy_consumption"):
            # Prepare features
            feature_columns = [
                'temperature', 'humidity', 'hour', 'day_of_week', 'is_weekend',
                'temp_rolling_mean', 'battery_rolling_std', 'device_type_encoded'
            ]
            
            available_features = [col for col in feature_columns if col in df.columns]
            X = df[available_features].fillna(0)
            y = df['energy_consumption']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers['energy'] = scaler
            
            # Train Gradient Boosting model
            gb_model = GradientBoostingRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            
            gb_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = gb_model.predict(X_test_scaled)
            
            # Calculate metrics
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            # Log metrics
            mlflow.log_metric("mse", mse)
            mlflow.log_metric("rmse", rmse)
            mlflow.log_metric("r2_score", r2)
            
            # Log model
            mlflow.sklearn.log_model(gb_model, "energy_consumption_model")
            
            self.models['energy_consumption'] = gb_model
            self.metrics['energy_consumption'] = {
                'mse': mse,
                'rmse': rmse,
                'r2_score': r2
            }
            
            logger.info(f"Energy consumption model trained - R² Score: {r2:.3f}")
            return self.metrics['energy_consumption']
    
    def train_all_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train all ML models in the pipeline"""
        logger.info("Starting comprehensive ML model training...")
        
        # Prepare features
        df_processed = self.prepare_features(df)
        
        # Train all models
        anomaly_metrics = self.train_anomaly_detection_model(df_processed)
        maintenance_metrics = self.train_predictive_maintenance_model(df_processed)
        energy_metrics = self.train_energy_consumption_model(df_processed)
        
        # Save models
        self.save_models()
        
        # Return comprehensive metrics
        all_metrics = {
            'anomaly_detection': anomaly_metrics,
            'maintenance_prediction': maintenance_metrics,
            'energy_consumption': energy_metrics
        }
        
        logger.info("All ML models trained successfully")
        return all_metrics
    
    def save_models(self, model_dir: str = "models"):
        """Save trained models and preprocessors"""
        os.makedirs(model_dir, exist_ok=True)
        
        for model_name, model in self.models.items():
            model_path = os.path.join(model_dir, f"{model_name}.joblib")
            joblib.dump(model, model_path)
            logger.info(f"Model saved: {model_path}")
        
        for scaler_name, scaler in self.scalers.items():
            scaler_path = os.path.join(model_dir, f"{scaler_name}_scaler.joblib")
            joblib.dump(scaler, scaler_path)
            logger.info(f"Scaler saved: {scaler_path}")
        
        for encoder_name, encoder in self.encoders.items():
            encoder_path = os.path.join(model_dir, f"{encoder_name}_encoder.joblib")
            joblib.dump(encoder, encoder_path)
            logger.info(f"Encoder saved: {encoder_path}")
    
    def load_models(self, model_dir: str = "models"):
        """Load pre-trained models and preprocessors"""
        for model_name in ['anomaly_detection', 'maintenance_prediction', 'energy_consumption']:
            model_path = os.path.join(model_dir, f"{model_name}.joblib")
            if os.path.exists(model_path):
                self.models[model_name] = joblib.load(model_path)
                logger.info(f"Model loaded: {model_name}")
        
        for scaler_name in ['anomaly', 'maintenance', 'energy']:
            scaler_path = os.path.join(model_dir, f"{scaler_name}_scaler.joblib")
            if os.path.exists(scaler_path):
                self.scalers[scaler_name] = joblib.load(scaler_path)
                logger.info(f"Scaler loaded: {scaler_name}")
    
    def predict_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict anomalies for new data"""
        if 'anomaly_detection' not in self.models:
            raise ValueError("Anomaly detection model not trained or loaded")
        
        # Prepare features
        feature_columns = [
            'temperature', 'humidity', 'battery_level', 'energy_consumption',
            'hour', 'day_of_week', 'temp_rolling_mean', 'battery_rolling_std',
            'temp_change', 'battery_change'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0)
        
        # Scale features
        X_scaled = self.scalers['anomaly'].transform(X)
        
        # Make predictions
        predictions = self.models['anomaly_detection'].predict(X_scaled)
        probabilities = self.models['anomaly_detection'].predict_proba(X_scaled)[:, 1]
        
        # Add predictions to dataframe
        df_result = df.copy()
        df_result['predicted_anomaly'] = predictions
        df_result['anomaly_probability'] = probabilities
        
        return df_result
    
    def predict_maintenance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict maintenance needs for new data"""
        if 'maintenance_prediction' not in self.models:
            raise ValueError("Maintenance prediction model not trained or loaded")
        
        # Prepare features
        feature_columns = [
            'temperature', 'humidity', 'battery_level', 'energy_consumption',
            'hour', 'day_of_week', 'temp_rolling_mean', 'battery_rolling_std',
            'temp_change', 'battery_change', 'device_type_encoded'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0)
        
        # Scale features
        X_scaled = self.scalers['maintenance'].transform(X)
        
        # Make predictions
        predictions = self.models['maintenance_prediction'].predict(X_scaled)
        probabilities = self.models['maintenance_prediction'].predict_proba(X_scaled)[:, 1]
        
        # Add predictions to dataframe
        df_result = df.copy()
        df_result['predicted_maintenance'] = predictions
        df_result['maintenance_probability'] = probabilities
        
        return df_result
    
    def predict_energy_consumption(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict energy consumption for new data"""
        if 'energy_consumption' not in self.models:
            raise ValueError("Energy consumption model not trained or loaded")
        
        # Prepare features
        feature_columns = [
            'temperature', 'humidity', 'hour', 'day_of_week', 'is_weekend',
            'temp_rolling_mean', 'battery_rolling_std', 'device_type_encoded'
        ]
        
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0)
        
        # Scale features
        X_scaled = self.scalers['energy'].transform(X)
        
        # Make predictions
        predictions = self.models['energy_consumption'].predict(X_scaled)
        
        # Add predictions to dataframe
        df_result = df.copy()
        df_result['predicted_energy_consumption'] = predictions
        
        return df_result

if __name__ == "__main__":
    # Example usage
    ml_pipeline = IoTMLPipeline()
    
    # Load sample data (replace with actual data loading)
    # df = pd.read_csv("iot_data.csv")
    
    # Train all models
    # metrics = ml_pipeline.train_all_models(df)
    # print("Training completed with metrics:", metrics)
    
    logger.info("ML pipeline initialized successfully")
